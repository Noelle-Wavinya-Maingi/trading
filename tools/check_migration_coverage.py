#!/usr/bin/env python3
"""Flags a field whose fields.<Type> changed between the base branch and this
diff with no accompanying migrations/ script in the same module -- the exact
gap that let ele_win_rate ship as a Float-to-Boolean change with no
migration, silently leaving any pre-existing database's column unreadable
or wrong after upgrade.

This does not run inside a live Odoo registry (no import of odoo, no
database) -- it is a static AST diff over the two versions of each changed
.py file, intentionally cheap enough to run on every PR. It only compares
field type at a fixed field name; it does NOT attempt to detect a field
being renamed or removed (the old name simply disappears from the new
AST, which this script cannot distinguish from "that field was deleted and
nobody cares" without deeper renaming-intent analysis), so this is a smoke
check on the type-change half of docs/MIGRATIONS.md's checklist, not a
proof that every diff needing a migration has one.

It also only recognizes a literal `fields.<Type>(...)` call as a field
definition. A field type expressed indirectly -- e.g. a module-level
`BOOL_TYPE = fields.Boolean` alias later used as `x = BOOL_TYPE()` -- is not
recognized at all, so a type change made through that pattern is a silent
false negative, the same way a rename or removal is. Write field
definitions as direct `fields.<Type>(...)` calls if you want this check to
see them.

Usage:
    python3 tools/check_migration_coverage.py [--base <git-ref>]

Exits 1 and prints every field whose type changed with no matching
migrations/ file in the same diff, 0 otherwise.
"""
import argparse
import ast
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCAN_ROOTS = ("shared/", "product/", "custom/")


def run(cmd):
    return subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)


def default_base():
    """Same intent as verify_boundaries.sh/check_extension_collisions.py's
    CI usage: compare against origin/main when it exists (a PR's actual
    merge base), falling back to a local main for a dev checkout that has
    no 'origin' configured."""
    for ref in ("origin/main", "main"):
        if run(["git", "rev-parse", "--verify", ref]).returncode == 0:
            return ref
    return "HEAD"


def changed_files(base):
    result = run(["git", "diff", f"{base}...HEAD", "--name-only"])
    if result.returncode != 0:
        result = run(["git", "diff", base, "--name-only"])
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def show(base, path):
    result = run(["git", "show", f"{base}:{path}"])
    return result.stdout if result.returncode == 0 else None


def module_name_for(path_str):
    """First path segment under a scan root is the addon's directory name,
    which is also its technical module name in every addon here -- same
    convention check_extension_collisions.py relies on."""
    parts = Path(path_str).parts
    if parts[0] == "shared":
        return parts[1] if len(parts) > 1 else None
    return parts[2] if len(parts) > 2 else (parts[1] if len(parts) > 1 else None)


def module_root(path_str):
    parts = Path(path_str).parts
    if parts[0] == "shared":
        return "/".join(parts[:2]) if len(parts) > 1 else None
    return "/".join(parts[:3]) if len(parts) > 2 else None


def _const_str(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def fields_type_name(call_node):
    """Given a `fields.X(...)` call node, return 'X', or None if this isn't
    a call to something under the fields module."""
    if not isinstance(call_node, ast.Call):
        return None
    func = call_node.func
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id == "fields":
        return func.attr
    return None


def extract_field_types(source):
    """fieldname -> fields.<Type> class name, for every class-level
    `fieldname = fields.<Type>(...)` assignment in the source."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}
    result = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for stmt in node.body:
            if not isinstance(stmt, ast.Assign):
                continue
            type_name = fields_type_name(stmt.value)
            if not type_name:
                continue
            for target in stmt.targets:
                if isinstance(target, ast.Name):
                    result[target.id] = type_name
    return result


def find_type_changes(base, changed_files_list):
    changes = []  # (module, module_root, path, field, old_type, new_type)
    for path_str in changed_files_list:
        old_source = show(base, path_str)
        if old_source is None:
            continue  # new file -- nothing to diff against
        new_path = REPO / path_str
        if not new_path.is_file():
            continue  # deleted file -- out of scope (see docstring)
        new_source = new_path.read_text()

        old_fields = extract_field_types(old_source)
        new_fields = extract_field_types(new_source)

        for name, new_type in new_fields.items():
            old_type = old_fields.get(name)
            if old_type and old_type != new_type:
                changes.append(
                    (module_name_for(path_str), module_root(path_str), path_str, name, old_type, new_type)
                )
    return changes


def has_migration_touch(changed_files_list, mod_root):
    prefix = f"{mod_root}/migrations/"
    return any(f.startswith(prefix) for f in changed_files_list)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=None, help="git ref to diff against (default: origin/main, falling back to main)")
    args = parser.parse_args()

    base = args.base or default_base()
    all_changed = changed_files(base)
    py_changed = [f for f in all_changed if f.endswith(".py") and f.startswith(SCAN_ROOTS)]

    changes = find_type_changes(base, py_changed)

    missing = [
        c for c in changes
        if c[1] and not has_migration_touch(all_changed, c[1])
    ]

    if not missing:
        print(f"no uncovered field type changes found (base: {base})")
        return 0

    print(f"{len(missing)} field type change(s) with no matching migrations/ file in this diff:\n")
    for module, mod_root, path, field, old_type, new_type in missing:
        print(f"  {module}: {field} changed fields.{old_type} -> fields.{new_type}")
        print(f"      {path}")
        print(f"      expected a changed file under {mod_root}/migrations/")
        print()

    print(
        "A field's type changed with no migrations/ script touched in the same diff.\n"
        "Existing databases will not have their column data converted automatically --\n"
        "see docs/MIGRATIONS.md for when a migration script is required and how to write one."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
