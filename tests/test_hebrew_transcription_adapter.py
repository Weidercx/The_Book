from src.adapters.hebrew_transcription_adapter import HebrewGenesisTranscriptionAdapter


SAMPLE_PAYLOAD = {
    "source_uri": "https://example.org/hebrew/genesis-manuscript.json",
    "source_version_date": "2026-03-16T00:00:00Z",
    "manuscript_siglum": "Sassoon-1053",
    "verses": [
        {
            "chapter": 1,
            "verse": 1,
            "text": "בראשית ברא אלהים",
            "fragment_id": "folio-001r",
        },
        {
            "chapter": 1,
            "verse": 2,
            "text": "והארץ היתה תהו ובהו",
            "fragment_id": "folio-001v",
        },
        {
            "chapter": 2,
            "verse": 1,
            "text": "ויכלו השמים",
            "fragment_id": "folio-002r",
        },
    ],
}


def test_extract_chapter_verses_filters_to_requested_chapter():
    rows = HebrewGenesisTranscriptionAdapter._extract_chapter_verses(SAMPLE_PAYLOAD, chapter=1)

    assert len(rows) == 2
    assert rows[0]["osis_id"] == "Gen.1.1"
    assert rows[0]["source_uri"].endswith("#Gen.1.1")
    assert rows[1]["osis_id"] == "Gen.1.2"


def test_parse_outputs_diplomatic_transcription_records():
    adapter = HebrewGenesisTranscriptionAdapter(
        config={
            "name": "Codex Sassoon 1053 Hebrew Transcriptions",
            "license": "CC-BY 4.0",
        }
    )

    raw_records = HebrewGenesisTranscriptionAdapter._extract_chapter_verses(SAMPLE_PAYLOAD, chapter=1)
    witness_records = adapter.parse(raw_records)

    assert len(witness_records) == 2
    assert witness_records[0].work_id == "bible.ot.genesis"
    assert witness_records[0].language_code == "heb"
    assert witness_records[0].origin_class == "diplomatic_transcription"
    assert witness_records[0].manuscript_siglum == "Sassoon-1053"
    assert witness_records[0].source_uri.endswith("#Gen.1.1")


def test_map_license_supports_cc_by_nc_4():
    code, url = HebrewGenesisTranscriptionAdapter._map_license("CC-BY-NC 4.0")

    assert code == "CC-BY-NC-4.0"
    assert url == "https://creativecommons.org/licenses/by-nc/4.0/"