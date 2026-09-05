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

Refresh with `python3 tools/cards/fetch_mitc.py`; issuer URLs are in
`tools/cards/mitc_sources.json`.

## Licence

These documents are the property of the issuing banks. See the repository
[LICENSE](../../../LICENSE) — they are stored unmodified, nothing is charged
for them, and they come down on request. The facts extracted from them into
`products/cards/` are ODbL and yours to take.
