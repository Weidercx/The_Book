#!/usr/bin/env python3
"""Cross-source Genesis chapter comparison with date-aware skeptical checks."""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

WORK_ID = "bible.ot.genesis"
VERSE_REF_RE = re.compile(r"Gen\.(\d+)\.(\d+)$")


def chapter_dir(chapter: int) -> str:
    return f"chapter_{chapter:03d}"


def default_raw_source_path(chapter: int, source_name: str) -> Path:
    return Path("data") / "raw" / WORK_ID / chapter_dir(chapter) / f"{source_name}.jsonl"


def default_report_json_path(chapter: int) -> Path:
    return Path("data") / "reports" / WORK_ID / chapter_dir(chapter) / "cross_source_diff.json"


def default_report_markdown_path(chapter: int) -> Path:
    return Path("data") / "reports" / WORK_ID / chapter_dir(chapter) / "cross_source_diff.md"


def load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def verse_sort_key(verse_ref: str) -> tuple[int, int, str]:
    """Sort verse refs in numeric chapter order when possible."""
    match = VERSE_REF_RE.search(verse_ref)
    if match:
        return int(match.group(1)), int(match.group(2)), ""
    return 999_999, 999_999, verse_ref


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def verse_key(record: Dict[str, Any]) -> str:
    source_uri = str(record.get("source_uri", ""))
    if "#" in source_uri:
        fragment = source_uri.split("#", maxsplit=1)[1]
        match = VERSE_REF_RE.search(fragment)
        if match:
            return f"Gen.{match.group(1)}.{match.group(2)}"

    notes = str(record.get("notes", ""))
    match = re.search(r"Genesis\s+(\d+):(\d+)", notes)
    if match:
        return f"Gen.{match.group(1)}.{match.group(2)}"

    return source_uri or notes or "unknown"


def source_dates(records: List[Dict[str, Any]]) -> List[str]:
    values = sorted({str(rec.get("source_version_date")) for rec in records if rec.get("source_version_date")})
    return values


def build_chronology_context(
    chronology_config: Dict[str, Any],
    work_id: str,
    source_a_name: str,
    source_b_name: str,
) -> Dict[str, Any]:
    works = chronology_config.get("works", {})
    work = works.get(work_id, {})
    anchors = work.get("source_tradition_anchors", {})

    selected_anchors: Dict[str, Any] = {}
    for source_name in (source_a_name, source_b_name):
        if source_name in anchors:
            selected_anchors[source_name] = anchors[source_name]

    return {
        "tradition_label": work.get("tradition_label"),
        "composition_window_bce": work.get("composition_window_bce"),
        "earliest_known_textual_witness_window_bce": work.get("earliest_known_textual_witness_window_bce"),
        "base_witness": work.get("base_witness"),
        "source_tradition_anchors": selected_anchors,
    }


def format_window_bce(window: Any) -> str:
    if not isinstance(window, dict):
        return "(unknown)"
    start = window.get("start")
    end = window.get("end")
    if start is None or end is None:
        return "(unknown)"
    return f"{start}-{end} BCE"


def format_anchor(anchor: Dict[str, Any]) -> str:
    if not anchor:
        return "(unknown)"

    label = anchor.get("witness_anchor_label") or anchor.get("label") or "(unnamed anchor)"
    date_ce = anchor.get("witness_anchor_date_ce") or anchor.get("date_ce")
    window_ce = anchor.get("witness_anchor_window_ce")

    if isinstance(window_ce, dict) and window_ce.get("start") is not None and window_ce.get("end") is not None:
        return f"{label} ({window_ce.get('start')}-{window_ce.get('end')} CE)"
    if date_ce is not None:
        return f"{label} ({date_ce} CE)"

    return str(label)


def record_detail(record: Dict[str, Any]) -> Dict[str, Any]:
    """Return human-review detail fields for one source record."""
    return {
        "source_archive": record.get("source_archive"),
        "source_uri": record.get("source_uri"),
        "source_version_date": record.get("source_version_date"),
        "content_hash": record.get("content_hash"),
        "text_content": record.get("text_content"),
    }


