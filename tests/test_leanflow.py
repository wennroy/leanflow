"""Exercise the local-memory CLI against real repositories, not prompt wording."""
import concurrent.futures
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


CLI = Path(__file__).resolve().parents[1] / "scripts" / "leanflow.py"


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.repo = self.base / "repo with spaces"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.test",
                 "commit", "--allow-empty", "-qm", "baseline")

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.repo), *args], text=True).strip()

    def call(self, *args, cwd=None, ok=True):
        result = subprocess.run(
            [sys.executable, str(CLI), "--cwd", str(cwd or self.repo), *args],
            capture_output=True, text=True,
        )
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        return result

    def new(self, name="sample", level=None):
        args = ["new", name, "--title", "Example feature"]
        if level:
            args.extend(["--level", level])
        return self.call(*args)

    def checks(self, **statuses):
        return json.dumps({name: {"status": statuses.get(name, "passed"),
                                  "evidence": "Unit fixture: explicit result/decision"}
                           for name in ("verification", "review", "e2e", "uat")})

    def test_delivery_cannot_replace_required_review_with_zero_calls(self):
        self.new(level="xhigh")
        result = self.call("checkpoint", "sample", "--revision", "0", "--phase", "awaiting_uat",
                           "--checks", self.checks(review="pending", uat="pending"))
        self.assertFalse(result["delivery"]["ready_for_uat"])
        self.assertIn("review", result["delivery"]["missing"])
        before = Path(result["path"]).read_bytes()
        self.call("checkpoint", "sample", "--revision", "1", "--phase", "done",
                  "--checks", self.checks(), ok=False)
        self.assertEqual(Path(result["path"]).read_bytes(), before)

    def test_low_delivery_requires_user_uat_without_extra_writes(self):
        self.new(level="low")
        pending = self.checks(review="not_applicable", e2e="not_applicable", uat="pending")
        ready = self.call("checkpoint", "sample", "--revision", "0", "--phase", "awaiting_uat",
                          "--checks", pending)
        self.assertTrue(ready["delivery"]["ready_for_uat"])
        self.assertFalse(ready["delivery"]["ready_for_done"])
        self.assertEqual(ready["state"]["revision"], 1)
        self.call("checkpoint", "sample", "--revision", "1", "--phase", "done", ok=False)
        done = self.call("checkpoint", "sample", "--revision", "1", "--phase", "done",
                         "--checks", self.checks(review="not_applicable", e2e="not_applicable"))
        self.assertTrue(done["delivery"]["ready_for_done"])

    def test_uat_does_not_override_failed_automatic_check(self):
        self.new()
        self.call("reserve", "sample", "reviewer")
        self.call("checkpoint", "sample", "--revision", "1", "--phase", "done",
                  "--checks", self.checks(verification="failed", e2e="not_applicable"), ok=False)

    def test_failed_review_dispatch_cannot_count_as_review_result(self):
        self.new()
        self.call("reserve", "sample", "reviewer")
        result = self.call("checkpoint", "sample", "--revision", "1", "--phase", "awaiting_uat",
                           "--checks", self.checks(review="pending", e2e="not_applicable", uat="pending"))
        self.assertFalse(result["delivery"]["automatic_complete"])
        self.assertIn("review", result["delivery"]["missing"])

    def test_downgrade_preserves_missing_review_until_explicit_waiver(self):
        self.new(level="high")
        self.call("checkpoint", "sample", "--revision", "0", "--phase", "awaiting_uat",
                  "--checks", self.checks(review="pending", uat="pending"))
        lowered = self.call("level", "sample", "low")
        self.assertIn("review", lowered["delivery"]["missing"])
        self.call("checkpoint", "sample", "--revision", "2", "--phase", "done",
                  "--checks", self.checks(review="not_applicable"), ok=False)
        waived = self.call("checkpoint", "sample", "--revision", "2", "--phase", "done",
                           "--checks", self.checks(review="waived"))
        self.assertTrue(waived["delivery"]["ready_for_done"])
        self.assertFalse(waived["delivery"]["automatic_complete"])

    def test_delivery_rejects_empty_evidence_and_preserves_previous_record(self):
        created = self.new(level="low")
        before = Path(created["path"]).read_bytes()
        checks = json.loads(self.checks(review="not_applicable", e2e="not_applicable"))
        checks["uat"]["evidence"] = " "
        self.call("checkpoint", "sample", "--revision", "0", "--phase", "done",
                  "--checks", json.dumps(checks), ok=False)
        self.assertEqual(Path(created["path"]).read_bytes(), before)

    def test_legacy_records_remain_readable_without_silent_gate_success(self):
        created = self.new()
        before = Path(created["path"]).read_bytes()
        result = self.call("show", "sample")
        self.assertFalse(result["delivery"]["ready_for_done"])
        self.assertIn("review", result["delivery"]["missing"])
        self.assertEqual(Path(created["path"]).read_bytes(), before)

    def test_recheck_reservation_invalidates_old_review_result(self):
        self.new()
        self.call("reserve", "sample", "reviewer")
        self.call("checkpoint", "sample", "--revision", "1", "--phase", "awaiting_uat",
                  "--checks", self.checks(e2e="not_applicable", uat="pending"))
        result = self.call("reserve", "sample", "reviewer")
        self.assertIn("review", result["delivery"]["missing"])

    def test_high_cannot_claim_independent_e2e_with_only_a_reviewer(self):
        self.new(level="high")
        self.call("reserve", "sample", "reviewer")
        result = self.call("checkpoint", "sample", "--revision", "1", "--phase", "awaiting_uat",
                           "--checks", self.checks(uat="pending"))
        self.assertIn("e2e", result["delivery"]["missing"])

    def test_high_with_completed_checks_can_finish_after_user_uat(self):
        self.new(level="high")
        self.call("reserve", "sample", "tester")
        self.call("reserve", "sample", "reviewer")
        ready = self.call("checkpoint", "sample", "--revision", "2", "--phase", "awaiting_uat",
                          "--checks", self.checks(uat="pending"))
        self.assertTrue(ready["delivery"]["automatic_complete"])
        done = self.call("checkpoint", "sample", "--revision", "3", "--phase", "done",
                         "--checks", self.checks())
        self.assertTrue(done["delivery"]["ready_for_done"])

    def test_upgrade_requires_new_e2e_but_preserves_review_evidence(self):
        self.new()
        self.call("reserve", "sample", "reviewer")
        self.call("checkpoint", "sample", "--revision", "1", "--phase", "awaiting_uat",
                  "--checks", self.checks(e2e="not_applicable", uat="pending"))
        upgraded = self.call("level", "sample", "high")
        self.assertEqual(upgraded["delivery"]["missing"], ["e2e", "uat"])
        self.assertEqual(upgraded["state"]["review_used"], 1)

    def test_missing_delivery_checks_are_not_silently_accepted(self):
        self.new(level="low")
        result = self.call("checkpoint", "sample", "--revision", "0", "--phase", "done", ok=False)
        self.assertIn("--checks", result.stderr)

    def test_locate_is_read_only_and_handles_nested_directories(self):
        nested = self.repo / "src"
        nested.mkdir()
        found = self.call("locate", cwd=nested)
        self.assertEqual(Path(found["root"]), self.repo / ".git" / "leanflow")
        self.assertFalse(Path(found["root"]).exists())

    def test_worktrees_share_memory_but_task_records_origin(self):
        worktree = self.base / "linked"
        self.git("worktree", "add", "--detach", str(worktree))
        created = self.new()
        located = self.call("locate", cwd=worktree)
        self.assertEqual(located["root"], self.call("locate")["root"])
        state = self.call("show", "sample", cwd=worktree)
        self.assertEqual(state["state"]["worktree"], str(self.repo))
        self.assertEqual(state["path"], created["path"])

    def test_one_file_untracked_and_default_medium(self):
        created = self.new()
        self.assertEqual(created["state"]["level"], "medium")
        self.assertEqual(created["state"]["review_used"], 0)
        root = self.repo / ".git" / "leanflow"
        self.assertEqual([p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()],
                         ["tasks/sample.md"])
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_default_precedence_and_project_body_preserved(self):
        self.call("default", "low")
        project = self.repo / ".git" / "leanflow" / "project.md"
        project.write_text(project.read_text() + "\nA durable decision.\n")
        self.call("default", "high")
        self.assertIn("A durable decision.", project.read_text())
        self.assertEqual(self.new()["state"]["level"], "high")
        self.assertEqual(self.new("explicit", "LOW")["state"]["level"], "low")
        self.call("default", "max")
        self.assertEqual(self.call("show", "sample")["state"]["level"], "high")

    def test_invalid_level_and_id_have_no_side_effects(self):
        self.call("new", "sample", "--level", "extreme", ok=False)
        self.call("new", "../escape", ok=False)
        self.assertFalse((self.repo / ".git" / "leanflow").exists())

    def test_existing_task_never_overwritten(self):
        created = self.new()
        before = Path(created["path"]).read_bytes()
        self.call("new", "sample", ok=False)
        self.assertEqual(Path(created["path"]).read_bytes(), before)

    def test_low_rejects_agent_reservation(self):
        self.new(level="low")
        for role in ("reviewer", "tester", "implementer", "product"):
            self.call("reserve", "sample", role, ok=False)
        self.assertEqual(self.call("show", "sample")["state"]["agents_used"], 0)

    def test_medium_delegates_eight_tasks_without_spending_review_budget(self):
        self.new()
        for _ in range(8):
            self.call("reserve", "sample", "implementer")
        implemented = self.call("show", "sample")
        self.assertEqual(implemented["state"]["agents_used"], 8)
        self.assertEqual(implemented["state"]["review_used"], 0)
        self.call("reserve", "sample", "reviewer")
        reviewed = self.call("reserve", "sample", "reviewer")
        self.assertEqual(reviewed["state"]["agents_used"], 10)
        before = Path(reviewed["path"]).read_bytes()
        self.assertIn("review budget exhausted", self.call("reserve", "sample", "reviewer", ok=False).stderr)
        self.assertEqual(Path(reviewed["path"]).read_bytes(), before)
        # Exhausting Review prevents another Review, not authorized implementation.
        repaired = self.call("reserve", "sample", "implementer")
        self.assertEqual(repaired["state"]["agents_used"], 11)
        self.assertEqual(repaired["state"]["review_used"], 2)

    def test_non_low_profiles_have_no_default_total_cap(self):
        for chosen, reviews in (("medium", 2), ("high", 3), ("xhigh", 6), ("max", 8)):
            with self.subTest(level=chosen):
                created = self.new("task-" + chosen, chosen)
                self.assertIsNone(created["policy"]["agent_limit"])
                self.assertEqual(created["policy"]["review_limit"], reviews)

    def test_medium_delegation_does_not_enable_product_or_e2e_tester(self):
        self.new()
        for _ in range(3):
            self.call("reserve", "sample", "implementer")
        self.assertIn("requires max", self.call("reserve", "sample", "product", ok=False).stderr)
        self.assertIn("disabled", self.call("reserve", "sample", "tester", ok=False).stderr)
        self.assertEqual(self.call("show", "sample")["state"]["agents_used"], 3)

    def test_explicit_total_cap_counts_all_roles_and_survives_level_change(self):
        self.new()
        self.call("budget", "sample", "--agents", "3", "--reason", "User requested a total cap")
        self.call("reserve", "sample", "implementer")
        self.call("reserve", "sample", "reviewer")
        self.call("reserve", "sample", "implementer")
        resumed = self.call("level", "sample", "max")
        self.assertEqual(resumed["policy"]["agent_limit"], 3)
        self.assertEqual(resumed["state"]["agents_used"], 3)
        for role in ("implementer", "reviewer", "tester", "product", "explorer"):
            with self.subTest(role=role):
                self.assertIn("total agent budget exhausted", self.call("reserve", "sample", role, ok=False).stderr)

    def test_concurrent_implementation_reservations_respect_explicit_total_cap(self):
        self.new()
        self.call("budget", "sample", "--agents", "2", "--reason", "User requested a total cap")
        def reserve(_):
            return subprocess.run([sys.executable, str(CLI), "--cwd", str(self.repo),
                                   "reserve", "sample", "implementer"], capture_output=True).returncode
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            codes = list(pool.map(reserve, range(6)))
        self.assertEqual(codes.count(0), 2)
        self.assertEqual(self.call("show", "sample")["state"]["agents_used"], 2)

    def test_removing_total_cap_preserves_usage_and_review_limit(self):
        self.new()
        self.call("budget", "sample", "--agents", "3", "--reason", "User requested a total cap")
        self.call("reserve", "sample", "reviewer")
        self.call("reserve", "sample", "reviewer")
        self.call("reserve", "sample", "implementer")
        self.call("reserve", "sample", "implementer", ok=False)
        changed = self.call("budget", "sample", "--agents", "unlimited", "--reason", "User removed the total cap")
        self.assertIsNone(changed["policy"]["agent_limit"])
        self.assertNotIn("agent_limit", changed["state"])
        self.assertEqual(changed["state"]["agents_used"], 3)
        self.assertEqual(changed["state"]["review_used"], 2)
        self.assertEqual(changed["policy"]["review_limit"], 2)
        self.call("reserve", "sample", "reviewer", ok=False)
        resumed = self.call("reserve", "sample", "implementer")
        self.assertEqual(resumed["state"]["agents_used"], 4)

    def test_removing_total_cap_does_not_enable_low_agents(self):
        self.new(level="low")
        self.call("budget", "sample", "--agents", "5", "--review", "4", "--reason", "User budget override")
        changed = self.call("budget", "sample", "--agents", "unlimited", "--reason", "User removed the total cap")
        self.assertEqual(changed["policy"]["agent_limit"], 0)
        self.call("reserve", "sample", "implementer", ok=False)
        raised = self.call("level", "sample", "medium")
        self.assertIsNone(raised["policy"]["agent_limit"])
        self.assertEqual(raised["policy"]["review_limit"], 4)

    def test_invalid_budget_changes_preserve_record(self):
        created = self.new()
        before = Path(created["path"]).read_bytes()
        for option, value in (("--agents", "-1"), ("--agents", "auto"), ("--agents", "null"),
                              ("--review", "unlimited")):
            with self.subTest(option=option, value=value):
                self.call("budget", "sample", option, value, "--reason", "Invalid input", ok=False)
                self.assertEqual(Path(created["path"]).read_bytes(), before)

    def test_old_record_without_override_resumes_without_resetting_counts(self):
        created = self.new()
        path = Path(created["path"])
        # Same schema-1 fields as a pre-0.3.3 task that reached the old medium cap.
        path.write_text(path.read_text().replace("agents_used: 0", "agents_used: 2")
                        .replace("review_used: 0", "review_used: 1"))
        before = path.read_bytes()
        resumed = self.call("show", "sample")
        self.assertIsNone(resumed["policy"]["agent_limit"])
        self.assertEqual(path.read_bytes(), before)
        reserved = self.call("reserve", "sample", "implementer")
        self.assertEqual(reserved["state"]["agents_used"], 3)
        self.assertEqual(reserved["state"]["review_used"], 1)

    def test_budget_survives_restarts_and_level_change(self):
        self.new()
        self.call("reserve", "sample", "reviewer")
        self.call("reserve", "sample", "reviewer")
        self.call("reserve", "sample", "reviewer", ok=False)
        upgraded = self.call("level", "sample", "High")
        self.assertEqual(upgraded["state"]["review_used"], 2)
        self.call("reserve", "sample", "reviewer")
        self.call("reserve", "sample", "reviewer", ok=False)
        downgraded = self.call("level", "sample", "low")
        self.assertEqual(downgraded["state"]["review_used"], 3)

    def test_concurrent_reservations_do_not_overspend(self):
        self.new()
        def reserve(_):
            return subprocess.run([sys.executable, str(CLI), "--cwd", str(self.repo),
                                   "reserve", "sample", "reviewer"], capture_output=True).returncode
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            codes = list(pool.map(reserve, range(6)))
        self.assertEqual(codes.count(0), 2)
        self.assertEqual(self.call("show", "sample")["state"]["review_used"], 2)

    def test_checkpoint_optimistic_revision_and_no_progress(self):
        created = self.new(level="max")
        body = self.base / "body.md"
        body.write_text("# Delivery\n\nA user decision.\n")
        first = self.call("checkpoint", "sample", "--revision", str(created["state"]["revision"]),
                          "--body", str(body), "--phase", "implement", "--progress", "no")
        self.call("checkpoint", "sample", "--revision", "0", "--body", str(body), ok=False)
        second = self.call("checkpoint", "sample", "--revision", str(first["state"]["revision"]),
                           "--progress", "no")
        self.assertEqual(second["state"]["stalled"], 2)
        self.call("reserve", "sample", "implementer", ok=False)
        self.assertIn("A user decision.", self.call("show", "sample")["body"])

    def test_budget_adjustment_preserves_counts_and_records_reason(self):
        self.new()
        self.call("reserve", "sample", "reviewer")
        changed = self.call("budget", "sample", "--review", "4", "--agents", "5",
                            "--reason", "User requested two more review passes")
        self.assertEqual(changed["state"]["review_used"], 1)
        self.assertEqual(changed["policy"]["review_limit"], 4)
        self.assertIn("User requested", changed["state"]["budget_reason"])

    def test_status_and_completed_task_are_preserved(self):
        created = self.new(level="low")
        done = self.call("checkpoint", "sample", "--revision", str(created["state"]["revision"]),
                         "--phase", "done", "--checks",
                         self.checks(review="not_applicable", e2e="not_applicable"))
        self.assertEqual(self.call("list")["tasks"], [])
        self.assertEqual(len(self.call("list", "--all")["tasks"]), 1)
        self.call("reserve", "sample", "reviewer", ok=False)
        self.assertEqual(self.call("show", "sample")["state"]["phase"], done["state"]["phase"])

    def test_corrupt_state_errors_instead_of_resetting_budget(self):
        created = self.new()
        path = Path(created["path"])
        path.write_text(path.read_text().replace('review_used: 0', 'review_used: "oops"'))
        self.call("reserve", "sample", "reviewer", ok=False)
        self.assertIn('review_used: "oops"', path.read_text())

    def test_export_is_explicit_snapshot_without_overwrite_or_commit(self):
        created = self.new()
        summary = self.base / "summary.md"
        summary.write_text("# Exported decision\nOnly a curated summary.\n")
        target = self.repo / "docs" / "sample.md"
        exported = self.call("export", "sample", "--summary", str(summary), "--to", str(target))
        self.assertEqual(Path(exported["path"]), target)
        self.assertIn("Only a curated summary.", target.read_text())
        self.assertIn(self.git("rev-parse", "HEAD"), target.read_text())
        self.assertNotIn("agents_used:", target.read_text())
        self.assertTrue(Path(created["path"]).exists())
        self.call("export", "sample", "--summary", str(summary), "--to", str(target), ok=False)
        self.assertEqual(self.git("diff", "--cached", "--name-only"), "")

    def test_non_git_root_fallback(self):
        folder = self.base / "plain"
        folder.mkdir()
        created = self.call("new", "plain-task", cwd=folder)
        self.assertEqual(Path(created["path"]), folder / ".leanflow" / "tasks" / "plain-task.md")

    def test_symlink_task_cannot_escape_memory_root(self):
        self.new()
        target = self.base / "other.md"
        target.write_text("Do not modify")
        alias = self.repo / ".git" / "leanflow" / "tasks" / "alias.md"
        alias.symlink_to(target)
        self.call("level", "alias", "high", ok=False)
        self.assertEqual(target.read_text(), "Do not modify")

    def test_fingerprint_tracks_uncommitted_and_untracked_scoped_files(self):
        source = self.repo / "src"
        source.mkdir()
        code = source / "main.py"
        code.write_text("x = 1\n")
        self.git("add", "src/main.py")
        first = self.call("fingerprint", "src")
        code.write_text("x = 2\n")
        second = self.call("fingerprint", "src")
        self.assertNotEqual(first["digest"], second["digest"])
        (source / "new.py").write_text("y = 3\n")
        third = self.call("fingerprint", "src")
        self.assertNotEqual(second["digest"], third["digest"])
        (self.repo / "notes.md").write_text("only documentation")
        self.assertEqual(third["digest"], self.call("fingerprint", "src")["digest"])
        self.call("fingerprint", "../", ok=False)

    def test_legacy_import_preserves_source_and_does_not_invent_baseline(self):
        source = self.repo / "plans" / "old.md"
        source.parent.mkdir()
        source.write_text("# Old feature\n- [x] Implementation\nUAT pending\n")
        content = source.read_text()
        imported = self.call("import", "old", "--source", str(source),
                             "--review-used", "2", "--agents-used", "3")
        self.assertIsNone(imported["state"]["baseline"])
        self.assertEqual(imported["state"]["review_used"], 2)
        self.assertEqual(source.read_text(), content)
        self.assertIn("UAT pending", imported["body"])

    def test_downgrade_to_low_does_not_reenable_agents_via_old_overrides(self):
        self.new()
        self.call("budget", "sample", "--review", "4", "--agents", "5", "--reason", "User choice")
        changed = self.call("level", "sample", "low")
        self.assertEqual(changed["policy"]["review_limit"], 0)
        self.assertEqual(changed["policy"]["agent_limit"], 0)
        self.call("reserve", "sample", "reviewer", ok=False)

    def test_missing_scope_is_not_reported_as_a_code_fingerprint(self):
        self.call("fingerprint", "does-not-exist", ok=False)

    def test_invalid_level_metadata_reports_error_without_traceback(self):
        created = self.new()
        path = Path(created["path"])
        path.write_text(path.read_text().replace('level: "medium"', 'level: null'))
        result = self.call("show", "sample", ok=False)
        self.assertNotIn("Traceback", result.stderr)

    def test_legacy_baseline_can_be_resolved_once_after_import(self):
        source = self.base / "old.md"
        source.write_text("# Legacy\n")
        created = self.call("import", "old", "--source", str(source),
                            "--review-used", "0", "--agents-used", "0")
        result = self.call("checkpoint", "old", "--revision", str(created["state"]["revision"]),
                           "--baseline", self.git("rev-parse", "HEAD"))
        self.assertEqual(result["state"]["baseline"], self.git("rev-parse", "HEAD"))
        self.call("checkpoint", "old", "--revision", str(result["state"]["revision"]),
                  "--baseline", "unknown-commit", ok=False)

    def test_git_init_migration_preserves_records_defaults_and_usage(self):
        plain = self.base / "plain"
        plain.mkdir()
        self.call("default", "high", cwd=plain)
        created = self.call("new", "ongoing", cwd=plain)
        self.call("reserve", "ongoing", "reviewer", cwd=plain)
        saved = self.call("show", "ongoing", cwd=plain)
        before = Path(created["path"]).read_bytes()
        subprocess.check_call(["git", "-C", str(plain), "init", "-q"])
        self.assertEqual(self.call("locate", cwd=plain)["migration_required"],
                         str(plain / ".leanflow"))
        self.assertIn("migrate", self.call("list", cwd=plain, ok=False).stderr)
        self.call("new", "duplicate", cwd=plain, ok=False)
        self.assertFalse((plain / ".git" / "leanflow").exists())
        self.call("migrate", cwd=plain)
        migrated = self.call("show", "ongoing", cwd=plain)
        self.assertEqual(migrated["state"], saved["state"])
        self.assertEqual(Path(migrated["path"]).read_bytes(), before)
        self.assertEqual(self.call("locate", cwd=plain)["default_level"], "high")
        self.assertFalse((plain / ".leanflow").exists())
        self.assertEqual(subprocess.check_output(
            ["git", "-C", str(plain), "status", "--porcelain"], text=True), "")
        self.call("checkpoint", "ongoing", "--revision", str(saved["state"]["revision"]),
                  "--phase", "awaiting_uat", "--checks",
                  self.checks(e2e="pending", uat="pending"), cwd=plain)

    def test_git_init_migration_refuses_conflicting_or_tracked_memory(self):
        plain = self.base / "plain"
        plain.mkdir()
        created = self.call("new", "ongoing", cwd=plain)
        before = Path(created["path"]).read_bytes()
        subprocess.check_call(["git", "-C", str(plain), "init", "-q"])
        target = plain / ".git" / "leanflow"
        target.mkdir()
        self.call("migrate", cwd=plain, ok=False)
        self.assertEqual(Path(created["path"]).read_bytes(), before)
        target.rmdir()
        subprocess.check_call(["git", "-C", str(plain), "add", ".leanflow"])
        self.call("migrate", cwd=plain, ok=False)
        self.assertEqual(Path(created["path"]).read_bytes(), before)
        self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
