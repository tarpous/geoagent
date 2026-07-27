"""Unit allowlists and conversion helpers."""

from __future__ import annotations

from geoagent.schemas.quantity import Unit

ALLOWED_UNITS: frozenset[str] = frozenset(
    {"m", "km", "m2", "ha", "percent", "count", "deg", "dimensionless"}
)

_LENGTH_TO_M = {"m": 1.0, "km": 1000.0}
_AREA_TO_M2 = {"m2": 1.0, "ha": 10_000.0}


def assert_known_unit(unit: str) -> Unit:
    if unit not in ALLOWED_UNITS:
        raise ValueError(f"unsupported unit: {unit}")
    return unit  # type: ignore[return-value]


def convert_length(value: float, from_unit: str, to_unit: str) -> float:
    if from_unit not in _LENGTH_TO_M or to_unit not in _LENGTH_TO_M:
        raise ValueError(f"length conversion not supported for {from_unit} -> {to_unit}")
    meters = value * _LENGTH_TO_M[from_unit]
    return meters / _LENGTH_TO_M[to_unit]


def convert_area(value: float, from_unit: str, to_unit: str) -> float:
    if from_unit not in _AREA_TO_M2 or to_unit not in _AREA_TO_M2:
        raise ValueError(f"area conversion not supported for {from_unit} -> {to_unit}")
    square_meters = value * _AREA_TO_M2[from_unit]
    return square_meters / _AREA_TO_M2[to_unit]
