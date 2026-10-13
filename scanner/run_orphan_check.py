"""Find `/daily` runs that died without recording themselves.

Between 2026-09-25 and 2026-10-03 seven `/daily` runs scanned a repo and then ended
in curation (a model safety stop), before Phase 6. State was only written at the
end, so `last_run` stayed stale, the one-scan-per-day rule never fired and every
morning spent a fresh scan: seven scans lost, nothing published, nobody told for a
week. A run now opens its record in `runs_recent` before it scans and closes it in
Phase 6. This check finds the records that never closed, and the scan output that
has no record at all.

Exit codes follow `run_verdict_check.py`: 0 when every run is accounted for, 2 on
any orphan.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

DEFAULT_STATE = Path("reports/.daily_state.json")
DEFAULT_REPORTS_DIR = Path("reports")
DEFAULT_SCANS_DIR = Path("docs/scans")
DEFAULT_PAUSE_FILE = Path(".daily-paused")

IN_PROGRESS = "in-progress"
OPEN_RECORD = "open-record"
UNRECORDED_SCAN = "unrecorded-scan"
UNREADABLE_STATE = "unreadable-state"


@dataclass(frozen=True)
class Orphan:
    """One run that did not finish recording itself."""

    slug: str
    kind: str
    reason: str


def load_state(path: Path) -> dict[str, Any]:
    """Read the state file.

    Args:
        path: Location of `reports/.daily_state.json`.

    Returns:
        The parsed state. A missing file is an empty state.

    Raises:
        ValueError: If the file exists but is not a readable JSON object.
    """
    if not path.exists():
        return {}
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{path} could not be read: {exc}") from exc
    if not isinstance(state, dict):
        raise ValueError(f"{path} does not hold a JSON object.")
    return state


def save_state(path: Path, state: dict[str, Any], today: str) -> None:
    """Rewrite the state file atomically, first keeping `<name>.bak-<today>`.

    The state file is gitignored, so there is no history to fall back on. The
    day's first backup is kept: a second rewrite the same day must not replace
    the copy that still holds the state as the interrupted run left it.
    """
    backup = path.with_name(f"{path.name}.bak-{today}")
    if path.exists() and not backup.exists():
        shutil.copy2(path, backup)
    staged = path.with_name(path.name + ".tmp")
    staged.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    staged.replace(path)


def _as_day(value: object) -> date | None:
    """Parse an ISO date, or return None when it is missing or malformed."""
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def _is_stale_open(entry: dict[str, Any], today: date) -> bool:
    """A record opened before today, or on a date nobody can read, and never closed."""
    if entry.get("outcome") != IN_PROGRESS:
        return False
    opened = _as_day(entry.get("date"))
    return opened is None or opened < today


def _is_scan_output(directory: Path) -> bool:
    """Scan output is a directory holding `raw/`, the first thing any scan writes.

    `disclosures/` and `fingerprint/` sit beside it and are not scans, and a name
    starting with `_` or `.` is scratch (`_daily_tmp/` holds `raw/` copies too).
    """
    return (
        directory.is_dir()
        and not directory.name.startswith(("_", "."))
        and (directory / "raw").is_dir()
    )


def find_orphans(
    state: dict[str, Any], reports_dir: Path, scans_dir: Path, today: str
) -> list[Orphan]:
    """Return every run that opened without closing and every scan nothing accounts for.

    Args:
        state: Parsed `reports/.daily_state.json`.
        reports_dir: Directory holding one `<slug>/` of scan output per run.
        scans_dir: Directory of published posts, `<slug>.md`.
        today: Local date as `YYYY-MM-DD`.

    Returns:
        Open records from an earlier day, then scan output written after `last_run`
        that has neither a post nor a run record.
    """
    today_day = date.fromisoformat(today)
    entries = [entry for entry in state.get("runs_recent") or [] if isinstance(entry, dict)]
    orphans = [
        Orphan(
            str(entry.get("slug") or "?"),
            OPEN_RECORD,
            f"run record from {entry.get('date') or 'an unknown day'} is still 'in-progress'",
        )
        for entry in entries
        if _is_stale_open(entry, today_day)
    ]

    recorded = {str(entry.get("slug")) for entry in entries}
    last_run = _as_day(state.get("last_run"))
    candidates = sorted(reports_dir.iterdir()) if reports_dir.is_dir() else []
    for directory in candidates:
        slug = directory.name
        if not _is_scan_output(directory) or slug in recorded:
            continue
        if (scans_dir / f"{slug}.md").is_file():
            continue
        written = date.fromtimestamp(directory.stat().st_mtime)
        if last_run is not None and written <= last_run:
            continue
        orphans.append(
            Orphan(
                slug,
                UNRECORDED_SCAN,
                f"scan output written {written.isoformat()} has no post and no run record",
            )
        )
    return orphans


def acknowledge(state: dict[str, Any], orphans: list[Orphan], today: str) -> int:
    """Mark every orphan as reviewed so the check stops flagging it.

    Closes each stale open record and adds a closed record for each unrecorded
    scan. Today's open record is left alone: its run may still be going.

    Args:
        state: Parsed state; modified in place.
        orphans: What `find_orphans` returned for this state.
        today: Local date as `YYYY-MM-DD`.

    Returns:
        How many entries were closed or added.
    """
    note = f"halted: acknowledged {today} after review"
    today_day = date.fromisoformat(today)
    entries = state.get("runs_recent")
    if not isinstance(entries, list):
        entries = state["runs_recent"] = []

    changed = 0
    for entry in entries:
        if isinstance(entry, dict) and _is_stale_open(entry, today_day):
            entry["outcome"] = note
            changed += 1
    for orphan in orphans:
        if orphan.kind == UNRECORDED_SCAN:
            entries.append({"date": today, "slug": orphan.slug, "outcome": note})
            changed += 1
    return changed


def write_pause(pause_file: Path, orphans: list[Orphan], today: str) -> bool:
    """Create the kill switch naming the orphans. An existing one is never overwritten.

    Returns:
        True when the file was created, False when one was already there.
    """
    lines = [
        f"Paused {today} by scanner/run_orphan_check.py.",
        "",
        "A previous /daily run ended without finishing, so scanning is stopped:",
        "",
        *[f"  - {orphan.slug}: {orphan.reason}" for orphan in orphans],
        "",
        "Review the items above (reports/<slug>/ and the run records in",
        "reports/.daily_state.json). When each one is understood, run",
        "  .venv/Scripts/python.exe scanner/run_orphan_check.py --acknowledge",
        "then delete this file to resume.",
    ]
    try:
        with pause_file.open("x", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
    except FileExistsError:
        return False
    return True


def _iso_day(value: str) -> str:
    """Argparse type for `--today`."""
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{value!r} is not a YYYY-MM-DD date.") from exc


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Find /daily runs that died without recording themselves."
    )
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORTS_DIR)
    parser.add_argument("--scans-dir", type=Path, default=DEFAULT_SCANS_DIR)
    parser.add_argument("--pause-file", type=Path, default=DEFAULT_PAUSE_FILE)
    parser.add_argument("--today", type=_iso_day, help="Override today's date (YYYY-MM-DD).")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--write-pause",
        action="store_true",
        help="On any orphan, create the kill switch naming it (never overwrites).",
    )
    mode.add_argument(
        "--acknowledge",
        action="store_true",
        help="After review, close every orphan so the check goes quiet.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI wrapper. Returns 0 when every run is accounted for, 2 otherwise."""
    args = parse_args(argv)
    today = args.today or date.today().isoformat()

    state: dict[str, Any] | None
    try:
        state = load_state(args.state)
    except ValueError as exc:
        # A pipeline that cannot read its own state must not scan blind.
        state = None
        orphans = [Orphan("<state file>", UNREADABLE_STATE, str(exc))]
    else:
        orphans = find_orphans(state, args.reports_dir, args.scans_dir, today)

    if args.acknowledge and state is not None:
        changed = acknowledge(state, orphans, today)
        if changed:
            save_state(args.state, state, today)
        print(f"Acknowledged {changed} interrupted run(s).")
        return 0

    if not orphans:
        print("No interrupted runs.")
        return 0

    print(f"{len(orphans)} interrupted run(s):", file=sys.stderr)
    for orphan in orphans:
        print(f"  - {orphan.slug}: {orphan.reason}", file=sys.stderr)
    if args.write_pause and write_pause(args.pause_file, orphans, today):
        print(f"Wrote {args.pause_file}.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
