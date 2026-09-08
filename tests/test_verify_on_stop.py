"""Exercise the optional Stop reminder without touching a real project."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


HOOK = Path(__file__).resolve().parents[1] / "hooks/scripts/verify-on-stop.sh"


class StopReminderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="leanflow-stop-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "project"
        (self.root / ".claude").mkdir(parents=True)
        self.cache = Path(self.temp.name) / "cache"
        self.cache.mkdir()
        self.verify = self.root / ".claude/verify.sh"
        self.env = dict(os.environ, CLAUDE_PROJECT_DIR=str(self.root), TMPDIR=str(self.cache))

    def run_hook(self):
        return subprocess.run(
            ["bash", str(HOOK)], cwd=self.root, env=self.env,
            input=json.dumps({"hook_event_name": "Stop", "stop_hook_active": False}),
            capture_output=True, text=True, timeout=10,
        )

    def fail_verification(self):
        self.verify.write_text("printf 'fixture: \"quoted\" failure\\n' >&2\nexit 1\n")

    def test_missing_verifier_is_silent(self):
        result = self.run_hook()
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout + result.stderr, "")

    def test_success_is_silent(self):
        self.verify.write_text("printf 'check passed\\n'\nexit 0\n")
        result = self.run_hook()
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout + result.stderr, "")

    def test_failure_warns_without_blocking_the_turn(self):
        self.fail_verification()
        result = self.run_hook()
        self.assertEqual(result.returncode, 0, result.stderr)
        warning = json.loads(result.stdout)
        self.assertIn('fixture: "quoted" failure', warning["systemMessage"])
        self.assertNotIn("decision", warning)
        self.assertNotIn("continue", warning)
        self.assertEqual(result.stderr, "")

    def test_repeated_failure_does_not_repeat_the_warning(self):
        self.fail_verification()
        self.run_hook()
        result = self.run_hook()
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout + result.stderr, "")

    def test_success_resets_the_failure_warning(self):
        self.fail_verification()
        self.run_hook()
        self.verify.write_text("exit 0\n")
        self.run_hook()
        self.fail_verification()
        result = self.run_hook()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("systemMessage", json.loads(result.stdout))


if __name__ == "__main__":
    unittest.main()
