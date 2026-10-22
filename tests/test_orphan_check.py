"""Tests for the interrupted-run check that guards the `/daily` pipeline.

Between 2026-09-25 and 2026-10-03 seven `/daily` runs scanned a repo and then
ended in curation, before Phase 6. State was only written at the end, so
`last_run` stayed stale, the one-scan-per-day rule never fired and every morning
spent a fresh scan: seven scans lost, nothing published, nobody told for a week.
These tests pin the check that makes such a run visible the next morning, and
the escape hatches that keep it from turning into a permanent false alarm.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from scanner.run_orphan_check import find_orphans, main

TODAY = "2026-10-13"
LAST_RUN = "2026-10-04"


def _entry(slug: str, date: str, outcome: str) -> dict[str, str]:
    """Build one `runs_recent` record."""
    return {"date": date, "slug": slug, "repo": f"owner/{slug}", "outcome": outcome}


def _set_day(path: Path, day: str) -> None:
    """Pin a directory's modification time to noon on `day`."""
    stamp = datetime.fromisoformat(f"{day}T12:00:00").timestamp()
    os.utime(path, (stamp, stamp))


def _scan_dir(reports: Path, slug: str, day: str) -> Path:
    """Create scan output (a `raw/` directory) last written on `day`."""
    directory = reports / slug
    (directory / "raw").mkdir(parents=True)
    _set_day(directory, day)
    return directory


@pytest.fixture()
def root(tmp_path: Path) -> Path:
    """A repo-shaped tree: stand-ins for `reports/` and `docs/scans/`, no state file yet."""
    (tmp_path / "reports").mkdir()
    (tmp_path / "scans").mkdir()
    return tmp_path


def _write_state(root: Path, **overrides: object) -> Path:
    """Write a state file shaped like `reports/.daily_state.json`."""
    state: dict[str, object] = {"last_run": LAST_RUN, "scans_count": 112, "runs_recent": []}
    state.update(overrides)
    path = root / "state.json"
    path.write_text(json.dumps(state), encoding="utf-8")
    return path


def _read_state(root: Path) -> dict[str, Any]:
    """Read back the state file the check may have rewritten."""
    return json.loads((root / "state.json").read_text(encoding="utf-8"))


def _orphans(root: Path) -> list[tuple[str, str]]:
    """Run the check against `root` and return (slug, kind) pairs."""
    found = find_orphans(_read_state(root), root / "reports", root / "scans", TODAY)
    return [(orphan.slug, orphan.kind) for orphan in found]


def _run(root: Path, *flags: str) -> int:
    """Invoke the CLI against `root` with today pinned."""
    return main(
        [
            "--state",
            str(root / "state.json"),
            "--reports-dir",
            str(root / "reports"),
            "--scans-dir",
            str(root / "scans"),
            "--pause-file",
            str(root / ".daily-paused"),
            "--today",
            TODAY,
            *flags,
        ]
    )


class TestRecordsLeftOpen:
    """A run that opened its record and never closed it died without saying so."""

    def test_record_left_in_progress_by_an_earlier_day_is_an_orphan(self, root: Path) -> None:
        _write_state(root, runs_recent=[_entry("isair-jarvis", "2026-10-12", "in-progress")])
        assert _orphans(root) == [("isair-jarvis", "open-record")]

    def test_record_opened_today_is_not_an_orphan(self, root: Path) -> None:
        """A live run, or a same-day re-invocation, must not pause itself."""
        _write_state(root, runs_recent=[_entry("isair-jarvis", TODAY, "in-progress")])
        assert _orphans(root) == []

    def test_open_record_without_a_date_fails_closed(self, root: Path) -> None:
        _write_state(root, runs_recent=[{"slug": "zju-real-easel", "outcome": "in-progress"}])
        assert _orphans(root) == [("zju-real-easel", "open-record")]

    @pytest.mark.parametrize(
        "outcome",
        [
            "post-only",
            "halted: safety stop during curation",
            "withheld-private (GHSA-xp54-2hxc-w78q, PVR triage)",
        ],
    )
    def test_closed_records_are_never_orphans(self, root: Path, outcome: str) -> None:
        _write_state(root, runs_recent=[_entry("fossasia-voxbento", "2026-09-28", outcome)])
        assert _orphans(root) == []


