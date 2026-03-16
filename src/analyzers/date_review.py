# The_Book/src/analyzers/date_review.py
# Date-first skeptical review for treating texts like code revisions.

from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional

HEBREW_CHAR_RE = re.compile(r"[\u0590-\u05FF]")
LATIN_CHAR_RE = re.compile(r"[A-Za-z]")
INLINE_NOTE_RE = re.compile(r"(We read|typographical error|BHS)", re.IGNORECASE)


def _parse_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _record_key(record: Dict[str, Any]) -> str:
    source_uri = str(record.get("source_uri", ""))
    if "#" in source_uri:
        return source_uri.split("#", maxsplit=1)[1]
    if source_uri:
        return source_uri
    return str(record.get("notes", "unknown"))


def _record_label(record: Dict[str, Any]) -> str:
    note = str(record.get("notes", "")).strip()
    if note:
        return note
    return _record_key(record)


class DateSkepticalReviewer:
    """Runs chronology-aware skeptical checks over witness records."""

    def __init__(self, chronology_config: Dict[str, Any]):
        self._work_chronology = chronology_config.get("works", {})

    def review(
        self,
        records: List[Dict[str, Any]],
        baseline_records: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        if not records:
            return {
                "status": "error",
                "risk_level": "high",
                "message": "No records provided for skeptical review",
                "findings": [
                    {
                        "severity": "high",
                        "code": "NO_RECORDS",
                        "message": "Cannot run chronology review without records",
                    }
                ],
            }

        work_id = str(records[0].get("work_id", "unknown"))
        chronology = self._work_chronology.get(work_id, {})

        findings: List[Dict[str, Any]] = []

        missing_source_version = self._check_source_version_dates(records, findings)
        contamination_flags = self._check_inline_contamination(records, findings)
        edition_drift = self._check_edition_drift(records, baseline_records, findings)

        temporal_summary = self._build_temporal_summary(records, chronology)
        if not chronology:
            findings.append(
                {
                    "severity": "medium",
                    "code": "MISSING_CHRONOLOGY_ENTRY",
                    "message": f"No chronology metadata configured for {work_id}",
                }
            )

        risk_level = self._risk_level(findings)

        return {
            "status": "ok",
            "review_generated_at": datetime.now(timezone.utc).isoformat(),
            "work_id": work_id,
            "record_count": len(records),
            "risk_level": risk_level,
            "chronology_reference": chronology,
            "temporal_summary": temporal_summary,
            "checks": {
                "source_version_date_present": {
                    "passed": missing_source_version == 0,
                    "missing_count": missing_source_version,
                },
                "inline_editorial_contamination": {
                    "passed": len(contamination_flags) == 0,
                    "flagged_count": len(contamination_flags),
                    "flagged_verses": contamination_flags,
                },
                "edition_drift": edition_drift,
            },
            "findings": findings,
        }

    def _check_source_version_dates(
        self,
        records: List[Dict[str, Any]],
        findings: List[Dict[str, Any]],
    ) -> int:
        missing_labels: List[str] = []
        for record in records:
            if record.get("source_version_date") is None:
                missing_labels.append(_record_label(record))

        if missing_labels:
            findings.append(
                {
                    "severity": "high",
                    "code": "MISSING_SOURCE_VERSION_DATE",
                    "message": "Records are missing source_version_date required for skeptical edition review",
                    "examples": missing_labels[:5],
                }
            )

        return len(missing_labels)

    def _check_inline_contamination(
        self,
        records: List[Dict[str, Any]],
        findings: List[Dict[str, Any]],
    ) -> List[str]:
        flagged: List[str] = []

        for record in records:
            text = str(record.get("text_content", ""))
            label = _record_label(record)

            if INLINE_NOTE_RE.search(text):
                flagged.append(label)
                continue

            hebrew_count = len(HEBREW_CHAR_RE.findall(text))
            latin_count = len(LATIN_CHAR_RE.findall(text))
            if hebrew_count > 0 and latin_count >= 12:
                flagged.append(label)

        if flagged:
            findings.append(
                {
                    "severity": "high",
                    "code": "INLINE_EDITORIAL_NOTE_CONTAMINATION",
                    "message": "Editorial note text appears inline with witness content",
                    "examples": flagged[:5],
                }
            )

        return flagged

    def _check_edition_drift(
        self,
        records: List[Dict[str, Any]],
        baseline_records: Optional[List[Dict[str, Any]]],
        findings: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if baseline_records is None:
            return {
                "baseline_compared": False,
                "changed_count": 0,
                "added_count": 0,
                "removed_count": 0,
            }

        current_by_key = {_record_key(record): record for record in records}
        baseline_by_key = {_record_key(record): record for record in baseline_records}

        changed: List[str] = []
        for key, current in current_by_key.items():
            if key not in baseline_by_key:
                continue
            baseline = baseline_by_key[key]
            if current.get("content_hash") != baseline.get("content_hash"):
                changed.append(key)

        added = sorted([key for key in current_by_key if key not in baseline_by_key])
        removed = sorted([key for key in baseline_by_key if key not in current_by_key])

        if changed or added or removed:
            findings.append(
                {
                    "severity": "medium",
                    "code": "EDITION_DRIFT_DETECTED",
                    "message": "Differences detected compared to baseline release",
                    "changed_examples": changed[:5],
                    "added_examples": added[:5],
                    "removed_examples": removed[:5],
                }
            )

        return {
            "baseline_compared": True,
            "changed_count": len(changed),
            "added_count": len(added),
            "removed_count": len(removed),
            "changed_examples": changed[:5],
            "added_examples": added[:5],
            "removed_examples": removed[:5],
        }

    def _build_temporal_summary(
        self,
        records: List[Dict[str, Any]],
        chronology: Dict[str, Any],
    ) -> Dict[str, Any]:
        source_dates = [
            parsed
            for parsed in (_parse_datetime(record.get("source_version_date")) for record in records)
            if parsed is not None
        ]
        acquisition_dates = [
            parsed
            for parsed in (_parse_datetime(record.get("acquisition_date")) for record in records)
            if parsed is not None
        ]

        latest_source_version = max(source_dates).isoformat() if source_dates else None
        latest_acquisition = max(acquisition_dates).isoformat() if acquisition_dates else None

        composition = chronology.get("composition_window_bce", {})
        composition_end_bce = composition.get("end")

        temporal_gap_years = None
        if source_dates and isinstance(composition_end_bce, int):
            temporal_gap_years = max(source_dates).year + composition_end_bce

        return {
            "latest_source_version_date": latest_source_version,
            "latest_acquisition_date": latest_acquisition,
            "composition_window_bce": composition,
            "estimated_gap_years_from_composition_end_to_latest_edition": temporal_gap_years,
        }

    @staticmethod
    def _risk_level(findings: List[Dict[str, Any]]) -> str:
        severities = {str(finding.get("severity", "")).lower() for finding in findings}
        if "high" in severities:
            return "high"
        if "medium" in severities:
            return "medium"
        return "low"
