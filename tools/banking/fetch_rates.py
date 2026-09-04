#!/usr/bin/env python3
"""Snapshot every bank's savings and FD rate pages, and detect when they change.

Rates move monthly and are LIVE data — they do not go in products/. What this
gives you is the dated snapshot and the change signal: when a bank cuts its
savings rate or repositions an FD bucket, the next run says so. Feed the parsed
rate into the service; keep the account's identity and terms in the repo.

  python3 tools/banking/fetch_rates.py            # fetch all, report changes
  python3 tools/banking/fetch_rates.py --diff hdfc-bank   # show what changed

Layout:
  tools/banking/snapshots/<slug>/<YYYY-MM-DD>.pdf     the document as published
  tools/banking/snapshots/<slug>/text-<date>.txt      extracted text, for diffing
  tools/banking/snapshots/index.json                  hash + date per issuer, per fetch
"""
import json, os, re, sys, hashlib, subprocess, urllib.request, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
STORE = os.path.join(HERE, "snapshots")
INDEX = os.path.join(STORE, "index.json")
SOURCES = json.load(open(os.path.join(HERE, "rate_sources.json")))
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
    for s in SOURCES["banks"]:
        slug, url = s["slug"], s.get("fd_rates") or s.get("savings")
        if not url: continue
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
        for slug in changed: print(f"  python3 tools/banking/fetch_rates.py --diff {slug}")

if __name__ == "__main__":
    main()
