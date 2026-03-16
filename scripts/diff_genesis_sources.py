#!/usr/bin/env python3
"""Cross-source Genesis chapter comparison with date-aware skeptical checks."""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

WORK_ID = "bible.ot.genesis"
VERSE_REF_RE = re.compile(r"Gen\.(\d+)\.(\d+)$")
HEBREW_DIACRITICS_RE = re.compile(r"[\u0591-\u05C7]")
KEEP_ALNUM_HEBREW_RE = re.compile(r"[^0-9A-Za-z\u05D0-\u05EA]+")
# Scholarly glossary: normalized Hebrew token -> (short gloss, significance note)
_HEBREW_GLOSSARY: Dict[str, tuple[str, str]] = {
    "ברא": (
        "bara — to create, a verb reserved exclusively for divine creative activity",
        "This verb occurs only with God as its subject in all of Biblical Hebrew. Its presence here "
        "stakes a specific theological claim: whatever happened at the beginning was categorically unlike "
        "anything a human hand could do. Any manuscript that alters this verb touches the central nerve "
        "of the entire creation account.",
    ),
    "אלהים": (
        "Elohim — grammatically plural, theologically singular; the generic word for God",
        "The grammatical plurality of Elohim used with singular verbs was one of the most "
        "argued points in ancient Jewish and early Christian theology. Every scribe who "
        "encountered it had to decide whether to preserve the anomaly or smooth it over. "
        "Those who smoothed it left their theological fingerprints on the text.",
    ),
    "יהוה": (
        "YHWH — the personal divine name, the Tetragrammaton",
        "So sacred that by the Second Temple period scribes refused to write or pronounce it "
        "and substituted Adonai instead. A medieval scribe later combined the consonants of "
        "YHWH with the vowels of Adonai and produced 'Jehovah' — a word that never actually "
        "existed in any ancient language. Any manuscript that substitutes Elohim for YHWH, "
        "or vice versa, reflects this profound scribal anxiety about the divine name and alters "
        "what every subsequent reader understood God to be called.",
    ),
    "שמים": (
        "shamayim — the heavens, always grammatically dual in Hebrew",
        "The dual form implies a layered sky, consistent with ancient Near Eastern cosmology "
        "that pictured multiple heavens stacked above the earth. Paul's 'third heaven' in "
        "2 Corinthians draws on this same tradition. How a scribe copied this word could "
        "signal which cosmological model he thought the text endorsed.",
    ),
    "ארץ": (
        "eretz — earth or land, one of Hebrew's most context-dependent nouns",
        "In a cosmological clause it means the whole earth; in a legal or national clause it "
        "means a specific territory. The Septuagint translators had to choose, and their choice "
        "influenced how every subsequent Bible reader in the Greek-speaking world understood this verse.",
    ),
    "תהו": (
        "tohu — formless waste, a term for primordial chaos",
        "Its Semitic cognates connect it to ancient Near Eastern chaos narratives. Isaiah later "
        "uses it of lands laid waste by divine judgment, as if creation were being unmade. Any "
        "reading that changes or omits tohu alters a word that carries the memory of a whole "
        "ancient worldview about what existed before God acted.",
    ),
    "בהו": (
        "bohu — emptiness; occurs only three times in all of Biblical Hebrew",
        "It appears only ever paired with tohu, suggesting it exists partly as a phonetic echo "
        "rather than an independent concept. Its rarity makes any variant reading significant "
        "by definition, since there is almost no other context in which scholars can check what it should say.",
    ),
    "רוח": (
        "ruach — spirit, wind, or breath; Hebrew uses one word for all three",
        "Whether this is the Spirit of God hovering protectively over the waters, or a great "
        "wind sweeping across them, is not a minor exegetical quibble. The two readings produce "
        "entirely different theologies of creation: one supervised by divine presence from the "
        "first instant, one not. Scribes reading the same word could walk away with opposite "
        "pictures of what Genesis was claiming.",
    ),
    "אור": (
        "or — light, created before the sun exists",
        "Light appears on Day One; the sun and moon do not appear until Day Four. This sequence "
        "was noticed in antiquity and generated centuries of theological explanation. The word "
        "itself is plain, but its placement is among the most discussed anomalies in the entire creation account.",
    ),
    "רקיע": (
        "raqia — the firmament, from a root meaning to beat or stamp flat",
        "The Septuagint rendered it stereoma — a solid structure. Ancient readers understood this as "
        "a physical dome holding back the upper waters. When post-Copernican readers encountered this word, "
        "the translation of raqia became a flashpoint between scientific and traditional readings of Genesis.",
    ),
    "מים": (
        "mayim — the primordial waters",
        "Crucially, the waters in Genesis 1 are never created — they pre-exist God's ordering of the world. "
        "This fact sat in quiet tension with later theological formulations of creation out of nothing. "
        "Every manuscript tradition that preserved this verse intact preserved that tension too, whether "
        "the scribe understood what he was copying or not.",
    ),
    "טוב": (
        "tov — good; not merely beautiful, but fit for purpose",
        "The repeated declaration that creation is tov carries moral and covenantal weight far beyond "
        "aesthetic approval. It means the created order is exactly what it was meant to be. A manuscript "
        "that altered or omitted tov would be quietly editing out one of the most theologically "
        "loaded words in the entire chapter.",
    ),
    "אדם": (
        "adam — both humanity as a species and the personal name of the first human",
        "The Hebrew text refuses to distinguish between these two meanings in the creation account, and "
        "this is almost certainly intentional. Manuscripts that diverge in how they render adam-related "
        "forms may reflect communities with different convictions about whether Genesis speaks of a "
        "single individual or of the entire human species.",
    ),
    "צלם": (
        "tzelem — image or icon; the same word used for cult statues in a temple",
        "Humanity is described using the same term applied to divine images set up in sanctuaries. "
        "The implication — that every human being is a living idol of God walking in the world — "
        "was breathtaking to ancient readers and remains so. Any variant in this word touches the "
        "most philosophically significant claim of the entire creation narrative.",
    ),
    "דמות": (
        "demut — likeness; a slight softening added alongside tzelem",
        "The pairing of tzelem and demut became the terminological foundation of the patristic "
        "imago Dei doctrine. Which words appear, in what order, and whether both are present in a "
        "given manuscript directly shaped how entire theological traditions understood what it means to be human.",
    ),
    "כל": ("kol — all, every; a spelling variant carrying no difference in meaning", ""),
    "כׇּל": ("kol — all, every; ketiv spelling differing only orthographically from the standard form", ""),
    "כָּל": ("kol — all, every; standard qere spelling", ""),
}

