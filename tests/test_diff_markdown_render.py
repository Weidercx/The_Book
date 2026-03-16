# The_Book/tests/test_diff_markdown_render.py

from scripts.diff_genesis_sources import compare_sources, render_markdown_report


def _record(source_archive: str, verse: int, text: str, content_hash: str, source_version_date: str):
    return {
        "work_id": "bible.ot.genesis",
        "source_archive": source_archive,
        "source_uri": f"https://example.org/Gen.xml#Gen.1.{verse}",
        "source_version_date": source_version_date,
        "content_hash": content_hash,
        "text_content": text,
        "notes": f"Genesis 1:{verse}",
    }


def _chronology():
    return {
        "works": {
            "bible.ot.genesis": {
                "tradition_label": "Hebrew Bible / Torah",
                "composition_window_bce": {"start": 1000, "end": 400},
                "earliest_known_textual_witness_window_bce": {"start": 250, "end": 100},
                "base_witness": {"label": "Leningrad Codex", "date_ce": 1008},
                "source_tradition_anchors": {
                    "oshb": {"witness_anchor_label": "Leningrad Codex", "witness_anchor_date_ce": 1008},
                    "sefaria_mam": {
                        "witness_anchor_label": "MAM Aleppo/Leningrad tradition",
                        "witness_anchor_window_ce": {"start": 930, "end": 1008},
                    },
                },
            }
        }
    }


def test_markdown_render_contains_diff_block_with_plus_and_minus_tokens():
    source_a = [_record("oshb", 1, "בראשית ברא", "h1", "2018-12-14T00:00:00")]
    source_b = [_record("sefaria", 1, "בראשית ברא אלהים", "h2", "2025-01-02T17:56:40Z")]

    report = compare_sources(
        source_a_name="oshb",
        source_a_records=source_a,
        source_b_name="sefaria_mam",
        source_b_records=source_b,
        chronology_config=_chronology(),
    )

    markdown = render_markdown_report(report, source_a_name="oshb", source_b_name="sefaria_mam")

    assert "```diff" in markdown
    assert "+ אלהים" in markdown
    assert "## Chronology Axis (Primary)" in markdown
    assert "Estimated original composition window: 1000-400 BCE" in markdown
    assert "## Digital Edition Dates (Secondary)" in markdown
