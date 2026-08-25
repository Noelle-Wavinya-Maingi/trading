# Onboarding a new vertical

Status: process reference, not a proposal. This describes how to add a new
industry vertical (or a new client's bespoke module) to this repository using
the mechanisms already built and tested, not new ones.

The goal of this document is to make the decision process repeatable —
someone other than the person who designed `shared/` should be able to follow
it and get the placement and wiring right on the first attempt.

---

## 1. Decide where the new code belongs

Ask these three questions, in order, and stop at the first "yes":

1. **Is this tied to one specific client, and not reproducible for another
   client in the same industry?** → `custom/<client>/`.
2. **Does it need knowledge of a specific business domain to make sense at
   all** (a trade, a freight file, a production order)? → `product/<line>/`.
3. **Does it need zero industry knowledge — would it work identically for a
   trading company, a freight forwarder, or a bakery?** → `shared/`.

If you land on `shared/`, that's a claim, not a fact yet — see step 4.

## 2. If it needs to plug into existing shared behavior, register — don't override

`shared/order_bridge`, `shared/budget_bridge`, and `shared/process_bridge`
each expose a hook that returns a list (`_bridge_definitions()`,
`_anchor_providers()`) rather than a single method to override outright.
Extend it like this:

```python
def _bridge_definitions(self):
    return super()._bridge_definitions() + [self._my_new_bridge_definition()]
```

**Always call `super()` and append. Never replace the list.** Two verticals
independently overriding the same hook without `super()` is a real bug that
already happened once in this repository (`order.bridge.mixin` and
`operations.budget.line` both hit it) — the registry pattern exists
specifically to prevent a repeat, and it only works if every consumer follows
this shape.

You don't have to take this on faith: `order.bridge.test.host`,
`process.bridge.test.host`, and `budget.bridge.test.host` (in each bridge
module's `tests/`) are synthetic, independent consumers built specifically to
prove the registry correctly runs every registered definition without one
clobbering another — proof the mechanism generalizes, not just a claim that
it should.

## 3. Namespace anything you add to a genuinely shared model

If your vertical adds an anchor field to `operations.budget.line` (or any
other model multiple verticals extend), it needs a name unique to your
domain — never a generic name like `budget_id`.

This is not a style preference. `ele_trading_budget` and `omni_budget` both
originally used `budget_id` pointing at different models; the two verticals
could never be installed together, and any `related=` path through the
loser failed at registry build with an opaque `KeyError`. They are now
`ele_trade_budget_id` and `mrp_budget_id` respectively — see
[shared/budgets/README.md](../shared/budgets/README.md) for the full naming
rule.

Some field names are the opposite case — required to stay **identical**
across every vertical, because a bridge mixin's own `@api.depends()`
hardcodes them (`budget_ids`, `budget_id`, `step_ids`). Check the relevant
bridge's README before renaming anything it depends on.

## 4. Prove the placement claim from step 1

If you decided something belongs in `shared/`, prove it: install that module
alone, in a database with no vertical present, and confirm it installs and
its own tests pass with nothing else pulled in. This is exactly what
`tools/verify_boundaries.sh` already automates for every existing `shared/`
module.

Add your new module to that script:
- If it's `shared/`: add a scenario asserting it installs alone, pulling in
  none of the existing verticals.
- If it's `product/` or `custom/`: add it to the "verticals coexist" scenario
  — install it alongside the existing verticals (`ele_trading`,
  `ele_trading_budget`, `omni_ops`, `omni_budget`, `quotation`) and run every
  vertical's own test suite together in one database. This is what actually
  proves your new registration doesn't collide with an existing one, rather
  than merely not crashing on its own.

## 5. Confirm nothing existing had to change

The whole point of the bridge pattern is that onboarding a new vertical is
additive. If step 2 required editing `ele_trading`, `omni_ops`, or any
`shared/` module's existing logic (not just appending a new registration),
that's a signal the bridge's contract is missing something — fix the
contract in the shared bridge module itself, generically, rather than
special-casing your vertical into someone else's code.

## Worked example (hypothetical, not implemented)

A new manufacturing client needs budget tracking like trading and freight
already have:

1. Placement: is it one client's bespoke need, or resellable to any
   manufacturing client? Decide `custom/<client>/` or a new
   `product/manufacturing/` accordingly — not `shared/`, since it clearly
   needs manufacturing-domain knowledge to make sense.
2. The new module `_inherit`s `budget.bridge.mixin` (if it needs
   `has_budget`/`budget_state`) and `budget.document.mixin` (for its own
   budget header model), registering an anchor provider on
   `operations.budget.line` via `_anchor_providers()`, following the same
   shape as `ele_trading_budget`'s `operations_budget_line.py`.
3. The anchor field gets a unique name — `mfg_budget_id`, not `budget_id`.
4. `verify_boundaries.sh` gains a line installing the new module alongside
   `ele_trading_budget` and `omni_budget`, confirming all three coexist.
5. No existing file changes — `shared/budgets`, `ele_trading_budget`, and
   `omni_budget` are all untouched by this addition.