# Literal lexical map used for readable English lines in verse diff output.
# This is intentionally approximate and transparent, not a polished translation edition.
_HEBREW_LITERAL_MAP: Dict[str, str] = {
    "ו": "and",
    "ה": "the",
    "ל": "to",
    "ב": "in",
    "מ": "from",
    "כ": "as",
    "על": "upon",
    "אל": "to",
    "פ": "face",
    "בראשית": "in the beginning",
    "ראשית": "beginning",
    "ברא": "created",
    "יברא": "he created",
    "ויברא": "and created",
    "אלהים": "God",
    "יהוה": "YHWH",
    "את": "",
    "כל": "all",
    "אשר": "that/which",
    "שמים": "heavens",
    "ארץ": "earth",
    "היתה": "was",
    "היו": "were",
    "יהי": "let there be",
    "ויהי": "and there was",
    "ויהיאור": "and there was light",
    "תהו": "formless",
    "בהו": "void",
    "חשך": "darkness",
    "אור": "light",
    "פני": "face of",
    "תהום": "the deep",
    "רוח": "spirit/wind",
    "מרחפת": "hovering",
    "מים": "waters",
    "אמר": "said",
    "ויאמר": "and said",
    "וירא": "and saw",
    "ירא": "saw",
    "כי": "that",
    "כיטוב": "that it was good",
    "טוב": "good",
    "ויבדל": "and separated",
    "יבדל": "he separates",
    "בין": "between",
    "ויקרא": "and called",
    "יקרא": "he called",
    "יום": "day",
    "לילה": "night",
    "ערב": "evening",
    "בקר": "morning",
    "ויהיערב": "and there was evening",
    "ויהיבקר": "and there was morning",
    "אחד": "one",
    "שני": "second",
    "שלישי": "third",
    "רביעי": "fourth",
    "חמישי": "fifth",
    "ששי": "sixth",
    "רקיע": "expanse",
    "עשה": "made",
    "ויעש": "and made",
    "כן": "so",
    "יקוו": "be gathered",
    "מקום": "place",
    "מקוה": "gathering",
    "תראה": "appeared",
    "יבשה": "dry land",
    "ים": "sea",
    "ימים": "seas",
    "דשא": "vegetation",
    "עשב": "plant",
    "מזריע": "seed-bearing",
    "זרע": "seed",
    "עץ": "tree",
    "פרי": "fruit",
    "מינה": "kind",
    "מינו": "its kind",
    "מינהו": "its kind",
    "מינהם": "their kinds",
    "מאור": "luminary",
    "מארת": "lights",
    "גדול": "great",
    "גדלים": "great",
    "קטן": "small",
    "ממשלת": "rule",
    "משל": "rule",
    "כוכבים": "stars",
    "נתן": "set",
    "ויתן": "and set",
    "תנינים": "great sea creatures",
    "תנינם": "great sea creatures",
    "נפש": "living creature",
    "חיה": "living thing",
    "חית": "beast of",
    "רמש": "creeping thing",
    "רמשת": "creeping thing",
    "רומש": "moving thing",
    "עוף": "bird",
    "כנף": "wing",
    "יברך": "he blessed",
    "ויברך": "and blessed",
    "פרו": "be fruitful",
    "רבו": "multiply",
    "מלאו": "fill",
    "שרצו": "swarm",
    "ישרצו": "let ... swarm",
    "יעופף": "let ... fly",
    "יעפף": "let ... fly",
    "דגת": "fish of",
    "בהמה": "livestock",
    "וחיתו": "and beast of",
    "חיתו": "beast of",
    "וחיתוארץ": "and beast of the earth",
    "חיתוארץ": "beast of the earth",
    "אדם": "humanity",
    "נעשה": "let us make",
    "צלם": "image",
    "צלמו": "his image",
    "צלמנו": "our image",
    "דמות": "likeness",
    "דמותנו": "our likeness",
    "רדו": "rule",
    "ירדו": "they shall rule",
    "כבשוה": "subdue it",
    "זכר": "male",
    "נקבה": "female",
    "נתתי": "I have given",
    "אכלה": "for food",
    "אתם": "you",
    "אתו": "with it",
    "בו": "in it",
    "לכם": "to you",
    "להם": "to them",
    "בתוך": "in the midst of",
    "תוך": "midst",
    "מעל": "above",
    "מתחת": "under",
    "תחת": "under",
    "יעש": "he made",
    "קרא": "called",
    "יאמר": "he said",
    "להבדיל": "to separate",
    "ולהבדיל": "and to separate",
    "מבדיל": "separating",
    "הבדיל": "separated",
    "תדשא": "let ... sprout",
    "תוצא": "let ... bring forth",
    "ותוצא": "and brought forth",
    "שרץ": "swarming thing",
    "להאיר": "to give light",
    "האיר": "to give light",
    "לאתת": "for signs",
    "אתות": "signs",
    "מועדים": "appointed times",
    "ולמועדים": "and for appointed times",
    "שנים": "years",
    "ושנים": "and years",
    "למאורת": "for a light",
    "מאורות": "lights",
    "הגדל": "the greater",
    "יהיה": "shall be",
    "ויהיכן": "and it was so",
    "יתן": "he set",
    "ירב": "be many",
    "ירבה": "multiply",
    "מיניהם": "their kinds",
    "זרעו": "its seed",
    "זרעובו": "seed in it",
    "אשרבו": "which is in it",
    "אדמה": "ground",
    "האדמה": "the ground",
    "ירק": "green plant",
    "וכבשה": "and subdue it",
    "עשהפרי": "making fruit",
    "פריעץ": "fruit tree",
    "אתכלירק": "every green thing",
    "מאד": "very",
    "הנה": "behold",
    "והנהטוב": "and behold, it was good",
}


