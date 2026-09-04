#!/usr/bin/env python3
"""Build site/data-funds.js from the open repo. Facts only — no NAV, no returns."""
import json, glob, os
REPO = os.path.expanduser("~/oc-data")
SITE = os.path.expanduser("~/skus-crawl/site")

out = []
for f in sorted(glob.glob(os.path.join(REPO, "products", "funds", "*.jsonl"))):
    for line in open(f, encoding="utf-8"):
        if not line.strip(): continue
        r = json.loads(line)
        a = r.get("attributes", {})
        out.append({
            "dom": "funds", "c": r["category"], "b": r["brand"], "t": r["name"],
            "p": None, "px": None, "m": None, "d": 0, "a": 1, "v": [], "g": [],
            "i": "", "u": "", "up": r["sources"][0]["checked"], "id": r["id"],
            "x": {k: v for k, v in {
                "sub_category": a.get("sub_category"),
                "management_style": a.get("management_style"),
                "plan": a.get("plan"),
                "option": a.get("option"),
                "scheme_type": a.get("scheme_type"),
                "amc": a.get("amc"),
                "scheme_code": a.get("scheme_code"),
                "isin": r.get("identifiers", {}).get("isin"),
                "fund_manager": a.get("fund_manager"),
                "theme": a.get("theme"),
            }.items() if v},
            "demo": 0, "src": "AMFI daily scheme file", "live": 0,
            "status": r.get("status", "entry"),
        })

open(os.path.join(SITE, "data-funds.js"), "w").write(
    "window.FUNDS=" + json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";\n")
from collections import Counter
print(f"wrote {len(out)} funds  ({os.path.getsize(os.path.join(SITE,'data-funds.js'))//1024} KB)")
print("asset class:", dict(Counter(r["c"] for r in out).most_common()))
print("style:", dict(Counter(r["x"].get("management_style") for r in out).most_common()))
print("houses:", len({r["b"] for r in out}))