class TestUnrecordedScans:
    """The safety net: scan output the pipeline has no record of and never published."""

    def test_new_scan_output_with_no_post_and_no_record_is_an_orphan(self, root: Path) -> None:
        _write_state(root)
        _scan_dir(root / "reports", "zju-real-easel", "2026-10-05")
        assert _orphans(root) == [("zju-real-easel", "unrecorded-scan")]

    def test_a_published_post_accounts_for_the_scan(self, root: Path) -> None:
        _write_state(root)
        _scan_dir(root / "reports", "zju-real-easel", "2026-10-05")
        (root / "scans" / "zju-real-easel.md").write_text("# post", encoding="utf-8")
        assert _orphans(root) == []

    def test_a_run_record_accounts_for_the_scan(self, root: Path) -> None:
        entry = _entry("zju-real-easel", "2026-10-05", "halted: safety stop")
        _write_state(root, runs_recent=[entry])
        _scan_dir(root / "reports", "zju-real-easel", "2026-10-05")
        assert _orphans(root) == []

    def test_scan_output_not_newer_than_last_run_is_ignored(self, root: Path) -> None:
        """History already handled must stay quiet: the seven stranded dirs predate last_run."""
        _write_state(root)
        _scan_dir(root / "reports", "samugit83-redamon", LAST_RUN)
        assert _orphans(root) == []

    def test_directories_that_are_not_scan_output_are_ignored(self, root: Path) -> None:
        _write_state(root)
        reports = root / "reports"
        for name in ("disclosures", "fingerprint"):
            (reports / name).mkdir()
            (reports / name / "note.md").write_text("x", encoding="utf-8")
            _set_day(reports / name, "2026-10-05")
        # Scratch directories are skipped by name even when they hold a `raw/`.
        _scan_dir(reports, "_daily_tmp", "2026-10-05")
        _scan_dir(reports, ".cache", "2026-10-05")
        (reports / "isair-jarvis.scan.log").write_text("x", encoding="utf-8")
        assert _orphans(root) == []

    def test_a_missing_state_file_still_checks_the_directories(self, root: Path) -> None:
        _scan_dir(root / "reports", "zju-real-easel", "2026-10-05")
        assert _run(root) == 2


