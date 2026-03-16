from pathlib import Path
import json

from scripts.build_source_diff_index import (
    discover_completed_pairs,
    diff_output_stem,
    normalize_analysis_diff_filenames,
    normalize_report_diff_filenames,
    normalize_diff_artifact_filenames,
    parse_pair_from_path,
)


def test_diff_output_stem_prefers_compact_year_span():
    output_stem = diff_output_stem(
        source_a="dss_4qgen",
        source_b="oshb",
        signed_year_by_source={"dss_4qgen": -250, "oshb": 1008},
        include_source_pair_suffix=False,
    )

    assert output_stem == "250BCE_1008CE"


def test_diff_output_stem_appends_pair_suffix_when_requested():
    output_stem = diff_output_stem(
        source_a="dss_4qgen",
        source_b="oshb",
        signed_year_by_source={"dss_4qgen": -250, "oshb": 1008},
        include_source_pair_suffix=True,
    )

    assert output_stem == "250BCE_1008CE__dss_4qgen_vs_oshb"


def test_parse_pair_from_prefixed_diff_path():
    path = Path("250BCE_1008CE__dss_4qgen_vs_oshb.json")

    assert parse_pair_from_path(path) == ("dss_4qgen", "oshb")


def test_normalize_analysis_diff_filenames_renames_existing_pair(tmp_path: Path):
    analysis_dir = tmp_path / "diffs"
    analysis_dir.mkdir()

    legacy_json = analysis_dir / "dss_4qgen_vs_oshb.json"
    legacy_json.write_text(
        json.dumps(
            {
                "source_ordering": {
                    "source_a_name": "dss_4qgen",
                    "source_b_name": "oshb",
                }
            }
        ),
        encoding="utf-8",
    )
    legacy_markdown = analysis_dir / "dss_4qgen_vs_oshb.md"
    legacy_markdown.write_text("# diff", encoding="utf-8")

    normalized = normalize_analysis_diff_filenames(
        analysis_dir=analysis_dir,
        signed_year_by_source={"dss_4qgen": -250, "oshb": 1008},
    )

    target_stem = diff_output_stem(
        source_a="dss_4qgen",
        source_b="oshb",
        signed_year_by_source={"dss_4qgen": -250, "oshb": 1008},
        include_source_pair_suffix=False,
    )

    assert len(normalized) == 1
    assert not legacy_json.exists()
    assert not legacy_markdown.exists()
    assert (analysis_dir / f"{target_stem}.json").exists()
    assert (analysis_dir / f"{target_stem}.md").exists()
    assert normalized[0]["json_to"].endswith(f"{target_stem}.json")


def test_normalize_report_diff_filenames_renames_cross_source_report(tmp_path: Path):
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()

    legacy_json = reports_dir / "cross_source_diff.json"
    legacy_json.write_text(
        json.dumps(
            {
                "source_ordering": {
                    "source_a_name": "dss_4qgen",
                    "source_b_name": "oshb",
                }
            }
        ),
        encoding="utf-8",
    )
    legacy_markdown = reports_dir / "cross_source_diff.md"
    legacy_markdown.write_text("# diff", encoding="utf-8")

    normalized = normalize_report_diff_filenames(
        reports_dir=reports_dir,
        signed_year_by_source={"dss_4qgen": -250, "oshb": 1008},
    )

    target_stem = diff_output_stem(
        source_a="dss_4qgen",
        source_b="oshb",
        signed_year_by_source={"dss_4qgen": -250, "oshb": 1008},
        include_source_pair_suffix=False,
    )

    assert len(normalized) == 1
    assert not legacy_json.exists()
    assert not legacy_markdown.exists()
    assert (reports_dir / f"{target_stem}.json").exists()
    assert (reports_dir / f"{target_stem}.md").exists()


def test_discover_completed_pairs_scans_all_report_json(monkeypatch, tmp_path: Path):
    reports_dir = tmp_path / "reports"
    analysis_dir = tmp_path / "analysis"
    reports_dir.mkdir()
    analysis_dir.mkdir()

    prefixed_report = reports_dir / "1000930_930CE__1001008_1008CE__sefaria_mam_vs_oshb.json"
    prefixed_report.write_text(
        json.dumps(
            {
                "source_ordering": {
                    "source_a_name": "sefaria_mam",
                    "source_b_name": "oshb",
                }
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "scripts.build_source_diff_index.default_reports_dir",
        lambda _work_id, _chapter: reports_dir,
    )
    monkeypatch.setattr(
        "scripts.build_source_diff_index.default_analysis_diff_dir",
        lambda _work_id, _chapter: analysis_dir,
    )

    completed_pairs = discover_completed_pairs(work_id="bible.ot.genesis", chapter=1)

    assert ("oshb", "sefaria_mam") in completed_pairs


def test_normalize_diff_artifacts_adds_suffix_on_year_collision(tmp_path: Path):
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()

    first = artifacts_dir / "legacy_one.json"
    first.write_text(
        json.dumps(
            {
                "source_ordering": {
                    "source_a_name": "source_alpha",
                    "source_b_name": "source_beta",
                }
            }
        ),
        encoding="utf-8",
    )
    second = artifacts_dir / "legacy_two.json"
    second.write_text(
        json.dumps(
            {
                "source_ordering": {
                    "source_a_name": "source_gamma",
                    "source_b_name": "source_delta",
                }
            }
        ),
        encoding="utf-8",
    )

    normalized = normalize_diff_artifact_filenames(
        artifacts_dir=artifacts_dir,
        signed_year_by_source={
            "source_alpha": 930,
            "source_beta": 1008,
            "source_gamma": 930,
            "source_delta": 1008,
        },
    )

    json_names = {path.name for path in artifacts_dir.glob("*.json")}

    assert len(normalized) == 2
    assert "930CE_1008CE__source_alpha_vs_source_beta.json" in json_names
    assert any(
        name.startswith("930CE_1008CE__") and "source_gamma" in name and "source_delta" in name
        for name in json_names
    )