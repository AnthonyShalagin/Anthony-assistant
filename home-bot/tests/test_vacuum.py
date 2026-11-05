"""Tests for vacuum.py's plain-word parsing and room matching (no network)."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from vacuum import match_rooms, parse_mode  # noqa: E402

ROOMS = {"Kitchen": 3, "Living Room": 0, "Bathroom": 5}


@pytest.mark.parametrize("word,expected", [
    ("vacuum", "VACUUM"),
    ("just vacuum", None),
    ("mop", "VACUUM_AND_MOP"),
    ("both", "VACUUM_AND_MOP"),
    ("Mop after", "MOP_AFTER_VACUUM"),
    ("mop-only", "MOP"),
])
def test_parse_mode(word, expected):
    if expected is None:
        with pytest.raises(ValueError):
            parse_mode(word)
    else:
        assert parse_mode(word) == expected


def test_match_rooms_case_and_spaces():
    assert match_rooms(["kitchen", "living room"], ROOMS) == [3, 0]


def test_match_rooms_unknown_lists_real_rooms():
    with pytest.raises(ValueError) as e:
        match_rooms(["garage"], ROOMS)
    assert "garage" in str(e.value) and "Kitchen" in str(e.value)
