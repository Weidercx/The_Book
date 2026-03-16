# The_Book/tests/test_sefaria_adapter.py

from src.adapters.sefaria_adapter import SefariaGenesisAdapter


def _sample_payload():
    return {
        "he": [
            "<big>בְּ</big>רֵאשִׁית בָּרָא",
            "וְהָאָרֶץ הָיְתָה",
        ],
        "heVersionTitle": "Miqra according to the Masorah",
        "heVersionSource": "https://he.wikisource.org/wiki/%D7%9E%D7%A9%D7%AA%D7%9E%D7%A9:Dovi/%D7%9E%D7%A7%D7%A8%D7%90_%D7%A2%D7%9C_%D7%A4%D7%99_%D7%94%D7%9E%D7%A1%D7%95%D7%A8%D7%94",
        "heLicense": "CC-BY-SA",
    }


def test_clean_text_strips_html_tags():
    cleaned = SefariaGenesisAdapter._clean_text("<big>בְּ</big>רֵאשִׁית")
    assert cleaned == "בְּרֵאשִׁית"


def test_parse_outputs_genesis_witness_records():
    adapter = SefariaGenesisAdapter(config={"name": "Sefaria Miqra"})

    raw = [
        {
            "chapter_number": 1,
            "verse_number": 1,
            "osis_id": "Gen.1.1",
            "text_content": "בְּרֵאשִׁית בָּרָא",
            "version_title": "Miqra according to the Masorah",
            "version_source": "https://he.wikisource.org/wiki/Example",
            "source_version_date": "2026-03-01T00:00:00+00:00",
            "license_label": "CC-BY-SA",
            "api_url": "https://www.sefaria.org/api/texts/Genesis.1?lang=he&context=0",
        }
    ]

    records = adapter.parse(raw)

    assert len(records) == 1
    assert records[0].work_id == "bible.ot.genesis"
    assert records[0].origin_class == "critical_edition_source_language"
    assert records[0].license.code == "CC-BY-SA-3.0"
    assert records[0].source_uri.endswith("#Gen.1.1")
