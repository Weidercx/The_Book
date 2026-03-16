#!/usr/bin/env python3
"""Run chronology-first skeptical review on Genesis chapter 1 JSONL output."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analyzers import DateSkepticalReviewer


WORK_ID = "bible.ot.genesis"


def chapter_dir(chapter: int) -> str:
    return f"chapter_{chapter:03d}"


def default_input_path(chapter: int) -> Path:
    return Path("data") / "raw" / WORK_ID / chapter_dir(chapter) / "sources" / "oshb.jsonl"


def default_output_path(chapter: int) -> Path:
    return Path("data") / "analysis" / WORK_ID / chapter_dir(chapter) / "skeptical_review.json"


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def _load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def run_review(
    input_path: Path,
    chronology_path: Path,
    output_path: Path,
    baseline_path: Optional[Path],
) -> int:
    records = _load_jsonl(input_path)
    chronology = _load_yaml(chronology_path)

    baseline_records: Optional[List[Dict[str, Any]]] = None
    if baseline_path is not None and baseline_path.exists():
        baseline_records = _load_jsonl(baseline_path)

    reviewer = DateSkepticalReviewer(chronology)
    report = reviewer.review(records=records, baseline_records=baseline_records)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)

    print(f"Review status: {report.get('status')}")
    print(f"Risk level: {report.get('risk_level')}")
    print(f"Findings: {len(report.get('findings', []))}")
    print(f"Output report: {output_path}")

    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Chronology-first skeptical review for Genesis chapter 1"
    )
    parser.add_argument(
        "--chapter",
        type=int,
        default=1,
        help="Genesis chapter number (default: 1)",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Path to input JSONL witness records (default: data/raw/bible.ot.genesis/chapter_XXX/sources/oshb.jsonl)",
    )
    parser.add_argument(
        "--chronology",
        type=Path,
        default=Path("config") / "chronology.yaml",
        help="Path to chronology config",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Path to output review JSON (default: data/analysis/bible.ot.genesis/chapter_XXX/skeptical_review.json)",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=None,
        help="Optional baseline JSONL for release comparison",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = args.input or default_input_path(args.chapter)
    output_path = args.output or default_output_path(args.chapter)
    return run_review(
        input_path=input_path,
        chronology_path=args.chronology,
        output_path=output_path,
        baseline_path=args.baseline,
    )


if __name__ == "__main__":
    raise SystemExit(main())
