#!/usr/bin/env python3
"""Offline structural checks; does not replace the host's plugin validator."""
import argparse
import json
from pathlib import Path
import re
import sys


def check(root):
    errors = []
    try:
        manifest = json.loads((root / ".claude-plugin/plugin.json").read_text())
        marketplace = json.loads((root / ".claude-plugin/marketplace.json").read_text())
        hooks = json.loads((root / "hooks/hooks.json").read_text())
        if manifest.get("name") != "leanflow" or not re.fullmatch(r"\d+\.\d+\.\d+", manifest.get("version", "")):
            errors.append("invalid plugin name/version")
        if not any(p.get("name") == manifest.get("name") and p.get("source") == "./"
                   for p in marketplace.get("plugins", [])):
            errors.append("marketplace does not reference this local plugin")
        for groups in hooks.get("hooks", {}).values():
            for group in groups:
                for hook in group.get("hooks", []):
                    for relative in re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}/([^\s\"']+)", hook.get("command", "")):
                        if not (root / relative).is_file():
                            errors.append(f"missing hook: {relative}")
    except (OSError, ValueError, TypeError) as error:
        errors.append(f"plugin metadata: {error}")

    entries = list((root / "commands").glob("*.md")) + list((root / "agents").glob("*.md"))
    entries += list((root / "skills").glob("*/SKILL.md"))
    for path in entries:
        content = path.read_text(encoding="utf-8")
        if not content.startswith("---\n") or "\n---\n" not in content[4:]:
            errors.append(f"missing frontmatter: {path.relative_to(root)}")
            continue
        header = content[4:].split("\n---\n", 1)[0]
        fields = {}
        for line in header.splitlines():
            key, separator, value = line.partition(":")
            if not separator or not value.strip() or key in fields:
                errors.append(f"invalid flat frontmatter: {path.relative_to(root)}")
            fields[key] = value.strip()
        if not fields.get("description"):
            errors.append(f"missing description: {path.relative_to(root)}")
        if "argument-hint" in fields:
            # JSON strings are valid YAML scalars; brackets in CLI help must stay text.
            # Enforce this narrow authoring rule without adding a YAML dependency.
            try:
                hint = json.loads(fields["argument-hint"])
            except ValueError:
                hint = None
            if not isinstance(hint, str) or not hint:
                errors.append(f"argument-hint must be a nonempty JSON-quoted string: {path.relative_to(root)}")
        if path.parent.name == "agents" and fields.get("name") != path.stem:
            errors.append(f"agent name mismatch: {path.name}")
        if path.name == "SKILL.md" and not re.fullmatch(r"[a-z0-9-]+", fields.get("name", "")):
            errors.append(f"invalid skill name: {path.relative_to(root)}")

    docs = entries + list((root / "references").glob("*.md")) + [root / "README.md"]
    for path in docs:
        content = path.read_text(encoding="utf-8")
        for relative in re.findall(r"(?<![\w/])((?:commands|agents|references|scripts)/[\w-]+\.(?:md|py))", content):
            if not (root / relative).is_file():
                errors.append(f"{path.relative_to(root)} references missing {relative}")
        for link in re.findall(r"\]\(([^\s)]+)\)", content):
            if "://" not in link and not link.startswith("#"):
                if not (path.parent / link.split("#", 1)[0]).is_file():
                    errors.append(f"{path.relative_to(root)} has broken link {link}")
    for path in (root / "scripts").glob("*.py"):
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except SyntaxError as error:
            errors.append(f"{path.name}: {error}")
    return errors


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=str(Path(__file__).resolve().parents[1]))
    failures = check(Path(parser.parse_args().root).resolve())
    for failure in failures:
        print(failure, file=sys.stderr)
    if not failures:
        print("Plugin structure, entrypoint metadata, references and Python syntax: OK")
    sys.exit(bool(failures))
