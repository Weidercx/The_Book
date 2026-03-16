#!/usr/bin/env python3
"""Build a chapter-local source index sorted by oldest textual witness date.

The output includes a prioritized diff queue so reviewers can run comparisons in
chronological order.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Dict, List

import yaml


WORK_ID_DEFAULT = "bible.ot.genesis"
UNKNOWN_YEAR_RANK = 9_999_999
HEBREW_CHAR_RE = re.compile(r"[\u0590-\u05FF]")
BLOCKING_DATA_QUALITY_FLAGS = {
    "placeholder_source_uri_detected",
    "no_hebrew_characters_detected_in_sample",
    "empty_text_content_in_sample",
}


def chapter_dir(chapter: int) -> str:
    return f"chapter_{chapter:03d}"


def default_sources_dir(work_id: str, chapter: int) -> Path:
    return Path("data") / "raw" / work_id / chapter_dir(chapter) / "sources"


def default_output_path(work_id: str, chapter: int) -> Path:
    return default_sources_dir(work_id, chapter) / "source_diff_index.json"


def default_analysis_diff_dir(work_id: str, chapter: int) -> Path:
    return Path("data") / "analysis" / work_id / chapter_dir(chapter) / "diffs"


def default_reports_dir(work_id: str, chapter: int) -> Path:
    return Path("data") / "reports" / work_id / chapter_dir(chapter)


def load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def signed_year_from_bce(year_bce: Any) -> int | None:
    if isinstance(year_bce, int):
        return -year_bce
    return None


def format_signed_year(year_signed: int | None) -> str:
    if year_signed is None:
        return "(unknown)"
    if year_signed < 0:
        return f"{abs(year_signed)} BCE"
    return f"{year_signed} CE"


def filename_year_label(year_signed: int | None) -> str:
    if year_signed is None:
        return "unknown"
    if year_signed < 0:
        return f"BCE{abs(year_signed)}"
    return f"CE{year_signed}"


def year_pair_stem(
    source_a: str,
    source_b: str,
    signed_year_by_source: Dict[str, int | None],
) -> str:
    year_a = signed_year_by_source.get(source_a)
    year_b = signed_year_by_source.get(source_b)
    return f"{filename_year_label(year_a)}_{filename_year_label(year_b)}"


def diff_output_stem(
    source_a: str,
    source_b: str,
    signed_year_by_source: Dict[str, int | None],
    include_source_pair_suffix: bool,
) -> str:
    stem = year_pair_stem(
        source_a=source_a,
        source_b=source_b,
        signed_year_by_source=signed_year_by_source,
    )
    if include_source_pair_suffix:
        return f"{stem}__{source_a}_vs_{source_b}"
    return stem


def canonical_pair(source_a: str, source_b: str) -> tuple[str, str]:
    return tuple(sorted((source_a, source_b)))


def parse_pair_from_path(path: Path) -> tuple[str, str] | None:
    stem = path.stem
    if "_vs_" not in stem:
        return None
    left, right = stem.split("_vs_", maxsplit=1)
    if "__" in left:
        left = left.rsplit("__", maxsplit=1)[-1]
    if not left or not right:
        return None
    return canonical_pair(left, right)


def extract_pair_from_report_payload(payload: Any) -> tuple[str, str] | None:
    if not isinstance(payload, dict):
        return None

    source_ordering = payload.get("source_ordering")
    if not isinstance(source_ordering, dict):
        return None

    source_a = source_ordering.get("source_a_name")
    source_b = source_ordering.get("source_b_name")
    if not isinstance(source_a, str) or not isinstance(source_b, str):
        return None

    return canonical_pair(source_a, source_b)


def load_json_payload(path: Path) -> Any | None:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None


def source_order_year(anchor: Dict[str, Any]) -> int | None:
    if not isinstance(anchor, dict):
        return None

    ordering_year_ce = anchor.get("ordering_year_ce")
    if isinstance(ordering_year_ce, int):
        return ordering_year_ce

    ordering_year_bce = signed_year_from_bce(anchor.get("ordering_year_bce"))
    if ordering_year_bce is not None:
        return ordering_year_bce

    window_ce = anchor.get("witness_anchor_window_ce")
    if isinstance(window_ce, dict) and isinstance(window_ce.get("start"), int):
        return int(window_ce["start"])

    window_bce = anchor.get("witness_anchor_window_bce")
    if isinstance(window_bce, dict):
        start_bce = signed_year_from_bce(window_bce.get("start"))
        if start_bce is not None:
            return start_bce

    date_ce = anchor.get("witness_anchor_date_ce") or anchor.get("date_ce")
    if isinstance(date_ce, int):
        return date_ce

    date_bce = signed_year_from_bce(anchor.get("witness_anchor_date_bce") or anchor.get("date_bce"))
    if date_bce is not None:
        return date_bce

    return None


def read_first_record(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                return {}
            if isinstance(parsed, dict):
                return parsed
            return {}
    return {}


def count_records(path: Path) -> int:
    count = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                count += 1
    return count


def source_content_flags(first_record: Dict[str, Any]) -> Dict[str, Any]:
    text_content = str(first_record.get("text_content") or "")
    source_uri = str(first_record.get("source_uri") or "")

    contains_hebrew = bool(HEBREW_CHAR_RE.search(text_content))
    placeholder_uri = ("example.org" in source_uri) or source_uri.startswith("dss://")

    flags: List[str] = []
    if not contains_hebrew:
        flags.append("no_hebrew_characters_detected_in_sample")
    if placeholder_uri:
        flags.append("placeholder_source_uri_detected")
    if not text_content:
        flags.append("empty_text_content_in_sample")

    return {
        "sample_text_preview": text_content[:80],
        "sample_source_uri": source_uri,
        "sample_contains_hebrew_characters": contains_hebrew,
        "sample_source_uri_looks_placeholder": placeholder_uri,
        "data_quality_flags": flags,
    }


def blocking_flags_for_source(source_row: Dict[str, Any]) -> List[str]:
    flags = source_row.get("data_quality_flags")
    if not isinstance(flags, list):
        return []

    blocking: List[str] = []
    for flag in flags:
        if isinstance(flag, str) and flag in BLOCKING_DATA_QUALITY_FLAGS:
            blocking.append(flag)

    return blocking


def discover_completed_pairs(work_id: str, chapter: int) -> set[tuple[str, str]]:
    completed: set[tuple[str, str]] = set()
    candidate_paths: List[Path] = []

    reports_dir = default_reports_dir(work_id, chapter)
    if reports_dir.exists():
        candidate_paths.extend(sorted(reports_dir.glob("*.json")))

    analysis_dir = default_analysis_diff_dir(work_id, chapter)
    if analysis_dir.exists():
        candidate_paths.extend(sorted(analysis_dir.glob("*.json")))

    for path in candidate_paths:
        payload = load_json_payload(path)

        inferred_from_payload = extract_pair_from_report_payload(payload)
        if inferred_from_payload is not None:
            completed.add(inferred_from_payload)
            continue

        inferred = parse_pair_from_path(path)
        if inferred is not None:
            completed.add(inferred)

    return completed


def order_pair_by_year(
    source_x: str,
    source_y: str,
    signed_year_by_source: Dict[str, int | None],
) -> tuple[str, str]:
    year_x = signed_year_by_source.get(source_x)
    year_y = signed_year_by_source.get(source_y)
    rank_x = year_x if isinstance(year_x, int) else UNKNOWN_YEAR_RANK
    rank_y = year_y if isinstance(year_y, int) else UNKNOWN_YEAR_RANK

    if rank_x < rank_y:
        return source_x, source_y
    if rank_y < rank_x:
        return source_y, source_x
    return (source_x, source_y) if source_x <= source_y else (source_y, source_x)


def build_pair_command(
    chapter: int,
    source_a_key: str,
    source_b_key: str,
    source_a_path: Path,
    source_b_path: Path,
    output_json: Path,
    output_markdown: Path,
) -> str:
    return (
        "python scripts/diff_genesis_sources.py "
        f"--chapter {chapter} "
        f'--source-a "{source_a_path.as_posix()}" '
        f"--source-a-name {source_a_key} "
        f'--source-b "{source_b_path.as_posix()}" '
        f"--source-b-name {source_b_key} "
        f'--output "{output_json.as_posix()}" '
        f'--markdown-output "{output_markdown.as_posix()}"'
    )


def build_diff_output_paths(
    work_id: str,
    chapter: int,
    source_a: str,
    source_b: str,
    signed_year_by_source: Dict[str, int | None],
    include_source_pair_suffix: bool,
) -> tuple[Path, Path]:
    analysis_diff_dir = default_analysis_diff_dir(work_id, chapter)
    output_stem = diff_output_stem(
        source_a=source_a,
        source_b=source_b,
        signed_year_by_source=signed_year_by_source,
        include_source_pair_suffix=include_source_pair_suffix,
    )
    return (
        analysis_diff_dir / f"{output_stem}.json",
        analysis_diff_dir / f"{output_stem}.md",
    )


def normalize_analysis_diff_filenames(
    analysis_dir: Path,
    signed_year_by_source: Dict[str, int | None],
) -> List[Dict[str, Any]]:
    return normalize_diff_artifact_filenames(
        artifacts_dir=analysis_dir,
        signed_year_by_source=signed_year_by_source,
    )


def normalize_report_diff_filenames(
    reports_dir: Path,
    signed_year_by_source: Dict[str, int | None],
) -> List[Dict[str, Any]]:
    return normalize_diff_artifact_filenames(
        artifacts_dir=reports_dir,
        signed_year_by_source=signed_year_by_source,
    )


def normalize_diff_artifact_filenames(
    artifacts_dir: Path,
    signed_year_by_source: Dict[str, int | None],
) -> List[Dict[str, Any]]:
    if not artifacts_dir.exists():
        return []

    raw_entries: List[Dict[str, Any]] = []
    for json_path in sorted(artifacts_dir.glob("*.json")):
        payload = load_json_payload(json_path)

        pair = extract_pair_from_report_payload(payload) or parse_pair_from_path(json_path)
        if pair is None:
            continue

        ordered_a, ordered_b = order_pair_by_year(
            pair[0],
            pair[1],
            signed_year_by_source,
        )
        raw_entries.append(
            {
                "json_path": json_path,
                "ordered_a": ordered_a,
                "ordered_b": ordered_b,
                "base_stem": year_pair_stem(
                    source_a=ordered_a,
                    source_b=ordered_b,
                    signed_year_by_source=signed_year_by_source,
                ),
            }
        )

    stem_counts: Dict[str, int] = {}
    for entry in raw_entries:
        base_stem = str(entry["base_stem"])
        stem_counts[base_stem] = stem_counts.get(base_stem, 0) + 1

    normalized: List[Dict[str, Any]] = []
    for entry in raw_entries:
        json_path = entry["json_path"]
        ordered_a = str(entry["ordered_a"])
        ordered_b = str(entry["ordered_b"])
        base_stem = str(entry["base_stem"])

        desired_stem = diff_output_stem(
            source_a=ordered_a,
            source_b=ordered_b,
            signed_year_by_source=signed_year_by_source,
            include_source_pair_suffix=stem_counts.get(base_stem, 0) > 1,
        )
        if json_path.stem == desired_stem:
            continue

        target_json = json_path.with_name(f"{desired_stem}.json")
        if target_json.exists() and target_json != json_path:
            continue

        markdown_from = json_path.with_suffix(".md")
        markdown_to = markdown_from.with_name(f"{desired_stem}.md")
        markdown_from_path = markdown_from.as_posix() if markdown_from.exists() else None
        markdown_to_path = None

        json_from_path = json_path.as_posix()
        json_path.rename(target_json)

        if markdown_from.exists() and markdown_from != markdown_to and not markdown_to.exists():
            markdown_from.rename(markdown_to)
            markdown_to_path = markdown_to.as_posix()
        elif markdown_to.exists():
            markdown_to_path = markdown_to.as_posix()

        normalized.append(
            {
                "source_a": ordered_a,
                "source_b": ordered_b,
                "json_from": json_from_path,
                "json_to": target_json.as_posix(),
                "markdown_from": markdown_from_path,
                "markdown_to": markdown_to_path,
            }
        )

    return normalized


def build_diff_queue(
    work_id: str,
    chapter: int,
    sources_dir: Path,
    sorted_sources: List[Dict[str, Any]],
    baseline_source: str,
    completed_pairs: set[tuple[str, str]],
    blocked_sources: Dict[str, List[str]],
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    _ = baseline_source  # retained for CLI/API compatibility
    queue: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    seen_pairs: set[tuple[str, str]] = set()
    source_order_years = {
        str(item.get("source_key")): item.get("witness_order_year_signed")
        for item in sorted_sources
    }
    source_partial_coverage = {
        str(item.get("source_key"))
        for item in sorted_sources
        if item.get("comparison_mode_hint") == "overlap_only"
    }
    year_stem_counts: Dict[str, int] = {}
    source_keys = [str(item.get("source_key")) for item in sorted_sources if isinstance(item.get("source_key"), str)]
    for index in range(len(source_keys) - 1):
        for index_b in range(index + 1, len(source_keys)):
            ordered_a, ordered_b = order_pair_by_year(
                source_keys[index],
                source_keys[index_b],
                source_order_years,
            )
            base_stem = year_pair_stem(
                source_a=ordered_a,
                source_b=ordered_b,
                signed_year_by_source=source_order_years,
            )
            year_stem_counts[base_stem] = year_stem_counts.get(base_stem, 0) + 1

    def enqueue(source_a: str, source_b: str, strategy: str, strategy_rank: int) -> None:
        pair = canonical_pair(source_a, source_b)
        if pair in seen_pairs or pair in completed_pairs:
            return

        seen_pairs.add(pair)

        blocking_reasons: List[Dict[str, Any]] = []
        if source_a in blocked_sources:
            blocking_reasons.append(
                {
                    "source": source_a,
                    "flags": blocked_sources[source_a],
                }
            )
        if source_b in blocked_sources:
            blocking_reasons.append(
                {
                    "source": source_b,
                    "flags": blocked_sources[source_b],
                }
            )

        if blocking_reasons:
            skipped.append(
                {
                    "source_a": source_a,
                    "source_b": source_b,
                    "strategy": strategy,
                    "reason": "blocked_source_data_quality",
                    "blocking_reasons": blocking_reasons,
                }
            )
            return

        base_stem = year_pair_stem(
            source_a=source_a,
            source_b=source_b,
            signed_year_by_source=source_order_years,
        )
        output_json, output_markdown = build_diff_output_paths(
            work_id=work_id,
            chapter=chapter,
            source_a=source_a,
            source_b=source_b,
            signed_year_by_source=source_order_years,
            include_source_pair_suffix=year_stem_counts.get(base_stem, 0) > 1,
        )
        source_a_path = sources_dir / f"{source_a}.jsonl"
        source_b_path = sources_dir / f"{source_b}.jsonl"

        queue.append(
            {
                "strategy": strategy,
                "strategy_rank": strategy_rank,
                "comparison_mode": (
                    "overlap_only"
                    if source_a in source_partial_coverage or source_b in source_partial_coverage
                    else "full_overlap"
                ),
                "source_a": source_a,
                "source_b": source_b,
                "output_json": output_json.as_posix(),
                "output_markdown": output_markdown.as_posix(),
                "command": build_pair_command(
                    chapter=chapter,
                    source_a_key=source_a,
                    source_b_key=source_b,
                    source_a_path=source_a_path,
                    source_b_path=source_b_path,
                    output_json=output_json,
                    output_markdown=output_markdown,
                ),
            }
        )

    if len(source_keys) < 2:
        return queue, skipped

    for index in range(len(source_keys) - 1):
        ordered_a, ordered_b = order_pair_by_year(
            source_keys[index],
            source_keys[index + 1],
            source_order_years,
        )
        enqueue(
            source_a=ordered_a,
            source_b=ordered_b,
            strategy="adjacent_chronological",
            strategy_rank=1,
        )

    for index, item in enumerate(queue, start=1):
        item["run_priority"] = index

    return queue, skipped


def build_source_index(
    work_id: str,
    chapter: int,
    sources_dir: Path,
    chronology: Dict[str, Any],
    sources_config: Dict[str, Any],
    baseline_source: str,
) -> Dict[str, Any]:
    work = (chronology.get("works") or {}).get(work_id, {})
    anchors = work.get("source_tradition_anchors") or {}
    archive_registry = (sources_config.get("archives") or {}) if isinstance(sources_config, dict) else {}

    source_rows: List[Dict[str, Any]] = []
    for file_path in sorted(sources_dir.glob("*.jsonl")):
        source_key = file_path.stem
        first_record = read_first_record(file_path)
        anchor = anchors.get(source_key, {}) if isinstance(anchors, dict) else {}
        archive = archive_registry.get(source_key, {}) if isinstance(archive_registry, dict) else {}

        order_year = source_order_year(anchor)
        content_flags = source_content_flags(first_record)

        source_rows.append(
            {
                "source_key": source_key,
                "source_file": file_path.as_posix(),
                "record_count": count_records(file_path),
                "source_archive": first_record.get("source_archive") or archive.get("name") or source_key,
                "source_url": archive.get("url"),
                "text_relation": archive.get("text_relation") or archive.get("witness_text_relation"),
                "is_translation": bool(archive.get("is_translation", False)),
                "is_transcription": bool(archive.get("is_transcription", False)),
                "attributed_author": anchor.get("attributed_author"),
                "source_basis": anchor.get("source_basis"),
                "discovery_location": anchor.get("discovery_location"),
                "witness_anchor_label": anchor.get("witness_anchor_label") or anchor.get("label"),
                "witness_order_year_signed": order_year,
                "witness_order_year_label": format_signed_year(order_year),
                "original_author_date_sort_year_signed": order_year,
                "original_author_date_label": format_signed_year(order_year),
                **content_flags,
            }
        )

    sorted_rows = sorted(
        source_rows,
        key=lambda item: (
            item.get("witness_order_year_signed")
            if isinstance(item.get("witness_order_year_signed"), int)
            else UNKNOWN_YEAR_RANK,
            str(item.get("source_key")),
        ),
    )

    source_order_years = {
        str(row.get("source_key")): row.get("witness_order_year_signed")
        for row in sorted_rows
        if isinstance(row.get("source_key"), str)
    }

    reports_dir = default_reports_dir(work_id, chapter)
    normalized_report_artifacts = normalize_report_diff_filenames(
        reports_dir=reports_dir,
        signed_year_by_source=source_order_years,
    )

    normalized_diff_artifacts = normalize_analysis_diff_filenames(
        analysis_dir=default_analysis_diff_dir(work_id, chapter),
        signed_year_by_source=source_order_years,
    )

    expected_chapter_verse_count = max(
        (int(row.get("record_count") or 0) for row in sorted_rows),
        default=0,
    )

    for row in sorted_rows:
        verse_count = int(row.get("record_count") or 0)
        missing_verse_count = max(expected_chapter_verse_count - verse_count, 0)
        coverage_complete = expected_chapter_verse_count > 0 and verse_count == expected_chapter_verse_count
        row["chapter_verse_count"] = verse_count
        row["expected_chapter_verse_count"] = expected_chapter_verse_count
        row["missing_chapter_verse_count"] = missing_verse_count
        row["chapter_coverage_complete"] = coverage_complete
        row["chapter_coverage_ratio"] = (
            round(verse_count / expected_chapter_verse_count, 4)
            if expected_chapter_verse_count > 0
            else None
        )

        flags = row.get("data_quality_flags")
        if isinstance(flags, list) and expected_chapter_verse_count > 0 and not coverage_complete:
            flags.append("incomplete_chapter_coverage")
            row["comparison_mode_hint"] = "overlap_only"
        else:
            row["comparison_mode_hint"] = "full_overlap"

    blocked_sources: Dict[str, List[str]] = {}
    for row in sorted_rows:
        source_key = row.get("source_key")
        if not isinstance(source_key, str):
            continue
        blocking = blocking_flags_for_source(row)
        if blocking:
            blocked_sources[source_key] = blocking

    discovered_completed_pairs = discover_completed_pairs(work_id=work_id, chapter=chapter)
    completed_pairs = {
        pair
        for pair in discovered_completed_pairs
        if pair[0] not in blocked_sources and pair[1] not in blocked_sources
    }
    excluded_completed_pairs = sorted(
        pair
        for pair in discovered_completed_pairs
        if pair not in completed_pairs
    )

    diff_queue, skipped_pairs = build_diff_queue(
        work_id=work_id,
        chapter=chapter,
        sources_dir=sources_dir,
        sorted_sources=sorted_rows,
        baseline_source=baseline_source,
        completed_pairs=completed_pairs,
        blocked_sources=blocked_sources,
    )

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "work_id": work_id,
        "chapter": chapter,
        "sources_directory": sources_dir.as_posix(),
        "ordering_basis": (
            "Sorted by original author date proxy using the oldest configured textual "
            "witness anchor for each source. BCE years sort earlier than CE years."
        ),
        "queue_policy": (
            "Queue unresolved adjacent chronological pairs only, skip pairs already present "
            "in reports/analysis outputs, and hard-block pairs if either source has "
            "blocking data-quality flags."
        ),
        "diff_filename_policy": (
            "Diff artifact filenames prefer compact year spans (<olderEra><olderYear>_<newerEra><newerYear>). "
            "If multiple pairs share the same year span, a <source_a>_vs_<source_b> suffix "
            "is appended to avoid collisions."
        ),
        "baseline_source": baseline_source,
        "normalized_report_artifacts": normalized_report_artifacts,
        "normalized_diff_artifacts": normalized_diff_artifacts,
        "completed_pairs": [list(pair) for pair in sorted(completed_pairs)],
        "excluded_completed_pairs": [list(pair) for pair in excluded_completed_pairs],
        "blocked_sources": [
            {"source": source, "flags": flags}
            for source, flags in sorted(blocked_sources.items())
        ],
        "skipped_pairs": skipped_pairs,
        "total_sources": len(sorted_rows),
        "sorted_sources": sorted_rows,
        "recommended_diff_queue": diff_queue,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a source index sorted by witness date with a diff execution queue"
    )
    parser.add_argument("--work-id", type=str, default=WORK_ID_DEFAULT)
    parser.add_argument("--chapter", type=int, default=1)
    parser.add_argument(
        "--sources-dir",
        type=Path,
        default=None,
        help="Override sources directory (default: data/raw/<work_id>/chapter_XXX/sources)",
    )
    parser.add_argument(
        "--chronology",
        type=Path,
        default=Path("config") / "chronology.yaml",
        help="Chronology config path",
    )
    parser.add_argument(
        "--sources-config",
        type=Path,
        default=Path("config") / "sources.yaml",
        help="Source registry config path",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSON path (default: <sources-dir>/source_diff_index.json)",
    )
    parser.add_argument(
        "--baseline-source",
        type=str,
        default="oshb",
        help="Baseline source key for unresolved gap queue generation (default: oshb)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    sources_dir = args.sources_dir or default_sources_dir(args.work_id, args.chapter)
    if not sources_dir.exists():
        raise FileNotFoundError(f"Sources directory not found: {sources_dir}")

    chronology = load_yaml(args.chronology) if args.chronology.exists() else {}
    sources_config = load_yaml(args.sources_config) if args.sources_config.exists() else {}

    output_path = args.output or default_output_path(args.work_id, args.chapter)

    index = build_source_index(
        work_id=args.work_id,
        chapter=args.chapter,
        sources_dir=sources_dir,
        chronology=chronology,
        sources_config=sources_config,
        baseline_source=args.baseline_source,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(index, handle, ensure_ascii=False, indent=2)

    print(f"Built source index for {args.work_id} chapter {args.chapter}")
    print(f"Sources indexed: {index['total_sources']}")
    print(f"Normalized report artifacts: {len(index['normalized_report_artifacts'])}")
    print(f"Normalized diff artifacts: {len(index['normalized_diff_artifacts'])}")
    print(f"Diff queue length: {len(index['recommended_diff_queue'])}")
    print(f"Output file: {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