class TestExitCodesAndPause:
    """Phase 0 relies on the exit code; the pause file is what survives the run."""

    def test_healthy_state_exits_zero_and_writes_no_pause_file(self, root: Path) -> None:
        _write_state(root, runs_recent=[_entry("fossasia-voxbento", "2026-09-28", "post-only")])
        assert _run(root, "--write-pause") == 0
        assert not (root / ".daily-paused").exists()

    def test_orphans_exit_two_and_are_named_on_stderr(
        self, root: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _write_state(root, runs_recent=[_entry("isair-jarvis", "2026-10-12", "in-progress")])
        assert _run(root) == 2
        assert "isair-jarvis" in capsys.readouterr().err

    def test_without_the_flag_no_pause_file_is_written(self, root: Path) -> None:
        """A status-only run reports orphans but must not pause the pipeline."""
        _write_state(root, runs_recent=[_entry("isair-jarvis", "2026-10-12", "in-progress")])
        assert _run(root) == 2
        assert not (root / ".daily-paused").exists()

    def test_write_pause_creates_the_kill_switch_naming_the_orphan(self, root: Path) -> None:
        _write_state(root, runs_recent=[_entry("isair-jarvis", "2026-10-12", "in-progress")])
        assert _run(root, "--write-pause") == 2
        assert "isair-jarvis" in (root / ".daily-paused").read_text(encoding="utf-8")

    def test_write_pause_keeps_an_existing_kill_switch(self, root: Path) -> None:
        """A hand-written pause note must not be clobbered by the automatic one."""
        _write_state(root, runs_recent=[_entry("isair-jarvis", "2026-10-12", "in-progress")])
        pause = root / ".daily-paused"
        pause.write_text("Paused by hand.\n", encoding="utf-8")
        assert _run(root, "--write-pause") == 2
        assert pause.read_text(encoding="utf-8") == "Paused by hand.\n"

    def test_unreadable_state_fails_closed(self, root: Path) -> None:
        """A pipeline that cannot read its own state must not scan blind."""
        (root / "state.json").write_text("{not json", encoding="utf-8")
        assert _run(root, "--write-pause") == 2
        assert (root / ".daily-paused").exists()


class TestAcknowledge:
    """After review the user must be able to clear a flag, or the pipeline never resumes."""

    def test_acknowledging_an_open_record_clears_the_check(self, root: Path) -> None:
        _write_state(root, runs_recent=[_entry("isair-jarvis", "2026-10-12", "in-progress")])
        assert _run(root, "--acknowledge") == 0
        assert _run(root) == 0
        outcome = _read_state(root)["runs_recent"][0]["outcome"]
        assert outcome == "halted: acknowledged 2026-10-13 after review"

    def test_acknowledging_an_unrecorded_scan_clears_the_check(self, root: Path) -> None:
        _write_state(root)
        _scan_dir(root / "reports", "zju-real-easel", "2026-10-05")
        assert _run(root, "--acknowledge") == 0
        assert _run(root) == 0
        slugs = [entry["slug"] for entry in _read_state(root)["runs_recent"]]
        assert slugs == ["zju-real-easel"]

    def test_acknowledging_leaves_todays_open_record_alone(self, root: Path) -> None:
        """Today's record may belong to a run that is still going."""
        _write_state(root, runs_recent=[_entry("isair-jarvis", TODAY, "in-progress")])
        assert _run(root, "--acknowledge") == 0
        assert _read_state(root)["runs_recent"][0]["outcome"] == "in-progress"

    def test_the_rewrite_keeps_every_other_key(self, root: Path) -> None:
        _write_state(
            root,
            excluded_repos=["a/b"],
            runs_recent=[_entry("isair-jarvis", "2026-10-12", "in-progress")],
        )
        assert _run(root, "--acknowledge") == 0
        state = _read_state(root)
        assert state["scans_count"] == 112
        assert state["excluded_repos"] == ["a/b"]
        assert state["last_run"] == LAST_RUN

    def test_the_previous_state_is_kept_as_a_dated_backup(self, root: Path) -> None:
        """The state file is gitignored, so a bad rewrite would be unrecoverable."""
        path = _write_state(root, runs_recent=[_entry("isair-jarvis", "2026-10-12", "in-progress")])
        before = path.read_text(encoding="utf-8")
        assert _run(root, "--acknowledge") == 0
        assert (root / f"state.json.bak-{TODAY}").read_text(encoding="utf-8") == before

    def test_a_second_acknowledgement_keeps_the_first_backup_of_the_day(self, root: Path) -> None:
        """The earliest copy is the one that holds the state as the run left it."""
        first = _entry("isair-jarvis", "2026-10-12", "in-progress")
        path = _write_state(root, runs_recent=[first])
        original = path.read_text(encoding="utf-8")
        assert _run(root, "--acknowledge") == 0
        _write_state(root, runs_recent=[_entry("zju-real-easel", "2026-10-11", "in-progress")])
        assert _run(root, "--acknowledge") == 0
        assert (root / f"state.json.bak-{TODAY}").read_text(encoding="utf-8") == original

    def test_nothing_to_acknowledge_leaves_the_state_untouched(self, root: Path) -> None:
        path = _write_state(root, runs_recent=[_entry("fossasia-voxbento", "2026-09-28", "done")])
        before = path.read_text(encoding="utf-8")
        assert _run(root, "--acknowledge") == 0
        assert path.read_text(encoding="utf-8") == before
        assert not list(root.glob("state.json.bak*"))
