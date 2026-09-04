#!/usr/bin/env python3
"""Import mutual fund scheme identity from AMFI's public NAVAll.txt.

Facts only. NAV is a price and does not enter this repo — the importer reads it,
reports it, and throws it away. Scheme identity (ISIN, code, AMC, category,
plan, option) is what stays true.

Source: https://portal.amfiindia.com/spages/NAVAll.txt (public, updated daily)
Usage:  python3 tools/import_amfi.py [--file /tmp/navall.txt]
"""
import json, os, re, sys, urllib.request, hashlib, unicodedata
from collections import Counter, defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = "https://portal.amfiindia.com/spages/NAVAll.txt"
TODAY = "2026-09-04"

def norm(s):
    s = unicodedata.normalize("NFKD", s or "").lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s)).strip()
def slugify(s): return re.sub(r"[^a-z0-9]+", "-", norm(s)).strip("-")
def mint(brand, name, size=""): return "oc_" + hashlib.sha1(f"{norm(brand)}|{norm(name)}|{size}".encode()).hexdigest()[:12]

# AMFI section header -> our category
def categorise(section):
    s = section.lower()
    if "solution oriented" in s or "children" in s or "retirement" in s: return "Solution oriented", section
    if "index funds" in s or "etf" in s or "gold" in s or "fund of funds" in s: return "Index / ETF", section
    if "hybrid" in s or "balanced" in s: return "Hybrid", section
    if "debt" in s or "income" in s or "liquid" in s or "gilt" in s or "money market" in s or "overnight" in s: return "Debt", section
    if "equity" in s or "growth" in s or "elss" in s or "cap fund" in s: return "Equity", section
    return "Other", section

SCHEME_TYPE = re.compile(r"^(Open|Close|Interval)\s*Ended", re.I)
SUBCAT = re.compile(r"\((.+?)\)\s*$")

def parse(text):
    section, scheme_type, subcat, amc = "", None, None, None
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("Scheme Code;"): continue
        if ";" not in line:
            if SCHEME_TYPE.match(line):
                section = line
                m = SUBCAT.search(line)
                subcat = m.group(1).split(" - ")[-1].strip() if m else None
                scheme_type = SCHEME_TYPE.match(line).group(1).title() + " ended"
            else:
                amc = line
            continue
        parts = line.split(";")
        if len(parts) < 8: continue
        code, isin_g, isin_r, name, plan, option, nav, date = [p.strip() for p in parts[:8]]
        rows.append({"code": code, "isin_g": isin_g if isin_g != "-" else None,
                     "isin_r": isin_r if isin_r != "-" else None, "name": name,
                     "plan": plan, "option": option, "nav": nav, "date": date,
                     "section": section, "scheme_type": scheme_type, "subcat": subcat, "amc": amc})
    return rows

PLAN_MAP = {"direct plan": "Direct", "regular plan": "Regular", "direct": "Direct", "regular": "Regular"}
def plan_of(p, name):
    v = PLAN_MAP.get(p.strip().lower())
    if v: return v
    n = name.lower()
    if "direct" in n: return "Direct"
    if "regular" in n: return "Regular"
    return None

def option_of(o):
    s = (o or "").lower()
    if "reinvest" in s: return "IDCW Reinvestment"
    if "payout" in s: return "IDCW Payout"
    if "idcw" in s or "dividend" in s: return "IDCW"
    if "bonus" in s: return "Bonus"
    if "growth" in s: return "Growth"
    return None

def build(r):
    plan, option = plan_of(r["plan"], r["name"]), option_of(r["option"])
    cat, section = categorise(r["section"])
    amc = (r["amc"] or "").replace(" Mutual Fund", "").strip()
    if not amc or not r["name"]: return None
    attrs = {"amc": amc, "plan": plan, "option": option,
             "scheme_type": r["scheme_type"], "sub_category": r["subcat"],
             "scheme_code": r["code"], "isin_growth": r["isin_g"], "isin_reinvest": r["isin_r"]}
    attrs = {k: v for k, v in attrs.items() if v}
    status = "entry" if all(attrs.get(k) for k in ("amc", "plan", "option")) else "candidate"
    # full name including plan/option so each buyable line is distinct
    full = f'{r["name"]} — {plan or "?"} {option or "?"}'.strip()
    return {
        "id": mint(amc, full),
        "slug": slugify(f"{amc} {full}")[:80],
        "name": full[:200],
        "brand": amc,
        "domain": "funds",
        "category": cat,
        "identifiers": {"gtin": None, "asin": None, "fsn": None, "ondc": None,
                        "isin": r["isin_g"] or r["isin_r"]},
        "attributes": attrs,
        "status": status,
        "confidence": "stated",
        "sources": [{"kind": "manual", "url": URL, "checked": TODAY,
                     "note": "AMFI daily scheme file — identity only, NAV excluded"}],
    }

def main():
    src = sys.argv[sys.argv.index("--file") + 1] if "--file" in sys.argv else None
    text = open(src, encoding="utf-8", errors="replace").read() if src else \
        urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": "opencatalogue/0.1"}), timeout=120).read().decode("utf-8", "replace")
    rows = parse(text)
    print(f"parsed {len(rows)} scheme lines from AMFI")

    by_amc, seen, dropped = defaultdict(list), set(), 0
    for r in rows:
        rec = build(r)
        if not rec: dropped += 1; continue
        if rec["id"] in seen: dropped += 1; continue
        seen.add(rec["id"]); by_amc[rec["brand"]].append(rec)

    out = os.path.join(REPO, "products", "funds")
    os.makedirs(out, exist_ok=True)
    total = entries = 0
    for amc, recs in sorted(by_amc.items()):
        recs.sort(key=lambda r: (r["category"], r["name"].lower()))
        with open(os.path.join(out, slugify(amc) + ".jsonl"), "w", encoding="utf-8") as f:
            for r in recs:
                f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
        total += len(recs); entries += sum(1 for r in recs if r["status"] == "entry")
    print(f"wrote {total} schemes across {len(by_amc)} fund houses ({entries} entries, {total-entries} candidates)")
    print(f"dropped {dropped} (duplicates or unparseable)")
    print("categories:", dict(Counter(r["category"] for v in by_amc.values() for r in v).most_common()))
    print("\nNAV was read and discarded — it is a price, and prices live in the service, not this repo.")

if __name__ == "__main__":
    main()
