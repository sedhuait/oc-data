#!/usr/bin/env python3
"""Snapshot every bank's savings and FD rate pages, and detect when they change.

Rates move monthly and are LIVE data — they do not go in products/. What this
gives you is the dated snapshot and the change signal: when a bank cuts its
savings rate or repositions an FD bucket, the next run says so. Feed the parsed
rate into the service; keep the account's identity and terms in the repo.

Fetching goes through oc-crawlers/lib/polite.py: robots.txt is obeyed, each
host is paced, and a bank that will not serve its rules is not crawled. A
response is kept only when it comes from the URL asked for — a redirect to a
home page or sitemap is treated as a failure, because storing those bytes
under the requested page's name is worse than having no snapshot at all.

  PAGE=fd_rates    python3 tools/banking/fetch_rates.py   # default
  PAGE=savings     python3 tools/banking/fetch_rates.py
  PAGE=debit_cards python3 tools/banking/fetch_rates.py
  PAGE=charges     python3 tools/banking/fetch_rates.py
  python3 tools/banking/fetch_rates.py --diff hdfc-bank   # show what changed

Layout:
  tools/banking/snapshots/<slug>/<YYYY-MM-DD>.pdf     the document as published
  tools/banking/snapshots/<slug>/text-<date>.txt      extracted text, for diffing
  tools/banking/snapshots/index.json                  hash + date per issuer, per fetch
"""
import json, os, re, sys, hashlib, subprocess, urllib.parse, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
STORE = os.path.join(HERE, "snapshots")
INDEX = os.path.join(STORE, "index.json")
SOURCES = json.load(open(os.path.join(HERE, "rate_sources.json")))
TODAY = datetime.date.today().isoformat()

# Fetch through the crawlers' polite layer rather than urllib directly. It
# obeys robots.txt, paces per host across processes, and fails closed when a
# host will not state its rules. The previous version sent a browser
# User-Agent straight at each bank, which asks no permission and gets an
# answer that looks like consent.
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "oc-crawlers"))
try:
    from lib.polite import Fetcher
except ImportError:
    sys.exit("needs oc-crawlers/lib/polite.py next to oc-data — clone it alongside this repo")

_FETCHERS = {}


def fetch(url, timeout=90):
    """(body, content-type, final-url), refusing anything but the page asked for.

       A bank site answers 200 for a path it no longer serves by redirecting to
       its home page or sitemap. Taking that body would file one page's bytes
       under another page's name — which is how a fixed-deposit directory came
       to hold a copy of a sitemap, indistinguishable in the index from a
       healthy fetch. So a redirect away from the requested URL is an error
       here, not a result."""
    host = urllib.parse.urlparse(url).netloc
    f = _FETCHERS.get(host)
    if f is None:
        f = _FETCHERS[host] = Fetcher(host, delay=3)
    if f.robots_unavailable:
        raise PermissionError(f"robots.txt unavailable on {host} — failing closed")
    if not f.allowed(url):
        raise PermissionError(f"robots.txt disallows {url}")
    body, ctype, final = f.get(url, timeout=timeout)
    if final.rstrip("/") != url.rstrip("/"):
        raise ValueError(f"redirected to {final} — not the page requested")
    return body, ctype, final

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

    changed, new, failed, skipped = [], [], [], []
    which = os.environ.get("PAGE", "fd_rates")
    for s in SOURCES["banks"]:
        slug = s["slug"]
        if s.get("unreachable"):
            skipped.append((slug, s["unreachable"][:70])); continue
        # Only the page type asked for. Falling back to another page would
        # store a savings page as though it were the FD page — the same
        # mislabelling the redirect check above exists to prevent.
        url = s.get(which)
        if not url: continue
        slug = f"{slug}-{which}" if which != "fd_rates" else slug
        d = os.path.join(STORE, slug); os.makedirs(d, exist_ok=True)
        try:
            body, ctype, final = fetch(url)
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
    print(f"\n{len(new)} new · {len(changed)} changed · {len(failed)} failed · "
          f"{len(skipped)} skipped · {len(index)} on file")
    for slug, why in failed: print(f"  ✗ {slug:24s} {why}")
    for slug, why in skipped: print(f"  – {slug:24s} recorded unreachable: {why}")
    if changed:
        print("\nChanged documents — review each before touching any record:")
        for slug in changed: print(f"  python3 tools/banking/fetch_rates.py --diff {slug}")

if __name__ == "__main__":
    main()