def token_diff_ops(source_a_text: str, source_b_text: str) -> Dict[str, Any]:
    """Compute token-level change operations between two verse strings."""
    a_tokens = source_a_text.split()
    b_tokens = source_b_text.split()
    matcher = difflib.SequenceMatcher(a=a_tokens, b=b_tokens, autojunk=False)

    operations: List[Dict[str, Any]] = []
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == "equal":
            continue
        operations.append(
            {
                "op": op,
                "source_a_range": [i1, i2],
                "source_b_range": [j1, j2],
                "source_a_tokens": a_tokens[i1:i2],
                "source_b_tokens": b_tokens[j1:j2],
            }
        )

    char_similarity = difflib.SequenceMatcher(a=source_a_text, b=source_b_text, autojunk=False).ratio()

    return {
        "source_a_token_count": len(a_tokens),
        "source_b_token_count": len(b_tokens),
        "token_similarity_ratio": matcher.ratio(),
        "char_similarity_ratio": char_similarity,
        "operations": operations,
    }


def render_token_pr_diff(source_a_text: str, source_b_text: str) -> str:
    """Render token-level PR-style diff with + and - prefixes."""
    a_tokens = source_a_text.split()
    b_tokens = source_b_text.split()

    rendered: List[str] = []
    for row in difflib.ndiff(a_tokens, b_tokens):
        if row.startswith("? "):
            continue

        marker = row[0]
        token = row[2:]
        if marker == "-":
            rendered.append(f"- {token}")
        elif marker == "+":
            rendered.append(f"+ {token}")
        else:
            rendered.append(f"  {token}")

    if not rendered:
        return "  (no token-level differences)"

    return "\n".join(rendered)


def render_markdown_report(report: Dict[str, Any], source_a_name: str, source_b_name: str) -> str:
    """Render human-readable PR/MR style markdown report with diff blocks."""
    lines: List[str] = []
    comparison = report.get("comparison", {})
    sources = report.get("sources", {})
    chronology = report.get("chronology", {})

    lines.append("# Genesis 1 Cross-Source Diff (PR Style)")
    lines.append("")
    lines.append(f"- Work: {report.get('work_id')}")
    lines.append(f"- Chapter: {report.get('chapter')}")
    lines.append(f"- Risk level: {report.get('risk_level')}")
    lines.append(f"- Shared verses: {comparison.get('shared_verses')}")
    lines.append(f"- Changed verses: {comparison.get('changed_hash_verses')}")
    lines.append("")

    lines.append("## Chronology Axis (Primary)")
    lines.append("")
    lines.append(f"- Tradition: {chronology.get('tradition_label') or '(unknown)'}")
    lines.append(
        "- Estimated original composition window: "
        f"{format_window_bce(chronology.get('composition_window_bce'))}"
    )
    lines.append(
        "- Earliest known textual witness window: "
        f"{format_window_bce(chronology.get('earliest_known_textual_witness_window_bce'))}"
    )

    base_witness = chronology.get("base_witness") or {}
    lines.append(f"- Baseline witness anchor: {format_anchor(base_witness)}")

    source_anchors = chronology.get("source_tradition_anchors", {})
    lines.append(f"- {source_a_name} witness anchor: {format_anchor(source_anchors.get(source_a_name, {}))}")
    lines.append(f"- {source_b_name} witness anchor: {format_anchor(source_anchors.get(source_b_name, {}))}")
    lines.append("")
    lines.append("## Digital Edition Dates (Secondary)")
    lines.append("")

    source_a_dates = ", ".join(sources.get(source_a_name, {}).get("source_version_dates", [])) or "(none)"
    source_b_dates = ", ".join(sources.get(source_b_name, {}).get("source_version_dates", [])) or "(none)"
    lines.append(f"- {source_a_name} digital/source edition dates: {source_a_dates}")
    lines.append(f"- {source_b_name} digital/source edition dates: {source_b_dates}")
    lines.append("")

    changed_details = comparison.get("changed_verse_details", [])
    if not changed_details:
        lines.append("No changed verses found.")
        lines.append("")
        return "\n".join(lines)

    lines.append("## Verse Diffs")
    lines.append("")

    for detail in changed_details:
        verse = detail.get("verse", "unknown")
        source_a = detail.get("source_a", {})
        source_b = detail.get("source_b", {})

        lines.append(f"### {verse}")
        lines.append("")
        lines.append(
            f"Source A ({source_a_name}): {source_a.get('source_archive')} | "
            f"digital/source edition date: {source_a.get('source_version_date')}"
        )
        lines.append(
            f"Source B ({source_b_name}): {source_b.get('source_archive')} | "
            f"digital/source edition date: {source_b.get('source_version_date')}"
        )
        lines.append("")
        lines.append("```diff")
        lines.append(
            render_token_pr_diff(
                source_a_text=str(source_a.get("text_content", "")),
                source_b_text=str(source_b.get("text_content", "")),
            )
        )
        lines.append("```")
        lines.append("")

    return "\n".join(lines)


