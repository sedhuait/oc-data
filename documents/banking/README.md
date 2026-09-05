# Bank schedules of charges

The document a bank's fees are actually set by. A product page advertises
"zero balance"; the schedule of charges states which balance, in which
location tier, and what falling short costs. Where the two disagree the
schedule wins, so it is the only thing the banking records cite for a fee.

These PDFs are each bank's copyright, not ours. They are mirrored
unmodified so that any figure in `products/banking/` can be checked against
the document it was read from, nothing is charged for them, and they come
down on request. What this project owns and gives away is the facts read
out of them.

Mirrored by `oc-crawlers/sources/banking/harvest_charges.py` on 2026-09-06.

## Reached (1 banks, 16 documents)

- **ICICI Bank** — `icici-bank/`, 16 documents

## Not reached (19)

Recorded so nobody re-tests them. No bot check was evaded to get
past any of these; a bank that refuses scripted clients is left alone.

- **AU Small Finance Bank** — 404. The savings product page does serve one unambiguous AMB figure per named product in the delivered HTML, so it is used as a cited source for min_balance_inr only; fees stay null.
- **Axis Bank** — The obvious schedule-of-charges PDF path 404s and the savings page links none in served HTML. Axis also states minimum balance only as a location-tier range (₹12,000 metro/urban, ₹5,000 semi-urban), which is several different facts about one product — so min_balance_inr stays null for Axis.
- **Bajaj Finance** — HTTP 404. The site has been restructured since these URLs were recorded on 2026-09-04; no replacement path was guessed.
- **Bandhan Bank** — HTTP 404. The site has been restructured since these URLs were recorded on 2026-09-04; no replacement path was guessed.
- **Bank of Baroda** — TLS handshake times out from this client on repeated attempts, and the savings path 404s. Left alone.
- **Canara Bank** — HTTP 404. The site has been restructured since these URLs were recorded on 2026-09-04; no replacement path was guessed.
- **Equitas Small Finance Bank** — HTTP 404. The site has been restructured since these URLs were recorded on 2026-09-04; no replacement path was guessed.
- **Federal Bank** — WAF. Every path returns HTTP 200 carrying a Radware CAPTCHA page from validate.perfdrive.com (~14 KB, zero facts) — which is why a status check alone is not enough here. Not worked around: no header was forged and no bot check evaded.
- **HDFC Bank** — Read timeout on repeated attempts — the host does not answer this client within 40s.
- **IDFC FIRST Bank** — HTTP 404. The site has been restructured since these URLs were recorded on 2026-09-04; no replacement path was guessed.
- **Post Office (India Post)** — HTTP 404. The site has been restructured since these URLs were recorded on 2026-09-04; no replacement path was guessed.
- **IndusInd Bank** — Soft 404: the site serves /in/en/404.html with an HTTP 200 status for any path it does not recognise — including the debit-card schedule-of-charges PDF its own page links to.
- **Kotak Mahindra Bank** — Reachable (HTTP 200, ~715 KB of real content) but links no schedule-of-charges PDF in the served markup — the document list is drawn client-side. The savings product page does state per-product AMB in served HTML, so that page is used as a weaker, clearly-cited source and every fee stays null.
- **Punjab National Bank** — Redirects to pnb.bank.in/Page-Not-Found.html with an HTTP 200.
- **RBL Bank** — HTTP 404. The site has been restructured since these URLs were recorded on 2026-09-04; no replacement path was guessed.
- **State Bank of India** — HTTP 404. The site has been restructured since these URLs were recorded on 2026-09-04; no replacement path was guessed.
- **Ujjivan Small Finance Bank** — Redirects to the homepage (www.ujjivansfb.bank.in/) with an HTTP 200. No product page is reachable.
- **Union Bank of India** — Redirects to /en/home?aspxerrorpath=... with an HTTP 200 — the ASP.NET error path, i.e. the page is gone.
- **Yes Bank** — HTTP 404. The site has been restructured since these URLs were recorded on 2026-09-04; no replacement path was guessed.
