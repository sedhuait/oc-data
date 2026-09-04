#!/usr/bin/env python3
"""Mint the canonical id for a product.  Usage: mint_id.py "Brand" "Product name" ["30 ml"]"""
import hashlib, re, sys, unicodedata

def norm(s):
    s = unicodedata.normalize("NFKD", s or "").lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s)).strip()

if len(sys.argv) < 3:
    sys.exit(__doc__)
brand, name = sys.argv[1], sys.argv[2]
size = (sys.argv[3] if len(sys.argv) > 3 else "").replace(" ", "")
print("oc_" + hashlib.sha1(f"{norm(brand)}|{norm(name)}|{size}".encode()).hexdigest()[:12])
print("slug:", re.sub(r"[^a-z0-9]+", "-", norm(f"{brand} {name}")).strip("-")[:80])
