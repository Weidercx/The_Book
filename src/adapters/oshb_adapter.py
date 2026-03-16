# The_Book/src/adapters/oshb_adapter.py
# Minimal OSHB adapter for first functional milestone: Genesis chapter 1

from __future__ import annotations

from datetime import datetime
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
                    source_version_date=raw.get("source_version_date"),
                    morphology_tagged=True,
                    notes=f"Genesis {chapter_number}:{verse_number}",
                )
            )

        return witness_records

    @classmethod
    def _extract_chapter_verses(cls, xml_content: str, chapter: int) -> List[Dict[str, Any]]:
        """Extract verse-level raw records for a specific Genesis chapter."""
        root = etree.fromstring(xml_content.encode("utf-8"))
        source_version_date = cls._extract_latest_revision_date(root)
        chapter_xpath = f"//osis:chapter[@osisID='Gen.{chapter}']/osis:verse"
        verse_elements = root.xpath(chapter_xpath, namespaces=cls.OSIS_NS)

        if not verse_elements:
            raise ValueError(f"No verses found for Genesis chapter {chapter}")

        extracted: List[Dict[str, Any]] = []
        for verse in verse_elements:
            osis_id = verse.attrib.get("osisID", "")
            verse_number = cls._parse_verse_number(osis_id)
            text_content = cls._extract_verse_text(verse)

            if not text_content:
                continue

            extracted.append(
                {
                    "chapter_number": chapter,
                    "verse_number": verse_number,
                    "osis_id": osis_id,
                    "text_content": text_content,
                    "source_version_date": source_version_date,
                }
            )

        return extracted

    @classmethod
    def _extract_verse_text(cls, verse: etree._Element) -> str:
        """
        Extract verse text from lexical tokens only.

        This intentionally excludes <note> content so editorial annotations are not
        injected into witness text.
        """
        tokens: List[str] = []
        for child in verse:
            local_name = etree.QName(child).localname
            if local_name not in {"w", "seg"}:
                continue

            token_text = "".join(child.itertext()).strip()
            if token_text:
                tokens.append(token_text)

        return cls._normalize_verse_text(" ".join(tokens))

    @classmethod
    def _extract_latest_revision_date(cls, root: etree._Element) -> datetime | None:
        """Extract latest OSHB revision date from the header metadata."""
        date_values = root.xpath(
            "//osis:header/osis:revisionDesc/osis:date/text()",
            namespaces=cls.OSIS_NS,
        )

        parsed_dates = [cls._parse_revision_date(str(value)) for value in date_values]
        valid_dates = [value for value in parsed_dates if value is not None]

        if not valid_dates:
            return None

        return max(valid_dates)

    @staticmethod
    def _parse_revision_date(value: str) -> datetime | None:
        """Parse OSHB header dates such as 2018.12.14 into datetime objects."""
        cleaned = value.strip()
        if not cleaned:
            return None

        parts = cleaned.split(".")
        if len(parts) == 3 and all(part.isdigit() for part in parts):
            year, month, day = (int(part) for part in parts)
            return datetime(year=year, month=month, day=day)

        try:
            return datetime.fromisoformat(cleaned)
        except ValueError:
            return None

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
