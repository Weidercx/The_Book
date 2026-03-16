#!/usr/bin/env python3
"""Pull Genesis chapter DSS Hebrew transcriptions and write verse-level JSONL output."""

from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import sys
from pathlib import Path
from typing import Any, Dict

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.adapters.dss_adapter import DSSGenesisTranscriptionAdapter
from src.core import IngestPolicy


WORK_ID = "bible.ot.genesis"
ARCHIVE_KEY_DEFAULT = "dss_4qgen"


def default_output_path(chapter: int, source_key: str) -> Path:
    chapter_dir = f"chapter_{chapter:03d}"
    return Path("data") / "raw" / WORK_ID / chapter_dir / "sources" / f"{source_key}.jsonl"


def load_source_config(config_path: Path, source_key: str) -> Dict[str, Any]:
    with config_path.open("r", encoding="utf-8") as handle:
        parsed = yaml.safe_load(handle)

    archives = parsed.get("archives", {})
    source_config = archives.get(source_key)
    if not source_config:
        raise ValueError(f"Missing '{source_key}' configuration in config/sources.yaml")

    return source_config


def resolve_adapter_class(source_config: Dict[str, Any]):
    adapter_path = str(source_config.get("adapter_class") or "").strip()
    if not adapter_path:
        return DSSGenesisTranscriptionAdapter

    module_path, _, class_name = adapter_path.rpartition(".")
    if not module_path or not class_name:
        raise ValueError(f"Invalid adapter_class path: {adapter_path}")

    module = importlib.import_module(module_path)
    adapter_class = getattr(module, class_name, None)
    if adapter_class is None:
        raise ValueError(f"Adapter class not found: {adapter_path}")

    return adapter_class


async def run_pull(
    source_key: str,
    chapter: int,
    output_path: Path | None,
    input_json: Path | None,
    timeout_seconds: int,
) -> int:
    config_path = Path("config") / "sources.yaml"
    source_config = load_source_config(config_path, source_key)

    payload_override: Dict[str, Any] | None = None
    if input_json is not None:
        with input_json.open("r", encoding="utf-8-sig") as handle:
            loaded = json.load(handle)
        if not isinstance(loaded, dict):
            raise ValueError("Input JSON must contain an object payload")
        payload_override = loaded

    adapter_class = resolve_adapter_class(source_config)
    adapter = adapter_class(config=source_config)
    witness_records = await adapter.run(
        chapter=chapter,
        timeout_seconds=timeout_seconds,
        payload_override=payload_override,
    )

    resolved_output_path = output_path or default_output_path(chapter, source_key)
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

    print(f"Pulled {source_key} Genesis chapter {chapter}")
    print(f"Verse records written: {len(witness_records)}")
    print(f"Policy gate failures: {failing_records}")
    if input_json is not None:
        print(f"Input payload: {input_json}")
    print(f"Output file: {resolved_output_path}")

    return 0 if witness_records else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Pull Genesis chapter from a Hebrew transcription payload into verse-level WitnessRecords"
        )
    )
    parser.add_argument(
        "--source-key",
        type=str,
        default=ARCHIVE_KEY_DEFAULT,
        help="Source key from config/sources.yaml (default: dss_4qgen)",
    )
    parser.add_argument(
        "--chapter",
        type=int,
        default=1,
        help="Genesis chapter number (default: 1)",
    )
    parser.add_argument(
        "--input-json",
        type=Path,
        default=None,
        help=(
            "Local transcription JSON payload. "
            "If omitted, adapter will use <source-key>.api_endpoint from config/sources.yaml"
        ),
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=45,
        help="HTTP timeout when fetching remote payloads (default: 45)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "JSONL output path "
            "(default: data/raw/bible.ot.genesis/chapter_XXX/sources/<source-key>.jsonl)"
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return asyncio.run(
        run_pull(
            source_key=args.source_key,
            chapter=args.chapter,
            output_path=args.output,
            input_json=args.input_json,
            timeout_seconds=args.timeout_seconds,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
