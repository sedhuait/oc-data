# SCOPE — what belongs in this dataset

This repo is the **fact layer** of Open Catalogue: things about a product that are
still true in a year. Prices, stock and price history are **not** here — they live in
the live service, because they expire.

## The three tests

A product is in scope only if **all three** hold.

1. **Static fact sheet.** Its attributes are fixed properties of the thing, not of the
   listing. A serum's ingredients, a phone's chipset, an AC's capacity. If the only
   "facts" are colour and size, it fails.
2. **Discriminating.** The facts distinguish it from its neighbours in the same
   category. Every kurta is cotton; that tells a buyer nothing. SPF 50 vs SPF 30 does.
3. **Identity across stores.** The same product can be recognised on a brand site, a
   marketplace, and a shelf. One-off, made-to-order and seasonal goods cannot.

Prices moving is expected and welcome — that's the point of the live layer. What must
not move is the fact sheet.

## In scope

Beauty and personal care · packaged food and nutrition · supplements · appliances ·
electronics, phones, laptops · tools and hardware · tyres and auto parts · pet food ·
baby care · financial products (cards, deposits, funds, insurance — fees and terms are
facts).

## Out of scope

Apparel and footwear (except spec'd athletic footwear) · home decor and furnishing ·
furniture · jewellery and watches below the enthusiast tier · toys · bags and luggage ·
stationery · books, music and film · handmade and artisanal goods · second-hand and
refurbished · fresh produce and meat · restaurant menus · flights, hotels and tickets ·
prescription medicines · generic marketplace accessories (cases, cables, screen guards).

These are excluded because they fail test 1, 2 or 3 — not because they're unimportant.
An "opinionated" product is fine if objective facts sit underneath the opinion
(sunscreen, phones, credit cards all qualify). A product is out when stripping the
taste away leaves an empty row.

## Required fields

Each category's schema in `/schemas` declares `required`. A record missing them is a
**candidate**, not an entry, and does not get merged. Incomplete records are welcome as
PRs marked `status: candidate` — they become the contribution queue.

## Provenance

Every fact carries where it came from and when it was checked. A record with no
`sources` fails validation. We publish uncertainty rather than hiding it:
`confidence: extracted` is honest, a confident wrong value is not.

## What a brand may do

A brand may **add** facts about its own products and correct errors, with evidence.
A brand may **not** remove an unflattering fact, reword an ingredient list, or change
another brand's record. Brand-submitted records are labelled `source: brand`.

## Changing this file

Scope is decided by PR like everything else. If you think a category passes the three
tests, open one and argue it.