def chapter_dir(chapter: int) -> str:
    return f"chapter_{chapter:03d}"


def default_raw_source_path(chapter: int, source_name: str) -> Path:
    return Path("data") / "raw" / WORK_ID / chapter_dir(chapter) / "sources" / f"{source_name}.jsonl"


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


def parse_year(value: Any) -> int | None:
    if value is None:
        return None
    match = re.search(r"(\d{4})", str(value))
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def signed_year_from_bce(year_bce: int | None) -> int | None:
    if not isinstance(year_bce, int):
        return None
    return -year_bce


def format_signed_year(year_ce: int | None) -> str:
    if year_ce is None:
        return "(unknown)"
    if year_ce < 0:
        return f"{abs(year_ce)} BCE"
    return f"{year_ce} CE"


def gap_years_without_year_zero(earlier_year: int, later_year: int) -> int:
    gap = later_year - earlier_year
    if earlier_year < 0 < later_year:
        return gap - 1
    return gap


def oldest_witness_anchor_year(anchor: Dict[str, Any]) -> int | None:
    if not isinstance(anchor, dict):
        return None

    ordering_year = anchor.get("ordering_year_ce")
    if isinstance(ordering_year, int):
        return ordering_year

    ordering_year_bce = anchor.get("ordering_year_bce")
    converted_ordering_bce = signed_year_from_bce(ordering_year_bce)
    if converted_ordering_bce is not None:
        return converted_ordering_bce

    window = anchor.get("witness_anchor_window_ce")
    if isinstance(window, dict):
        start = window.get("start")
        if isinstance(start, int):
            return start

    window_bce = anchor.get("witness_anchor_window_bce")
    if isinstance(window_bce, dict):
        start_bce = window_bce.get("start")
        converted_start_bce = signed_year_from_bce(start_bce)
        if converted_start_bce is not None:
            return converted_start_bce

    date_ce = anchor.get("witness_anchor_date_ce") or anchor.get("date_ce")
    if isinstance(date_ce, int):
        return date_ce

    date_bce = anchor.get("witness_anchor_date_bce") or anchor.get("date_bce")
    converted_date_bce = signed_year_from_bce(date_bce)
    if converted_date_bce is not None:
        return converted_date_bce

    return None


def build_source_profile(
    source_name: str,
    records: List[Dict[str, Any]],
    source_anchor: Dict[str, Any],
    sources_config: Dict[str, Any],
) -> Dict[str, Any]:
    archive_config = (sources_config.get("archives", {}) if isinstance(sources_config, dict) else {}).get(source_name, {})
    sample = records[0] if records else {}

    version_dates = source_dates(records)
    digital_years = sorted(year for year in (parse_year(value) for value in version_dates) if year is not None)

    return {
        "source_name": source_name,
        "display_name": archive_config.get("name") or sample.get("source_archive") or source_name,
        "record_count": len(records),
        "source_archive": sample.get("source_archive") or archive_config.get("name") or source_name,
        "source_url": archive_config.get("url") or sample.get("source_uri"),
        "api_endpoint": archive_config.get("api_endpoint"),
        "text_relation": archive_config.get("text_relation") or archive_config.get("witness_text_relation"),
        "is_translation": bool(archive_config.get("is_translation", False)),
        "is_transcription": bool(archive_config.get("is_transcription", False)),
        "source_uri_example": sample.get("source_uri"),
        "source_version_dates": version_dates,
        "digital_edition_dates": version_dates,
        "oldest_digital_year_ce": digital_years[0] if digital_years else None,
        "witness_anchor": source_anchor,
        "oldest_witness_anchor_year_ce": oldest_witness_anchor_year(source_anchor),
        "source_basis": source_anchor.get("source_basis"),
        "discovery_location": source_anchor.get("discovery_location"),
        "attributed_author": source_anchor.get("attributed_author"),
    }


def source_is_translation(profile: Dict[str, Any]) -> bool:
    relation = str(profile.get("text_relation") or "").strip().lower()
    if relation in {
        "translation",
        "translated",
        "target_language_translation",
    }:
        return True
    return bool(profile.get("is_translation", False))


def source_order_key(profile: Dict[str, Any]) -> tuple[int, int, str]:
    witness_year = profile.get("oldest_witness_anchor_year_ce")
    digital_year = profile.get("oldest_digital_year_ce")
    witness_rank = witness_year if isinstance(witness_year, int) else 9_999_999
    digital_rank = digital_year if isinstance(digital_year, int) else 9_999_999
    return witness_rank, digital_rank, str(profile.get("source_name"))


