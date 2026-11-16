"""Load, inspect, validate, and clean the support-ticket dataset.

Design choices:
- Every value is read as text first. Types are converted explicitly, so a
  bad value is reported instead of silently becoming NaN.
- Rows are never fixed by guessing. A row that breaks a rule is moved to a
  "rejected" table together with the reason(s), so a person can review it.
- Normalization only maps known spellings to a canonical value
  (for example "Español" -> "es"). Unknown values are rejected, not invented.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd

from . import schema


class PipelineError(Exception):
    """Raised when the input cannot be processed at all (missing file, wrong columns...)."""


@dataclass
class PipelineResult:
    clean: pd.DataFrame
    rejected: pd.DataFrame
    stats: dict = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Loading and inspection
# --------------------------------------------------------------------------- #

def load_csv(path: str | Path) -> pd.DataFrame:
    """Read the CSV as text and check that the expected columns exist."""
    path = Path(path)
    if not path.is_file():
        raise PipelineError(f"Input file not found: {path}")
    try:
        df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8")
    except pd.errors.EmptyDataError as exc:
        raise PipelineError(f"Input file is empty: {path}") from exc
    except UnicodeDecodeError as exc:
        raise PipelineError(f"Input file is not valid UTF-8: {path}") from exc

    missing = [c for c in schema.REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise PipelineError(f"Missing required column(s): {', '.join(missing)}")
    return df[schema.REQUIRED_COLUMNS]


def inspect(df: pd.DataFrame) -> dict:
    """Describe the raw data before any change is made."""
    stripped = df.apply(lambda col: col.str.strip())
    return {
        "rows": int(len(df)),
        "columns": list(df.columns),
        "empty_values_per_column": {c: int((stripped[c] == "").sum()) for c in df.columns},
        "exact_duplicate_rows": int(stripped.duplicated().sum()),
        "repeated_ticket_ids": int(stripped["ticket_id"].duplicated().sum()),
    }


# --------------------------------------------------------------------------- #
# Value-level helpers (small and pure, so they are easy to test)
# --------------------------------------------------------------------------- #

def normalize_text(value: str | None) -> str | None:
    """Trim whitespace, collapse inner spaces, and turn empty strings into None."""
    if value is None:
        return None
    cleaned = " ".join(str(value).split())
    return cleaned or None


def map_value(value: str | None, mapping: dict[str, str]) -> tuple[str | None, bool]:
    """Map a free-text value to its canonical form.

    Returns (canonical_value, is_valid). Missing values are valid here;
    whether they are allowed is decided separately.
    """
    if value is None:
        return None, True
    canonical = mapping.get(value.lower())
    return canonical, canonical is not None


def parse_date(value: str | None) -> datetime | None:
    """Parse a date using the accepted formats; return None if it is not a real date."""
    if value is None:
        return None
    for fmt in schema.DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def parse_number(value: str | None) -> tuple[float | None, bool]:
    """Convert text to float. Returns (number, is_valid); missing is valid."""
    if value is None:
        return None, True
    try:
        return float(value), True
    except ValueError:
        return None, False


# --------------------------------------------------------------------------- #
# Row validation and the full cleaning process
# --------------------------------------------------------------------------- #

def validate_row(row: dict) -> tuple[dict, list[str]]:
    """Return the typed/normalized row and the list of problems found in it."""
    issues: list[str] = []
    out = {key: normalize_text(row.get(key)) for key in schema.REQUIRED_COLUMNS}

    for column in schema.MANDATORY_VALUES:
        if out[column] is None:
            issues.append(f"missing_{column}")

    for column, mapping in (
        ("language", schema.LANGUAGE_MAP),
        ("channel", schema.CHANNEL_MAP),
        ("category", schema.CATEGORY_MAP),
        ("priority", schema.PRIORITY_MAP),
    ):
        canonical, ok = map_value(out[column], mapping)
        if not ok:
            issues.append(f"invalid_{column}")
        out[column] = canonical

    if out["created_at"] is not None:
        parsed = parse_date(out["created_at"])
        if parsed is None:
            issues.append("invalid_created_at")
        out["created_at"] = parsed.date().isoformat() if parsed else None

    hours, ok = parse_number(out["resolution_hours"])
    if not ok:
        issues.append("non_numeric_resolution_hours")
    elif hours is not None and hours < 0:
        issues.append("negative_resolution_hours")
    out["resolution_hours"] = hours

    score, ok = parse_number(out["satisfaction_score"])
    low, high = schema.SATISFACTION_RANGE
    if not ok:
        issues.append("non_numeric_satisfaction_score")
    elif score is not None and (score != int(score) or not low <= score <= high):
        issues.append("satisfaction_score_out_of_range")
    out["satisfaction_score"] = score

    if out["country"] is not None:
        out["country"] = out["country"].title()

    return out, issues


def clean(df: pd.DataFrame) -> PipelineResult:
    """Run the full cleaning process on a raw (all-text) DataFrame."""
    stripped = df.apply(lambda col: col.str.strip())

    # 1. Exact duplicates are the same record exported twice: drop silently, but count.
    exact_dup_mask = stripped.duplicated(keep="first")
    working = df.loc[~exact_dup_mask]  # keeps the original index for traceability

    # 2. A ticket_id that remains repeated now has different content in each copy.
    #    We cannot know which version is correct, so every copy goes to review.
    ids = stripped.loc[~exact_dup_mask, "ticket_id"]
    conflicting = ids.duplicated(keep=False) & (ids != "")

    # 3. Validate and normalize each row.
    clean_rows, rejected_rows = [], []
    for index, raw in working.iterrows():
        row, issues = validate_row(raw.to_dict())
        if conflicting[index]:
            issues.append("conflicting_ticket_id")

        if issues:
            rejected = raw.to_dict()
            rejected["source_row"] = index + 2  # line number in the CSV (header is line 1)
            rejected["rejection_reasons"] = ";".join(issues)
            rejected_rows.append(rejected)
        else:
            clean_rows.append(row)

    clean_df = pd.DataFrame(clean_rows, columns=schema.REQUIRED_COLUMNS)
    clean_df["satisfaction_score"] = clean_df["satisfaction_score"].astype("Int64")
    clean_df["resolution_hours"] = clean_df["resolution_hours"].astype("Float64")
    clean_df = clean_df.sort_values("ticket_id").reset_index(drop=True)

    rejected_df = pd.DataFrame(
        rejected_rows,
        columns=["source_row", *schema.REQUIRED_COLUMNS, "rejection_reasons"],
    )

    reason_counts: dict[str, int] = {}
    for reasons in rejected_df["rejection_reasons"]:
        for reason in reasons.split(";"):
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

    stats = {
        "input_rows": int(len(df)),
        "exact_duplicates_removed": int(exact_dup_mask.sum()),
        "clean_rows": int(len(clean_df)),
        "rejected_rows": int(len(rejected_df)),
        "rejection_reasons": dict(sorted(reason_counts.items())),
    }
    return PipelineResult(clean=clean_df, rejected=rejected_df, stats=stats)