def compare_sources(
    source_a_name: str,
    source_a_records: List[Dict[str, Any]],
    source_b_name: str,
    source_b_records: List[Dict[str, Any]],
    chronology_config: Dict[str, Any] | None = None,
    chapter: int = 1,
) -> Dict[str, Any]:
    work_id = WORK_ID
    chronology_context = build_chronology_context(
        chronology_config or {},
        work_id=work_id,
        source_a_name=source_a_name,
        source_b_name=source_b_name,
    )

    a_by_verse = {verse_key(rec): rec for rec in source_a_records}
    b_by_verse = {verse_key(rec): rec for rec in source_b_records}

    shared = sorted(set(a_by_verse).intersection(b_by_verse), key=verse_sort_key)
    only_a = sorted(set(a_by_verse).difference(b_by_verse), key=verse_sort_key)
    only_b = sorted(set(b_by_verse).difference(a_by_verse), key=verse_sort_key)

    identical: List[str] = []
    changed: List[str] = []
    changed_verse_details: List[Dict[str, Any]] = []

    for key in shared:
        a_record = a_by_verse[key]
        b_record = b_by_verse[key]

        if a_record.get("content_hash") == b_record.get("content_hash"):
            identical.append(key)
        else:
            changed.append(key)
            source_a_text = str(a_record.get("text_content", ""))
            source_b_text = str(b_record.get("text_content", ""))
            changed_verse_details.append(
                {
                    "verse": key,
                    "source_a": record_detail(a_record),
                    "source_b": record_detail(b_record),
                    "token_diff": token_diff_ops(source_a_text=source_a_text, source_b_text=source_b_text),
                }
            )

    only_in_source_a_details = [{"verse": key, "source_a": record_detail(a_by_verse[key])} for key in only_a]
    only_in_source_b_details = [{"verse": key, "source_b": record_detail(b_by_verse[key])} for key in only_b]

    a_dates = source_dates(source_a_records)
    b_dates = source_dates(source_b_records)
    date_overlap = sorted(set(a_dates).intersection(b_dates))

    findings: List[Dict[str, Any]] = []

    if not chronology_context.get("composition_window_bce"):
        findings.append(
            {
                "severity": "high",
                "code": "MISSING_ORIGINAL_COMPOSITION_DATES",
                "message": "Original composition window is missing from chronology config",
            }
        )

    if not a_dates or not b_dates:
        findings.append(
            {
                "severity": "high",
                "code": "MISSING_SOURCE_DATES",
                "message": "At least one source lacks source_version_date; skeptical temporal review is weakened",
                "source_a_dates": a_dates,
                "source_b_dates": b_dates,
            }
        )

    if a_dates and b_dates and date_overlap:
        findings.append(
            {
                "severity": "medium",
                "code": "SOURCE_DATE_OVERLAP",
                "message": "Sources share at least one source version date; temporal separation may be weak",
                "overlap": date_overlap,
            }
        )

    if changed:
        findings.append(
            {
                "severity": "medium",
                "code": "CROSS_SOURCE_TEXTUAL_DIVERGENCE",
                "message": "Shared verses differ across sources and require skeptical line-by-line review",
                "changed_count": len(changed),
                "examples": changed[:10],
            }
        )

    if len(changed) == 0:
        findings.append(
            {
                "severity": "low",
                "code": "NO_TEXTUAL_DIFF",
                "message": "No textual content-hash differences found in shared verses",
            }
        )

    risk_level = "low"
    severities = {f.get("severity") for f in findings}
    if "high" in severities:
        risk_level = "high"
    elif "medium" in severities:
        risk_level = "medium"

    return {
        "status": "ok",
        "work_id": work_id,
        "chapter": chapter,
        "chronology": chronology_context,
        "sources": {
            source_a_name: {
                "record_count": len(source_a_records),
                "source_version_dates": a_dates,
                "digital_edition_dates": a_dates,
            },
            source_b_name: {
                "record_count": len(source_b_records),
                "source_version_dates": b_dates,
                "digital_edition_dates": b_dates,
            },
        },
        "comparison": {
            "shared_verses": len(shared),
            "identical_hash_verses": len(identical),
            "changed_hash_verses": len(changed),
            "only_in_source_a": len(only_a),
            "only_in_source_b": len(only_b),
            "changed_examples": changed[:10],
            "changed_verse_details": changed_verse_details,
            "only_in_source_a_details": only_in_source_a_details,
            "only_in_source_b_details": only_in_source_b_details,
        },
        "risk_level": risk_level,
        "findings": findings,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare Genesis 1 across two sources")
    parser.add_argument(
        "--chapter",
        type=int,
        default=1,
        help="Genesis chapter number (default: 1)",
    )
    parser.add_argument(
        "--source-a",
        type=Path,
        default=None,
        help="First source JSONL (default: data/raw/bible.ot.genesis/chapter_XXX/oshb.jsonl)",
    )
    parser.add_argument(
        "--source-b",
        type=Path,
        default=None,
        help="Second source JSONL (default: data/raw/bible.ot.genesis/chapter_XXX/sefaria_mam.jsonl)",
    )
    parser.add_argument(
        "--source-a-name",
        type=str,
        default="oshb",
        help="Display name for source A",
    )
    parser.add_argument(
        "--source-b-name",
        type=str,
        default="sefaria_mam",
        help="Display name for source B",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output report JSON path (default: data/reports/bible.ot.genesis/chapter_XXX/cross_source_diff.json)",
    )
    parser.add_argument(
        "--chronology",
        type=Path,
        default=Path("config") / "chronology.yaml",
        help="Chronology config path for original composition dates",
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=None,
        help="PR/MR style markdown report path (default: data/reports/bible.ot.genesis/chapter_XXX/cross_source_diff.md)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    source_a_path = args.source_a or default_raw_source_path(args.chapter, "oshb")
    source_b_path = args.source_b or default_raw_source_path(args.chapter, "sefaria_mam")
    output_path = args.output or default_report_json_path(args.chapter)
    markdown_output_path = args.markdown_output or default_report_markdown_path(args.chapter)

    source_a_records = load_jsonl(source_a_path)
    source_b_records = load_jsonl(source_b_path)
    chronology_config = load_yaml(args.chronology) if args.chronology.exists() else {}

    report = compare_sources(
        source_a_name=args.source_a_name,
        source_a_records=source_a_records,
        source_b_name=args.source_b_name,
        source_b_records=source_b_records,
        chronology_config=chronology_config,
        chapter=args.chapter,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)

    markdown_output_path.parent.mkdir(parents=True, exist_ok=True)
    markdown = render_markdown_report(
        report=report,
        source_a_name=args.source_a_name,
        source_b_name=args.source_b_name,
    )
    with markdown_output_path.open("w", encoding="utf-8") as handle:
        handle.write(markdown)

    print(f"Cross-source report status: {report.get('status')}")
    print(f"Risk level: {report.get('risk_level')}")
    print(f"Shared verses: {report['comparison']['shared_verses']}")
    print(f"Changed hash verses: {report['comparison']['changed_hash_verses']}")
    print(f"Output report: {output_path}")
    print(f"Markdown diff report: {markdown_output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