def year_gap_summary(older_year: int | None, newer_year: int | None, method: str) -> Dict[str, Any]:
    if older_year is None or newer_year is None:
        return {
            "known": False,
            "years": None,
            "older_year_ce": older_year,
            "newer_year_ce": newer_year,
            "older_year_label": format_signed_year(older_year),
            "newer_year_label": format_signed_year(newer_year),
            "method": method,
        }

    earlier_year = min(older_year, newer_year)
    later_year = max(older_year, newer_year)

    return {
        "known": True,
        "years": gap_years_without_year_zero(earlier_year, later_year),
        "older_year_ce": earlier_year,
        "newer_year_ce": later_year,
        "older_year_label": format_signed_year(earlier_year),
        "newer_year_label": format_signed_year(later_year),
        "method": method,
    }


def safe_ratio(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator, 4)


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
        "textual_authorship": work.get("textual_authorship"),
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
    date_bce = anchor.get("witness_anchor_date_bce") or anchor.get("date_bce")
    window_ce = anchor.get("witness_anchor_window_ce")
    window_bce = anchor.get("witness_anchor_window_bce")

    if isinstance(window_ce, dict) and window_ce.get("start") is not None and window_ce.get("end") is not None:
        return f"{label} ({window_ce.get('start')}-{window_ce.get('end')} CE)"
    if isinstance(window_bce, dict) and window_bce.get("start") is not None and window_bce.get("end") is not None:
        return f"{label} ({window_bce.get('start')}-{window_bce.get('end')} BCE)"
    if date_ce is not None:
        return f"{label} ({date_ce} CE)"
    if date_bce is not None:
        return f"{label} ({date_bce} BCE)"

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


def canonical_token(token: str) -> str:
    """Normalize one token so semantic comparison focuses on lexical letters."""
    normalized = HEBREW_DIACRITICS_RE.sub("", token)
    normalized = normalized.replace("/", "")
    normalized = normalized.replace("־", "")
    normalized = normalized.replace("{", "").replace("}", "")
    return KEEP_ALNUM_HEBREW_RE.sub("", normalized)


def canonical_token_stream(text: str) -> List[str]:
    tokens = [canonical_token(token) for token in text.split()]
    return [token for token in tokens if token]


def _normalize_for_literal_translation(text: str) -> str:
    normalized = HEBREW_DIACRITICS_RE.sub("", text)
    normalized = normalized.replace("/", "")
    normalized = normalized.replace("{", "").replace("}", "")
    normalized = normalized.replace("־", " ")
    normalized = KEEP_ALNUM_HEBREW_RE.sub(" ", normalized)
    return " ".join(normalized.split())


def _translate_hebrew_token(token: str, depth: int = 0) -> tuple[str, bool]:
    token = token.strip()
    if not token:
        return "", True
    if depth > 5:
        return f"[{token}]", False

    if token in _HEBREW_LITERAL_MAP:
        return _HEBREW_LITERAL_MAP[token], True

    for prefix, english in (("את", ""), ("כל", "all"), ("על", "upon"), ("אל", "to")):
        if token.startswith(prefix) and len(token) > len(prefix):
            remainder = token[len(prefix):]
            remainder_text, remainder_known = _translate_hebrew_token(remainder, depth + 1)
            if remainder_known:
                if prefix == "את":
                    return remainder_text, True
                if prefix == "כל":
                    return (f"all {remainder_text}".strip(), True)
                return (f"{english} {remainder_text}".strip(), True)

    for prefix, english in (
        ("ו", "and"),
        ("ב", "in"),
        ("ל", "to"),
        ("כ", "as"),
        ("מ", "from"),
        ("ש", "that"),
        ("ה", "the"),
    ):
        if token.startswith(prefix) and len(token) > 1:
            remainder = token[1:]
            remainder_text, remainder_known = _translate_hebrew_token(remainder, depth + 1)
            if remainder_known:
                if prefix == "ה":
                    return (f"the {remainder_text}".strip(), True)
                return (f"{english} {remainder_text}".strip(), True)

    # Attempt an internal split when compound forms were merged in transmission.
    for idx in range(2, len(token) - 1):
        left = token[:idx]
        right = token[idx:]
        left_text, left_known = _translate_hebrew_token(left, depth + 1)
        if not left_known:
            continue
        right_text, right_known = _translate_hebrew_token(right, depth + 1)
        if not right_known:
            continue
        combined = f"{left_text} {right_text}".strip()
        if combined:
            return combined, True

    return f"[{token}]", False


def literal_english_translation(text: str) -> str:
    """Build an approximate literal English rendering from normalized Hebrew tokens."""
    normalized = _normalize_for_literal_translation(text)
    if not normalized:
        return "(empty)"

    rendered_tokens: List[str] = []
    for token in normalized.split():
        translated, _known = _translate_hebrew_token(token)
        if translated:
            rendered_tokens.append(translated)

    if not rendered_tokens:
        return "(unable to produce literal translation)"

    sentence = " ".join(rendered_tokens)
    sentence = re.sub(r"\s+", " ", sentence).strip()
    if sentence:
        sentence = sentence[0].upper() + sentence[1:]
    return sentence


def _is_segmentation_variant(left: str, right: str) -> bool:
    """True when two token strings are identical after removing whitespace — a maqqef-split artifact."""
    return bool(left) and bool(right) and left.replace(" ", "") == right.replace(" ", "")


