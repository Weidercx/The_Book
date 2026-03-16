# The_Book/tests/test_oshb_adapter.py

from src.adapters.oshb_adapter import OSHBGenesisAdapter


SAMPLE_XML = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<osis xmlns=\"http://www.bibletechnologies.net/2003/OSIS/namespace\">
  <header>
    <revisionDesc>
      <date>2018.12.14</date>
    </revisionDesc>
  </header>
  <osisText>
    <div type=\"book\" osisID=\"Gen\">
      <chapter osisID=\"Gen.1\">
        <verse osisID=\"Gen.1.1\"><w>בראשית</w><w>ברא</w></verse>
        <verse osisID=\"Gen.1.2\"><w>והארץ</w><note n=\"c\">We read punctuation in L differently from BHS.</note><w>היתה</w></verse>
      </chapter>
      <chapter osisID=\"Gen.2\">
        <verse osisID=\"Gen.2.1\"><w>ויכלו</w></verse>
      </chapter>
    </div>
  </osisText>
</osis>
"""


def test_extract_chapter_verses_filters_to_one_chapter():
    raw_records = OSHBGenesisAdapter._extract_chapter_verses(SAMPLE_XML, chapter=1)

    assert len(raw_records) == 2
    assert raw_records[0]["osis_id"] == "Gen.1.1"
    assert raw_records[1]["osis_id"] == "Gen.1.2"
    assert "We read" not in raw_records[1]["text_content"]


def test_parse_returns_witness_records_for_genesis():
    adapter = OSHBGenesisAdapter(config={"name": "Open Scriptures Hebrew Bible"})
    raw_records = OSHBGenesisAdapter._extract_chapter_verses(SAMPLE_XML, chapter=1)

    witness_records = adapter.parse(raw_records)

    assert len(witness_records) == 2
    assert witness_records[0].work_id == "bible.ot.genesis"
    assert witness_records[0].language_code == "heb"
    assert witness_records[0].source_uri.endswith("#Gen.1.1")
    assert witness_records[0].source_version_date.year == 2018
