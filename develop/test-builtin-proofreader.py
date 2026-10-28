#!/usr/bin/env python3
"""Test the actual signed runtime and native service supervisor without live Rime files."""
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
APP = Path(os.environ.get('LIUR_BUILTIN_APP', ROOT / '.squirrel-proofreader/original/Squirrel.app'))


class BuiltinTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.helper = APP / 'Contents/Resources/LiurChecker/LiurChecker'
        cls.data = APP / 'Contents/SharedSupport/proofreader'
        cls.client = APP / 'Contents/Helpers/liur_proofread_client'
        cls.temp = tempfile.TemporaryDirectory(prefix='liur-builtin-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.scratch = Path(cls.temp.name)
        cls.environment = {'PATH': '/usr/bin:/bin', 'HOME': cls.temp.name}
        cls.harness = cls.scratch / 'lifecycle'
        subprocess.run(['xcrun', 'clang', '-fobjc-arc', '-framework', 'Cocoa',
                        '-I', str(ROOT / 'develop/squirrel-proofreader'),
                        str(ROOT / 'develop/squirrel-proofreader/test-service.m'),
                        str(ROOT / 'develop/squirrel-proofreader/LiurProofreadService.m'),
                        '-o', str(cls.harness)], check=True)

    def test_no_external_python(self):
        result = subprocess.run([str(self.helper), '--model-dir', str(self.data / 'model'),
                                 '--rime-dir', str(self.data), '--self-test'],
                                env=self.environment, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('意議→意義', result.stdout)

    def test_lifecycle(self):
        subprocess.run([str(self.harness), str(APP), str(self.scratch / 'normal.sock')],
                       env=self.environment, check=True, timeout=30)

    def test_parent_crash_stops_helper(self):
        path = self.scratch / 'orphan.sock'
        env = {**self.environment, 'LIUR_TEST_ABANDON_PARENT': '1'}
        subprocess.run([str(self.harness), str(APP), str(path)], env=env, check=True, timeout=30)
        deadline = time.monotonic() + 3
        while path.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        self.assertFalse(path.exists(), 'helper must exit and unlink socket when parent dies')

    def test_socket_queries(self):
        path = self.scratch / 'query.sock'
        worker = subprocess.Popen([str(self.helper), '--model-dir', str(self.data / 'model'),
                                   '--rime-dir', str(self.data), '--socket', str(path),
                                   '--parent-pid', str(os.getpid())], env=self.environment,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 10
            while not path.exists():
                self.assertIsNone(worker.poll())
                self.assertLess(time.monotonic(), deadline)
                time.sleep(0.05)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            for history, original, expected in [('意', '議', '義\t意義\n'), ('備', '住', '註\t備註\n'),
                                                ('居', '住', '\n')]:
                result = subprocess.run([str(self.client), str(path), history, original],
                                        env=self.environment, capture_output=True, text=True, timeout=2)
                self.assertEqual(result.stdout, expected)
        finally:
            worker.terminate()
            worker.wait(timeout=5)
            self.assertEqual(worker.stderr.read(), b'')
            worker.stderr.close()


if __name__ == '__main__':
    unittest.main(verbosity=2)
