# The_Book/src/adapters/dss_adapter.py
# Adapter for Dead Sea Scrolls Genesis Hebrew transcription payloads.

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp

from .base_adapter import BaseAdapter
from ..core import OriginClass, ScriptFamily, WitnessRecord


class DSSGenesisTranscriptionAdapter(BaseAdapter):
    """Fetch and parse DSS Genesis transcription data into WitnessRecords."""

    async def fetch(
        self,
        chapter: int = 1,
        timeout_seconds: int = 45,
        payload_override: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        if chapter < 1:
            raise ValueError("chapter must be >= 1")

        payload = payload_override
        if payload is None:
            endpoint = str(self.api_endpoint or self.config.get("transcription_url") or "").strip()
            if not endpoint:
                raise ValueError(
                    "DSS adapter requires api_endpoint in config/sources.yaml or payload_override"
                )
            payload = await self._load_payload(endpoint=endpoint, timeout_seconds=timeout_seconds)

        if not isinstance(payload, dict):
            raise ValueError("DSS payload must be a JSON object")

        return self._extract_chapter_verses(payload=payload, chapter=chapter)

    def parse(self, raw_records: List[Dict[str, Any]]) -> List[WitnessRecord]:
        license_code, license_url = self._map_license(str(self.config.get("license") or ""))

        witness_records: List[WitnessRecord] = []
        for raw in raw_records:
            witness_records.append(
                self._make_witness_record(
                    work_id="bible.ot.genesis",
                    work_title="Genesis",
                    language_code="heb",
                    script_family=ScriptFamily.HEBREW,
                    text_content=raw["text_content"],
                    origin_class=OriginClass.DIPLOMATIC_TRANSCRIPTION,
                    source_uri=str(raw.get("source_uri")),
                    license_code=license_code,
                    license_url=license_url,
                    source_version_date=raw.get("source_version_date"),
                    morphology_tagged=False,
                    manuscript_siglum=raw.get("manuscript_siglum"),
                    notes=raw.get("notes"),
                )
            )

        return witness_records

    @staticmethod
    async def _load_payload(endpoint: str, timeout_seconds: int) -> Dict[str, Any]:
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            timeout = aiohttp.ClientTimeout(total=timeout_seconds)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(endpoint) as response:
                    response.raise_for_status()
                    payload = await response.json()
            if not isinstance(payload, dict):
                raise ValueError("Remote DSS payload must be a JSON object")
            return payload

        payload_path = Path(endpoint)
        if not payload_path.exists():
            raise FileNotFoundError(f"DSS payload file not found: {payload_path}")

        with payload_path.open("r", encoding="utf-8-sig") as handle:
            payload = json.load(handle)

        if not isinstance(payload, dict):
            raise ValueError("Local DSS payload must be a JSON object")

        return payload

    @staticmethod
    def _extract_chapter_verses(payload: Dict[str, Any], chapter: int) -> List[Dict[str, Any]]:
        verses = payload.get("verses")
        if not isinstance(verses, list):
            raise ValueError("DSS payload must include a 'verses' array")

        source_uri_base = str(payload.get("source_uri") or payload.get("source_url") or "").strip()
        if not source_uri_base:
            source_uri_base = "dss://genesis/transcription"

        source_version_date = DSSGenesisTranscriptionAdapter._coerce_datetime(
            payload.get("source_version_date")
        )
        manuscript_siglum = str(
            payload.get("manuscript_siglum")
            or payload.get("siglum")
            or payload.get("source_siglum")
            or "DSS-Genesis"
        ).strip()

        extracted: List[Dict[str, Any]] = []
        for verse in verses:
            if not isinstance(verse, dict):
                continue

            verse_chapter = DSSGenesisTranscriptionAdapter._parse_int(verse.get("chapter"), default=chapter)
            if verse_chapter != chapter:
                continue

            verse_number = DSSGenesisTranscriptionAdapter._parse_int(verse.get("verse"))
            if verse_number is None:
                continue

            verse_text = DSSGenesisTranscriptionAdapter._normalize_text(
                str(verse.get("text") or verse.get("hebrew") or verse.get("transcription") or "")
            )
            if not verse_text:
                continue

            osis_id = str(verse.get("osis_id") or f"Gen.{chapter}.{verse_number}")

            verse_source_uri = verse.get("source_uri") or verse.get("uri")
            if verse_source_uri:
                source_uri = str(verse_source_uri)
            elif "#" in source_uri_base:
                source_uri = source_uri_base
            else:
                source_uri = f"{source_uri_base}#{osis_id}"

            note_parts = [f"Genesis {chapter}:{verse_number}", f"DSS siglum: {manuscript_siglum}"]
            fragment_id = str(verse.get("fragment_id") or verse.get("fragment") or "").strip()
            if fragment_id:
                note_parts.append(f"Fragment: {fragment_id}")

            extracted.append(
                {
                    "chapter_number": chapter,
                    "verse_number": verse_number,
                    "osis_id": osis_id,
                    "text_content": verse_text,
                    "source_uri": source_uri,
                    "source_version_date": source_version_date,
                    "manuscript_siglum": manuscript_siglum,
                    "notes": " | ".join(note_parts),
                }
            )

        if not extracted:
            raise ValueError(f"No DSS transcription verses found for Genesis chapter {chapter}")

        return extracted

    @staticmethod
    def _parse_int(value: Any, default: int | None = None) -> int | None:
        if value is None:
            return default
        if isinstance(value, int):
            return value
        try:
            return int(str(value).strip())
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _coerce_datetime(value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value

        text = str(value).strip()
        if not text:
            return None

        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None

    @staticmethod
    def _normalize_text(text: str) -> str:
        return " ".join(text.split())

    @staticmethod
    def _map_license(license_label: str) -> tuple[str, str]:
        label = (license_label or "").upper()

        if "PUBLIC" in label or "CC0" in label:
            return "Public-Domain", "https://creativecommons.org/publicdomain/mark/1.0/"
        if "BY-NC-SA" in label and "4.0" in label:
            return "CC-BY-NC-SA-4.0", "https://creativecommons.org/licenses/by-nc-sa/4.0/"
        if "BY-NC-SA" in label:
            return "CC-BY-NC-SA-3.0", "https://creativecommons.org/licenses/by-nc-sa/3.0/"
        if "BY-NC" in label and "4.0" in label:
            return "CC-BY-NC-4.0", "https://creativecommons.org/licenses/by-nc/4.0/"
        if "BY-NC" in label:
            return "CC-BY-NC-3.0", "https://creativecommons.org/licenses/by-nc/3.0/"
        if "BY-SA" in label and "4.0" in label:
            return "CC-BY-SA-4.0", "https://creativecommons.org/licenses/by-sa/4.0/"
        if "BY-SA" in label:
            return "CC-BY-SA-3.0", "https://creativecommons.org/licenses/by-sa/3.0/"
        if "BY" in label and "4.0" in label:
            return "CC-BY-4.0", "https://creativecommons.org/licenses/by/4.0/"
        if "BY" in label:
            return "CC-BY-3.0", "https://creativecommons.org/licenses/by/3.0/"

        return "CC-BY-4.0", "https://creativecommons.org/licenses/by/4.0/"