def _env_truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _unique_preserving_order(items: List[str]) -> List[str]:
    seen: set[str] = set()
    ordered: List[str] = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def _lexical_change_profile(source_a_text: str, source_b_text: str) -> Dict[str, Any]:
    """Compute lexical substitutions/additions/omissions after canonical normalization."""
    a_canonical = canonical_token_stream(source_a_text)
    b_canonical = canonical_token_stream(source_b_text)
    canonical_matcher = difflib.SequenceMatcher(a=a_canonical, b=b_canonical, autojunk=False)

    substitutions: List[tuple[str, str]] = []
    additions: List[str] = []
    omissions: List[str] = []
    changed_tokens: List[str] = []

    for op, i1, i2, j1, j2 in canonical_matcher.get_opcodes():
        if op == "equal":
            continue

        left_tokens = [token for token in a_canonical[i1:i2] if token]
        right_tokens = [token for token in b_canonical[j1:j2] if token]

        left = " ".join(left_tokens).strip()
        right = " ".join(right_tokens).strip()
        if op == "replace":
            if left and right:
                if _is_segmentation_variant(left, right):
                    continue  # maqqef-split artifact
                else:
                    substitutions.append((left, right))
                    changed_tokens.extend(left_tokens)
                    changed_tokens.extend(right_tokens)
            elif left:
                omissions.append(left)
                changed_tokens.extend(left_tokens)
            elif right:
                additions.append(right)
                changed_tokens.extend(right_tokens)
        elif op == "delete" and left:
            omissions.append(left)
            changed_tokens.extend(left_tokens)
        elif op == "insert" and right:
            additions.append(right)
            changed_tokens.extend(right_tokens)

    ordered_substitutions: List[tuple[str, str]] = []
    seen_pairs: set[tuple[str, str]] = set()
    for pair in substitutions:
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        ordered_substitutions.append(pair)

    return {
        "substitutions": ordered_substitutions,
        "additions": _unique_preserving_order(additions),
        "omissions": _unique_preserving_order(omissions),
        "changed_tokens": _unique_preserving_order(changed_tokens),
    }


def _is_significant_change(profile: Dict[str, Any]) -> bool:
    substitutions = profile.get("substitutions", [])
    additions = profile.get("additions", [])
    omissions = profile.get("omissions", [])
    changed_tokens = profile.get("changed_tokens", [])

    if not substitutions and not additions and not omissions:
        return False

    # Treat lexical substitutions as meaningful by default.
    if substitutions:
        return True

    # Phrase-level additions/omissions are almost always interpretively relevant.
    if any(" " in phrase for phrase in additions + omissions):
        return True

    significant_lexemes = {
        token
        for token, (_gloss_value, significance_note) in _HEBREW_GLOSSARY.items()
        if significance_note
    }
    if any(token in significant_lexemes for token in changed_tokens):
        return True

    # Tiny function-word-only drift is treated as non-significant noise.
    return (len(additions) + len(omissions)) >= 2


def _format_change_examples(values: List[str], limit: int = 3) -> str:
    if not values:
        return "(none)"
    sample = values[:limit]
    rendered = "; ".join(f"'{item}'" for item in sample)
    if len(values) > limit:
        return f"{rendered}; ..."
    return rendered


def _build_genai_prompt(
    *,
    verse_ref: str,
    source_a_label: str,
    source_b_label: str,
    source_a_text: str,
    source_b_text: str,
    profile: Dict[str, Any],
) -> str:
    substitutions = profile.get("substitutions", [])
    substitution_text = "(none)"
    if substitutions:
        chunks = [f"'{left}' -> '{right}'" for left, right in substitutions[:3]]
        substitution_text = "; ".join(chunks)
        if len(substitutions) > 3:
            substitution_text += "; ..."

    return (
        "You are a textual critic and historian of Biblical Hebrew. "
        "Write only meaningful commentary and avoid generic filler.\n\n"
        f"Verse reference: {verse_ref}\n"
        f"Older witness label: {source_a_label}\n"
        f"Newer witness label: {source_b_label}\n"
        f"Older witness Hebrew: {source_a_text}\n"
        f"Newer witness Hebrew: {source_b_text}\n"
        f"Older witness English (literal, approximate): {literal_english_translation(source_a_text)}\n"
        f"Newer witness English (literal, approximate): {literal_english_translation(source_b_text)}\n"
        "Word-level changes after canonical normalization:\n"
        f"- Substitutions: {substitution_text}\n"
        f"- Additions in newer witness: {_format_change_examples(profile.get('additions', []))}\n"
        f"- Omissions in newer witness: {_format_change_examples(profile.get('omissions', []))}\n\n"
        "Output exactly 2 bullet lines in plain English, no extra headings:\n"
        "- Textual observation: [specific wording change in concrete terms]\n"
        "- Historical significance: [why this matters historically/theologically, or explicitly state uncertainty]\n"
        "Do not output similarity scores, code-like labels, or repetitive boilerplate."
    )


def _extract_chat_text(response_payload: Dict[str, Any]) -> str | None:
    choices = response_payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return None

    first_choice = choices[0] if isinstance(choices[0], dict) else {}
    message = first_choice.get("message") if isinstance(first_choice, dict) else {}
    if not isinstance(message, dict):
        return None

    content = message.get("content")
    if isinstance(content, str):
        return content.strip() or None

    if isinstance(content, list):
        parts: List[str] = []
        for part in content:
            if not isinstance(part, dict):
                continue
            text = part.get("text")
            if isinstance(text, str) and text.strip():
                parts.append(text.strip())
        if parts:
            return "\n".join(parts)

    return None


