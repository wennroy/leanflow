#!/usr/bin/env python3
"""Small local state helper. One Markdown record per delivery; no agent runner."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile


# Workflow budgets, independent of the host model's reasoning effort.
PROFILES = {
    "low": {"review_limit": 0, "agent_limit": 0, "e2e": "off"},
    "medium": {"review_limit": 2, "agent_limit": 2, "e2e": "off"},
    "high": {"review_limit": 3, "agent_limit": 6, "e2e": "core"},
    "xhigh": {"review_limit": 6, "agent_limit": 12, "e2e": "scenarios"},
    "max": {"review_limit": 8, "agent_limit": 24, "e2e": "scenarios"},
}
PHASES = ("plan", "implement", "verify", "review", "awaiting_decision",
          "awaiting_uat", "blocked", "done")
ROLES = ("reviewer", "implementer", "tester", "product", "explorer")
CHECK_NAMES = ("verification", "review", "e2e", "uat")
CHECK_STATUSES = ("passed", "pending", "failed", "not_applicable", "waived")
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_body(source):
    return sys.stdin.read() if source == "-" else Path(source).read_text(encoding="utf-8")


def level(value):
    if not isinstance(value, str):
        raise ValueError("level must be a string")
    result = value.lower()
    if result not in PROFILES:
        raise ValueError("level must be low, medium, high, xhigh or max")
    return result


def nonnegative(value):
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("must be nonnegative")
    return number


def git(cwd, *args):
    result = subprocess.run(["git", "-C", str(cwd), *args], text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    return result.stdout.strip() if result.returncode == 0 else None


def locate(cwd):
    cwd = Path(cwd).resolve(strict=True)
    if not cwd.is_dir():
        raise ValueError("cwd must be a directory")
    top = git(cwd, "rev-parse", "--show-toplevel")
    if top:
        common = git(cwd, "rev-parse", "--git-common-dir")
        root = (cwd / common).resolve() / "leanflow"
    else:
        root = cwd / ".leanflow"
    if root.is_symlink():
        raise ValueError("memory root must not be a symlink")
    previous = Path(top) / ".leanflow" if top else None
    return {"root": str(root), "worktree": str(Path(top).resolve() if top else cwd),
            "head": git(cwd, "rev-parse", "HEAD") if top else None,
            "migration_required": str(previous) if previous is not None
            and (previous.exists() or previous.is_symlink()) else None}


def read_record(path):
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"not a managed record: {path}; legacy plans must be imported explicitly")
    state = {}
    for index, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            return state, "".join(lines[index + 1:]).lstrip("\n")
        key, separator, raw = line.partition(":")
        if not separator or not re.fullmatch(r"[a-z_]+", key) or key in state:
            raise ValueError(f"invalid or duplicate metadata in {path}")
        try:
            state[key] = json.loads(raw)
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid metadata value for {key} in {path}") from error
    raise ValueError(f"unterminated metadata in {path}")


def safe_path(root, task):
    if SLUG.fullmatch(task):
        path = root / "tasks" / (task + ".md")
    else:
        path = Path(task)
        if not path.is_absolute():
            raise ValueError("use a kebab-case task id or an absolute managed task path")
    if path.is_symlink() or path.resolve().parent != root / "tasks" or path.suffix != ".md":
        raise ValueError("task must be a regular Markdown file in this repository's memory/tasks")
    if not SLUG.fullmatch(path.stem):
        raise ValueError("invalid task id")
    return path


def project_default(root):
    path = root / "project.md"
    if path.is_symlink():
        raise ValueError("project memory must not be a symlink")
    if not path.exists():
        return "medium"
    state, _ = read_record(path)
    return level(state.get("default_level", "medium"))


def policy(state):
    result = dict(PROFILES[level(state["level"])])
    for key in ("review_limit", "agent_limit"):
        if state.get(key) is not None:
            value = state[key]
            if type(value) is not int or value < 0:
                raise ValueError(f"invalid {key}; refusing to replace it with a default")
            result[key] = value
    if state["level"] == "low":
        result.update(review_limit=0, agent_limit=0)
    result["stall_limit"] = 2
    return result


def load_task(path):
    state, body = read_record(path)
    if state.get("schema") != 1 or state.get("id") != path.stem:
        raise ValueError("unknown task schema or mismatching id")
    if state.get("phase") not in PHASES:
        raise ValueError("invalid task phase")
    for key in ("revision", "review_used", "agents_used", "stalled"):
        if type(state.get(key)) is not int or state[key] < 0:
            raise ValueError(f"invalid {key}; refusing to reset task state")
    if state["review_used"] > state["agents_used"]:
        raise ValueError("review count exceeds total agent count")
    policy(state)
    if "checks" in state:
        validate_checks(state["checks"])
    return state, body


def validate_checks(checks):
    if not isinstance(checks, dict) or set(checks) != set(CHECK_NAMES):
        raise ValueError("checks must contain verification, review, e2e and uat")
    for name, check in checks.items():
        if not isinstance(check, dict) or check.get("status") not in CHECK_STATUSES:
            raise ValueError(f"invalid {name} check status")
        if not isinstance(check.get("evidence"), str) or not check["evidence"].strip():
            raise ValueError(f"{name} requires evidence or a pending reason; waived requires user authorization")


def delivery(state):
    """Check recorded prerequisites, not the truth or freshness of agent evidence."""
    checks = state.get("checks", {})
    chosen = level(state["level"])
    optional = {"verification"}
    if chosen == "low":
        optional.add("review")
    if PROFILES[chosen]["e2e"] == "off":
        optional.add("e2e")
    missing, waived = [], []
    for name in CHECK_NAMES:
        status = checks.get(name, {}).get("status")
        if status == "waived":
            waived.append(name)
        elif status == "passed":
            if name == "review" and state["review_used"] == 0:
                missing.append(name)
            if name == "e2e" and PROFILES[chosen]["e2e"] != "off" and state["agents_used"] <= state["review_used"]:
                missing.append(name)
        elif not (status == "not_applicable" and name in optional):
            missing.append(name)
    automatic_missing = [name for name in missing if name != "uat"]
    if state["stalled"] >= 2 or state["phase"] == "blocked":
        automatic_missing.append("blocked")
        missing.append("blocked")
    return {"automatic_complete": not automatic_missing and not any(name != "uat" for name in waived),
            "ready_for_uat": not automatic_missing, "ready_for_done": not missing,
            "missing": missing, "waived": waived}


@contextmanager
def locked(root):
    """Lock the directory inode: crash-safe unlock, no permanent lock file."""
    root.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(root, os.O_RDONLY)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def write_record(path, state, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    header = "\n".join(f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in state.items())
    text = f"---\n{header}\n---\n\n{body.rstrip()}\n"
    descriptor, temporary = tempfile.mkstemp(prefix=".leanflow-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def report(path, state, body):
    return {"path": str(path), "state": state, "policy": policy(state),
            "delivery": delivery(state), "body": body}


def resolve_baseline(worktree, reference):
    commit = git(worktree, "rev-parse", "--verify", "--end-of-options", reference + "^{commit}")
    if not commit:
        raise ValueError("baseline must identify an existing commit")
    return commit


def migrate(location):
    """Move non-Git memory after git init, preserving record bytes and counters."""
    previous = location["migration_required"]
    if previous is None:
        raise ValueError("no pre-Git memory to migrate; run from the initialized project")
    source, target = Path(previous), Path(location["root"])
    if source.is_symlink() or not source.is_dir():
        raise ValueError("pre-Git memory must be a real directory")
    if git(location["worktree"], "ls-files", "--", ".leanflow"):
        raise ValueError(".leanflow is already tracked; resolve its Git index/history before migration")
    # Stop other task writers before this one-time move. No duplicate state or merge guesses.
    with locked(target.parent), locked(source):
        if target.exists():
            raise ValueError("destination memory already exists; reconcile both roots before migration")
        project_default(source)
        for candidate in (source / "tasks").glob("*.md"):
            load_task(safe_path(source, str(candidate)))
        source.rename(target)
    return {"root": str(target), "migrated_from": str(source), "preserved_records": True}


def fingerprint(location, scopes):
    worktree = Path(location["worktree"])
    if not git(worktree, "rev-parse", "--show-toplevel"):
        raise ValueError("fingerprint requires Git; record non-Git code state explicitly")
    normalized = []
    for scope in scopes:
        candidate = (worktree / scope).resolve()
        try:
            relative = candidate.relative_to(worktree)
        except ValueError as error:
            raise ValueError("fingerprint scope must stay inside the worktree") from error
        if ".git" in relative.parts or ".leanflow" in relative.parts:
            raise ValueError("fingerprint code paths, not memory or Git internals")
        normalized.append(relative.as_posix())
    result = subprocess.run(["git", "-C", str(worktree), "--literal-pathspecs", "ls-files",
                             "--cached", "--others", "--exclude-standard", "-z", "--", *normalized],
                            check=True, stdout=subprocess.PIPE)
    names = sorted(set(part for part in result.stdout.split(b"\0") if part))
    if not names:
        raise ValueError("fingerprint scope matched no tracked or untracked code files")
    digest = hashlib.sha256()
    for name in names:
        path = worktree / os.fsdecode(name)
        digest.update(name + b"\0")
        if not path.exists() and not path.is_symlink():
            digest.update(b"deleted\0")
            continue
        mode = path.lstat().st_mode
        digest.update(str(stat.S_IFMT(mode) | (mode & 0o111)).encode() + b"\0")
        if path.is_symlink():
            contents = os.fsencode(os.readlink(path))
        elif path.is_file():
            contents = path.read_bytes()
        else:
            raise ValueError(f"fingerprint submodules separately: {path}")
        digest.update(hashlib.sha256(contents).digest())
    return {"head": location["head"], "scope": normalized, "files": len(names),
            "digest": digest.hexdigest()}


def run(args):
    location = locate(args.cwd)
    root = Path(location["root"])
    command = args.command
    if command == "locate":
        return {**location, "default_level": None if location["migration_required"]
                else project_default(root)}
    if command == "migrate":
        return migrate(location)
    if location["migration_required"]:
        raise ValueError("pre-Git memory found; stop other task writers and run migrate before resuming")
    if command == "fingerprint":
        return fingerprint(location, args.paths)
    if command == "list":
        tasks = []
        for candidate in sorted((root / "tasks").glob("*.md")):
            path = safe_path(root, str(candidate))
            state, _ = load_task(path)
            if args.all or state["phase"] != "done":
                tasks.append({"id": state["id"], "title": state["title"], "path": str(path),
                              "level": state["level"], "phase": state["phase"],
                              "worktree": state["worktree"]})
        return {**location, "tasks": tasks}
    if command == "default":
        chosen = level(args.level)  # Validate before creating any files.
        with locked(root):
            path = root / "project.md"
            project_default(root)  # Detect corruption/symlinks before mutation.
            state, body = read_record(path) if path.exists() else ({}, "# Project memory\n")
            state["default_level"] = chosen
            write_record(path, state, body)
        return {"path": str(path), "default_level": chosen}

    path = safe_path(root, args.task)
    if command == "show":
        return report(path, *load_task(path))
    if command in ("new", "import"):
        chosen = level(args.level) if args.level else project_default(root)
        imported = command == "import"
        source = args.source if imported else args.body
        body = read_body(source) if source else f"# {args.title or args.task}\n"
        if imported and args.review_used > args.agents_used:
            raise ValueError("review count cannot exceed total agent count")
        baseline = location["head"]
        if imported:
            baseline = resolve_baseline(location["worktree"], args.baseline) if args.baseline else None
        with locked(root):
            if path.exists():
                raise ValueError("task already exists; resume it or choose a different id")
            state = {"schema": 1, "id": path.stem, "title": args.title or path.stem,
                     "level": chosen, "phase": "plan", "revision": 0,
                     "worktree": location["worktree"], "baseline": baseline,
                     "review_used": args.review_used if imported else 0,
                     "agents_used": args.agents_used if imported else 0, "stalled": 0,
                     "created": now(), "updated": now()}
            if imported:
                state["imported_from"] = str(Path(args.source).resolve())
            write_record(path, state, body)
        return report(path, state, body)

    if command == "export":
        state, _ = load_task(path)
        summary = read_body(args.summary).strip()
        if not summary:
            raise ValueError("export requires a nonempty curated summary")
        target = Path(args.to).resolve()
        docs = Path(location["worktree"]) / "docs"
        if docs not in target.parents or target.suffix != ".md":
            raise ValueError("export destination must be a Markdown file under this worktree's docs/")
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("x", encoding="utf-8") as stream:
            stream.write(f"<!-- leanflow snapshot: task={state['id']}; revision={state['revision']}; "
                         f"exported={now()}; HEAD={location['head'] or 'non-git'}; "
                         "HEAD is provenance, not verification of uncommitted changes -->\n\n")
            stream.write(summary + "\n")
        return {"path": str(target), "source": str(path), "committed": False}

    with locked(root):
        state, body = load_task(path)
        if command == "level":
            state["level"] = level(args.level)
            # Explicit budget overrides remain authoritative after a level change.
        elif command == "budget":
            if args.review is None and args.agents is None:
                raise ValueError("provide --review and/or --agents")
            if not args.reason.strip():
                raise ValueError("record the user's authorization in --reason")
            for option, key in ((args.review, "review_limit"), (args.agents, "agent_limit")):
                if option is not None:
                    state[key] = option
            state["budget_reason"] = args.reason
        elif command == "reserve":
            limits = policy(state)
            if state["level"] == "low":
                raise ValueError("low has no agents; change level explicitly before dispatch")
            if state["phase"] in ("done", "blocked") or state["stalled"] >= limits["stall_limit"]:
                raise ValueError("task is done or blocked; resolve the recorded blocker before dispatch")
            if args.role == "product" and state["level"] != "max":
                raise ValueError("product agent requires max")
            if args.role == "tester" and limits["e2e"] == "off":
                raise ValueError("dedicated E2E tester is disabled at this level")
            if state["agents_used"] >= limits["agent_limit"]:
                raise ValueError("total agent budget exhausted")
            if args.role == "reviewer":
                if state["review_used"] >= limits["review_limit"]:
                    raise ValueError("review budget exhausted (rechecks also count)")
                state["review_used"] += 1
            state["agents_used"] += 1
            if "checks" in state:
                invalidated = {"reviewer": ("review",), "tester": ("e2e",),
                               "implementer": CHECK_NAMES}.get(args.role, ())
                for name in invalidated:
                    if args.role == "implementer" and state["checks"][name]["status"] == "not_applicable":
                        continue
                    state["checks"][name] = {"status": "pending",
                                             "evidence": f"Reserved {args.role}; result not yet recorded"}
        elif command == "checkpoint":
            if args.revision != state["revision"]:
                raise ValueError("record changed; reread it and merge before checkpointing")
            if args.baseline:
                baseline = resolve_baseline(location["worktree"], args.baseline)
                if state["baseline"] is not None and state["baseline"] != baseline:
                    raise ValueError("existing baseline cannot be replaced during resume")
                state["baseline"] = baseline
            if args.body:
                body = read_body(args.body)
            if args.checks is not None:
                checks = json.loads(args.checks)
                validate_checks(checks)
                for name, previous in state.get("checks", {}).items():
                    if previous["status"] in ("failed", "pending") and checks[name]["status"] == "not_applicable":
                        raise ValueError(f"preserve unresolved {name}; resolve it or record an explicit user waiver")
                state["checks"] = checks
            if args.phase:
                state["phase"] = args.phase
            if args.progress == "yes":
                state["stalled"] = 0
            elif args.progress == "no":
                state["stalled"] += 1
            if state["stalled"] >= policy(state)["stall_limit"]:
                state["phase"] = "blocked"
            if state["phase"] in ("awaiting_uat", "done") and "checks" not in state:
                raise ValueError("delivery checkpoint requires --checks; reuse verified existing evidence")
            if state["phase"] == "done" and not delivery(state)["ready_for_done"]:
                raise ValueError("cannot mark done; unresolved checks: " + ", ".join(delivery(state)["missing"]))
        state["revision"] += 1
        state["updated"] = now()
        write_record(path, state, body)
    return {"path": str(path), "state": state, "policy": policy(state), "delivery": delivery(state)}


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--cwd", default=".", help="project directory (default: current directory)")
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("locate", help="locate shared local memory without writing")
    commands.add_parser("migrate", help="move pre-Git .leanflow into Git memory without resetting state")
    commands.add_parser("fingerprint", help="hash scoped tracked and untracked code, without writing").add_argument("paths", nargs="+")
    commands.add_parser("list", help="list active tasks").add_argument("--all", action="store_true")
    commands.add_parser("default", help="set project default level").add_argument("level")
    new = commands.add_parser("new", help="create one task; refuses replacement")
    new.add_argument("task")
    new.add_argument("--title")
    new.add_argument("--level")
    new.add_argument("--body", help="UTF-8 Markdown body file, or - for stdin")
    legacy = commands.add_parser("import", help="copy a legacy plan into one canonical local record")
    legacy.add_argument("task")
    legacy.add_argument("--source", required=True)
    legacy.add_argument("--title")
    legacy.add_argument("--level")
    legacy.add_argument("--baseline", help="verified pre-implementation commit, never guessed from current HEAD")
    legacy.add_argument("--review-used", required=True, type=nonnegative)
    legacy.add_argument("--agents-used", required=True, type=nonnegative)
    commands.add_parser("show", help="read task, revision and effective policy").add_argument("task")
    change = commands.add_parser("level", help="change level without resetting usage")
    change.add_argument("task")
    change.add_argument("level")
    budget = commands.add_parser("budget", help="explicitly authorized budget adjustment")
    budget.add_argument("task")
    budget.add_argument("--review", type=nonnegative)
    budget.add_argument("--agents", type=nonnegative)
    budget.add_argument("--reason", required=True)
    reserve = commands.add_parser("reserve", help="reserve one agent invocation BEFORE dispatch")
    reserve.add_argument("task")
    reserve.add_argument("role", choices=ROLES)
    checkpoint = commands.add_parser("checkpoint", help="atomically merge body and phase with revision check")
    checkpoint.add_argument("task")
    checkpoint.add_argument("--revision", required=True, type=nonnegative)
    checkpoint.add_argument("--body", help="replacement Markdown body file, or - for stdin; no frontmatter")
    checkpoint.add_argument("--phase", choices=PHASES)
    checkpoint.add_argument("--checks", help="JSON delivery checks with status/evidence; stored in the same record")
    checkpoint.add_argument("--baseline", help="fill an unknown baseline once verified from history")
    checkpoint.add_argument("--progress", choices=("yes", "no"), help="completed cycle made material progress")
    export = commands.add_parser("export", help="export a curated snapshot; never git add/commit")
    export.add_argument("task")
    export.add_argument("--summary", required=True, help="reviewed Markdown summary file, or - for stdin")
    export.add_argument("--to", required=True, help="new path under the current worktree's docs/")
    return result


def main():
    try:
        print(json.dumps(run(parser().parse_args()), ensure_ascii=False))
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(f"leanflow: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
