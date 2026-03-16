# The_Book/tests/test_date_review.py

from src.analyzers import DateSkepticalReviewer


def _sample_record(**overrides):
    record = {
        "work_id": "bible.ot.genesis",
        "notes": "Genesis 1:1",
        "source_uri": "https://example.org/Gen.xml#Gen.1.1",
        "text_content": "בְּרֵאשִׁית בָּרָא",
        "content_hash": "hash-1",
        "source_version_date": "2018-12-14T00:00:00",
        "acquisition_date": "2026-03-16T00:00:00",
    }
    record.update(overrides)
    return record


def _chronology():
    return {
        "works": {
            "bible.ot.genesis": {
                "composition_window_bce": {"start": 1000, "end": 400},
                "base_witness": {"label": "Leningrad Codex", "date_ce": 1008},
            }
        }
    }


def test_review_flags_missing_source_version_date():
    reviewer = DateSkepticalReviewer(_chronology())
    records = [_sample_record(source_version_date=None)]

    report = reviewer.review(records)

    assert report["risk_level"] == "high"
    assert report["checks"]["source_version_date_present"]["passed"] is False


def test_review_flags_inline_editorial_contamination():
    reviewer = DateSkepticalReviewer(_chronology())
    records = [
        _sample_record(
            text_content="בְּרֵאשִׁית We read punctuation in L differently from BHS"
        )
    ]

    report = reviewer.review(records)

    assert report["checks"]["inline_editorial_contamination"]["passed"] is False
    assert report["risk_level"] == "high"


def test_review_detects_edition_drift_against_baseline():
    reviewer = DateSkepticalReviewer(_chronology())
    current = [_sample_record(content_hash="new-hash")]
    baseline = [_sample_record(content_hash="old-hash")]

    report = reviewer.review(current, baseline_records=baseline)

    assert report["checks"]["edition_drift"]["changed_count"] == 1
    assert any(finding["code"] == "EDITION_DRIFT_DETECTED" for finding in report["findings"])