def _call_genai_review(prompt: str, enable_genai_review: bool | None = None) -> str | None:
    if enable_genai_review is None:
        enable_genai_review = _env_truthy(os.getenv("GENAI_REVIEW_ENABLED"))
    if not enable_genai_review:
        return None

    api_key = os.getenv("GENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    base_url = os.getenv("GENAI_API_BASE", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("GENAI_MODEL", "gpt-4.1-mini")
    max_tokens = int(os.getenv("GENAI_MAX_TOKENS", "320"))
    temperature = float(os.getenv("GENAI_TEMPERATURE", "0.2"))

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You produce concise, non-repetitive scholarly notes about Biblical Hebrew textual variants. "
                    "Do not invent manuscript facts that are not in the prompt."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    request = urllib.request.Request(
        url=f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError, ValueError):
        return None

    try:
        payload_json = json.loads(body)
    except json.JSONDecodeError:
        return None

    return _extract_chat_text(payload_json)


def _parse_genai_comment_lines(text: str) -> List[str]:
    raw_lines: List[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        line = line.lstrip("-*• ").strip()
        if line:
            raw_lines.append(line)

    if not raw_lines:
        return []

    observation = ""
    significance = ""

    for line in raw_lines:
        lowered = line.lower()
        if lowered.startswith("textual observation:") and not observation:
            observation = "Textual observation:" + line.split(":", maxsplit=1)[1].strip()
            if not observation.endswith((".", "!", "?")):
                observation += "."
        elif lowered.startswith("historical significance:") and not significance:
            significance = "Historical significance:" + line.split(":", maxsplit=1)[1].strip()
            if not significance.endswith((".", "!", "?")):
                significance += "."

    if observation and significance:
        return [observation, significance]

    if len(raw_lines) >= 2:
        fallback_observation = raw_lines[0]
        fallback_significance = raw_lines[1]
        if not fallback_observation.lower().startswith("textual observation:"):
            fallback_observation = f"Textual observation: {fallback_observation}"
        if not fallback_significance.lower().startswith("historical significance:"):
            fallback_significance = f"Historical significance: {fallback_significance}"
        return [fallback_observation, fallback_significance]

    return []


def simulated_review_comments(
    source_a_text: str,
    source_b_text: str,
    token_diff: Dict[str, Any],
    *,
    verse_ref: str,
    source_a_label: str,
    source_b_label: str,
    enable_genai_review: bool | None = None,
) -> List[str]:
    """Generate reviewer comments only for significant changes, using GenAI when enabled."""
    _ = token_diff  # Reserved for future prompt enrichment.
    profile = _lexical_change_profile(source_a_text, source_b_text)

    if not _is_significant_change(profile):
        return []

    prompt = _build_genai_prompt(
        verse_ref=verse_ref,
        source_a_label=source_a_label,
        source_b_label=source_b_label,
        source_a_text=source_a_text,
        source_b_text=source_b_text,
        profile=profile,
    )
    generated = _call_genai_review(prompt, enable_genai_review=enable_genai_review)
    if not generated:
        return []

    comments = _parse_genai_comment_lines(generated)
    if len(comments) == 2 and comments[0] == comments[1]:
        return [comments[0]]
    return comments


def render_markdown_report(
    report: Dict[str, Any],
    source_a_name: str,
    source_b_name: str,
    *,
    enable_genai_review: bool | None = None,
) -> str:
    """Render human-readable PR/MR style markdown report with diff blocks."""
    lines: List[str] = []
    comparison = report.get("comparison", {})
    sources = report.get("sources", {})
    chronology = report.get("chronology", {})
    source_ordering = report.get("source_ordering", {})

    ordered_a_name = source_ordering.get("source_a_name") or source_a_name
    ordered_b_name = source_ordering.get("source_b_name") or source_b_name

    ordered_a = sources.get(ordered_a_name, {})
    ordered_b = sources.get(ordered_b_name, {})

    lines.append("# Genesis 1 Cross-Source Diff (PR Style)")
    lines.append("")
    lines.append(f"- Work: {report.get('work_id')}")
    lines.append(f"- Chapter: {report.get('chapter')}")
    lines.append(f"- Risk level: {report.get('risk_level')}")
    lines.append(f"- Shared verses: {comparison.get('shared_verses')}")
    lines.append(f"- Changed verses: {comparison.get('changed_hash_verses')}")
    lines.append("")

    lines.append("## Source Ordering (Oldest First)")
    lines.append("")

    ordered_a_year_label = format_signed_year(ordered_a.get("oldest_witness_anchor_year_ce"))
    ordered_b_year_label = format_signed_year(ordered_b.get("oldest_witness_anchor_year_ce"))

    lines.append(
        f"- Source A (oldest witness): {ordered_a_name} | "
        f"anchor year: {ordered_a_year_label}"
    )
    lines.append(
        f"- Source B (newer witness): {ordered_b_name} | "
        f"anchor year: {ordered_b_year_label}"
    )

    witness_gap = source_ordering.get("witness_year_gap", {})
    if witness_gap.get("known"):
        older_label = witness_gap.get("older_year_label") or format_signed_year(witness_gap.get("older_year_ce"))
        newer_label = witness_gap.get("newer_year_label") or format_signed_year(witness_gap.get("newer_year_ce"))
        lines.append(
            "- Estimated year gap between source witnesses: "
            f"{witness_gap.get('years')} years "
            f"({older_label} -> {newer_label})"
        )
    else:
        lines.append("- Estimated year gap between source witnesses: (unknown)")
    lines.append("")

    lines.append("## Coverage Alignment")
    lines.append("")
    lines.append(
        "- Matching strategy: verse reference alignment from source_uri fragments or notes"
    )
    lines.append(
        "- Input order handling: file order ignored; verses are matched and sorted by reference"
    )
    coverage_mode = str(comparison.get("coverage_mode") or "full_overlap")
    lines.append(
        f"- Coverage mode: {'overlap only' if coverage_mode == 'overlap_only' else 'full overlap'}"
    )
    lines.append(f"- {ordered_a_name} verses available: {comparison.get('source_a_total_verses')}")
    lines.append(f"- {ordered_b_name} verses available: {comparison.get('source_b_total_verses')}")
    lines.append(f"- Shared verses compared: {comparison.get('shared_verses')}")
    lines.append(f"- Only in {ordered_a_name}: {comparison.get('only_in_source_a')}")
    lines.append(f"- Only in {ordered_b_name}: {comparison.get('only_in_source_b')}")

    only_in_a_details = comparison.get("only_in_source_a_details", [])
    only_in_b_details = comparison.get("only_in_source_b_details", [])
    only_in_a_refs = [str(item.get("verse")) for item in only_in_a_details[:10] if item.get("verse")]
    only_in_b_refs = [str(item.get("verse")) for item in only_in_b_details[:10] if item.get("verse")]
    if only_in_a_refs:
        lines.append(f"- {ordered_a_name}-only verse refs: {', '.join(only_in_a_refs)}")
    if only_in_b_refs:
        lines.append(f"- {ordered_b_name}-only verse refs: {', '.join(only_in_b_refs)}")
    lines.append("")

    lines.append("## Authorship and Source Context")
    lines.append("")
    authorship = chronology.get("textual_authorship") or {}
    lines.append(
        "- Text traditional attribution: "
        f"{authorship.get('traditional_attribution') or '(unknown)'}"
    )
    lines.append(
        "- Text scholarly attribution model: "
        f"{authorship.get('scholarly_model') or '(unknown)'}"
    )

    for label, source_name in (("Source A", ordered_a_name), ("Source B", ordered_b_name)):
        source_meta = sources.get(source_name, {})
        lines.append(f"- {label} key: {source_name}")
        lines.append(f"- {label} source/archive: {source_meta.get('display_name') or source_meta.get('source_archive') or '(unknown)'}")
        lines.append(f"- {label} source URL: {source_meta.get('source_url') or '(unknown)'}")
        lines.append(f"- {label} source basis: {source_meta.get('source_basis') or '(unknown)'}")
        lines.append(f"- {label} attributed author/editor: {source_meta.get('attributed_author') or '(unknown)'}")
        lines.append(f"- {label} discovery location: {source_meta.get('discovery_location') or '(unknown)'}")
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
    lines.append(f"- {ordered_a_name} witness anchor: {format_anchor(source_anchors.get(ordered_a_name, {}))}")
    lines.append(f"- {ordered_b_name} witness anchor: {format_anchor(source_anchors.get(ordered_b_name, {}))}")
    lines.append("")
    lines.append("## Digital Edition Dates (Secondary)")
    lines.append("")

    source_a_dates = ", ".join(sources.get(ordered_a_name, {}).get("source_version_dates", [])) or "(none)"
    source_b_dates = ", ".join(sources.get(ordered_b_name, {}).get("source_version_dates", [])) or "(none)"
    lines.append(f"- {ordered_a_name} digital/source edition dates: {source_a_dates}")
    lines.append(f"- {ordered_b_name} digital/source edition dates: {source_b_dates}")
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
        token_diff = detail.get("token_diff") if isinstance(detail.get("token_diff"), dict) else {}
        source_a_text = str(source_a.get("text_content", ""))
        source_b_text = str(source_b.get("text_content", ""))

        lines.append(f"### {verse}")
        lines.append("")
        lines.append(
            f"Source A ({ordered_a_name}): {source_a.get('source_archive')} | "
            f"digital/source edition date: {source_a.get('source_version_date')}"
        )
        lines.append(
            f"Source B ({ordered_b_name}): {source_b.get('source_archive')} | "
            f"digital/source edition date: {source_b.get('source_version_date')}"
        )
        lines.append(
            "Source A English (literal, auto-generated; approximate): "
            f"{literal_english_translation(source_a_text)}"
        )
        lines.append(
            "Source B English (literal, auto-generated; approximate): "
            f"{literal_english_translation(source_b_text)}"
        )
        lines.append("")
        lines.append("```diff")
        lines.append(
            render_token_pr_diff(
                source_a_text=source_a_text,
                source_b_text=source_b_text,
            )
        )
        lines.append("```")
        lines.append("")
        comments = simulated_review_comments(
            source_a_text=source_a_text,
            source_b_text=source_b_text,
            token_diff=token_diff,
            verse_ref=str(verse),
            source_a_label=ordered_a_name,
            source_b_label=ordered_b_name,
            enable_genai_review=enable_genai_review,
        )
        if comments:
            lines.append("Reviewer notes:")
            for comment in comments:
                lines.append(f"- {comment}")
            lines.append("")

    return "\n".join(lines)


def compare_sources(
    source_a_name: str,
    source_a_records: List[Dict[str, Any]],
    source_b_name: str,
    source_b_records: List[Dict[str, Any]],
    chronology_config: Dict[str, Any] | None = None,
    sources_config: Dict[str, Any] | None = None,
    chapter: int = 1,
) -> Dict[str, Any]:
    work_id = WORK_ID
    chronology_context = build_chronology_context(
        chronology_config or {},
        work_id=work_id,
        source_a_name=source_a_name,
        source_b_name=source_b_name,
    )

    source_inputs: Dict[str, List[Dict[str, Any]]] = {
        source_a_name: source_a_records,
        source_b_name: source_b_records,
    }

    source_anchors = chronology_context.get("source_tradition_anchors", {})
    source_profiles = {
        name: build_source_profile(
            source_name=name,
            records=records,
            source_anchor=source_anchors.get(name, {}),
            sources_config=sources_config or {},
        )
        for name, records in source_inputs.items()
    }

    translated_sources = [
        profile["source_name"]
        for profile in source_profiles.values()
        if source_is_translation(profile)
    ]
    if translated_sources:
        labels = ", ".join(translated_sources)
        raise ValueError(
            "Translated witnesses are not allowed for this comparison. "
            f"Provide original-language witnesses or transcriptions instead: {labels}"
        )

    ordered_profiles = sorted(
        source_profiles.values(),
        key=source_order_key,
    )
    ordered_a_name = ordered_profiles[0]["source_name"]
    ordered_b_name = ordered_profiles[1]["source_name"]

    ordered_a_profile = source_profiles[ordered_a_name]
    ordered_b_profile = source_profiles[ordered_b_name]
    ordered_a_records = source_inputs[ordered_a_name]
    ordered_b_records = source_inputs[ordered_b_name]

    witness_gap = year_gap_summary(
        older_year=ordered_a_profile.get("oldest_witness_anchor_year_ce"),
        newer_year=ordered_b_profile.get("oldest_witness_anchor_year_ce"),
        method="difference between configured witness ordering years (window uses start year)",
    )

    digital_gap = year_gap_summary(
        older_year=ordered_a_profile.get("oldest_digital_year_ce"),
        newer_year=ordered_b_profile.get("oldest_digital_year_ce"),
        method="difference between earliest digital/source edition years",
    )

    ordering_basis = "lowest textual witness anchor year (fallback: lowest digital/source year)"

    a_by_verse = {verse_key(rec): rec for rec in ordered_a_records}
    b_by_verse = {verse_key(rec): rec for rec in ordered_b_records}

    shared = sorted(set(a_by_verse).intersection(b_by_verse), key=verse_sort_key)
    only_a = sorted(set(a_by_verse).difference(b_by_verse), key=verse_sort_key)
    only_b = sorted(set(b_by_verse).difference(a_by_verse), key=verse_sort_key)
    coverage_mode = "full_overlap" if not only_a and not only_b else "overlap_only"

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

    a_dates = source_dates(ordered_a_records)
    b_dates = source_dates(ordered_b_records)
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

    if ordered_a_profile.get("oldest_witness_anchor_year_ce") is None or ordered_b_profile.get("oldest_witness_anchor_year_ce") is None:
        findings.append(
            {
                "severity": "medium",
                "code": "MISSING_WITNESS_ANCHOR_DATES",
                "message": "One or more sources are missing witness anchor dates; source ordering fell back to digital years",
                "source_a": ordered_a_name,
                "source_b": ordered_b_name,
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

    if only_a or only_b:
        findings.append(
            {
                "severity": "medium",
                "code": "PARTIAL_VERSE_OVERLAP",
                "message": (
                    "Sources were aligned by verse reference and compared only where both "
                    "witnesses contain the verse; unmatched verses remain listed separately"
                ),
                "source_a_total_verses": len(a_by_verse),
                "source_b_total_verses": len(b_by_verse),
                "shared_verses": len(shared),
                "only_in_source_a": len(only_a),
                "only_in_source_b": len(only_b),
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
        "source_ordering": {
            "source_a_name": ordered_a_name,
            "source_b_name": ordered_b_name,
            "ordering_basis": ordering_basis,
            "witness_year_gap": witness_gap,
            "digital_year_gap": digital_gap,
        },
        "sources": {
            ordered_a_name: ordered_a_profile,
            ordered_b_name: ordered_b_profile,
        },
        "comparison": {
            "matching_strategy": "verse_reference_alignment",
            "order_independent_alignment": True,
            "coverage_mode": coverage_mode,
            "source_a_total_verses": len(a_by_verse),
            "source_b_total_verses": len(b_by_verse),
            "shared_coverage_ratio_source_a": safe_ratio(len(shared), len(a_by_verse)),
            "shared_coverage_ratio_source_b": safe_ratio(len(shared), len(b_by_verse)),
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
        help="First source JSONL (default: data/raw/bible.ot.genesis/chapter_XXX/sources/oshb.jsonl)",
    )
    parser.add_argument(
        "--source-b",
        type=Path,
        default=None,
        help="Second source JSONL (default: data/raw/bible.ot.genesis/chapter_XXX/sources/sefaria_mam.jsonl)",
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
        "--sources-config",
        type=Path,
        default=Path("config") / "sources.yaml",
        help="Source registry config path for source/archive metadata",
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=None,
        help="PR/MR style markdown report path (default: data/reports/bible.ot.genesis/chapter_XXX/cross_source_diff.md)",
    )
    parser.add_argument(
        "--enable-genai-review",
        action="store_true",
        help=(
            "Enable GenAI reviewer notes for significant verse changes only. "
            "Requires GENAI_API_KEY or OPENAI_API_KEY."
        ),
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
    sources_config = load_yaml(args.sources_config) if args.sources_config.exists() else {}

    report = compare_sources(
        source_a_name=args.source_a_name,
        source_a_records=source_a_records,
        source_b_name=args.source_b_name,
        source_b_records=source_b_records,
        chronology_config=chronology_config,
        sources_config=sources_config,
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
        enable_genai_review=args.enable_genai_review,
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
