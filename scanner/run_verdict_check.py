"""Command line check and summary for the dismissal corpus.

The curation half of `verdicts.json` is written as JSON by hand during
`/daily` Phase 4, so nothing constructs a `VerdictRecord` and nothing enforces
the closed vocabularies. A closed vocabulary is only closed if something closes
it - on the first production run, scan #109 wrote six curation rows with an
empty `rule` and a `verdict` of `"by-design not-reachable"`, neither of which
the schema allows. This is that enforcement.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scanner.verdict_corpus import load_corpus, validate_payload
from scanner.verdicts import count_by_reason, total_dismissed

DEFAULT_CORPUS_DIR = Path("corpus/verdicts")


def check_file(path: Path) -> list[str]:
    """Return every problem in one verdicts file, or an empty list."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"could not be read: {exc}"]
    return validate_payload(payload)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Validate and summarize the dismissal corpus.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", help="Path to a verdicts.json to validate.")
    mode.add_argument(
        "--summary",
        nargs="?",
        const=str(DEFAULT_CORPUS_DIR),
        help=f"Count the archived corpus (default: {DEFAULT_CORPUS_DIR}).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI wrapper. Returns 0 when valid, 2 on any problem."""
    args = parse_args(argv)

    if args.check:
        path = Path(args.check)
        problems = check_file(path)
        if problems:
            print(f"{path}: {len(problems)} problem(s)", file=sys.stderr)
            for problem in problems:
                print(f"  - {problem}", file=sys.stderr)
            return 2
        print(f"{path}: valid")
        return 0

    corpus_dir = Path(args.summary)
    if not corpus_dir.is_dir():
        print(f"No corpus directory at {corpus_dir}", file=sys.stderr)
        return 2

    try:
        records = load_corpus(corpus_dir)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Corpus could not be loaded: {exc}", file=sys.stderr)
        return 2

    scans = len(list(corpus_dir.glob("*.json")))
    print(f"Corpus: {scans} scans, {total_dismissed(records)} findings dismissed")
    for reason, count in count_by_reason(records).items():
        print(f"  {count:>6}  {reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
