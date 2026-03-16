# The_Book/src/adapters/sefaria_adapter.py
# Second-source Genesis adapter using Sefaria Hebrew API (MAM / Wikisource-backed)

from __future__ import annotations

from datetime import datetime
from html import unescape
import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote, unquote, urlparse

import aiohttp

from .base_adapter import BaseAdapter
from ..core import OriginClass, ScriptFamily, WitnessRecord


class SefariaGenesisAdapter(BaseAdapter):
    """Fetch and parse Genesis chapter text from Sefaria Hebrew API."""

    API_TEMPLATE = "https://www.sefaria.org/api/texts/Genesis.{chapter}?lang=he&context=0"
    TAG_RE = re.compile(r"<[^>]+>")
    REQUEST_HEADERS = {
        "User-Agent": "TheBookCorpusBot/0.1 (https://github.com/Weidercx/The_Book; research use)",
        "Api-User-Agent": "TheBookCorpusBot/0.1 (https://github.com/Weidercx/The_Book)",
        "From": "noreply@example.com",
    }

    async def fetch(
        self,
        chapter: int = 1,
        timeout_seconds: int = 45,
        payload_override: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        if chapter < 1:
            raise ValueError("chapter must be >= 1")

        if payload_override is None:
            timeout = aiohttp.ClientTimeout(total=timeout_seconds)
            async with aiohttp.ClientSession(timeout=timeout, headers=self.REQUEST_HEADERS) as session:
                api_url = self.API_TEMPLATE.format(chapter=chapter)
                async with session.get(api_url) as response:
                    response.raise_for_status()
                    payload = await response.json()

                source_version_date = await self._fetch_source_version_date(session, payload)
        else:
            payload = payload_override
            source_version_date = None

        he_verses = payload.get("he", [])
        if not isinstance(he_verses, list) or not he_verses:
            raise ValueError("Sefaria response has no Hebrew verse list in 'he'")

        version_title = str(payload.get("heVersionTitle") or payload.get("versionTitle") or "")
        version_source = str(payload.get("heVersionSource") or payload.get("versionSource") or "")
        license_label = str(payload.get("heLicense") or payload.get("license") or "")

        raw_records: List[Dict[str, Any]] = []
        for index, verse in enumerate(he_verses, start=1):
            verse_text = self._clean_text(str(verse))
            if not verse_text:
                continue

            raw_records.append(
                {
                    "chapter_number": chapter,
                    "verse_number": index,
                    "osis_id": f"Gen.{chapter}.{index}",
                    "text_content": verse_text,
                    "version_title": version_title,
                    "version_source": version_source,
                    "source_version_date": source_version_date,
                    "license_label": license_label,
                    "api_url": self.API_TEMPLATE.format(chapter=chapter),
                }
            )

        return raw_records

    def parse(self, raw_records: List[Dict[str, Any]]) -> List[WitnessRecord]:
        witness_records: List[WitnessRecord] = []

        for raw in raw_records:
            chapter_number = raw["chapter_number"]
            verse_number = raw["verse_number"]
            source_uri = f"{raw['api_url']}#{raw['osis_id']}"

            license_code, license_url = self._map_license(str(raw.get("license_label", "")))
            version_title = str(raw.get("version_title", "")).strip()
            note_parts = [f"Genesis {chapter_number}:{verse_number}"]
            if version_title:
                note_parts.append(f"Source edition: {version_title}")

            witness_records.append(
                self._make_witness_record(
                    work_id="bible.ot.genesis",
                    work_title="Genesis",
                    language_code="heb",
                    script_family=ScriptFamily.HEBREW,
                    text_content=raw["text_content"],
                    origin_class=OriginClass.CRITICAL_EDITION_SOURCE_LANGUAGE,
                    source_uri=source_uri,
                    license_code=license_code,
                    license_url=license_url,
                    source_version_date=raw.get("source_version_date"),
                    morphology_tagged=False,
                    notes=" | ".join(note_parts),
                )
            )

        return witness_records

    @staticmethod
    def _clean_text(text: str) -> str:
        no_tags = SefariaGenesisAdapter.TAG_RE.sub("", text)
        decoded = unescape(no_tags)
        return " ".join(decoded.split())

    @staticmethod
    def _map_license(license_label: str) -> tuple[str, str]:
        label = (license_label or "").upper()

        if "BY-SA" in label and "4.0" in label:
            return "CC-BY-SA-4.0", "https://creativecommons.org/licenses/by-sa/4.0/"
        if "BY-SA" in label:
            return "CC-BY-SA-3.0", "https://creativecommons.org/licenses/by-sa/3.0/"
        if "BY" in label and "4.0" in label:
            return "CC-BY-4.0", "https://creativecommons.org/licenses/by/4.0/"
        if "BY" in label:
            return "CC-BY-3.0", "https://creativecommons.org/licenses/by/3.0/"

        # Conservative fallback for unknown labels.
        return "CC-BY-SA-3.0", "https://creativecommons.org/licenses/by-sa/3.0/"

    async def _fetch_source_version_date(
        self,
        session: aiohttp.ClientSession,
        payload: Dict[str, Any],
    ) -> Optional[datetime]:
        source_url = str(payload.get("heVersionSource") or payload.get("versionSource") or "").strip()
        if not source_url:
            return None

        parsed = urlparse(source_url)
        if "wikisource.org" not in parsed.netloc:
            return None

        title = self._extract_wiki_title(source_url)
        if not title:
            return None

        api_url = (
            f"{parsed.scheme}://{parsed.netloc}/w/api.php"
            f"?action=query&prop=revisions&titles={quote(title)}"
            f"&rvprop=timestamp&rvlimit=1&format=json"
        )

        async with session.get(api_url) as response:
            if response.status != 200:
                return None
            data = await response.json()

        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            revisions = page.get("revisions")
            if not revisions:
                continue
            timestamp = revisions[0].get("timestamp")
            if not timestamp:
                continue

            # MediaWiki returns ISO timestamps ending with Z.
            return datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))

        return None

    @staticmethod
    def _extract_wiki_title(source_url: str) -> str:
        parsed = urlparse(source_url)
        marker = "/wiki/"
        if marker not in parsed.path:
            return ""
        encoded_title = parsed.path.split(marker, maxsplit=1)[1]
        return unquote(encoded_title)
