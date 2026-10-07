"""Reject command hints that YAML would interpret as collections or syntax."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("check_package", ROOT / "scripts/check_package.py")
PACKAGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PACKAGE)


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for folder in (".claude-plugin", "hooks", "commands"):
            (self.root / folder).mkdir()
        self.write(".claude-plugin/plugin.json", '{"name":"leanflow","version":"0.3.2"}')
        self.write(".claude-plugin/marketplace.json", '{"plugins":[{"name":"leanflow","source":"./"}]}')
        self.write("hooks/hooks.json", '{"hooks":{}}')
        self.write("README.md", "# Fixture\n")

    def write(self, relative, content):
        (self.root / relative).write_text(content, encoding="utf-8")

    def check_hint(self, value):
        self.write("commands/memory.md", f"---\ndescription: Example\nargument-hint: {value}\n---\n")
        return PACKAGE.check(self.root)

    def test_quoted_hint_preserves_nested_options(self):
        hint = "[list|show <id>|export <id> [--to <path>]]"
        self.assertEqual(self.check_hint(json.dumps(hint)), [])

    def test_rejects_unquoted_hints_and_non_string_values(self):
        for value in ("[list|show <id>|export <id> [--to <path>]]",
                      "[--level <level>] [任务 id/路径]", "[任务 id/路径]",
                      '["task"]', "true", "42", "null", '{"task": "id"}', '""'):
            with self.subTest(value=value):
                errors = self.check_hint(value)
                self.assertTrue(any("argument-hint" in error for error in errors), errors)

    def test_current_package(self):
        self.assertEqual(PACKAGE.check(ROOT), [])
