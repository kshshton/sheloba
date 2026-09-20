import pytest

from scripts.load_flats.data_quality import DataQualityError, validate_schema


def test_validate_schema_accepts_expected_record():
    record = {
        "id": "123",
        "slug": "riverside-loft",
        "name": "Riverside Loft",
        "price": "$1,200",
        "livingSpace": "72",
        "rooms": "2",
        "address": "Main Street 1",
        "latitude": 52.52,
        "longitude": 13.405,
    }

    assert validate_schema(record) == record


def test_validate_schema_rejects_missing_or_invalid_fields():
    with pytest.raises(DataQualityError):
        validate_schema(
            {
                "id": "123",
                "slug": "riverside-loft",
                "name": "Riverside Loft",
                "price": "$1,200",
                "livingSpace": "72",
                "rooms": "2",
                "address": "Main Street 1",
                "latitude": "bad-latitude",
                "longitude": 13.405,
            }
        )
