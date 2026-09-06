# Aditya Birla Health — source documents

Two policy wordings, located through the InsuranceDekho aggregator and
downloaded from the CDN it links to. They are here so that a fact recorded
about one of these policies can be checked against the document it was read
from.

Aditya Birla's own downloads page is not reachable by a polite HTTP client, so
this repo's 30 Aditya Birla records were built from a product listing page with
no document behind any of them. These are the first two that have one.

- `documents.json` — the index: product, UIN, document type, sha256, source URL.
- `proposed-facts.json` — every field `parse_wordings.py` read, with the exact
  sentence, the page, and a confidence marker. Two proposals were REJECTED by
  audit and the reason is recorded there rather than silently dropped.
- `*.pdf` — the documents, filenames as served by the CDN.

The aggregator was the index; the wording is the authority. No figure here was
read from an aggregator page.
