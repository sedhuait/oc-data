#!/usr/bin/env python3
"""Canonical formatter. Run before committing; CI checks the repo is already formatted.
Deterministic output = small, readable diffs in PRs.
  - one JSON object per line, keys sorted
  - lines sorted by (category, name)
  - empty/null-only fields dropped
"""
import json, os, glob, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def clean(r):
    out = {}
    for k, v in r.items():
        if v in (None, "", [], {}): 
            if k in ("attributes", "identifiers", "urls"): pass
            else: continue
        if isinstance(v, dict):
            v = {kk: vv for kk, vv in v.items() if vv not in ("", [])}
        out[k] = v
    return out

def main():
    check = "--check" in sys.argv
    dirty = []
    for f in sorted(glob.glob(os.path.join(ROOT, "products", "**", "*.jsonl"), recursive=True)):
        recs = [json.loads(l) for l in open(f, encoding="utf-8") if l.strip()]
        recs.sort(key=lambda r: (r.get("category", ""), (r.get("name") or "").lower(), r.get("id", "")))
        body = "".join(json.dumps(clean(r), ensure_ascii=False, sort_keys=True) + "\n" for r in recs)
        if open(f, encoding="utf-8").read() != body:
            dirty.append(os.path.relpath(f, ROOT))
            if not check: open(f, "w", encoding="utf-8").write(body)
    if check and dirty:
        print("These files are not canonically formatted. Run: python3 scripts/format.py")
        for d in dirty: print("  " + d)
        return 1
    print(("would reformat " if check else "formatted ") + f"{len(dirty)} files")
    return 0

if __name__ == "__main__":
    sys.exit(main())
