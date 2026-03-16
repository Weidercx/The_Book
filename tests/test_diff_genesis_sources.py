# The_Book/tests/test_diff_genesis_sources.py

import pytest

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
                    "dss_4qgen": {
                        "witness_anchor_label": "Qumran Genesis fragments",
                        "witness_anchor_window_bce": {"start": 250, "end": 100},
                        "ordering_year_bce": 250,
                        "source_basis": "DSS Hebrew diplomatic transcription",
                        "attributed_author": "Second Temple Jewish scribal tradition",
                        "discovery_location": "Qumran caves",
                    },
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
                        "witness_anchor_window_ce": {"start": 930, "end": 1008},
                        "ordering_year_ce": 930,
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
    assert report["source_ordering"]["witness_year_gap"]["years"] == 78


def test_compare_sources_rejects_translation_sources():
    source_a = [_record("oshb", 1, "בראשית ברא", "h1", "2018-12-14T00:00:00")]
    source_b = [_record("lxx", 1, "ΕΝ ΑΡΧΗ", "h2", "2024-01-01T00:00:00Z")]

    with pytest.raises(ValueError, match="Translated witnesses are not allowed"):
        compare_sources(
            source_a_name="oshb",
            source_a_records=source_a,
            source_b_name="lxx",
            source_b_records=source_b,
            chronology_config=_chronology(),
            sources_config={
                "archives": {
                    "oshb": {
                        "name": "Open Scriptures Hebrew Bible",
                        "text_relation": "original_language_transcription",
                        "is_translation": False,
                        "is_transcription": True,
                    },
                    "lxx": {
                        "name": "Septuagint",
                        "text_relation": "translation",
                        "is_translation": True,
                        "is_transcription": True,
                    },
                }
            },
        )


def test_compare_sources_orders_bce_witness_before_ce_witness():
    source_a = [_record("oshb", 1, "בראשית ברא", "h1", "2018-12-14T00:00:00")]
    source_b = [_record("dss", 1, "בראשית ברא", "h2", "2024-01-01T00:00:00Z")]

    report = compare_sources(
        source_a_name="oshb",
        source_a_records=source_a,
        source_b_name="dss_4qgen",
        source_b_records=source_b,
        chronology_config=_chronology(),
        sources_config={
            "archives": {
                "oshb": {
                    "name": "Open Scriptures Hebrew Bible",
                    "text_relation": "original_language_transcription",
                    "is_translation": False,
                    "is_transcription": True,
                },
                "dss_4qgen": {
                    "name": "Dead Sea Scrolls Genesis Transcriptions",
                    "text_relation": "original_language_transcription",
                    "is_translation": False,
                    "is_transcription": True,
                },
            }
        },
    )

    assert report["source_ordering"]["source_a_name"] == "dss_4qgen"
    assert report["source_ordering"]["source_b_name"] == "oshb"
    assert report["source_ordering"]["witness_year_gap"]["years"] == 1257
    assert report["source_ordering"]["witness_year_gap"]["older_year_label"] == "250 BCE"
    assert report["source_ordering"]["witness_year_gap"]["newer_year_label"] == "1008 CE"


def test_compare_sources_handles_fragmentary_out_of_order_alignment_by_verse_reference():
    dss_records = [
        {
            "work_id": "bible.ot.genesis",
            "source_archive": "dss",
            "source_uri": "https://www.deadseascrolls.org.il/explore-the-archive/search#q=item_id:'4Q1'",
            "source_version_date": "2026-03-16T00:00:00Z",
            "content_hash": "dss-2",
            "text_content": "והארץ היתה תהו ובהו",
            "notes": "Genesis 1:2 | DSS siglum: 4QGen",
        },
        {
            "work_id": "bible.ot.genesis",
            "source_archive": "dss",
            "source_uri": "https://www.deadseascrolls.org.il/explore-the-archive/search#q=item_id:'4Q1'",
            "source_version_date": "2026-03-16T00:00:00Z",
            "content_hash": "dss-1",
            "text_content": "בראשית ברא אלהים",
            "notes": "Genesis 1:1 | DSS siglum: 4QGen",
        },
    ]
    oshb_records = [_record("oshb", 1, "בראשית ברא", "oshb-1", "2018-12-14T00:00:00")]

    report = compare_sources(
        source_a_name="dss_4qgen",
        source_a_records=dss_records,
        source_b_name="oshb",
        source_b_records=oshb_records,
        chronology_config=_chronology(),
        sources_config={
            "archives": {
                "dss_4qgen": {
                    "name": "Dead Sea Scrolls Genesis Transcriptions",
                    "text_relation": "original_language_transcription",
                    "is_translation": False,
                    "is_transcription": True,
                },
                "oshb": {
                    "name": "Open Scriptures Hebrew Bible",
                    "text_relation": "original_language_transcription",
                    "is_translation": False,
                    "is_transcription": True,
                },
            }
        },
    )

    assert report["comparison"]["matching_strategy"] == "verse_reference_alignment"
    assert report["comparison"]["order_independent_alignment"] is True
    assert report["comparison"]["coverage_mode"] == "overlap_only"
    assert report["comparison"]["shared_verses"] == 1
    assert report["comparison"]["source_a_total_verses"] == 2
    assert report["comparison"]["source_b_total_verses"] == 1
    assert report["comparison"]["changed_verse_details"][0]["verse"] == "Gen.1.1"
    assert report["comparison"]["only_in_source_a"] == 1
    assert report["comparison"]["only_in_source_a_details"][0]["verse"] == "Gen.1.2"
    assert any(
        finding.get("code") == "PARTIAL_VERSE_OVERLAP"
        for finding in report["findings"]
    )
