# Credit cards

Every number in `products/cards/` comes from the issuer's **Most Important Terms
and Conditions** — the document the RBI requires them to publish. If a figure is
not in one of those documents, it does not go in a record.

## The pipeline

```
tools/cards/mitc_sources.json     where each issuer publishes its MITC
tools/cards/fetch_mitc.py         fetch, hash, store, and report what changed
tools/cards/parse_<issuer>.py     one parser per issuer — their tables all differ
tools/cards/mitc/<slug>/          every version we have ever fetched, dated
```

`fetch_mitc.py` is the important one. It stores each document with its date and
hash, so when an issuer quietly revises a fee or halves a lounge allowance, the
next fetch reports it and `--diff` shows exactly what changed. **That dated
change log is the thing no comparison site keeps**, and it is why this is worth
doing properly rather than scraping a marketing page.

## Why parsing is only half the job

These are PDFs of merged-cell tables, not data. Reading them by regex gets the
wrong number the moment a cell spans two rows — we tried, and it produced
"Diners Black: ₹5". The parser now slices by **column position** derived from the
table header, which is correct where the layout holds and blank where it does not.

So the rule is: **a merged or ambiguous cell becomes a `candidate` with the fee
left null, never an inherited or guessed number.** A missing fee is a task. A
wrong fee is a broken promise.

Realistically each issuer needs its own parser plus a human reading the document
once — budget one to two hours per issuer for the first pass. After that the
diff does the work.

## Contributing

The most useful things you can do here, in order:

1. **Fix a `mitc_sources.json` URL.** Twelve of the fifteen 404 right now because
   they were guessed. One correct URL unlocks a whole issuer.
2. **Verify a `candidate`.** Open the linked MITC, read the fee off the table,
   fill it in, set `"confidence": "verified"`, and say in `sources[].note` which
   page you read it from.
3. **Write a parser for another issuer.** Copy `parse_hdfc.py`; the column-slicing
   approach transfers, the column names will not.
4. **Add the conditional benefits.** Reward rates, caps and lounge conditions live
   in `options[]`. A benefit without its cap is a marketing claim, not a fact.
