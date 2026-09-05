# Credit card MITCs

The Most Important Terms and Conditions document for each issuer, as published
by the issuer, dated and hashed on every fetch.

RBI requires issuers to publish an MITC, and it is where a card's real fees
live: the joining and annual fee, the interest rate, the forex markup, the
cash-advance charge, the late-payment bands. A brochure will tell you a card
is "lifetime free"; the MITC tells you what happens when it is not.

## The change log is the point

Issuers revise fees, caps and benefits quietly. Nobody keeps a dated record of
what the document said last year, so nobody can show that a fee went up. This
does: `index.json` holds the hash, the size and the date of every version
fetched, so a change is a fact with a date on it rather than something a
customer notices on a statement.

Refresh with `python3 sources/mitc/fetch_mitc.py` (in oc-crawlers); issuer URLs
are in `sources/mitc/mitc_sources.json`.

## A stored document must actually be a document

Fourteen of the fifteen issuer URLs here were wrong until 2026-09-05: they had
been guessed from patterns like `<bank>.com/pdf/mitc.pdf`, and twelve simply
404ed. Two were worse than a 404 — `yesbank.in/pdf/mitc_creditcards.pdf` and
`indusind.com/.../mitc.pdf` returned an HTML error page and a JavaScript shell,
which the fetcher's 2,000-byte size floor happily accepted and indexed as real
documents. A 5,640-byte challenge page sat in this directory labelled as Yes
Bank's MITC.

So the acceptance test is now content, not size or filename: a response is
stored only if it starts with the `%PDF` magic and runs to at least 3 KB. And
the URLs were re-derived by scanning each issuer's own card pages for links
whose text says "most important terms", rather than by guessing paths.

RBI has moved Indian banks onto `.bank.in` hostnames, but not uniformly — some
issuers serve from both, some never moved their asset host — so each URL is
verified individually and carries its own `checked` date.

## Licence

These documents are the property of the issuing banks. See the repository
[LICENSE](../../../LICENSE) — they are stored unmodified, nothing is charged
for them, and they come down on request. The facts extracted from them into
`products/cards/` are ODbL and yours to take.
