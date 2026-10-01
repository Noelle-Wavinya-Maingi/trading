"""Exercise the shell runner with fake Odoo/PostgreSQL executables."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class TestRunner(unittest.TestCase):
    def run_check(self, status=0, summary=True, database_failure=False):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            for name, content in {
                'createdb': 'exit ' + ('1' if database_failure else '0'),
                'dropdb': 'exit 0',
                'psql': 'case "$*" in *count*) echo 1;; esac',
            }.items():
                path = directory / name
                path.write_text('#!/bin/sh\n' + content + '\n')
                path.chmod(0o755)
            (directory / 'odoo-bin').write_text(
                'import sys\n' +
                ('print("odoo.tests.result: 0 failed, 0 error(s) of 1 tests")\n' if summary else '') +
                f'sys.exit({status})\n')
            env = dict(os.environ, PATH=temp + os.pathsep + os.environ['PATH'],
                       ODOO_PATH=temp, ODOO_PYTHON=sys.executable,
                       VERIFY_MODULES='ele_ap_validation')
            env.pop('ODOO_ENTERPRISE_PATH', None)
            return subprocess.run(['bash', str(ROOT / 'tools/verify_boundaries.sh')],
                                  env=env, capture_output=True, text=True)

    def test_success_selects_only_requested_addon(self):
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('install [ele_ap_validation]', result.stdout)
        self.assertNotIn('install [budgets]', result.stdout)

    def test_nonzero_odoo_exit_fails_even_with_clean_summary(self):
        self.assertNotEqual(self.run_check(status=1).returncode, 0)

    def test_missing_test_summary_fails(self):
        self.assertNotEqual(self.run_check(summary=False).returncode, 0)

    def test_database_creation_failure_fails(self):
        self.assertNotEqual(self.run_check(database_failure=True).returncode, 0)
