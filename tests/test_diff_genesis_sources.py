# The_Book/tests/test_diff_genesis_sources.py

from scripts.diff_genesis_sources import compare_sources


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
                "textual_authorship": {
                    "traditional_attribution": "Traditionally attributed to Moses",
                    "scholarly_model": "Composite redaction model",
                },
                "composition_window_bce": {"start": 1000, "end": 400},
                "earliest_known_textual_witness_window_bce": {"start": 250, "end": 100},
                "base_witness": {"label": "Leningrad Codex", "date_ce": 1008},
                "source_tradition_anchors": {
                    "oshb": {
                        "witness_anchor_label": "Leningrad Codex",
                        "witness_anchor_date_ce": 1008,
                        "ordering_year_ce": 1008,
                        "source_basis": "WLC/Leningrad witness tradition",
                        "attributed_author": "Masoretic scribal tradition",
                        "discovery_location": "Saint Petersburg",
                    },
                    "sefaria_mam": {
                        "witness_anchor_label": "MAM Aleppo/Leningrad tradition",
                        "witness_anchor_window_ce": {"start": 903, "end": 1008},
                        "ordering_year_ce": 903,
                        "source_basis": "MAM Aleppo/Leningrad stream",
                        "attributed_author": "Masoretic scribal tradition",
                        "discovery_location": "Aleppo/Jerusalem",
                    },
                },
            }
        }
    }


def test_compare_sources_includes_full_changed_verse_details():
    source_a = [_record("oshb", 1, "בראשית ברא", "h1", "2018-12-14T00:00:00")]
    source_b = [_record("sefaria", 1, "בראשית ברא אלהים", "h2", "2025-01-02T17:56:40Z")]

    report = compare_sources(
        source_a_name="oshb",
        source_a_records=source_a,
        source_b_name="sefaria_mam",
        source_b_records=source_b,
        chronology_config=_chronology(),
    )

    details = report["comparison"]["changed_verse_details"]
    assert len(details) == 1
    assert details[0]["verse"] == "Gen.1.1"
    assert details[0]["source_a"]["text_content"] == "בראשית ברא אלהים"
    assert details[0]["source_b"]["text_content"] == "בראשית ברא"
    assert len(details[0]["token_diff"]["operations"]) >= 1
    assert report["chronology"]["composition_window_bce"]["start"] == 1000
    assert report["source_ordering"]["source_a_name"] == "sefaria_mam"
    assert report["source_ordering"]["source_b_name"] == "oshb"
    assert report["source_ordering"]["witness_year_gap"]["years"] == 105
