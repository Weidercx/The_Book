#!/usr/bin/env python3
"""Build a Genesis chapter payload from the DT-UCPH Samaritan Pentateuch TF data."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
from typing import Dict, Iterable, List, Tuple
from urllib.request import Request, urlopen
import unicodedata

RAW_BASE_URL = "https://raw.githubusercontent.com/DT-UCPH/sp/main/tf/{version}/{filename}"
LEAD_ID_RE = re.compile(r"^(\d+)\s+(.*)$")
HEADER_DATE_RE = re.compile(r"^@dateWritten=(.+)$", flags=re.MULTILINE)


def default_output_path(chapter: int) -> Path:
    chapter_dir = f"chapter_{chapter:03d}"
    return (
        Path("data")
        / "raw"
        / "bible.ot.genesis"
        / chapter_dir
        / "sources"
        / "samaritan_pentateuch_sp.payload.json"
    )


def fetch_tf_text(version: str, filename: str, timeout_seconds: int) -> str:
    url = RAW_BASE_URL.format(version=version, filename=filename)
    request = Request(url=url, headers={"User-Agent": "TheBook-Agent"})
    with urlopen(request, timeout=timeout_seconds) as response:
        return response.read().decode("utf-8-sig")


def parse_feature_text(text: str) -> Dict[int, str]:
    data: Dict[int, str] = {}
    current_node: int | None = None

    for raw_line in text.splitlines():
        if not raw_line or raw_line.startswith("@"):
            continue

        match = LEAD_ID_RE.match(raw_line)
        if match:
            current_node = int(match.group(1))
            data[current_node] = match.group(2)
            continue

        if current_node is None:
            continue

        current_node += 1
        data[current_node] = raw_line

    return data


def parse_otype_ranges_text(text: str) -> Dict[str, Tuple[int, int]]:
    ranges: Dict[str, Tuple[int, int]] = {}

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("@"):
            continue

        parts = line.split()
        if len(parts) < 2:
            continue

        node_range = parts[0]
        otype = parts[1]

        if "-" in node_range:
            start_str, end_str = node_range.split("-", maxsplit=1)
        else:
            start_str = node_range
            end_str = node_range

        if not (start_str.isdigit() and end_str.isdigit()):
            continue

        ranges[otype] = (int(start_str), int(end_str))

    return ranges


def parse_slot_segment(segment: str) -> Tuple[int, int] | None:
    stripped = segment.strip()
    if not stripped:
        return None

    if "-" in stripped:
        start_str, end_str = stripped.split("-", maxsplit=1)
        if not (start_str.isdigit() and end_str.isdigit()):
            return None
        return int(start_str), int(end_str)

    if not stripped.isdigit():
        return None

    value = int(stripped)
    return value, value


def parse_oslots_text(text: str) -> Dict[int, Tuple[int, int]]:
    data: Dict[int, Tuple[int, int]] = {}
    current_node: int | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("@"):
            continue

        match = LEAD_ID_RE.match(line)
        if match:
            current_node = int(match.group(1))
            slot_spec = match.group(2)
        else:
            if current_node is None:
                continue
            current_node += 1
            slot_spec = line

        first_slot: int | None = None
        last_slot: int | None = None

        for token in slot_spec.split():
            for segment in token.split(","):
                parsed = parse_slot_segment(segment)
                if parsed is None:
                    continue

                slot_start, slot_end = parsed
                if first_slot is None or slot_start < first_slot:
                    first_slot = slot_start
                if last_slot is None or slot_end > last_slot:
                    last_slot = slot_end

        if first_slot is not None and last_slot is not None:
            data[current_node] = (first_slot, last_slot)

    return data


def normalize_hebrew_text(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).split())


def parse_latest_header_date(*texts: str) -> str | None:
    parsed_dates: List[datetime] = []

    for text in texts:
        for raw_date in HEADER_DATE_RE.findall(text):
            date_str = raw_date.strip()
            if not date_str:
                continue

            normalized = date_str
            if normalized.endswith("Z"):
                normalized = normalized[:-1]
                # Some TF headers include both offset and trailing Z (e.g. +00:00Z).
                if not re.search(r"[+-]\d{2}:\d{2}$", normalized):
                    normalized = f"{normalized}+00:00"

            try:
                parsed_dates.append(datetime.fromisoformat(normalized))
            except ValueError:
                continue

    if not parsed_dates:
        return None

    newest = max(parsed_dates)
    return newest.isoformat().replace("+00:00", "Z")


def interval_within(child: Tuple[int, int], parent: Tuple[int, int]) -> bool:
    return child[0] >= parent[0] and child[1] <= parent[1]


def build_payload(chapter: int, version: str, timeout_seconds: int) -> Dict[str, object]:
    tf_files = {
        "book": fetch_tf_text(version=version, filename="book.tf", timeout_seconds=timeout_seconds),
        "chapter": fetch_tf_text(version=version, filename="chapter.tf", timeout_seconds=timeout_seconds),
        "verse": fetch_tf_text(version=version, filename="verse.tf", timeout_seconds=timeout_seconds),
        "otype": fetch_tf_text(version=version, filename="otype.tf", timeout_seconds=timeout_seconds),
        "oslots": fetch_tf_text(version=version, filename="oslots.tf", timeout_seconds=timeout_seconds),
        "g_cons_utf8": fetch_tf_text(version=version, filename="g_cons_utf8.tf", timeout_seconds=timeout_seconds),
    }

    book_feature = parse_feature_text(tf_files["book"])
    chapter_feature = parse_feature_text(tf_files["chapter"])
    verse_feature = parse_feature_text(tf_files["verse"])
    word_feature = parse_feature_text(tf_files["g_cons_utf8"])
    oslots = parse_oslots_text(tf_files["oslots"])
    otype_ranges = parse_otype_ranges_text(tf_files["otype"])

    if "verse" not in otype_ranges or "word" not in otype_ranges:
        raise ValueError("otype.tf missing verse/word ranges")

    genesis_book_nodes = [node for node, value in book_feature.items() if value == "Genesis"]
    if not genesis_book_nodes:
        raise ValueError("Unable to locate Genesis in book.tf")

    genesis_book_node = genesis_book_nodes[0]
    genesis_slot_range = oslots.get(genesis_book_node)
    if genesis_slot_range is None:
        raise ValueError("Missing oslots range for Genesis book node")

    chapter_nodes = [
        node
        for node, value in chapter_feature.items()
        if str(value).strip() == str(chapter)
        and node in oslots
        and interval_within(oslots[node], genesis_slot_range)
    ]
    if not chapter_nodes:
        raise ValueError(f"No Genesis chapter {chapter} node found in TF data")

    chapter_nodes.sort(key=lambda node: oslots[node][0])
    chapter_node = chapter_nodes[0]
    chapter_slot_range = oslots[chapter_node]

    verse_start, verse_end = otype_ranges["verse"]
    verse_nodes = [
        node
        for node in range(verse_start, verse_end + 1)
        if node in verse_feature and node in oslots and interval_within(oslots[node], chapter_slot_range)
    ]
    if not verse_nodes:
        raise ValueError(f"No verse nodes found for Genesis chapter {chapter}")

    verse_nodes.sort(key=lambda node: oslots[node][0])

    word_start, word_end = otype_ranges["word"]
    chapter_word_nodes = [
        node
        for node in range(word_start, word_end + 1)
        if node in word_feature and node in oslots and interval_within(oslots[node], chapter_slot_range)
    ]
    chapter_word_nodes.sort(key=lambda node: oslots[node][0])

    verse_rows: List[Dict[str, object]] = []
    for verse_node in verse_nodes:
        verse_number_raw = str(verse_feature[verse_node]).strip()
        if not verse_number_raw.isdigit():
            continue

        verse_number = int(verse_number_raw)
        verse_slot_range = oslots[verse_node]
        verse_word_nodes = [
            node
            for node in chapter_word_nodes
            if interval_within(oslots[node], verse_slot_range)
        ]

        verse_text = normalize_hebrew_text(" ".join(word_feature[node] for node in verse_word_nodes))
        if not verse_text:
            continue

        verse_rows.append(
            {
                "chapter": chapter,
                "verse": verse_number,
                "text": verse_text,
                "osis_id": f"Gen.{chapter}.{verse_number}",
                "fragment_id": f"sp-ms-751-gen-{chapter:02d}-{verse_number:03d}",
            }
        )

    if not verse_rows:
        raise ValueError(f"No verse text extracted for Genesis chapter {chapter}")

    source_version_date = parse_latest_header_date(
        tf_files["book"],
        tf_files["chapter"],
        tf_files["verse"],
        tf_files["g_cons_utf8"],
    )

    return {
        "source_uri": f"https://github.com/DT-UCPH/sp/tree/main/tf/{version}",
        "source_version_date": source_version_date,
        "manuscript_siglum": "SP-CBL-751+Garizim-1",
        "verses": verse_rows,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Genesis chapter payload from DT-UCPH Samaritan Pentateuch TF data"
    )
    parser.add_argument("--chapter", type=int, default=1, help="Genesis chapter number (default: 1)")
    parser.add_argument(
        "--version",
        type=str,
        default="6.1",
        help="DT-UCPH/sp TF dataset version folder (default: 6.1)",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=45,
        help="HTTP timeout for raw feature downloads (default: 45)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Output payload JSON path "
            "(default: data/raw/bible.ot.genesis/chapter_XXX/sources/samaritan_pentateuch_sp.payload.json)"
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    payload = build_payload(
        chapter=args.chapter,
        version=args.version,
        timeout_seconds=args.timeout_seconds,
    )

    output_path = args.output or default_output_path(chapter=args.chapter)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    print(f"Built Samaritan Pentateuch payload for Genesis chapter {args.chapter}")
    print(f"Verse rows: {len(payload['verses'])}")
    print(f"Output file: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
