#!/usr/bin/env python3
"""Fetch every issuer's MITC, store it, and detect when it changes.

The change log is the point. Issuers revise fees, caps and benefits quietly;
nobody keeps a dated record of what the document said before. This does.

  python3 tools/cards/fetch_mitc.py            # fetch all, report changes
  python3 tools/cards/fetch_mitc.py --diff hdfc-bank   # show what changed

Layout — under documents/, with every other publisher's document, because the
terms on them are the publisher's and should not depend on which directory a
file happens to sit in:
  documents/cards/mitc/<slug>/<YYYY-MM-DD>.pdf   the document as published
  documents/cards/mitc/<slug>/text-<date>.txt    extracted text, for diffing
  documents/cards/mitc/index.json                hash + date per issuer, per fetch
"""
import json, os, re, sys, hashlib, subprocess, urllib.request, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
STORE = os.path.join(ROOT, "documents", "cards", "mitc")
INDEX = os.path.join(STORE, "index.json")
SOURCES = json.load(open(os.path.join(HERE, "mitc_sources.json")))
TODAY = datetime.date.today().isoformat()
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"

def fetch(url, timeout=90):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/pdf,text/html,*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(), r.headers.get("Content-Type", ""), r.status

def to_text(path):
    """pdftotext if available (it ships with poppler / macOS via brew); else empty."""
    for cmd in (["pdftotext", "-layout", path, "-"], ["/opt/homebrew/bin/pdftotext", "-layout", path, "-"]):
        try:
            out = subprocess.run(cmd, capture_output=True, timeout=120)
            if out.returncode == 0 and out.stdout:
                return out.stdout.decode("utf-8", "replace")
        except FileNotFoundError:
            continue
        except Exception:
            break
    return ""

def normalise(t):
    """Ignore whitespace and page numbers so a reflow isn't reported as a change."""
    t = re.sub(r"Page \d+ of \d+", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()

def main():
    os.makedirs(STORE, exist_ok=True)
    index = json.load(open(INDEX)) if os.path.exists(INDEX) else {}

    if "--diff" in sys.argv:
        slug = sys.argv[sys.argv.index("--diff") + 1]
        d = os.path.join(STORE, slug)
        texts = sorted(f for f in os.listdir(d) if f.startswith("text-"))
        if len(texts) < 2: sys.exit(f"only {len(texts)} version(s) of {slug} on file — nothing to diff yet")
        a, b = os.path.join(d, texts[-2]), os.path.join(d, texts[-1])
        print(f"# {slug}: {texts[-2][5:-4]} → {texts[-1][5:-4]}\n")
        subprocess.run(["diff", "-u", "--label", texts[-2], "--label", texts[-1], a, b])
        return

    changed, new, failed = [], [], []
    for s in SOURCES["issuers"]:
        slug, url = s["slug"], s["mitc"]
        d = os.path.join(STORE, slug); os.makedirs(d, exist_ok=True)
        try:
            body, ctype, status = fetch(url)
        except Exception as e:
            failed.append((slug, f"{type(e).__name__}: {str(e)[:70]}")); continue
        if len(body) < 2000:
            failed.append((slug, f"suspiciously small response ({len(body)} bytes)")); continue

        digest = hashlib.sha256(body).hexdigest()[:16]
        prev = index.get(slug, {})
        ext = "pdf" if "pdf" in ctype.lower() or body[:4] == b"%PDF" else "html"
        path = os.path.join(d, f"{TODAY}.{ext}")

        if prev.get("sha") == digest:
            index[slug] = {**prev, "last_checked": TODAY}
            print(f"  = {slug:24s} unchanged since {prev.get('first_seen', '?')}")
            continue

        open(path, "wb").write(body)
        text = to_text(path) if ext == "pdf" else re.sub(r"<[^>]+>", " ", body.decode("utf-8", "replace"))
        if text:
            open(os.path.join(d, f"text-{TODAY}.txt"), "w", encoding="utf-8").write(normalise(text))
        (new if not prev else changed).append(slug)
        index[slug] = {"sha": digest, "url": url, "bytes": len(body), "type": ext,
                       "first_seen": prev.get("first_seen", TODAY), "changed_on": TODAY,
                       "last_checked": TODAY, "versions": prev.get("versions", []) + [TODAY],
                       "text_chars": len(text)}
        print(f"  {'+' if not prev else '!'} {slug:24s} {len(body)//1024:>5} KB  {'new' if not prev else 'CHANGED'}  {len(text)} chars of text")

    json.dump(index, open(INDEX, "w"), indent=1, sort_keys=True)
    print(f"\n{len(new)} new · {len(changed)} changed · {len(failed)} failed · {len(index)} on file")
    for slug, why in failed: print(f"  ✗ {slug:24s} {why}")
    if changed:
        print("\nChanged documents — review each before touching any record:")
        for slug in changed: print(f"  python3 tools/cards/fetch_mitc.py --diff {slug}")

if __name__ == "__main__":
    main()
