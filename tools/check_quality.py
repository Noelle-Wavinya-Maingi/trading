#!/usr/bin/env python3
"""Block new naming and lint findings outside custom/omnifreight.

The reviewed baseline records existing debt. Findings include their source
line, so a different violation cannot replace an old one at the same count.
Run with the pinned tools in tools/requirements-quality.txt.
"""
import argparse
import ast
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT / 'tools/quality_baseline.json'
EXCLUDED = 'custom/omnifreight/'
STANDARD_FIELDS = {'name', 'active', 'sequence', 'company_id', 'currency_id', 'state',
                   'display_name', 'description'}


def files():
    return sorted(path for folder in ('shared', 'product', 'custom', 'tools')
                  for path in (ROOT / folder).rglob('*.py')
                  if '__pycache__' not in path.parts
                  and not path.relative_to(ROOT).as_posix().startswith(EXCLUDED))


def naming_findings(paths):
    findings = []
    classes = []
    known_fields = {
        'stock.picking': {'picking_type_code'},
        'budget.bridge.mixin': {'budget_id', 'budget_ids'},
        'process.bridge.mixin': {'step_ids'},
    }
    for path in paths:
        relative = path.relative_to(ROOT).as_posix()
        if relative.startswith('tools/'):
            continue
        if path.name == '__manifest__.py' and not path.parent.name.startswith('ele_'):
            findings.append(('naming', relative, 'addon-prefix', path.parent.name))
        tree = ast.parse(path.read_text())
        for cls in (node for node in tree.body if isinstance(node, ast.ClassDef)):
            values = {}
            for node in cls.body:
                if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                    values[node.targets[0].id] = node.value
            name_node = values.get('_name')
            name = name_node.value if isinstance(name_node, ast.Constant) else None
            inherit_node = values.get('_inherit')
            inherited = ast.literal_eval(inherit_node) if inherit_node is not None else []
            inherited = [inherited] if isinstance(inherited, str) else inherited
            fields = {field for field, value in values.items()
                      if isinstance(value, ast.Call) and isinstance(value.func, ast.Attribute)
                      and isinstance(value.func.value, ast.Name) and value.func.value.id == 'fields'}
            if name and name not in inherited:
                known_fields.setdefault(name, set()).update(fields)
            classes.append((relative, cls.name, name, inherited, fields))
    for relative, class_name, name, inherited, fields in classes:
        if name and name not in inherited and not name.startswith('ele.'):
            findings.append(('naming', relative, 'model-prefix', name))
        if not inherited or (name and name not in inherited):
            continue
        for field in fields:
            existing = any(field in known_fields.get(model, set()) for model in inherited)
            setting = 'res.config.settings' in inherited and field.startswith('module_ele_')
            if not (field.startswith('ele_') or field in STANDARD_FIELDS or existing or setting):
                findings.append(('naming', relative, 'extension-field-prefix', class_name + '.' + field))
    return findings


def run(command, valid_codes):
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    if result.returncode not in valid_codes:
        raise RuntimeError(result.stdout + result.stderr)
    return result.stdout


def lint_findings(paths):
    findings = []
    names = [str(p.relative_to(ROOT)) for p in paths]
    output = run([sys.executable, '-m', 'flake8', '--format=%(path)s|%(row)d|%(code)s|%(text)s',
                  *names], {0, 1})
    for row in output.splitlines():
        path, line, code, message = row.split('|', 3)
        source = (ROOT / path).read_text().splitlines()[int(line) - 1].strip()
        findings.append(('flake8', path, code, message, source))
    addon_names = [name for name in names if not name.startswith('tools/')]
    output = run([sys.executable, '-m', 'pylint', '--rcfile=.pylintrc',
                  '--disable=all', '--enable=odoolint', '--disable=manifest-required-author',
                  '--valid-odoo-versions=19.0',
                  '--output-format=json', '--reports=n', '--score=n', *addon_names], set(range(32)))
    for item in json.loads(output):
        path = Path(item['path'])
        path = path.relative_to(ROOT) if path.is_absolute() else path
        source_lines = (ROOT / path).read_text().splitlines()
        source = source_lines[item['line'] - 1].strip() if item['line'] else ''
        findings.append(('pylint-odoo', path.as_posix(), item['symbol'], item['message'], source))
    return findings


def new_findings(current, baseline):
    return Counter(map(tuple, current)) - Counter(map(tuple, baseline))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', help='Reject increases to an existing baseline relative to this Git ref')
    parser.add_argument('--write-baseline', action='store_true', help='Maintainer-only: review the resulting diff')
    args = parser.parse_args()
    paths = files()
    findings = naming_findings(paths) + lint_findings(paths)
    if args.write_baseline:
        # New/untracked code must be clean rather than silently grandfathered.
        tracked = set(run(['git', 'ls-files'], {0}).splitlines())
        findings = [item for item in findings if item[1] in tracked]
        BASELINE.write_text(json.dumps(sorted(findings), indent=2) + '\n')
        print(f'Recorded {len(findings)} existing findings; review baseline changes.')
        return 0
    baseline = json.loads(BASELINE.read_text())
    if args.base:
        old = subprocess.run(['git', 'show', f'{args.base}:tools/quality_baseline.json'],
                             cwd=ROOT, text=True, capture_output=True, check=False)
        if old.returncode == 0 and new_findings(baseline, json.loads(old.stdout)):
            raise RuntimeError('The quality baseline may shrink, but CI does not allow adding exceptions.')
    added = new_findings(findings, baseline)
    for finding, count in sorted(added.items()):
        print(f'{count} new: ' + ' | '.join(finding))
    print(f'{sum(added.values())} new findings; {len(findings)} current findings; Omnifreight excluded.')
    return bool(added)


if __name__ == '__main__':
    sys.exit(main())
