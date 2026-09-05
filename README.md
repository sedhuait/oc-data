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
src/schema.ts                          the TypeScript types — one source of truth
src/validate.ts                        the checks CI runs on your PR
src/format.ts                          canonical formatting — run before you commit
src/*.test.ts                          tests proving each check fires
tools/                                 crawlers and importers (Python, not needed to contribute)
```

TypeScript, no build step and no dependencies — Node 22.6+ runs `.ts` directly.

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

## What needs doing

**[NEEDS-WORK.md](NEEDS-WORK.md)** is generated from the data: every missing fact,
ranked by how many records it affects and which brands. About half the catalogue
is marked `candidate` — published honestly, with a fact we could not verify left
empty. Those are not mistakes, they are the queue.

Regenerate it with `npm run gaps`.

## Contributing

Anything from a one-word typo fix to a new brand file is welcome.

1. **Fix a fact.** Edit the line, add a source with today's date, open a PR.
2. **Add a product.** Copy the shape above. Don't invent an `id` — run
   `npm run mint -- "Brand" "Product name" "30 ml"`.
3. **Add ingredients.** The most valuable contribution we have. Most brands publish INCI
   as an image, so this needs a human. Type what's on the pack, in order, and link a
   photo or the product page in `sources`.
4. **Add a category schema.** Pick something in scope that we don't cover — tyres, pet
   food, FDs — and write `schemas/<domain>.json`. Decide which facts matter. That's a
   real design decision and it's yours to make.

Before you push:

```bash
npm run format     # canonical order and shape
npm run validate   # the same checks CI runs
npm test           # or just: npm run check
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

### Source documents in `documents/`

Some facts can only be checked against the document they were read from — a policy
wording, an MITC, a scheme information document. Where we mirror one, it lives under
`documents/<domain>/<issuer>/` alongside a manifest recording the URL it came from.

**Those files are not ours and are not ODbL.** Each remains the copyrighted property of
the issuer or manufacturer that published it — the insurer, the bank, the AMC, the brand.
We claim no ownership and grant no licence over them.

What we undertake:

- **They are unmodified.** Every file is stored byte-for-byte as the publisher served it.
  The manifest records each source URL, so anyone can re-download and compare.
- **We make no money from them.** No advertising, no sponsorship, nothing sold, no
  placement for sale — the project's whole premise. They are mirrored so that a published
  fact can be verified against its source, and for no other purpose.
- **We remove on request.** If a publisher would rather their documents were not mirrored
  here, they come out on request. The manifest of source URLs stays, so the facts remain
  checkable against the publisher's own site.

This is fair dealing for the purpose of verifying published facts, under §52 of the
Copyright Act, 1957.

**The facts extracted from them are a separate matter, and those are open.** A waiting
period, a fee, an ingredient, a capacity is a fact, and facts are not copyrightable in
India (*Eastern Book Company v. D.B. Modak*, 2008). Everything under `products/` is ODbL
and yours to take.
