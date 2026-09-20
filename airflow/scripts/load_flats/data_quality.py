from __future__ import annotations

from typing import Any

REQUIRED_FIELDS = {
    "id",
    "slug",
    "name",
    "price",
    "livingSpace",
    "rooms",
    "address",
    "latitude",
    "longitude",
}


class DataQualityError(ValueError):
    """Raised when a scraped record does not match the expected schema."""


def validate_schema(record: dict[str, Any]) -> dict[str, Any]:
    """Validate a single scraped listing before it is written to Postgres."""
    if not isinstance(record, dict):
        raise DataQualityError(f"Record must be an object, got {type(record).__name__}")

    missing = sorted(REQUIRED_FIELDS - set(record.keys()))
    if missing:
        raise DataQualityError(f"Record is missing required fields: {missing}")

    for field in ("id", "slug", "name", "price", "livingSpace", "rooms", "address"):
        value = record[field]
        if not isinstance(value, str) or not value.strip():
            raise DataQualityError(f"Field '{field}' must be a non-empty string")

    for field in ("latitude", "longitude"):
        value = record[field]
        if isinstance(value, str):
            try:
                float(value)
            except ValueError as exc:
                raise DataQualityError(f"Field '{field}' must be numeric") from exc
        elif not isinstance(value, (int, float)) or isinstance(value, bool):
            raise DataQualityError(f"Field '{field}' must be numeric")

    return record
