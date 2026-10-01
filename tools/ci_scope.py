#!/usr/bin/env python3
"""Select Odoo checks from changed addons and their transitive dependants.

--base is the PR merge base or the previous push commit. --files accepts a
newline-separated list for local previews. No Odoo/PostgreSQL is needed.
"""
import argparse
import ast
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROOTS = ('shared', 'product', 'custom', 'third_parties')
UPGRADE_TOOLS = {'tools/verify_upgrades.py', 'tools/upgrade_fixture.py'}
RUNTIME_TOOLS = {
    'tools/ci_scope.py', 'tools/verify_boundaries.sh',
    '.github/workflows/verify-boundaries.yml',
} | UPGRADE_TOOLS
COEXIST = {'ele_trading', 'ele_trading_budget'}
ENTERPRISE_DEPS = {'account_accountant', 'hr_payroll'}


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def manifests(base=None):
    if base:
        paths = git('ls-tree', '-r', '--name-only', base).splitlines()
        sources = ((p, git('show', f'{base}:{p}')) for p in paths
                   if p.endswith('/__manifest__.py') and p.split('/')[0] in ROOTS)
    else:
        sources = ((p.relative_to(ROOT).as_posix(), p.read_text())
                   for root in ROOTS for p in (ROOT / root).rglob('__manifest__.py'))
    result = {}
    for path, source in sources:
        if path.startswith('custom/omnifreight/'):
            continue
        name = Path(path).parent.name
        if not re.fullmatch(r'[a-z][a-z0-9_]*', name):
            raise ValueError(f'Invalid addon name: {name}')
        if name in result:
            raise ValueError(f'Duplicate addon: {name}')
        result[name] = {'path': str(Path(path).parent),
                        'depends': ast.literal_eval(source).get('depends', [])}
    return result


def closure(names, modules, reverse=False):
    result = set(names)
    while True:
        added = ({name for name, data in modules.items()
                  if result.intersection(data['depends'])} if reverse else
                 {dep for name in result if name in modules
                  for dep in modules[name]['depends']})
        if added <= result:
            return result
        result.update(added)


def affected(paths, current, previous=None):
    # The old graph preserves consumers when an addon is deleted/renamed or
    # a dependency is removed in this change.
    previous = previous or {}
    combined = {name: dict(data) for name, data in previous.items()}
    for name, data in current.items():
        combined[name] = {'path': data['path'], 'depends': sorted(
            set(data['depends']) | set(previous.get(name, {}).get('depends', [])))}
    changed = set()
    for path in paths:
        if path in RUNTIME_TOOLS:
            return set(current), set(current)
        if Path(path).suffix.lower() in {'.md', '.rst'}:
            continue
        for catalog in (current, previous):
            changed.update(name for name, data in catalog.items()
                           if path.startswith(data['path'] + '/'))
    return changed, closure(changed, combined, reverse=True) & current.keys()


def upgrade_targets(paths, current, previous=None):
    if set(paths) & UPGRADE_TOOLS:
        return {name for name, data in current.items()
                if not data['path'].startswith('custom/omnifreight/')}
    data_paths = [path for path in paths if path not in RUNTIME_TOOLS
                  and '/tests/' not in path
                  and (path.endswith('.py') or path.endswith('.xml') or path.endswith('.csv'))]
    selected = affected(data_paths, current, previous)[1]
    return {name for name in selected
            if not current[name]['path'].startswith('custom/omnifreight/')}


def scenarios(selected, modules, edition):
    rows = []
    eligible = {name for name in selected if edition == 'enterprise' or
                not closure({name}, modules).intersection(ENTERPRISE_DEPS)}
    # Enterprise runs only checks requiring Enterprise. Community-compatible
    # addons already ran in the Community job; simply adding an Enterprise
    # addons path does not install Enterprise modules or test their overrides.
    if edition == 'enterprise':
        eligible = {name for name in eligible
                    if closure({name}, modules).intersection(ENTERPRISE_DEPS)}
    verticals = {name for name, data in modules.items()
                 if not data['path'].startswith('shared/')} | {'mrp'}
    for name in sorted(eligible):
        forbidden = set()
        if modules[name]['path'].startswith('shared/'):
            forbidden = verticals
        elif name in {'ele_ap_validation', 'ele_bank_reconcile'}:
            forbidden = COEXIST | {'mrp'}
        elif name == 'ele_trading':
            forbidden = {'budgets', 'budgets_hr_expense', 'ele_trading_budget'}
        rows.append((name + '_alone', [name], [name], sorted(forbidden)))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--addon-roots', action='store_true')
    parser.add_argument('--base')
    parser.add_argument('--files', type=Path)
    parser.add_argument('--github-output', type=Path)
    parser.add_argument('--rows', choices=['community', 'enterprise'])
    parser.add_argument('--modules', help='comma-separated affected addons; omitted means all')
    args = parser.parse_args()
    current = manifests()
    if args.addon_roots:
        print(','.join(str(ROOT / path) for path in sorted(
            {str(Path(data['path']).parent) for data in current.values()})))
        return
    if args.rows:
        selected = set(args.modules.split(',')) - {''} if args.modules is not None else set(current)
        unknown = selected - current.keys()
        if unknown:
            parser.error(f'Unknown selected addons: {sorted(unknown)}')
        for label, install, tests, forbidden in scenarios(selected, current, args.rows):
            def sql_names(names):
                return ','.join(f"'{name}'" for name in names) or '-'
            print('|'.join([label, ','.join(install), ','.join('/' + n for n in tests),
                            sql_names(install), sql_names(forbidden)]))
        return
    if not args.base and not args.files:
        parser.error('Provide --base or --files')
    # --no-renames exposes both the removed and added paths, so both addon
    # graphs are considered when files move between addons.
    paths = (args.files.read_text().splitlines() if args.files else
             git('diff', '--no-renames', '--name-only', args.base, 'HEAD').splitlines())
    previous = manifests(args.base) if args.base else {}
    changed, selected = affected(paths, current, previous)
    result = {'changed': sorted(changed), 'affected': sorted(selected)}
    upgrades = upgrade_targets(paths, current, previous)
    for edition in ('community', 'enterprise'):
        result[edition] = [r[0] for r in scenarios(selected, current, edition)]
        result['upgrade_' + edition] = sorted({r[1][0] for r in scenarios(upgrades, current, edition)
                                               if r[0] != 'bridge_collision_regression'})
    print(json.dumps(result, indent=2))
    if args.github_output:
        with args.github_output.open('a') as stream:
            stream.write('modules=' + ','.join(sorted(selected)) + '\n')
            for edition in ('community', 'enterprise'):
                stream.write(f'{edition}={str(bool(result[edition])).lower()}\n')
                stream.write('upgrade_' + edition + '=' + ','.join(result['upgrade_' + edition]) + '\n')


if __name__ == '__main__':
    main()
