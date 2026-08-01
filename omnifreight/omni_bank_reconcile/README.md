# Bank Reconciliation Match Quality

Classifies each bank statement line by how confidently it reconciles, so a
reviewer can skip the obvious ones:

- **Perfect** — every journal item is backed by an invoice/bill, or the line is
  recognisable as a bank fee, internal transfer or forex movement (things that
  legitimately have no invoice).
- **Partial** — anything else, needing review.

## Depends on
`account`

That is the whole dependency list. **No freight, manufacturing or budgeting
dependency** — this module only extends `account.bank.statement.line` and is
usable by any client on any chart of accounts.

## Why this is a separate module

It was buried inside `omni_ops`, a 3,800-line freight module, despite having
zero freight coupling — so no other client could use it. Extracting it was the
cleanest of the `omni_ops` splits: the code moved unchanged, and the module
installs on a bare database pulling in nothing but `account`.

## Configuration (Settings → Bank Reconciliation)

The values it matches on were hardcoded — and were Belgian- and English-specific.
They are now per-company settings, each falling back to the original literal so
an existing database behaves identically until configured.

| Setting | Falls back to | Why it matters |
|---|---|---|
| Reconciliation Tolerance Accounts | codes `655000` / `755000` | chart-of-accounts specific; the defaults are Belgian and will misclassify elsewhere |
| Bank Charge Patterns | 15 built-in English regexes | bank- and language-specific |
| Internal Transfer Keywords | 6 built-in English keywords | bank- and language-specific |

Patterns and keywords are one per line; blank lines are ignored.

## Automated tests

`tests/test_reconcile_config.py` asserts both halves of every setting — the
historical literal when unset, the configured value when set — plus an
end-to-end check that tolerance detection on the statement line honours the
configured accounts rather than the defaults.
