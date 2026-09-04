# Open Catalogue — data

The **fact layer** of [opencatalogue.in](https://opencatalogue.in): what a product *is*.
Ingredients, specs, size, identity. Open data, ODbL, anyone can contribute.

Prices, stock and price history are **not** in this repo. They change daily and live in
the service. What's here should still be true in a year.

**1,237 records · 13 brands · beauty and personal care.** Early days.

---

## Layout

```
products/<domain>/<brand-slug>.jsonl   one JSON object per line, one file per brand
schemas/product.json                   the record shape every entry must match
schemas/<domain>.json                  which facts each category needs, with units and ranges
SCOPE.md                               what belongs here and what doesn't
scripts/validate.py                    the tests CI runs on your PR
scripts/format.py                      canonical formatting — run before you commit
```

A record looks like this:

```json
{"id":"oc_4f2a91c07b3e","name":"Niacinamide 10% Face Serum","brand":"Minimalist",
 "domain":"beauty","category":"Face serum","size":"30 ml",
 "attributes":{"size":"30 ml","actives":["Niacinamide","Zinc"],"skin":["Oily","Acne-prone"]},
 "ingredients":["Aqua","Niacinamide","Zinc PCA","..."],
 "identifiers":{"gtin":null,"shopify_handle":"niacinamide-10-face-serum"},
 "urls":{"brand":"https://beminimalist.co/products/..."},
 "status":"entry","confidence":"verified",
 "sources":[{"kind":"brand-store","url":"https://...","checked":"2026-09-04"}]}
```

## Contributing

Anything from a one-word typo fix to a new brand file is welcome.

1. **Fix a fact.** Edit the line, add a source with today's date, open a PR.
2. **Add a product.** Copy the shape above. Don't invent an `id` — run
   `python3 scripts/mint_id.py "Brand" "Product name" "30 ml"`.
3. **Add ingredients.** The most valuable contribution we have. Most brands publish INCI
   as an image, so this needs a human. Type what's on the pack, in order, and link a
   photo or the product page in `sources`.
4. **Add a category schema.** Pick something in scope that we don't cover — tyres, pet
   food, FDs — and write `schemas/<domain>.json`. Decide which facts matter. That's a
   real design decision and it's yours to make.

Before you push:

```bash
python3 scripts/format.py     # canonical order and shape
python3 scripts/validate.py   # the same checks CI runs
```

### The rules that matter

- **Facts only.** No scores, no rankings, no "best for". If it's a judgment, it doesn't
  belong in a record.
- **Say where it came from.** Every record needs at least one source with a date. A
  record with no provenance fails validation.
- **Never delete a fact to flatter a brand.** Corrections need evidence. Brands are
  welcome here and are labelled `brand-submitted`; they can add and correct, not remove.
- **Incomplete is fine, wrong is not.** Missing required fields? Mark
  `"status":"candidate"` and it merges as a known gap rather than a false entry.
- **`extracted` means a machine read it.** Only mark `verified` if a human checked it
  against the pack or the brand's own page.

## Where the data comes from

Brands' own public storefronts, marketplace catalogues, packaging photographs, and
people. Every record says which. The crawler and the browser extension propose new
facts continuously; those arrive as a bot PR on the 1st of each month, which you're
welcome to review.

## Licence

Data: [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/) — use it, including
commercially. Attribute Open Catalogue, and if you publish a derived database, publish
it open too. Scripts: MIT.

If this project ever starts ranking, scoring or selling placement, fork this repo. It's
why the data is here.
