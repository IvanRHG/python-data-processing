"""Tests for the cleaning pipeline. Run with: python -m pytest"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import run_pipeline  # noqa: E402
from ticket_pipeline import PipelineError, clean, inspect, load_csv  # noqa: E402
from ticket_pipeline.cleaning import map_value, normalize_text, parse_date, validate_row  # noqa: E402
from ticket_pipeline.schema import LANGUAGE_MAP, REQUIRED_COLUMNS  # noqa: E402

VALID_ROW = {
    "ticket_id": "TCK-0001",
    "created_at": "2026-03-01",
    "language": " Español ",
    "country": "colombia",
    "channel": "E-mail",
    "category": "shipping",
    "priority": "HIGH",
    "resolution_hours": "12.5",
    "satisfaction_score": "4",
    "agent_id": "AG-01",
}


def make_df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=REQUIRED_COLUMNS).astype(str)


# --- value helpers -------------------------------------------------------- #

def test_normalize_text_trims_and_collapses_spaces():
    assert normalize_text("  live   chat ") == "live chat"
    assert normalize_text("   ") is None


def test_map_value_known_unknown_and_missing():
    assert map_value("Français", LANGUAGE_MAP) == ("fr", True)
    assert map_value("Portuguese", LANGUAGE_MAP) == (None, False)
    assert map_value(None, LANGUAGE_MAP) == (None, True)


@pytest.mark.parametrize("text", ["2026-13-02", "yesterday", "2026-02-30", "05/03/2026"])
def test_parse_date_rejects_invalid_or_ambiguous(text):
    assert parse_date(text) is None


def test_parse_date_accepts_supported_formats():
    assert parse_date("2026/04/28").date().isoformat() == "2026-04-28"


# --- row validation ------------------------------------------------------- #

def test_valid_row_is_normalized():
    row, issues = validate_row(VALID_ROW)
    assert issues == []
    assert row["language"] == "es"
    assert row["channel"] == "email"
    assert row["category"] == "delivery"
    assert row["priority"] == "high"
    assert row["country"] == "Colombia"
    assert row["resolution_hours"] == 12.5


@pytest.mark.parametrize(
    "field, value, expected_issue",
    [
        ("category", "", "missing_category"),
        ("created_at", "yesterday", "invalid_created_at"),
        ("resolution_hours", "-1", "negative_resolution_hours"),
        ("resolution_hours", "N/A", "non_numeric_resolution_hours"),
        ("satisfaction_score", "7", "satisfaction_score_out_of_range"),
        ("satisfaction_score", "3.5", "satisfaction_score_out_of_range"),
        ("satisfaction_score", "three", "non_numeric_satisfaction_score"),
        ("language", "Portuguese", "invalid_language"),
    ],
)
def test_invalid_values_are_reported(field, value, expected_issue):
    _, issues = validate_row({**VALID_ROW, field: value})
    assert expected_issue in issues


def test_missing_optional_values_are_allowed():
    _, issues = validate_row({**VALID_ROW, "satisfaction_score": "", "country": ""})
    assert issues == []


# --- full process --------------------------------------------------------- #

def test_exact_duplicates_removed_and_conflicts_rejected():
    conflict = {**VALID_ROW, "ticket_id": "TCK-0002", "priority": "low"}
    rows = [
        VALID_ROW,
        dict(VALID_ROW),                                   # exact duplicate -> dropped
        {**VALID_ROW, "ticket_id": "TCK-0002"},
        conflict,                                          # same id, different content
        {**VALID_ROW, "ticket_id": "TCK-0003", "created_at": "bad"},
    ]
    result = clean(make_df(rows))
    assert result.stats["exact_duplicates_removed"] == 1
    assert list(result.clean["ticket_id"]) == ["TCK-0001"]
    assert result.stats["rejected_rows"] == 3
    assert result.stats["rejection_reasons"]["conflicting_ticket_id"] == 2
    # source_row must point to the real line in the CSV (header = line 1).
    assert sorted(result.rejected["source_row"]) == [4, 5, 6]


def test_inspect_counts_problems():
    report = inspect(make_df([VALID_ROW, VALID_ROW, {**VALID_ROW, "country": " "}]))
    assert report["rows"] == 3
    assert report["exact_duplicate_rows"] == 1
    assert report["empty_values_per_column"]["country"] == 1


# --- error handling ------------------------------------------------------- #

def test_missing_file_raises_clear_error(tmp_path):
    with pytest.raises(PipelineError, match="not found"):
        load_csv(tmp_path / "nope.csv")


def test_missing_columns_raise_clear_error(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("ticket_id,created_at\nTCK-1,2026-01-01\n", encoding="utf-8")
    with pytest.raises(PipelineError, match="Missing required column"):
        load_csv(path)


def test_empty_file_raises_clear_error(tmp_path):
    path = tmp_path / "empty.csv"
    path.write_text("", encoding="utf-8")
    with pytest.raises(PipelineError, match="empty"):
        load_csv(path)


def test_cli_returns_error_code_for_missing_input(tmp_path, capsys):
    code = run_pipeline.main(["--input", str(tmp_path / "missing.csv"), "--output-dir", str(tmp_path)])
    assert code == 1
    assert "ERROR" in capsys.readouterr().err


# --- reproducibility of the committed sample ------------------------------ #

def test_sample_dataset_produces_documented_numbers(tmp_path):
    """The numbers quoted in the README must match what the code produces."""
    code = run_pipeline.main(["--output-dir", str(tmp_path)])
    assert code == 0
    clean_df = pd.read_csv(tmp_path / "support_tickets_clean.csv")
    rejected_df = pd.read_csv(tmp_path / "rejected_rows.csv")
    assert len(clean_df) == 99
    assert len(rejected_df) == 12
    assert clean_df["ticket_id"].is_unique
    assert set(clean_df["language"]) <= {"es", "en", "fr"}
    assert clean_df["satisfaction_score"].dropna().between(1, 5).all()
    assert (clean_df["resolution_hours"].dropna() >= 0).all()
