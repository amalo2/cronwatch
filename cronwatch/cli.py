"""Command-line entry point for cronwatch history management."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

from cronwatch.history import DEFAULT_HISTORY_PATH, HistoryStore
from cronwatch.pruner import prune_all, DEFAULT_MAX_ENTRIES, DEFAULT_MAX_AGE_DAYS


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cronwatch-history",
        description="Inspect and manage cronwatch execution history.",
    )
    p.add_argument(
        "--history-file",
        default=str(DEFAULT_HISTORY_PATH),
        metavar="PATH",
        help="Path to the history JSON file (default: %(default)s).",
    )
    sub = p.add_subparsers(dest="command", required=True)

    # list
    ls = sub.add_parser("list", help="List recorded executions for a job.")
    ls.add_argument("job", help="Job name.")

    # clear
    cl = sub.add_parser("clear", help="Clear history for a job.")
    cl.add_argument("job", help="Job name.")

    # prune
    pr = sub.add_parser("prune", help="Prune old history entries.")
    pr.add_argument("--max-entries", type=int, default=DEFAULT_MAX_ENTRIES)
    pr.add_argument("--max-age-days", type=int, default=DEFAULT_MAX_AGE_DAYS)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    store = HistoryStore(path=Path(args.history_file))

    if args.command == "list":
        history = store.get_history(args.job)
        if not history:
            print(f"No history found for job '{args.job}'.")
        else:
            for dt in history:
                print(dt.strftime("%Y-%m-%d %H:%M:%S"))

    elif args.command == "clear":
        store.clear(args.job)
        print(f"Cleared history for job '{args.job}'.")

    elif args.command == "prune":
        prune_all(store, max_entries=args.max_entries, max_age_days=args.max_age_days)
        print("Pruning complete.")

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
