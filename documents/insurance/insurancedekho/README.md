# InsuranceDekho — document index (not a fact source)

InsuranceDekho is an aggregator. It sells policies; it does not write them. So
it is used here for exactly one thing: finding IRDAI policy wordings we do not
already hold. No figure in this repo was read off an InsuranceDekho page.

That distinction is the whole point. Our insurance facts come from the policy
wording and the Customer Information Sheet — the documents that legally govern
a claim. **An aggregator's summary of a policy is not the policy.** Where an
aggregator page and a wording disagree, the wording wins, every time.

## What is here

- `documents.json` — the index: every document this source led to that was both
  authoritative and about a policy we already carry, with its UIN, its sha256,
  the URL it came from, and `mirrored_to` — the insurer directory the PDF
  actually lives in.

The PDFs are stored under each insurer's own mirror (`../aditya-birla-health/`,
`../hdfc-ergo/`, `../star-health/`), because that is where `parse_wordings.py`
and `parse_cis.py` look for them. Keeping a second copy here would double the
bytes to say the same thing twice.

## What was found, and what it was worth

The crawler (`oc-crawlers/sources/insurance/harvest_insurancedekho.py`) read
318 `/wording` pages, which resolve to **198 distinct PDFs**. Of those:

- **68** are policy wordings and **7** are Customer Information Sheets — the
  authoritative documents.
- **44** are prospectuses and **1** a brochure. These summarise a contract and
  are superseded by it, so they are recorded but never parsed for facts.
- **78** could not be classified from their own text, and **19** of the 198 are
  scanned images with no extractable text at all.
- **137** carry a UIN; **61** carry none.

Only **10** join a UIN we already hold, and **5** of those are brochures. So
**5 documents** were usable. The other **127 UIN-bearing documents are wordings
for policies this repo does not carry** — which is not a failure, it is a map
of where the catalogue could grow next.

## Why the join rate is low, honestly

InsuranceDekho indexes roughly 29 general insurers. We hold records for three
(Star Health, HDFC ERGO, Aditya Birla Health) plus six life insurers. Almost
everything it links — Future Generali, Bajaj, ICICI Lombard, Reliance, Acko,
Godigit, Niva Bupa and twenty more — is for an insurer we have no records for,
so there is nothing to join to. And all 318 wording pages are health insurance,
while 89 of our 254 records are term life, which this source cannot reach.

## The trap in this source

**Its own labels are wrong.** The same PDF is listed as both "Care Care
Brochure" and "Care Health Insurance Care". Files it calls brochures open with
"Policy Terms and Conditions"; files it calls policies are eight pages of
marketing. Every document here was therefore classified **from its own first
page**, never from the link text that pointed at it. Trusting the label would
have filed sales copy as a contract — the one mistake this pipeline exists to
prevent.

The documents are their insurers' copyright, mirrored unmodified so that a
published fact can be checked against its source. Nothing is charged for them
and they come down on request — see the LICENSE in oc-data.
