#!/usr/bin/env python3
"""Flags the exact bug shape that broke order.bridge.mixin and
operations.budget.line: two modules extending the SAME Odoo model define a
method with the SAME name, and neither calls super() -- meaning whichever
module's class ends up leafmost in Odoo's MRO silently wins for every record
of that model, and the other module's implementation never runs at all.

This does not run inside a live Odoo registry (no import of odoo, no
database) -- it is a static AST scan over the module source, intentionally
cheap enough to run on every commit. It cannot see abstract-mixin
indirection or decorator-driven dispatch, so it is a smoke check, not a
proof: a clean run means "no obvious instance of this bug shape", not "this
codebase has no cross-module collisions of any kind".

Usage:
    python3 tools/check_extension_collisions.py

Exits 1 and prints every offending model/method pair if any are found,
0 otherwise.
"""
import ast
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCAN_ROOTS = ["shared", "custom", "product", "third_parties"]
SKIP_DIR_NAMES = {"tests", "migrations", "__pycache__"}

# Standard Odoo lifecycle/framework methods are meant to be overridden
# cooperatively via super() by design (create/write/unlink chain up through
# every parent automatically) -- flagging every module that defines create()
# would be all noise, not signal. _compute_* is excluded too: those are tied
# to specific fields via @api.depends, so two verticals defining differently
# -depended-on computes of the same name on the same model is a naming
# coincidence, not the same bug shape (the risk here is a plain hook method
# with no @api.depends binding it to specific data).
SAFE_METHOD_NAMES = {
    "create", "write", "unlink", "copy", "copy_data", "name_get", "read",
    "search", "search_read", "default_get", "fields_get", "fields_view_get",
    "get_view", "action_confirm", "action_cancel", "action_done",
    "action_draft", "button_confirm", "button_draft", "button_cancel",
    "_compute_display_name",
}


def is_safe_name(name):
    return name in SAFE_METHOD_NAMES or name.startswith("_compute_")


def extended_model_name(class_node):
    """Return the model name this class extends, or None if it defines a
    brand new model (only _name, no _inherit) or isn't a model class at all."""
    name_value = None
    inherit_value = None
    for stmt in class_node.body:
        if not isinstance(stmt, ast.Assign):
            continue
        targets = [t.id for t in stmt.targets if isinstance(t, ast.Name)]
        if "_name" in targets:
            name_value = _const_str(stmt.value)
        if "_inherit" in targets:
            inherit_value = stmt.value

    if inherit_value is None:
        return None  # no _inherit at all -> not extending anything

    if isinstance(inherit_value, ast.Constant) and isinstance(inherit_value.value, str):
        return inherit_value.value  # _inherit = 'some.model'

    if isinstance(inherit_value, (ast.List, ast.Tuple)):
        entries = [_const_str(e) for e in inherit_value.elts]
        entries = [e for e in entries if e]
        if not entries:
            return None
        # `_name = X` alongside a list _inherit means X is the existing model
        # being extended and the other list entries are abstract mixins being
        # pulled in (see dispatch's order_bridge_mixin.py
        # callers' own convention
        # comment) -- the mixins aren't independently "extended" here.
        if name_value:
            return name_value
        return entries[0]

    return None


def _const_str(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def calls_super(func_node):
    for node in ast.walk(func_node):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            inner = node.func.value
            if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name) and inner.func.id == "super":
                return True
    return False


def module_name_for(path):
    """First path segment under a scan root is the addon's directory name,
    which is also its technical module name in every addon here."""
    rel = path.relative_to(REPO)
    parts = rel.parts
    # shared/<module>/..., custom/omnifreight/<module>/..., product/commodity_trading/<module>/...
    if parts[0] == "shared":
        return parts[1]
    return parts[2] if len(parts) > 2 else parts[1]


def direct_depends(manifest_path):
    try:
        tree = ast.parse(manifest_path.read_text(), filename=str(manifest_path))
    except SyntaxError:
        return []
    # The manifest is a single dict literal expression -- find the 'depends' key.
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if _const_str(key) == "depends" and isinstance(value, (ast.List, ast.Tuple)):
                    return [e for e in (_const_str(el) for el in value.elts) if e]
    return []


