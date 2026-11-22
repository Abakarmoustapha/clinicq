import pytest
from rest_framework import serializers

from .serializers import clean_name, clean_phone


@pytest.mark.parametrize(
    "value",
    [
        "abc",
        "123",
        "00000000",
        "11111111",
        "12345678",
        "87654321",
        "+2356612345678901",
        "6612 34 5x",
    ],
)
def test_bad_phone_numbers_are_rejected(value):
    with pytest.raises(serializers.ValidationError):
        clean_phone(value)


@pytest.mark.parametrize(
    "value, expected",
    [
        ("+235 66 12 34 56", "+23566123456"),
        ("66-12-34-56", "66123456"),
        ("0612345678", "0612345678"),
    ],
)
def test_good_phone_numbers_are_cleaned(value, expected):
    assert clean_phone(value) == expected


@pytest.mark.parametrize(
    "value", ["", "x", "123", "Amina123", "!!!", "<script>", "12 34"]
)
def test_bad_names_are_rejected(value):
    with pytest.raises(serializers.ValidationError):
        clean_name(value)


# The Arabic name is written with escape codes so this file stays plain ASCII.
ARABIC_NAME = "\u0623\u0645\u064a\u0646\u0629 \u0645\u062d\u0645\u062f"


@pytest.mark.parametrize(
    "value, expected",
    [
        ("Amina", "Amina"),
        ("Jean-Pierre O'Neil", "Jean-Pierre O'Neil"),
        (ARABIC_NAME, ARABIC_NAME),
        ("  Amina   Ali  ", "Amina Ali"),
    ],
)
def test_good_names_are_accepted(value, expected):
    assert clean_name(value) == expected