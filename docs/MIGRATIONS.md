# Migrations

This documents when and how to write an Odoo migration script in this repo,
and how to retire a module that no longer has any install base. Neither of
these was written down before — `ele_win_rate` shipped as a field-type change
with no migration, and four bridge modules (`order_bridge`, `process_bridge`,
`budget_bridge`) have been renamed with no documented cleanup path for
databases that installed them under their old name.

## When a migration script is required

A migration script is required whenever a change would leave existing
databases holding data the ORM can no longer read correctly, or would leave
Odoo unable to find a record it needs to find:

- **Field type change** — e.g. a `Float` field becoming a `Boolean`. Odoo's
  auto-migration on module upgrade does not convert existing column data to
  the new type; on Postgres it can outright fail to alter the column, or
  silently produce garbage values.
- **Field rename or removal** — the ORM has no way to know the old column
  held the same data as the new field name; without a script, existing
  values are orphaned or lost.
- **Module rename** — Odoo tracks installed modules by name in
  `ir_module_module`. A rename with no bridging leaves an existing
  install permanently pointed at a module name that no longer exists in
  the addons path.
- **Table/column rename via bridge/anchor re-namespacing** — when two
  modules extending the same shared model previously collided on a
  generic column name (e.g. both adding `budget_id`) and each is given
  its own namespaced field instead.

### Real precedent in this repo

`product/commodity_trading/ele_trading_budget/migrations/19.0.1.0.1/pre-migrate.py`
and `custom/omnifreight/omni_budget/migrations/19.0.1.0.1/pre-migrate.py` both
handle the same underlying problem: `operations.budget.line` used to get a
`budget_id` anchor column from whichever of `ele_trading_budget` or
`omni_budget` was installed, so the two modules could never coexist in one
database. Each bridge now adds its own namespaced anchor
(`trade_budget_id` / `mrp_budget_id`), and each module's pre-migrate script
renames its own column in place, guarded so it is a no-op if the column has
already been renamed (fresh install) or belongs to the other module.

Read both scripts before writing a new one. The pattern to match:

- Guard on `if not version: return` — a fresh install has no prior version
  to migrate from, so `migrate()` should do nothing.
- Check `information_schema.columns` before touching anything — never
  assume the old column exists.
- Check the target column doesn't already exist before renaming — makes
  the script safe to run more than once.
- Use `ALTER TABLE ... RENAME COLUMN` (or `ALTER COLUMN ... TYPE`) directly
  against the database, plus an `ir_model_fields` update if the field's own
  `name` also changed (not needed for a type-only change).

## Where scripts live

Odoo's standard layout, keyed to the manifest version that **first ships**
the breaking change:

```
<module_name>/migrations/<version>/pre-migrate.py
<module_name>/migrations/<version>/post-migrate.py
```

`pre-migrate.py` runs before the module's own `-u` upgrade logic (field
declarations, views, etc.) is applied; `post-migrate.py` runs after. A raw
column rename or type change belongs in `pre-migrate.py`, before Odoo's own
auto-migration has a chance to see the old schema and get confused by it.

**The version in the migrations/ path must match a version that is actually
set in `__manifest__.py`.** Odoo only runs a migration script when it
notices, during `-u`, that the module's currently-installed version in
`ir_module_module` is older than the version declared in the manifest, and
it walks every intermediate `migrations/<version>/` folder between the two.
If the manifest version is never bumped, the script sits in the tree
unused and silently never runs — this is the exact gap that let
`ele_win_rate` ship as a field-type change with no migration: the schema
changed, but nothing told Odoo a migration was owed.

## Version scheme

This repo uses `19.0.x.y.z`. Bump the **last segment** for a schema-affecting
patch that needs a migration script, e.g. `19.0.1.0.0` → `19.0.1.0.1`, matching
the precedent above. Reserve the earlier segments for larger, deliberate
version bumps (major Odoo version, module rewrite, etc.).

## Orphaned module cleanup runbook

Use this whenever a module is renamed or retired with zero (or believed-zero)
install base, to confirm that and remove its stale `ir_module_module` record
cleanly rather than leaving it to be silently reinstalled under its old name
on a future upgrade. `<module_name>` below is a placeholder — this has
already recurred for `order_bridge` → `dispatch`, `process_bridge` →
`workflow`, and `budget_bridge` → `budget_flag`, and will recur again.

1. Confirm the old name is genuinely gone from the addons path — if
   `<module_name>` still resolves to real module code somewhere on
   `--addons-path`, this is not a cleanup, it's a live module; stop.
2. Connect to the target database with a real Odoo shell:
   ```
   odoo-bin shell --no-http -d <db_name> --addons-path=<addons_path>
   ```
3. Inside the shell, find the stale record and uninstall it:
   ```python
   module = env['ir.module.module'].search([('name', '=', '<module_name>')])
   module.button_immediate_uninstall()
   ```
   `button_immediate_uninstall()` is the same call the UI's "Uninstall"
   button makes — it drops the module's own tables/columns and removes its
   `ir.model.data` records, so this is the real uninstall path, not a
   shortcut around it.
4. Confirm no orphaned data remains: re-query `ir_module_module` for the
   module name and check its `state`, and spot-check for any table or
   column that module used to own.

`tools/cleanup_orphaned_module.sh` wraps steps 1–3 for the common case (see
that script for its own addons-path guard and preconditions).

## PR checklist addition

There is no `.github/` pull request template in this repo to add this to, so
it is documented here instead:

- **Does this diff change a field's type or name, or rename a module? If
  yes, is there a matching `migrations/` script in the same PR, and has the
  version it's keyed to actually been bumped in `__manifest__.py`?**

`tools/check_migration_coverage.py` gives a partial, automated check of the
field-type-change half of this (see that script's docstring for what it does
and does not catch); the module-rename half still needs a human to catch it.
