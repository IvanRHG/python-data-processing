"""Build the summary report and export all outputs."""

from __future__ import annotations

import json
from pathlib import Path

from .cleaning import PipelineResult


def summarize(result: PipelineResult, inspection: dict) -> dict:
    """Collect the figures shown in the report."""
    df = result.clean
    by_category = (
        df.groupby("category")["resolution_hours"].mean().round(1).astype(float).to_dict()
    )
    by_channel = (
        df.groupby("channel")["satisfaction_score"].mean().round(2).astype(float).to_dict()
    )
    return {
        "inspection": inspection,
        "cleaning": result.stats,
        "clean_data": {
            "rows_per_language": df["language"].value_counts().sort_index().to_dict(),
            "rows_per_category": df["category"].value_counts().sort_index().to_dict(),
            "missing_optional_values": {
                c: int(n) for c, n in df.isna().sum().items() if n > 0
            },
            "mean_resolution_hours_by_category": by_category,
            "mean_satisfaction_by_channel": by_channel,
        },
    }


def _table(mapping: dict, key_title: str, value_title: str) -> str:
    lines = [f"| {key_title} | {value_title} |", "|---|---:|"]
    lines += [f"| {k} | {v} |" for k, v in mapping.items()]
    return "\n".join(lines)


def to_markdown(summary: dict) -> str:
    """Render the summary as a short, readable Markdown report."""
    ins, cln, data = summary["inspection"], summary["cleaning"], summary["clean_data"]
    empty_cols = {c: n for c, n in ins["empty_values_per_column"].items() if n}
    parts = [
        "# Data Cleaning Report — Support Tickets (synthetic data)",
        "",
        "## 1. Raw data inspection",
        f"- Rows: **{ins['rows']}**, columns: **{len(ins['columns'])}**",
        f"- Exact duplicate rows: **{ins['exact_duplicate_rows']}**",
        f"- Repeated `ticket_id` values (including exact duplicates): **{ins['repeated_ticket_ids']}**",
        "",
        "Empty values per column (raw):",
        "",
        _table(empty_cols, "Column", "Empty values"),
        "",
        "## 2. Cleaning result",
        f"- Input rows: **{cln['input_rows']}**",
        f"- Exact duplicates removed: **{cln['exact_duplicates_removed']}**",
        f"- Rejected rows (sent to `rejected_rows.csv` for review): **{cln['rejected_rows']}**",
        f"- Clean rows: **{cln['clean_rows']}**",
        "",
        "Rejection reasons (a row can have more than one):",
        "",
        _table(cln["rejection_reasons"], "Reason", "Rows"),
        "",
        "## 3. Clean data overview",
        "",
        _table(data["rows_per_language"], "Language", "Tickets"),
        "",
        _table(data["rows_per_category"], "Category", "Tickets"),
        "",
        "Missing optional values kept as empty:",
        "",
        _table(data["missing_optional_values"], "Column", "Empty values"),
        "",
        _table(data["mean_resolution_hours_by_category"], "Category", "Mean resolution hours"),
        "",
        _table(data["mean_satisfaction_by_channel"], "Channel", "Mean satisfaction (1–5)"),
        "",
        "_The data is synthetic. These figures describe the sample, not any real business._",
        "",
    ]
    return "\n".join(parts)


def export(result: PipelineResult, summary: dict, output_dir: str | Path) -> list[Path]:
    """Write clean data, rejected rows, and the report. Returns the written paths."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "clean": output_dir / "support_tickets_clean.csv",
        "rejected": output_dir / "rejected_rows.csv",
        "json": output_dir / "summary_report.json",
        "md": output_dir / "summary_report.md",
    }
    result.clean.to_csv(paths["clean"], index=False, encoding="utf-8", lineterminator="\n")
    result.rejected.to_csv(paths["rejected"], index=False, encoding="utf-8", lineterminator="\n")
    paths["json"].write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    paths["md"].write_text(to_markdown(summary), encoding="utf-8", newline="\n")
    return list(paths.values())
