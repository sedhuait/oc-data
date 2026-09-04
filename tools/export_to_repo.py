#!/usr/bin/env python3
"""Move fact data out of the crawl into the open repo.
Live data (price, MRP, stock, history, affiliate links) is deliberately left behind.

Usage: python3 export_to_repo.py [--limit N]
Reads : ~/skus-crawl/data/*.json  (brand-store crawl)
Writes: ~/oc-data/products/<domain>/<brand>.jsonl
"""
import json, os, re, sys, glob, hashlib, unicodedata
sys.path.insert(0, os.path.expanduser("~/skus-crawl"))
from extract import extract

CRAWL = os.path.expanduser("~/skus-crawl")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TODAY = "2026-09-04"

ALIAS = {"minimalist":"Minimalist","plum":"Plum","dot-and-key":"Dot & Key","mcaffeine":"mCaffeine","pilgrim":"Pilgrim",
         "foxtale":"Foxtale","juicy-chemistry":"Juicy Chemistry","renee":"Renee","sugar":"SUGAR","mamaearth":"Mamaearth",
         "the-derma-co":"The Derma Co","bombay-shaving-company":"Bombay Shaving Company","just-herbs":"Just Herbs"}
DOMAINS = json.load(open(os.path.join(REPO, "schemas", "beauty.json")))
CATS = set(DOMAINS["categories"]) - {"_default"}

# crawl category -> repo category (only those the beauty schema declares)
CATMAP = {"Sunscreen":"Sunscreen","Face serum":"Face serum","Moisturiser":"Moisturiser",
          "Face wash & cleanser":"Face wash & cleanser","Shampoo":"Shampoo","Lipstick":"Lipstick",
          "Fragrance":"Fragrance"}

def norm(s):
    s = unicodedata.normalize("NFKD", s or "").lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s)).strip()
def slugify(s): return re.sub(r"[^a-z0-9]+", "-", norm(s)).strip("-")
def pid(brand, name, size): return "oc_" + hashlib.sha1(f"{norm(brand)}|{norm(name)}|{size}".encode()).hexdigest()[:12]

RULES = [("Sunscreen", r"sunscreen|sun screen|\bspf\b"), ("Shampoo", r"shampoo"),
         ("Face wash & cleanser", r"face ?wash|cleanser|facewash"), ("Face serum", r"serum"),
         ("Moisturiser", r"moisturi[sz]|face cream|day cream|night cream"),
         ("Lipstick", r"lipstick|liquid lip|lip colou?r|lip crayon"),
         ("Fragrance", r"perfume|eau de|body mist|deodorant")]
SKIP = re.compile(r"combo|\bkit\b|\bset\b|pack of|bundle|hamper|gift|\bduo\b|\btrio\b|byob|\bfree\b|sample|tester", re.I)

def categorise(title, ptype):
    t = f"{title} {ptype}"
    for cat, rx in RULES:
        if re.search(rx, t, re.I): return cat
    return None

FLAGS_OK = set(json.load(open(os.path.join(REPO, "schemas", "beauty.json")))["fields"]["flags"]["values"])
SKIN_OK = set(json.load(open(os.path.join(REPO, "schemas", "beauty.json")))["fields"]["skin"]["values"])

def build(p, brand):
    x = extract(p)
    cat = categorise(p["title"], p.get("product_type", ""))
    if not cat: return None
    size = f"{round(x['size'])} {x['unit']}" if x["size"] and x["unit"] in ("ml", "g") else None
    attrs = {}
    if size: attrs["size"] = size
    if x.get("spf"): attrs["spf"] = int(x["spf"])
    if x.get("pa"): attrs["pa"] = x["pa"]
    if x.get("actives"): attrs["actives"] = x["actives"]
    if x.get("skin"): attrs["skin"] = [s for s in x["skin"] if s in SKIN_OK]
    if x.get("flags"): attrs["flags"] = [f for f in x["flags"] if f in FLAGS_OK]
    attrs = {k: v for k, v in attrs.items() if v not in (None, "", [])}

    required = DOMAINS["categories"].get(cat, DOMAINS["categories"]["_default"])["required"]
    status = "entry" if all(attrs.get(k) for k in required) else "candidate"
    ing = [i for i in (x.get("ing") or []) if 2 < len(i) < 80][:120]

    rec = {
        "id": pid(brand, p["title"], size or ""),
        "slug": slugify(f"{brand} {p['title']}")[:80],
        "name": p["title"][:200],
        "brand": brand,
        "domain": "beauty",
        "category": cat,
        "size": (size.replace(" ", " ") if size else None),
        "identifiers": {"gtin": None, "asin": None, "fsn": None, "ondc": None,
                        "shopify_handle": p.get("handle")},
        "attributes": attrs,
        "variants": [{"name": v["title"], "sku": v.get("sku") or None, "gtin": None}
                     for v in p["variants"][:60] if v.get("title")],
        "images": [p["image"]] if p.get("image") else [],
        "urls": {"brand": p["url"], "flipkart": None, "amazon": None},
        "status": status,
        "confidence": "verified" if len(ing) >= 5 else "extracted",
        "sources": [{"kind": "brand-store", "url": p["url"], "checked": TODAY,
                     "note": "public Shopify products.json"}],
        "first_seen": (p.get("published_at") or "")[:10] or None,
        "superseded_by": None,
    }
    if ing: rec["ingredients"] = ing
    return rec

def main():
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    by_brand, skipped, dupes = {}, 0, 0
    seen = set()
    for f in sorted(glob.glob(os.path.join(CRAWL, "data", "*.json"))):
        try: rows = json.load(open(f))
        except Exception: continue
        if not isinstance(rows, list) or not rows or "title" not in (rows[0] or {}): continue
        brand = ALIAS.get(rows[0]["brand"], rows[0]["brand"])
        for p in rows:
            if SKIP.search(p["title"]) or not p.get("price_min") or p["price_min"] <= 10:
                skipped += 1; continue
            rec = build(p, ALIAS.get(p["brand"], p["brand"]))
            if not rec: skipped += 1; continue
            if rec["id"] in seen: dupes += 1; continue
            seen.add(rec["id"])
            by_brand.setdefault((rec["domain"], rec["brand"]), []).append(rec)

    written = 0
    for (dom, brand), recs in sorted(by_brand.items()):
        recs.sort(key=lambda r: (r["category"], r["name"].lower()))
        if limit: recs = recs[:limit]
        d = os.path.join(REPO, "products", dom)
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, slugify(brand) + ".jsonl")
        with open(path, "w", encoding="utf-8") as fh:
            for r in recs:
                fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
        written += len(recs)
        print(f"  {os.path.relpath(path, REPO):46s} {len(recs):>4} records")
    entries = sum(1 for v in by_brand.values() for r in v if r["status"] == "entry")
    print(f"\nwrote {written} records · {entries} entries, {written-entries} candidates")
    print(f"skipped {skipped} (bundles, freebies, uncategorised) · {dupes} duplicate ids merged")
    print("left behind on purpose: prices, MRP, stock, price history, affiliate links")

if __name__ == "__main__":
    main()
