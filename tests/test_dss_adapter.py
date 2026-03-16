# The_Book/tests/test_dss_adapter.py

from src.adapters.dss_adapter import DSSGenesisTranscriptionAdapter


SAMPLE_PAYLOAD = {
    "source_uri": "https://example.org/dss/genesis-4qgen.json",
    "source_version_date": "2025-10-01T00:00:00Z",
    "manuscript_siglum": "4QGen",
    "verses": [
        {
            "chapter": 1,
            "verse": 1,
            "text": "בראשית ברא אלהים",
            "fragment_id": "4QGen frg 1",
        },
        {
            "chapter": 1,
            "verse": 2,
            "text": "והארץ היתה תהו ובהו",
            "fragment_id": "4QGen frg 2",
        },
        {
            "chapter": 2,
            "verse": 1,
            "text": "ויכלו השמים",
            "fragment_id": "4QGen frg 3",
        },
    ],
}


def test_extract_chapter_verses_filters_to_requested_chapter():
    rows = DSSGenesisTranscriptionAdapter._extract_chapter_verses(SAMPLE_PAYLOAD, chapter=1)

    assert len(rows) == 2
    assert rows[0]["osis_id"] == "Gen.1.1"
    assert rows[0]["source_uri"].endswith("#Gen.1.1")
    assert rows[1]["osis_id"] == "Gen.1.2"


def test_parse_outputs_diplomatic_transcription_records():
    adapter = DSSGenesisTranscriptionAdapter(
        config={
            "name": "Dead Sea Scrolls Genesis Transcriptions (4QGen)",
            "license": "CC-BY 4.0",
        }
    )

    raw_records = DSSGenesisTranscriptionAdapter._extract_chapter_verses(SAMPLE_PAYLOAD, chapter=1)
    witness_records = adapter.parse(raw_records)

    assert len(witness_records) == 2
    assert witness_records[0].work_id == "bible.ot.genesis"
    assert witness_records[0].language_code == "heb"
    assert witness_records[0].origin_class == "diplomatic_transcription"
    assert witness_records[0].manuscript_siglum == "4QGen"
    assert witness_records[0].source_uri.endswith("#Gen.1.1")


def test_map_license_supports_cc_by_nc_4():
    code, url = DSSGenesisTranscriptionAdapter._map_license("CC-BY-NC 4.0")

    assert code == "CC-BY-NC-4.0"
    assert url == "https://creativecommons.org/licenses/by-nc/4.0/"
