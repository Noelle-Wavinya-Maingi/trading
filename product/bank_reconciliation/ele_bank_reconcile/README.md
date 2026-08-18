# Bank Reconciliation Match Quality

Classifies each bank statement line by how confidently it reconciles, so a
reviewer can skip the obvious ones:

- **Perfect** — every journal item is backed by an invoice/bill, or the line is
  recognisable as a bank fee, internal transfer or forex movement (things that
  legitimately have no invoice).
- **Partial** — anything else, needing review.

## Depends on
`account`, `account_accountant`

**Requires Odoo Enterprise.** Community ships the underlying data
(`account.bank.statement.line`, a generic `reconcile()` method on journal
items) but no UI at all to reconcile a bank statement line — that entire
workflow, the Bank Matching widget, lives in `account_accountant`
(`OEEL-1` licensed, `"Bank synchronization (Enterprise)"` per its own
manifest). Without it there's no reconciliation for this module's
classification to sit on top of, so depending on it directly is the honest
choice rather than pretending to be Community-standalone.

That Enterprise dependency buys real inline UI: `static/src/xml/statement_line.xml`
patches the Bank Matching widget's own "Reconciled" badge (an OWL/QWeb
template, `account_accountant.BankRecStatementLine`) to show green for a
Perfect match and orange for Partial, right where you're already
reconciling — no separate screen to check.

## Configuration (Settings → General Settings → Accounting → Bank & Cash)

The values it matches on are per-company settings, each falling back to a
built-in default so an unconfigured database still works.

| Setting | Falls back to | Why it matters |
|---|---|---|
| Reconciliation Tolerance Accounts | codes `655000` / `755000` | chart-of-accounts specific; the defaults are Belgian and will misclassify elsewhere |
| Bank Charge Patterns | 15 built-in English regexes | bank- and language-specific |
| Internal Transfer Keywords | 6 built-in English keywords | bank- and language-specific |

Patterns and keywords are one per line; blank lines are ignored.

## Automated tests

`tests/test_reconcile_config.py` asserts both halves of every setting — the
built-in default when unset, the configured value when set — plus an
end-to-end check that tolerance detection on the statement line honours the
configured accounts rather than the defaults.
