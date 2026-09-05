# Star Health — source documents

Every file here was downloaded from the insurer's own downloads page,
<https://www.starhealth.in/downloads/>, on 2026-09-05. They are kept in the
repo so that any fact recorded about a Star Health policy can be checked
against the document it was read from, by anyone, without asking us and
without trusting us.

That is the whole point of a fact registry. A claim like "room rent capped at
1% of sum insured" is worth nothing on its own; it is worth something when the
wording that says so is one click away and everyone can see the same page.

## What is here

- `documents.json` — every document on the page: the product it belongs to,
  its IRDAI UIN where the title carries one, its type, the file in this
  directory, and the URL it came from.
- `products.json` — one entry per policy (92 of them), with its UIN, the
  oc-data category it maps to, and links to each of its documents.
- `*.pdf` — the documents themselves, filenames as served by the insurer's CDN.

## Document types, and which one wins

An insurer publishes several documents per policy and they do not carry equal
weight:

| Type | What it is |
|---|---|
| **Policy Clause** | The contract. This is what a claim is settled against, and the only document that decides anything. |
| Customer Information Sheet | IRDAI-mandated summary of the main terms. Useful, not binding. |
| Prospectus | The product as filed with IRDAI. |
| Brochure | Marketing. Simplified, selective, and superseded by the wording wherever the two differ. |
| Proposal | The form a buyer fills in. |

When recording a fact, read the **policy wording**. If a brochure and a wording
disagree, the wording is right and the brochure is a sales document.

## Licence — what is ours and what is theirs

This matters because of the promise this project makes. The registry says its
data is ODbL and that anyone may take it and use it without asking. That
promise has to be exactly true, which means being precise about which part of
this directory it covers.

**The facts are ours to give away, and we do.** A waiting period, a room-rent
cap, a co-pay percentage, a sum insured — these are facts, and facts are not
copyrightable in India (*Eastern Book Company v. D.B. Modak*, 2008). Every
figure extracted from these documents into `products/insurance/` is ODbL, free
for anyone to take, republish and build on. That is this project's own work.

**The documents belong to the insurer.** Every PDF in this directory is the
copyrighted property of **Star Health and Allied Insurance Co Ltd**. We claim
no ownership of them and grant no licence over them.

Our undertaking, plainly:

- **We do not modify them.** Each file is stored byte-for-byte as the insurer
  served it, under the filename their own CDN used. `documents.json` records
  the source URL of every one, so anyone can re-download and compare.
- **We do not charge for them, and we make no money from them.** There is no
  advertising on this project, nothing is sponsored, and no part of it is sold.
  These files are mirrored for one reason: so that a fact we publish can be
  checked against the document it was read from.
- **We remove on request.** If Star Health would rather these were not mirrored
  here, tell us and they come out; the manifest of source URLs stays, so the
  facts remain checkable against the insurer's own site.

This is fair dealing for the purpose of verifying published facts, under §52 of
the Copyright Act, 1957. Star Health's own Terms of Usage reserve their rights,
and we are not disputing that — we are recording it:

> Star Health reserves its right to seek appropriate legal remedy for any
> violation or breach of any intellectual property rights including but not
> limited to unauthorized use of any trademarks, logos, slogans, service marks
> and contents of this website.
> — <https://www.starhealth.in/terms-of-usage/>

**So, concretely.** Take the facts and do anything you like with them; that is
what they are here for. The documents are the insurer's, mirrored unmodified as
evidence — if you want to redistribute those, get them from the insurer, and
every source URL is in `documents.json`.

## Refreshing

Insurers revise wordings without renaming them. `documents.json` records the
URL each file came from; re-fetching those URLs and comparing is how you find
out that a waiting period changed. A changed document is a fact to re-check,
not a file to quietly overwrite.
