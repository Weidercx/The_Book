# The_Book/src/adapters/oshb_adapter.py
# Minimal OSHB adapter for first functional milestone: Genesis chapter 1

from __future__ import annotations

from typing import Any, Dict, List

import aiohttp
from lxml import etree

from .base_adapter import BaseAdapter
from ..core import OriginClass, ScriptFamily, WitnessRecord


class OSHBGenesisAdapter(BaseAdapter):
    """Adapter that fetches and parses Genesis chapter data from OSHB WLC XML."""

    RAW_GENESIS_XML_URL = (
        "https://raw.githubusercontent.com/openscriptures/morphhb/master/wlc/Gen.xml"
    )
    OSIS_NS = {"osis": "http://www.bibletechnologies.net/2003/OSIS/namespace"}

    async def fetch(
        self,
        chapter: int = 1,
        timeout_seconds: int = 45,
        xml_content: str | None = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch and extract raw verse records for one Genesis chapter.

        Args:
            chapter: Genesis chapter number
            timeout_seconds: HTTP timeout
            xml_content: Optional XML override for tests

        Returns:
            List of raw verse dicts for the requested chapter.
        """
        if chapter < 1:
            raise ValueError("chapter must be >= 1")

        if xml_content is None:
            timeout = aiohttp.ClientTimeout(total=timeout_seconds)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(self.RAW_GENESIS_XML_URL) as response:
                    response.raise_for_status()
                    xml_content = await response.text(encoding="utf-8")

        return self._extract_chapter_verses(xml_content=xml_content, chapter=chapter)

    def parse(self, raw_records: List[Dict[str, Any]]) -> List[WitnessRecord]:
        """Normalize raw Genesis records into WitnessRecord objects."""
        witness_records: List[WitnessRecord] = []

        for raw in raw_records:
            chapter_number = raw["chapter_number"]
            verse_number = raw["verse_number"]
            source_uri = f"{self.RAW_GENESIS_XML_URL}#{raw['osis_id']}"

            witness_records.append(
                self._make_witness_record(
                    work_id="bible.ot.genesis",
                    work_title="Genesis",
                    language_code="heb",
                    script_family=ScriptFamily.HEBREW,
                    text_content=raw["text_content"],
                    origin_class=OriginClass.WITNESS,
                    source_uri=source_uri,
                    license_code="CC-BY-4.0",
                    license_url="https://creativecommons.org/licenses/by/4.0/",
                    morphology_tagged=True,
                    notes=f"Genesis {chapter_number}:{verse_number}",
                )
            )

        return witness_records

    @classmethod
    def _extract_chapter_verses(cls, xml_content: str, chapter: int) -> List[Dict[str, Any]]:
        """Extract verse-level raw records for a specific Genesis chapter."""
        root = etree.fromstring(xml_content.encode("utf-8"))
        chapter_xpath = f"//osis:chapter[@osisID='Gen.{chapter}']/osis:verse"
        verse_elements = root.xpath(chapter_xpath, namespaces=cls.OSIS_NS)

        if not verse_elements:
            raise ValueError(f"No verses found for Genesis chapter {chapter}")

        extracted: List[Dict[str, Any]] = []
        for verse in verse_elements:
            osis_id = verse.attrib.get("osisID", "")
            verse_number = cls._parse_verse_number(osis_id)
            text_content = cls._normalize_verse_text(" ".join(verse.itertext()))

            if not text_content:
                continue

            extracted.append(
                {
                    "chapter_number": chapter,
                    "verse_number": verse_number,
                    "osis_id": osis_id,
                    "text_content": text_content,
                }
            )

        return extracted

    @staticmethod
    def _parse_verse_number(osis_id: str) -> int:
        """Parse verse number from OSIS id like Gen.1.31."""
        parts = osis_id.split(".")
        if len(parts) != 3:
            raise ValueError(f"Unexpected osisID format: {osis_id}")
        return int(parts[2])

    @staticmethod
    def _normalize_verse_text(text: str) -> str:
        """Normalize whitespace while preserving original script characters."""
        return " ".join(text.split())
