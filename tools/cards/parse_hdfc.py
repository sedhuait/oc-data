#!/usr/bin/env python3
"""Parse HDFC Bank's MITC fee table by COLUMN POSITION, not by regex.

pdftotext -layout preserves horizontal position, so the reliable way to read a
table is to find the header row, derive column boundaries from it, and slice
every following line at those offsets. Regex over the flattened text guesses
which number belongs to which column and gets it wrong the moment a cell is
merged — which in this document is often.

Rules kept deliberately strict:
  - a value is only used if it falls inside that column's slice
  - a merged or blank fee cell produces a `candidate`, never an inherited number
  - every record carries mitc_url and mitc_version so each number is traceable
"""
import json, os, re, glob, subprocess, hashlib, unicodedata, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
ISSUER, SLUG = "HDFC Bank", "hdfc-bank"
TODAY = datetime.date.today().isoformat()
MITC_URL = next(i["mitc"] for i in json.load(open(os.path.join(HERE, "mitc_sources.json")))["issuers"] if i["slug"] == SLUG)

def norm(s):
    s = unicodedata.normalize("NFKD", s or "").lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s)).strip()
def slugify(s): return re.sub(r"[^a-z0-9]+", "-", norm(s)).strip("-")
def mint(b, n): return "oc_" + hashlib.sha1(f"{norm(b)}|{norm(n)}|".encode()).hexdigest()[:12]

def rupees(s):
    if not s: return None
    s = s.replace("₹", " ").replace("Rs.", " ").replace("`", " ").strip()
    if re.fullmatch(r"free", s, re.I): return 0
    if re.fullmatch(r"n\.?a\.?", s, re.I): return None
    m = re.search(r"(\d[\d,]*(?:\.\d+)?)\s*(lakh|lac)?", s, re.I)
    if not m: return None
    v = float(m.group(1).replace(",", ""))
    if m.group(2) or re.search(r"lakh|lac", s, re.I): v = v * 100000 if v < 1000 else v
    return int(v)

def lines_of(pdf, first, last):
    out = subprocess.run(["pdftotext", "-layout", "-f", str(first), "-l", str(last), pdf, "-"],
                         capture_output=True, timeout=120)
    return out.stdout.decode("utf-8", "replace").split("\n")

VERSION = re.compile(r"Version\s+([\d.]+)\s+Dated\s+([A-Za-z]+-\d{4})", re.I)
NOISE = re.compile(r"fuel|surcharge|foreign|currency|transaction|membership|minimum spend|waiver|"
                   r"next year|table of|section|updated on|dear customer|version|goods and services|"
                   r"regional language|statement cycle|maximum|applicable|^wef|^#|lounge|charges|"
                   r"please|refer|cardmember|bank ltd|joining fee|annual|card variant|^\(|^\*", re.I)

def column_bounds(header):
    cols = [header.index("Card variant")]
    for kw in ("Joining", "Minimum", "Fuel", "Foreign"):
        j = header.find(kw)
        if j > cols[0]: cols.append(j)
    return sorted(set(cols))

def slice_row(line, cols):
    out = []
    for k, c in enumerate(cols):
        end = cols[k + 1] if k + 1 < len(cols) else len(line)
        out.append(line[c:end].strip() if c < len(line) else "")
    return out

def parse(lines):
    ver = None
    for l in lines:
        m = VERSION.search(l)
        if m: ver = f"{m.group(1)} ({m.group(2)})"; break
    STOP = re.compile(r"^\s*(ii\.|iii\.|iv\.|B\)|C\)|Cash advance fee|Service charges)", re.I)
    cols, rows, i = None, [], 0
    while i < len(lines):
        line = lines[i]
        if "Card variant" in line:
            cols = column_bounds(line); i += 1; continue
        if cols and STOP.match(line):
            cols = None; i += 1; continue          # fee table ended on this page
        if cols and line.strip():
            cells = slice_row(line, cols)
            name = " ".join(cells[0].split()).strip(" ,")
            fee_cell = cells[1] if len(cells) > 1 else ""
            spend_cell = cells[2] if len(cells) > 2 else ""
            forex_cell = cells[4] if len(cells) > 4 else ""
            frag = re.match(r"^(DFC|FC|GA|CK|E |I |L |Pay/|Rewards |Edition|More than|Less than|CTC|Pay Mega)", name) or re.fullmatch(r"HDFC Bank", name)
            chargey = re.search(r"fee[s]?:|late fee|processing|excluding|conve", name, re.I)
            if (name and not NOISE.search(name) and not frag and not chargey
                    and len(name) > 3 and re.match(r"^[A-Z0-9]", name)):
                rows.append({"name": name, "fee_raw": fee_cell, "spend_raw": spend_cell,
                             "fee": rupees(fee_cell), "spend": rupees(spend_cell),
                             "forex": forex_cell})
        i += 1
    return ver, rows

