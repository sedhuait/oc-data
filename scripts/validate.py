#!/usr/bin/env python3
"""Validate every record in /products against the schemas and the scope rules.
Exit 1 on any error. Warnings don't fail the build but are printed for review.

Checks:
  E1  JSON parse / one object per line
  E2  product.json schema conformance (no jsonschema dependency: hand-rolled, explicit)
  E3  id format + uniqueness across the whole repo
  E4  file placement: /products/<domain>/<brand-slug>.jsonl matches record's domain+brand
  E5  category exists in the domain schema
  E6  required fields present for that category (else status must be 'candidate')
  E7  attribute keys declared in the domain schema; values match type/enum/range
  E8  sources present, kind valid, checked is a real past date
  E9  identifiers well-formed; GTIN check digit
  E10 no prices, no stock, no affiliate tags anywhere in the repo
  W1  duplicate GTIN across records
  W2  near-duplicate (same brand + normalised name + size)
  W3  BEE star >= 4 with no rating_year
  W4  lines not sorted / file not deterministic
"""
import json, os, re, sys, glob, unicodedata
from datetime import date, datetime
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
E, W = [], []
def err(f, ln, code, msg): E.append(f"{f}:{ln}  [{code}] {msg}")
def warn(f, ln, code, msg): W.append(f"{f}:{ln}  [{code}] {msg}")

PRODUCT = json.load(open(os.path.join(ROOT, "schemas", "product.json")))
DOMAIN_SCHEMAS = {}
for p in glob.glob(os.path.join(ROOT, "schemas", "*.json")):
    if os.path.basename(p) == "product.json": continue
    d = json.load(open(p))
    DOMAIN_SCHEMAS[d["domain"]] = d

ID_RE = re.compile(r"^oc_[0-9a-f]{12}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SIZE_RE = re.compile(r"^[0-9.]+ ?(ml|g|kg|l|pcs)$")
BANNED_KEYS = {"price", "mrp", "selling_price", "stock", "in_stock", "availability", "discount", "offers"}
AFFILIATE = re.compile(r"(affid=|[?&]tag=[a-z0-9-]+-\d\d|utm_)", re.I)

def norm(s):
    s = unicodedata.normalize("NFKD", s or "").lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s)).strip()

def gtin_ok(g):
    if not g or not g.isdigit() or len(g) not in (8, 12, 13, 14): return False
    ds = [int(c) for c in g][::-1]
    return sum(d * (3 if i % 2 else 1) for i, d in enumerate(ds)) % 10 == 0

def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", norm(s)).strip("-")

def check_type(field, spec, val, f, ln, key):
    t = spec.get("type")
    if t == "integer":
        if not isinstance(val, int) or isinstance(val, bool):
            return err(f, ln, "E7", f"{key} must be an integer, got {val!r}")
    elif t == "number":
        if not isinstance(val, (int, float)) or isinstance(val, bool):
            return err(f, ln, "E7", f"{key} must be a number, got {val!r}")
    elif t in ("enum",):
        if val not in spec.get("values", []):
            return err(f, ln, "E7", f"{key}={val!r} not in {spec['values']}")
    elif t == "list":
        if not isinstance(val, list):
            return err(f, ln, "E7", f"{key} must be a list")
        vals = spec.get("values")
        if vals:
            for v in val:
                if v not in vals: err(f, ln, "E7", f"{key} contains {v!r}, not in the declared vocabulary")
        return
    elif t == "quantity":
        if not isinstance(val, str) or not SIZE_RE.match(val):
            return err(f, ln, "E7", f"{key}={val!r} must look like '30 ml'")
        return
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        if "min" in spec and val < spec["min"]: err(f, ln, "E7", f"{key}={val} below min {spec['min']}")
        if "max" in spec and val > spec["max"]: err(f, ln, "E7", f"{key}={val} above max {spec['max']}")

