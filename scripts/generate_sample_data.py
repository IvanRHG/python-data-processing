"""Generate the synthetic raw dataset used by this project.

The data describes fictional customer-support tickets. Every value is
randomly generated from a fixed seed, so running this script always
produces the same file. No real people, companies, or tickets are involved.

Data-quality problems are injected on purpose (missing values, duplicates,
inconsistent spelling, invalid dates and numbers) so that the cleaning
pipeline has realistic work to do.

Usage:
    python scripts/generate_sample_data.py
"""

from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

SEED = 2026
N_CLEAN_ROWS = 110
OUTPUT = Path(__file__).resolve().parents[1] / "data" / "raw" / "support_tickets_raw.csv"

COLUMNS = [
    "ticket_id",
    "created_at",
    "language",
    "country",
    "channel",
    "category",
    "priority",
    "resolution_hours",
    "satisfaction_score",
    "agent_id",
]

# Each language appears in several spellings to simulate manual data entry.
LANGUAGE_VARIANTS = {
    "es": ["es", "ES", "Spanish", "español", " Español "],
    "en": ["en", "EN", "English", "english ", "Inglés"],
    "fr": ["fr", "FR", "French", "français", "Francés"],
}
COUNTRIES = {
    "es": ["Colombia", "Mexico", "Spain", "Argentina"],
    "en": ["United States", "Canada", "United Kingdom"],
    "fr": ["France", "Canada", "Belgium"],
}
CHANNEL_VARIANTS = {
    "email": ["email", "Email", "E-mail", " EMAIL"],
    "chat": ["chat", "Chat", "live chat", "CHAT "],
    "phone": ["phone", "Phone", "telephone", "PHONE"],
}
CATEGORY_VARIANTS = {
    "billing": ["billing", "Billing", "BILLING"],
    "technical": ["technical", "Technical", "tech support"],
    "account": ["account", "Account", "account access"],
    "delivery": ["delivery", "Delivery", "shipping"],
}
PRIORITIES = ["low", "medium", "high", "Low", "Medium", "HIGH"]


def random_row(rng: random.Random, ticket_number: int) -> dict[str, str]:
    """Build one plausible (but messy) ticket row."""
    lang = rng.choice(list(LANGUAGE_VARIANTS))
    created = date(2026, 1, 1) + timedelta(days=rng.randint(0, 180))
    # Most dates use ISO format; some use slashes, which the pipeline accepts.
    created_text = created.isoformat() if rng.random() < 0.85 else created.strftime("%Y/%m/%d")
    channel = rng.choice(list(CHANNEL_VARIANTS))
    category = rng.choice(list(CATEGORY_VARIANTS))
    return {
        "ticket_id": f"TCK-{ticket_number:04d}",
        "created_at": created_text,
        "language": rng.choice(LANGUAGE_VARIANTS[lang]),
        "country": rng.choice(COUNTRIES[lang]),
        "channel": rng.choice(CHANNEL_VARIANTS[channel]),
        "category": rng.choice(CATEGORY_VARIANTS[category]),
        "priority": rng.choice(PRIORITIES),
        "resolution_hours": f"{rng.uniform(0.5, 72):.1f}",
        "satisfaction_score": str(rng.randint(1, 5)),
        "agent_id": f"AG-{rng.randint(1, 8):02d}",
    }


def inject_problems(rows: list[dict[str, str]], rng: random.Random) -> list[dict[str, str]]:
    """Add documented data-quality problems at fixed positions."""
    # Missing optional values (allowed: kept in the clean data as empty).
    rows[3]["satisfaction_score"] = ""
    rows[17]["satisfaction_score"] = ""
    rows[29]["resolution_hours"] = ""
    rows[41]["country"] = ""

    # Missing required values (must be rejected).
    rows[8]["category"] = ""
    rows[52]["created_at"] = ""

    # Invalid dates.
    rows[12]["created_at"] = "2026-13-02"
    rows[60]["created_at"] = "yesterday"

    # Invalid numbers.
    rows[21]["resolution_hours"] = "-4.0"
    rows[33]["resolution_hours"] = "N/A"
    rows[45]["satisfaction_score"] = "7"
    rows[70]["satisfaction_score"] = "three"

    # Values outside the allowed vocabulary.
    rows[25]["language"] = "Portuguese"
    rows[77]["category"] = "refund??"

    # Exact duplicates (same ticket submitted twice by the export tool).
    duplicates = [dict(rows[5]), dict(rows[50]), dict(rows[90])]

    # Conflicting duplicate: same ticket_id, different content.
    conflict = dict(rows[15])
    conflict["priority"] = "low" if rows[15]["priority"].lower() != "low" else "high"
    conflict["resolution_hours"] = "99.0"

    rows.extend(duplicates + [conflict])
    rng.shuffle(rows)
    return rows


def main() -> None:
    rng = random.Random(SEED)
    rows = [random_row(rng, i + 1) for i in range(N_CLEAN_ROWS)]
    rows = inject_problems(rows, rng)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {OUTPUT}")


if __name__ == "__main__":
    main()
