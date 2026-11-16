"""Expected structure of the support-ticket dataset and its allowed values.

Keeping these rules in one place makes the cleaning logic easy to audit:
if a rule changes, it changes here and nowhere else.
"""

from __future__ import annotations

REQUIRED_COLUMNS = [
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

# A row without any of these values cannot be used and is rejected.
MANDATORY_VALUES = ["ticket_id", "created_at", "language", "category"]

# Accepted date formats, tried in order.
DATE_FORMATS = ["%Y-%m-%d", "%Y/%m/%d"]

# Synonym maps: lower-cased, trimmed input -> canonical value.
LANGUAGE_MAP = {
    "es": "es", "spanish": "es", "español": "es", "espanol": "es",
    "en": "en", "english": "en", "inglés": "en", "ingles": "en",
    "fr": "fr", "french": "fr", "français": "fr", "francais": "fr", "francés": "fr", "frances": "fr",
}
CHANNEL_MAP = {
    "email": "email", "e-mail": "email",
    "chat": "chat", "live chat": "chat",
    "phone": "phone", "telephone": "phone",
}
CATEGORY_MAP = {
    "billing": "billing",
    "technical": "technical", "tech support": "technical",
    "account": "account", "account access": "account",
    "delivery": "delivery", "shipping": "delivery",
}
PRIORITY_MAP = {"low": "low", "medium": "medium", "high": "high"}

SATISFACTION_RANGE = (1, 5)
