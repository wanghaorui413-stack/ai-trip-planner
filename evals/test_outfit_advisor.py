"""Offline checks for city and POI outfit advice payloads.

Run with:
    python evals/test_outfit_advisor.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from outfit_advisor import get_city_outfit, get_poi_outfit


def assert_has_keys(payload: dict, keys: set[str]) -> None:
    missing = keys - set(payload)
    assert not missing, f"Missing keys: {sorted(missing)}"
    for key in keys:
        assert payload[key], f"Empty value for {key}"


def test_city_outfit() -> None:
    outfit = get_city_outfit("上海")
    assert_has_keys(
        outfit,
        {"style_name", "description", "outfit_formula", "palette", "essentials", "note"},
    )
    assert isinstance(outfit["palette"], list)
    assert isinstance(outfit["essentials"], list)


def test_city_alias_falls_back_to_profile() -> None:
    outfit = get_city_outfit("Shanghai")
    assert outfit["style_name"] == get_city_outfit("上海")["style_name"]


def test_poi_outfit_payload() -> None:
    outfit = get_poi_outfit("杭州", {"name": "西湖", "category": "nature", "tags": ["湖", "城市漫步"]})
    assert_has_keys(outfit, {"style", "clothing", "shoes", "extras", "tip"})
    assert isinstance(outfit["extras"], list)


def test_unknown_destination_uses_default_city_style() -> None:
    outfit = get_city_outfit("未知城市")
    assert outfit["style_name"] == "轻松城市探索"


if __name__ == "__main__":
    for check in (
        test_city_outfit,
        test_city_alias_falls_back_to_profile,
        test_poi_outfit_payload,
        test_unknown_destination_uses_default_city_style,
    ):
        check()
    print("Outfit advisor checks passed.")

