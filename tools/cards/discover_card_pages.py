#!/usr/bin/env python3
"""Discover credit card product pages from each issuer's card listing page.

These pages are server-rendered, so plain HTTP works — no headless browser.
This finds the per-card URLs; a second pass reads each one for the facts the
MITC doesn't state (network, lounge, reward rate, eligibility).

Polite by default: identifies itself, one request at a time, honours robots.txt.
"""
import json, os, re, sys, time, socket, urllib.request, urllib.parse, urllib.robotparser, html
from collections import OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
UA = "opencatalogue-bot/0.1 (+https://opencatalogue.in/about; open product data)"
socket.setdefaulttimeout(20)
BROWSER_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"

LISTINGS = [
    ("HDFC Bank",        "hdfc-bank",        "https://www.hdfcbank.com/personal/pay/cards/credit-cards",        r"/personal/pay/cards/credit-cards/[a-z0-9\-]+$"),
    ("Axis Bank",        "axis-bank",        "https://www.axisbank.com/retail/cards/credit-card",               r"/retail/cards/credit-card/[a-z0-9\-]+$"),
    ("ICICI Bank",       "icici-bank",       "https://www.icicibank.com/personal-banking/cards/credit-card",     r"/personal-banking/cards/credit-card/[a-z0-9\-]+"),
    ("SBI Card",         "sbi-card",         "https://www.sbicard.com/en/personal/credit-cards.page",            r"/credit-cards/[a-z0-9\-]+\.page"),
    ("IDFC FIRST Bank",  "idfc-first-bank",  "https://www.idfcfirstbank.com/credit-card",                        r"/credit-card/[a-z0-9\-]+$"),
    ("Kotak Mahindra",   "kotak-mahindra",   "https://www.kotak.com/en/personal-banking/cards/credit-cards.html", r"/credit-cards/[a-z0-9\-]+\.html"),
    ("IndusInd Bank",    "indusind-bank",    "https://www.indusind.com/in/en/personal/cards/credit-card.html",   r"/cards/credit-card/[a-z0-9\-]+\.html"),
    ("RBL Bank",         "rbl-bank",         "https://www.rblbank.com/category/credit-cards",                    r"/credit-card/[a-z0-9\-]+"),
    ("AU Small Finance", "au-small-finance", "https://www.aubank.in/personal-banking/credit-cards",              r"/credit-cards/[a-z0-9\-]+"),
    ("Yes Bank",         "yes-bank",         "https://www.yesbank.in/personal-banking/yes-individual/cards/credit-cards", r"/credit-cards/[a-z0-9\-]+"),
]

def can_fetch(url):
    """robots check with a hard timeout — a hanging robots.txt must not block the run."""
    try:
        p = urllib.parse.urlparse(url)
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(f"{p.scheme}://{p.netloc}/robots.txt")
        req = urllib.request.Request(f"{p.scheme}://{p.netloc}/robots.txt", headers={"User-Agent": BROWSER_UA})
        rp.parse(urllib.request.urlopen(req, timeout=12).read().decode("utf-8", "replace").splitlines())
        return rp.can_fetch(UA, url), rp.can_fetch("*", url)
    except Exception:
        return True, True

def get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": BROWSER_UA, "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace"), r.status

TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)

def links(page, base, pattern):
    out = OrderedDict()
    rx = re.compile(pattern, re.I)
    for m in re.finditer(r'<a[^>]+href="([^"#?]+)"[^>]*>(.*?)</a>', page, re.S | re.I):
        href, text = m.group(1), re.sub(r"<[^>]+>", " ", m.group(2))
        text = html.unescape(re.sub(r"\s+", " ", text)).strip()
        url = urllib.parse.urljoin(base, href)
        if not rx.search(urllib.parse.urlparse(url).path): continue
        if len(text) < 3 or len(text) > 70: text = ""
        if url not in out or (not out[url] and text): out[url] = text
    return out

def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    result = {}
    for issuer, slug, listing, pattern in LISTINGS:
        if only and only != slug: continue
        ours, star = can_fetch(listing)
        if not star:
            print(f"  x {issuer:20s} robots.txt disallows this path — skipping", flush=True); continue
        try:
            page, status = get(listing)
        except Exception as e:
            print(f"  x {issuer:20s} {type(e).__name__}: {str(e)[:50]}", flush=True); continue
        found = links(page, listing, pattern)
        result[slug] = {"issuer": issuer, "listing": listing, "cards":
                        [{"name": t or None, "url": u} for u, t in found.items()]}
        print(f"  {'+' if found else '.'} {issuer:20s} {len(page)//1024:>5} KB   {len(found):>3} card pages", flush=True)
        for u, t in list(found.items())[:3]:
            print(f"      {(t or '(no link text)')[:42]:44s} {urllib.parse.urlparse(u).path[:46]}", flush=True)
        time.sleep(1.5)
    out = os.path.join(HERE, "card_pages.json")
    json.dump(result, open(out, "w"), indent=1, ensure_ascii=False)
    total = sum(len(v["cards"]) for v in result.values())
    print(f"\n{total} card pages across {len(result)} issuers -> {os.path.relpath(out, os.path.dirname(HERE))}", flush=True)

if __name__ == "__main__":
    main()
