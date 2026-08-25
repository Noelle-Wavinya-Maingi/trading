# Order Confirmation Bridge Mixin

Shared template for the "confirm an order → derive an industry operational
record" flow, so it's implemented once instead of once per vertical.

## Depends on
`sale`, `purchase`

## Design principle

`order.bridge.mixin` supplies the four-step skeleton — filter qualifying
lines, group them, create-or-update the target record per group, link back —
since that shape is identical everywhere it's needed. What genuinely differs
per vertical (which lines qualify, how they're grouped, what fields map to
what) stays as required overrides via a **registered definition**, not a
hook method the including model overrides directly.

| Method | Purpose |
|---|---|
| `_bridge_definitions()` | Return the list of definitions this model registers. Base case: empty list. |
| `_bridge_run_definition(definition)` | Run one definition's filter → group → create-or-update → link cycle. |
| `_bridge_sync()` | Run every registered definition and return their combined results. |
| `_bridge_default_create(record_model, vals)` | Default record creation; override if a vertical needs custom creation logic. |

A definition is a plain dict of callables: `qualifying_lines`, `group_lines`,
`find_existing`, `vals`, `record_model`, `create` (optional), `link`.

**Register, don't override.** Include the mixin via `_inherit`, then append
your own definition from `_bridge_definitions()`:

```python
def _bridge_definitions(self):
    return super()._bridge_definitions() + [self._my_bridge_definition()]
```

Never replace the list outright — another vertical extending the same order
model (`sale.order`, `purchase.order`) may have already registered its own
definition, and replacing the list drops it silently.

**Current consumers:** `ele_trading` (`sale.order`, `purchase.order` →
`trading.trade`) and `omnifreight`'s `omni_ops`/`quotation` (`sale.order` →
freight operational records).

## Automated tests

`tests/test_order_bridge_mixin.py` (module `dispatch`)
exercises the registry mechanism against
`order.bridge.test.host` — a test-only model living in `models/` (not
`tests/`, since Odoo builds its registry before importing test modules, so a
model defined only in a test file never actually joins it). It proves two
independently registered definitions both run on the same host, and that an
existing record is updated rather than duplicated — the exact shape of bug
that motivated the registry pattern over a bare hook-method override.
