#!/usr/bin/env python3
"""Install previous code, seed data, dump/restore, upgrade, and verify records.

Only selected addons outside Omnifreight run. Each addon uses separate,
uniquely named disposable databases. An upgrade fixture must exist for new
concrete products; fresh installations alone do not prove data preservation.
"""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import uuid

from ci_scope import ROOT, closure, manifests


def run(args, *, input_text=None, env=None):
    result = subprocess.run(args, input=input_text, text=True, capture_output=True, env=env, check=False)
    if result.returncode:
        raise RuntimeError(f'{args[0]} failed ({result.returncode}):\n' + result.stdout[-6000:] + result.stderr[-6000:])
    return result.stdout + result.stderr


def addon_roots(root):
    return sorted({str(p.parent.parent) for folder in ('shared', 'product', 'custom', 'third_parties')
                   for p in (root / folder).rglob('__manifest__.py')})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', required=True)
    parser.add_argument('--modules', required=True)
    args = parser.parse_args()
    current = manifests()
    previous = manifests(args.base)
    names = sorted(set(args.modules.split(',')) - {''})
    for name in names:
        if name not in current or current[name]['path'].startswith('custom/omnifreight/'):
            parser.error(f'Unsupported or excluded upgrade target: {name}')
    odoo = Path(os.environ['ODOO_PATH'])
    python = os.environ.get('ODOO_PYTHON', sys.executable)
    with tempfile.TemporaryDirectory(prefix='ele-upgrade-') as temporary:
        temp = Path(temporary)
        old = temp / 'previous'
        old.mkdir()
        archive = temp / 'previous.tar'
        with archive.open('wb') as stream:
            subprocess.run(['git', 'archive', args.base], cwd=ROOT, stdout=stream, check=True)
        run(['tar', '-xf', str(archive), '-C', str(old)])
        data = temp / 'data'
        data.mkdir()
        fixture = (ROOT / 'tools/upgrade_fixture.py').read_text()
        for name in names:
            if name not in previous:
                print(f'{name}: new addon; fresh-install tests cover this release.')
                continue
            original = 'ele_upgrade_old_' + uuid.uuid4().hex[:12]
            restored = 'ele_upgrade_new_' + uuid.uuid4().hex[:12]

            def command(root, db, shell=False):
                roots = [str(odoo / 'odoo/addons'), str(odoo / 'addons'), *addon_roots(root)]
                if os.environ.get('ODOO_ENTERPRISE_PATH'):
                    roots.insert(0, os.environ['ODOO_ENTERPRISE_PATH'])
                return [python, str(odoo / 'odoo-bin'), *(['shell'] if shell else []),
                        '-d', db, '--addons-path=' + ','.join(roots), '--no-http',
                        '--http-port=' + os.environ.get('HTTP_PORT', '8187'), '--data-dir=' + str(data)]

            try:
                run(['createdb', original])
                run(command(old, original) + ['-i', name, '--stop-after-init'])
                run(command(old, original, True), input_text=f'MODULE={name!r}\nPHASE="seed"\n' + fixture)
                dump = temp / 'database.dump'
                run(['pg_dump', '-Fc', '-f', str(dump), original])
                run(['createdb', restored])
                run(['pg_restore', '--exit-on-error', '--no-owner', '-d', restored, str(dump)])
                if (data / 'filestore' / original).exists():
                    shutil.copytree(data / 'filestore' / original, data / 'filestore' / restored)
                upgrade_names = ','.join(sorted(closure({name}, current) & set(names)))
                output = run(command(ROOT, restored) + ['-u', upgrade_names, '--test-enable',
                             '--test-tags=/' + name, '--stop-after-init'])
                if 'odoo.tests.result' not in output:
                    raise RuntimeError('The upgrade run produced no test summary.')
                run(command(ROOT, restored, True), input_text=f'MODULE={name!r}\nPHASE="check"\n' + fixture)
                print(f'{name}: previous install, dump/restore, upgrade tests and preserved records passed.', flush=True)
            finally:
                for db in (restored, original):
                    run(['dropdb', '--if-exists', db])


if __name__ == '__main__':
    main()
