#!/usr/bin/env python3
"""Pull Genesis chapter 1 from Sefaria Hebrew API and write verse-level JSONL output."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.adapters.sefaria_adapter import SefariaGenesisAdapter
from src.core import IngestPolicy


WORK_ID = "bible.ot.genesis"


def default_output_path(chapter: int) -> Path:
    chapter_dir = f"chapter_{chapter:03d}"
    return Path("data") / "raw" / WORK_ID / chapter_dir / "sources" / "sefaria_mam.jsonl"


def load_sefaria_config(config_path: Path) -> Dict[str, Any]:
    with config_path.open("r", encoding="utf-8") as handle:
        parsed = yaml.safe_load(handle)

    archives = parsed.get("archives", {})
    sefaria_config = archives.get("sefaria_mam")
    if not sefaria_config:
        raise ValueError("Missing 'sefaria_mam' configuration in config/sources.yaml")

    return sefaria_config


async def run_pull(chapter: int, output_path: Path | None) -> int:
    config_path = Path("config") / "sources.yaml"
    sefaria_config = load_sefaria_config(config_path)

    adapter = SefariaGenesisAdapter(config=sefaria_config)
    witness_records = await adapter.run(chapter=chapter)

    resolved_output_path = output_path or default_output_path(chapter)

    resolved_output_path.parent.mkdir(parents=True, exist_ok=True)

    failing_records = 0
    with resolved_output_path.open("w", encoding="utf-8") as handle:
        for record in witness_records:
            gate_results = IngestPolicy.check_ingest_gates(record)
            gate_ok = all(result[0] for result in gate_results.values())
            if not gate_ok:
                failing_records += 1

            payload = record.model_dump(mode="json")
            payload["gate_results"] = {
                gate: {"valid": valid, "message": message}
                for gate, (valid, message) in gate_results.items()
            }
            payload["gate_ok"] = gate_ok

            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    print(f"Pulled Sefaria Genesis chapter {chapter}")
    print(f"Verse records written: {len(witness_records)}")
    print(f"Policy gate failures: {failing_records}")
    print(f"Output file: {resolved_output_path}")

    return 0 if witness_records else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pull Genesis chapter from Sefaria into verse-level WitnessRecords"
    )
    parser.add_argument(
        "--chapter",
        type=int,
        default=1,
        help="Genesis chapter number (default: 1)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="JSONL output path (default: data/raw/bible.ot.genesis/chapter_XXX/sources/sefaria_mam.jsonl)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return asyncio.run(run_pull(chapter=args.chapter, output_path=args.output))


if __name__ == "__main__":
    raise SystemExit(main())