def build_dependency_closure():
    """module -> set of every module it depends on, directly or transitively.
    Modules outside this repo (base, sale, account, ...) are included as
    leaf nodes with no further deps -- harmless, since collisions can only
    be reported for modules this scan actually found extension classes in."""
    direct = {}
    for root_name in SCAN_ROOTS:
        root = REPO / root_name
        if not root.is_dir():
            continue
        for manifest_path in root.rglob("__manifest__.py"):
            module = module_name_for(manifest_path)
            direct[module] = direct_depends(manifest_path)

    closure = {}

    def resolve(module, seen):
        if module in closure:
            return closure[module]
        if module in seen:
            return set()  # defensive: circular depends shouldn't happen, don't hang if it does
        seen.add(module)
        deps = set(direct.get(module, []))
        for dep in list(deps):
            deps |= resolve(dep, seen)
        closure[module] = deps
        return deps

    for module in direct:
        resolve(module, set())
    return closure


def in_dependency_chain(module_a, module_b, closure):
    return module_b in closure.get(module_a, ()) or module_a in closure.get(module_b, ())


def scan():
    # model -> method -> list of (module, file, lineno, calls_super)
    registry = {}

    for root_name in SCAN_ROOTS:
        root = REPO / root_name
        if not root.is_dir():
            continue
        for path in root.rglob("*.py"):
            if any(part in SKIP_DIR_NAMES for part in path.parts):
                continue
            try:
                tree = ast.parse(path.read_text(), filename=str(path))
            except SyntaxError:
                continue

            module = module_name_for(path)
            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                model = extended_model_name(node)
                if not model:
                    continue
                for stmt in node.body:
                    if not isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        continue
                    if stmt.name.startswith("__") or is_safe_name(stmt.name):
                        continue
                    registry.setdefault(model, {}).setdefault(stmt.name, []).append(
                        (module, str(path.relative_to(REPO)), stmt.lineno, calls_super(stmt))
                    )
    return registry


def find_collisions(registry, closure):
    collisions = []
    for model, methods in registry.items():
        for method, defs in methods.items():
            modules = {d[0] for d in defs}
            if len(modules) < 2:
                continue  # same module defining it twice (e.g. two mixins it itself composes) isn't this bug

            # A module overriding a method from something it depends on is a
            # normal, safe single-inheritance-chain override (Odoo resolves
            # it deterministically: the dependent module is always leafmost)
            # regardless of whether it calls super() -- that's not this bug.
            # The risk is specifically two modules with NO dependency
            # relationship between them both claiming the same method name,
            # since nothing then determines which one Odoo keeps.
            sibling_pairs = [
                (defs[i], defs[j])
                for i in range(len(defs))
                for j in range(i + 1, len(defs))
                if defs[i][0] != defs[j][0]
                and not in_dependency_chain(defs[i][0], defs[j][0], closure)
            ]
            if not sibling_pairs:
                continue

            # Only the definitions that actually appear in a sibling pair are
            # at risk -- a common ancestor all the siblings chain through
            # (e.g. a registry's own base returning `[]`) is excluded from
            # every sibling_pairs entry above precisely because it's in
            # everyone's dependency chain, so it has nothing to prove here
            # even if it doesn't call super() itself.
            at_risk_modules = {module for pair in sibling_pairs for entry in pair for module in (entry[0],)}
            at_risk_defs = [d for d in defs if d[0] in at_risk_modules]

            if all(d[3] for d in at_risk_defs):
                continue  # every sibling definition calls super() -- cooperative override, the safe pattern

            collisions.append((model, method, defs))
    return collisions


def main():
    registry = scan()
    closure = build_dependency_closure()
    collisions = find_collisions(registry, closure)

    if not collisions:
        print("no cross-module method collisions found")
        return 0

    print(f"{len(collisions)} potential cross-module collision(s) found:\n")
    for model, method, defs in sorted(collisions):
        print(f"  {model}.{method}()")
        for module, file, lineno, calls_super_ in sorted(defs):
            tag = "calls super()" if calls_super_ else "does NOT call super()"
            print(f"      {module:20s} {file}:{lineno}  ({tag})")
        print()

    print(
        "Two or more modules define the same method name on the same model,\n"
        "and at least one does not call super() -- this is the exact shape that\n"
        "broke order.bridge.mixin and operations.budget.line: Odoo's MRO keeps\n"
        "only one implementation alive, so the other module's logic silently\n"
        "never runs. If these modules genuinely need independent behavior here,\n"
        "register hooks into an accumulating list instead (see\n"
        "shared/dispatch/models/order_bridge_mixin.py's docstring)."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
