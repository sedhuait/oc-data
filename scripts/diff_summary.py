#!/usr/bin/env python3
"""Human-readable PR summary: what actually changed, in product terms."""
import json, subprocess, sys, collections

def load(ref):
    out = {}
    files = subprocess.run(["git", "ls-tree", "-r", "--name-only", ref, "products/"],
                           capture_output=True, text=True).stdout.split()
    for f in files:
        if not f.endswith(".jsonl"): continue
        blob = subprocess.run(["git", "show", f"{ref}:{f}"], capture_output=True, text=True).stdout
        for line in blob.splitlines():
            if line.strip():
                r = json.loads(line); out[r["id"]] = r
    return out

def main():
    base, head = sys.argv[1], sys.argv[2]
    a, b = load(base), load(head)
    added = [b[i] for i in b.keys() - a.keys()]
    removed = [a[i] for i in a.keys() - b.keys()]
    changed = []
    for i in a.keys() & b.keys():
        if a[i] != b[i]:
            fields = sorted({k for k in set(a[i]) | set(b[i]) if a[i].get(k) != b[i].get(k)})
            changed.append((b[i], fields))

    print("## What this changes\n")
    print(f"**{len(added)} added · {len(changed)} updated · {len(removed)} removed**\n")
    if added:
        by = collections.Counter((r["brand"], r["category"]) for r in added)
        print("### Added")
        for (br, c), n in by.most_common(12): print(f"- {br} — {c}: {n}")
        print()
    if changed:
        print("### Updated")
        for r, fields in changed[:20]:
            print(f"- {r['brand']} — {r['name'][:60]}: {', '.join(fields)}")
        if len(changed) > 20: print(f"- …and {len(changed)-20} more")
        print()
    if removed:
        print("### Removed — needs a maintainer to confirm")
        for r in removed[:20]: print(f"- {r['brand']} — {r['name'][:60]} ({r['id']})")
        print()
    ing = [r for r, f in changed if "ingredients" in f]
    if ing:
        print(f"> {len(ing)} ingredient lists changed. Ingredients are the fact people trust most — "
              f"each needs a source URL or a photo of the pack.\n")

if __name__ == "__main__":
    main()
