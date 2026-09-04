#!/usr/bin/env python3
"""Export financial-product records from the open repo to the site.
Facts only — no rates, no premiums, no NAV. Those are live-layer data.
"""
import json, glob, os, sys
from collections import Counter
REPO = os.path.expanduser("~/oc-data")
SITE = os.path.expanduser("~/skus-crawl/site")

DOMAINS = sys.argv[1:] or ["cards", "banking", "insurance"]
out = []
for dom in DOMAINS:
    for f in sorted(glob.glob(os.path.join(REPO, "products", dom, "*.jsonl"))):
        for line in open(f, encoding="utf-8"):
            if not line.strip(): continue
            r = json.loads(line)
            a = r.get("attributes", {})
            out.append({
                "dom": dom, "c": r["category"], "b": r["brand"], "t": r["name"],
                "p": None, "px": None, "m": None, "d": 0, "a": 1, "v": [], "g": [],
                "i": "", "u": "", "up": r["sources"][0]["checked"], "id": r["id"],
                "x": {k: v for k, v in a.items() if v not in (None, "", [])},
                "demo": 0, "live": 0, "status": r.get("status", "entry"),
                "src": r["sources"][0].get("note", ""),
            })

open(os.path.join(SITE, "data-fin.js"), "w").write(
    "window.FIN=" + json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";\n")
print(f"wrote {len(out)} records -> site/data-fin.js")
print(dict(Counter(r["dom"] for r in out)))
print("entries:", sum(1 for r in out if r["status"] == "entry"),
      "· candidates:", sum(1 for r in out if r["status"] == "candidate"))