def build(c, version):
    name = c["name"]
    full = name if re.search(r"\bcard\b", name, re.I) else f"{name} Credit Card"
    attrs = {"issuer": ISSUER, "mitc_url": MITC_URL}
    if version: attrs["mitc_version"] = version
    fee = c["fee"]
    if fee is not None and not (fee == 0 or fee >= 99):
        fee = None                      # ₹1-₹98 is a column mis-read, not a fee
    if fee is not None:
        attrs["joining_fee_inr"] = fee
        attrs["annual_fee_inr"] = fee
    if c["spend"] is not None:
        attrs["fee_waiver_spend_inr"] = c["spend"]
    fx = re.search(r"([\d.]+)\s*%", c.get("forex") or "")
    if fx: attrs["forex_markup_pct"] = float(fx.group(1))
    required = ["issuer", "joining_fee_inr", "annual_fee_inr"]
    status = "entry" if all(attrs.get(k) is not None for k in required) else "candidate"
    note = (f'fee read from the "Joining / Annual membership Fee" column'
            if c["fee"] is not None else
            "fee cell is merged or blank in the source PDF — a human needs to read it off the document")
    return {
        "id": mint(ISSUER, full),
        "slug": slugify(f"{ISSUER} {full}")[:80],
        "name": full[:200],
        "brand": ISSUER,
        "domain": "cards",
        "category": "Credit cards",
        "attributes": attrs,
        "status": status,
        "confidence": "extracted",
        "sources": [{"kind": "manual", "url": MITC_URL, "checked": TODAY,
                     "note": f"HDFC Bank MITC {version or 'version unknown'} — {note}"}],
    }

def main():
    pdfs = sorted(glob.glob(os.path.join(HERE, "mitc", SLUG, "*.pdf")))
    if not pdfs: raise SystemExit("no MITC on file — run tools/cards/fetch_mitc.py first")
    pdf = pdfs[-1]
    version, rows = parse(lines_of(pdf, 2, 8))
    print(f"MITC {version}  ({os.path.basename(pdf)})\n")

    recs, seen = [], {}
    for c in rows:
        r = build(c, version)
        prev = seen.get(r["id"])
        if prev:
            # keep the row that actually carried a fee
            if prev["status"] != "entry" and r["status"] == "entry": seen[r["id"]] = r
            continue
        seen[r["id"]] = r
    recs = sorted(seen.values(), key=lambda r: r["name"].lower())

    out = os.path.join(REPO, "products", "cards"); os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, SLUG + ".jsonl"), "w", encoding="utf-8") as f:
        for r in recs: f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")

    entries = sum(1 for r in recs if r["status"] == "entry")
    print(f"{len(recs)} cards — {entries} entries, {len(recs)-entries} candidates awaiting a human\n")
    for r in recs:
        a = r["attributes"]
        fee = f'₹{a["annual_fee_inr"]:,}' if a.get("annual_fee_inr") is not None else "—"
        wv = f'₹{a["fee_waiver_spend_inr"]:,}' if a.get("fee_waiver_spend_inr") else "—"
        fx = f'{a["forex_markup_pct"]}%' if a.get("forex_markup_pct") else "—"
        print(f'  {r["name"][:40]:42s} fee {fee:>9}  waived at {wv:>11}  forex {fx:>6}  {r["status"]}')

if __name__ == "__main__":
    main()