def validate_record(r, f, ln, seen_ids, seen_gtin, seen_key):
    # E2 required top-level
    for k in PRODUCT["required"]:
        if k not in r or r[k] in (None, "", []):
            err(f, ln, "E2", f"missing required field '{k}'")
    for k in r:
        if k not in PRODUCT["properties"]:
            err(f, ln, "E2", f"unknown top-level field '{k}'")
    rid = r.get("id", "")
    if not ID_RE.match(rid): err(f, ln, "E3", f"id {rid!r} must match oc_<12 hex>")
    elif rid in seen_ids: err(f, ln, "E3", f"duplicate id {rid} (also in {seen_ids[rid]})")
    else: seen_ids[rid] = f"{f}:{ln}"

    dom, brand, cat = r.get("domain"), r.get("brand", ""), r.get("category", "")
    # E4 file placement
    want = os.path.join("products", str(dom), slugify(brand) + ".jsonl")
    got = os.path.relpath(f, ROOT)
    if want != got: err(f, ln, "E4", f"record belongs in {want}, found in {got}")

    ds = DOMAIN_SCHEMAS.get(dom)
    if not ds:
        err(f, ln, "E5", f"no schema for domain '{dom}'"); return
    cats = ds["categories"]
    cs = cats.get(cat) or cats.get("_default")
    if cat not in cats and "_default" not in cats:
        err(f, ln, "E5", f"category '{cat}' not declared in schemas/{dom}.json")
        return

    attrs = r.get("attributes") or {}
    # E7 attribute keys + types
    for k, v in attrs.items():
        spec = ds["fields"].get(k)
        if not spec:
            err(f, ln, "E7", f"attribute '{k}' not declared in schemas/{dom}.json")
            continue
        if v is None or v == "": continue
        check_type(k, spec, v, f, ln, k)

    # E6 required fields for the category
    missing = [k for k in cs.get("required", []) if not attrs.get(k)]
    status = r.get("status", "entry")
    if missing and status == "entry":
        err(f, ln, "E6", f"category '{cat}' requires {cs['required']}; missing {missing}. "
                         f"Mark status:'candidate' or supply them.")

    # E8 sources
    for s in r.get("sources") or []:
        if s.get("kind") not in PRODUCT["properties"]["sources"]["items"]["properties"]["kind"]["enum"]:
            err(f, ln, "E8", f"source kind {s.get('kind')!r} not allowed")
        d = s.get("checked", "")
        if not DATE_RE.match(d): err(f, ln, "E8", f"source.checked {d!r} must be YYYY-MM-DD")
        else:
            try:
                if datetime.strptime(d, "%Y-%m-%d").date() > date.today():
                    err(f, ln, "E8", f"source.checked {d} is in the future")
            except ValueError:
                err(f, ln, "E8", f"source.checked {d} is not a real date")

    # E9 identifiers
    ids = r.get("identifiers") or {}
    g = ids.get("gtin")
    if g:
        if not gtin_ok(g): err(f, ln, "E9", f"GTIN {g} fails the check digit")
        elif g in seen_gtin: warn(f, ln, "W1", f"GTIN {g} also on {seen_gtin[g]}")
        else: seen_gtin[g] = rid
    for k, pat in (("asin", r"^[A-Z0-9]{10}$"), ("fsn", r"^[A-Z0-9]{16}$")):
        v = ids.get(k)
        if v and not re.match(pat, v): err(f, ln, "E9", f"{k} {v!r} is malformed")

    # E10 no live data, no affiliate tags
    blob = json.dumps(r)
    for k in BANNED_KEYS:
        if f'"{k}"' in blob:
            err(f, ln, "E10", f"'{k}' is live data — it belongs in the service, not this repo")
    if AFFILIATE.search(blob):
        err(f, ln, "E10", "affiliate tag or tracking parameter found in a URL; store clean canonical URLs")

    # W2 near-duplicate
    key = (norm(brand), norm(r.get("name", "")), r.get("size") or "")
    if key in seen_key: warn(f, ln, "W2", f"looks like a duplicate of {seen_key[key]}")
    else: seen_key[key] = rid

    # W3 star rating without its year
    if dom == "appliances" and (attrs.get("star") or 0) >= 4 and not attrs.get("rating_year"):
        warn(f, ln, "W3", "BEE star >= 4 with no rating_year — thresholds change, so this may mislead")

def main():
    files = sorted(glob.glob(os.path.join(ROOT, "products", "**", "*.jsonl"), recursive=True))
    seen_ids, seen_gtin, seen_key = {}, {}, {}
    n = 0
    for f in files:
        prev = None
        for ln, line in enumerate(open(f, encoding="utf-8"), 1):
            line = line.rstrip("\n")
            if not line.strip(): continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError as e:
                err(f, ln, "E1", f"not valid JSON: {e}"); continue
            if not isinstance(r, dict):
                err(f, ln, "E1", "each line must be one JSON object"); continue
            n += 1
            validate_record(r, f, ln, seen_ids, seen_gtin, seen_key)
            key = (r.get("category", ""), (r.get("name") or "").lower(), r.get("id", ""))
            if prev and key < prev: warn(f, ln, "W4", "lines out of canonical order — run scripts/format.py")
            prev = key

    print(f"checked {n} records in {len(files)} files")
    for w in W[:60]: print("  warn  " + w)
    if len(W) > 60: print(f"  … and {len(W)-60} more warnings")
    for e in E[:120]: print("  ERROR " + e)
    if len(E) > 120: print(f"  … and {len(E)-120} more errors")
    print(f"\n{len(E)} errors, {len(W)} warnings")
    return 1 if E else 0

if __name__ == "__main__":
    sys.exit(main())
