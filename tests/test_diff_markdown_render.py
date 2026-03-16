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
    assert "- אלהים" in markdown
    assert "## Source Ordering (Oldest First)" in markdown
    assert "Source A (oldest witness): sefaria_mam" in markdown
    assert "Estimated year gap between source witnesses: 78 years" in markdown
    assert "## Authorship and Source Context" in markdown
    assert "Text traditional attribution: Traditionally attributed to Moses" in markdown
    assert "Source A discovery location: Aleppo/Jerusalem" in markdown
    assert "## Chronology Axis (Primary)" in markdown
    assert "Estimated original composition window: 1000-400 BCE" in markdown
    assert "## Digital Edition Dates (Secondary)" in markdown
    assert "Source A English (literal, auto-generated; approximate):" in markdown
    assert "Source B English (literal, auto-generated; approximate):" in markdown
    assert "Reviewer notes:" in markdown
    assert "Textual observation:" in markdown
    assert "Historical significance:" in markdown


def test_markdown_render_formats_bce_year_labels_for_oldest_source():
    source_a = [_record("oshb", 1, "בראשית", "h1", "2018-12-14T00:00:00")]
    source_b = [_record("dss", 1, "בראשית", "h2", "2024-01-01T00:00:00Z")]

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

    markdown = render_markdown_report(report, source_a_name="oshb", source_b_name="dss_4qgen")

    assert "Source A (oldest witness): dss_4qgen | anchor year: 250 BCE" in markdown
    assert "(250 BCE -> 1008 CE)" in markdown


def test_markdown_render_reports_overlap_only_for_fragmentary_sources():
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

    markdown = render_markdown_report(report, source_a_name="dss_4qgen", source_b_name="oshb")

    assert "## Coverage Alignment" in markdown
    assert "Matching strategy: verse reference alignment from source_uri fragments or notes" in markdown
    assert "Input order handling: file order ignored; verses are matched and sorted by reference" in markdown
    assert "Coverage mode: overlap only" in markdown
    assert "Only in dss_4qgen: 1" in markdown
    assert "dss_4qgen-only verse refs: Gen.1.2" in markdown
