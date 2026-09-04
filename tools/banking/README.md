# Banking, deposits and debit cards

Two different things live here, and the split matters:

- **The repo** holds what a product *is* — account type, minimum balance, DICGC
  cover, premature-withdrawal terms, and for debit cards the fees, limits, lounge
  visits and bundled insurance.
- **The service** holds the interest rate and its history. Rates move monthly; a
  rate in a Git repo is stale the week you commit it.

## Sources

`rate_sources.json` lists 20 institutions with three page types each:
`savings`, `fd_rates` and `debit_cards`. `fetch_rates.py` snapshots any of them:

```bash
python3 tools/banking/fetch_rates.py                  # FD rate pages
PAGE=savings      python3 tools/banking/fetch_rates.py
PAGE=debit_cards  python3 tools/banking/fetch_rates.py
python3 tools/banking/fetch_rates.py --diff icici-bank
```

Each page is stored dated and hashed, so a savings-rate cut or a quiet change to
the free-ATM-transaction limit shows up as a diff on the next run. That change
signal is worth more than the snapshot itself.

Current state: 9 of 20 FD pages and 10 of 20 debit card pages fetch. The rest are
guessed URLs that 404 — **fixing one is the most useful thing you can do here.**

## Why debit cards sit under banking

Nobody chooses a bank for its debit card; the card arrives with the account. So a
debit card is modelled as a category under the issuing bank, not a domain of its
own — the same way a variant sits under a product.

They are worth recording for three facts people never see:

1. **The fees.** Annual fee charged whether or not you use the card, and the
   per-transaction fee once the free ATM limit is used up. Small, frequent, ignored.
2. **Lounge access.** Several premium debit cards carry domestic lounge visits the
   holder never learns about. ICICI's debit card page mentions lounges 246 times;
   almost no cardholder could tell you their own allowance.
3. **Bundled accident cover.** Real money, rarely claimed, and usually conditional
   on having used the card recently — record the condition, not just the number.

## What still needs doing

The pages carry the data; getting it out needs a parser per bank, because every
bank lays its fee table out differently. Same lesson as the credit card MITCs:
regex over flattened text guesses wrong, so parse by table structure and leave a
field null rather than publishing a number you inferred.
