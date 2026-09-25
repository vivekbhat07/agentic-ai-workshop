"""UNIT tests: tools are pure functions -> fast, deterministic, no LLM."""
import pytest

from travel_agent.tools import calculator, convert_currency, get_weather


def test_get_weather_known_city_is_case_insensitive() -> None:
    assert get_weather("PARIS") == {"city": "Paris", "temp_c": 18, "condition": "cloudy"}


def test_get_weather_unknown_city_raises() -> None:
    with pytest.raises(ValueError, match="No weather data"):
        get_weather("Atlantis")


@pytest.mark.parametrize(
    ("amount", "src", "dst", "expected"),
    [(100, "USD", "USD", 100.0), (100, "EUR", "USD", 108.0), (0, "USD", "INR", 0.0)],
)
def test_convert_currency(amount: float, src: str, dst: str, expected: float) -> None:
    assert convert_currency(amount, src, dst) == expected


def test_convert_currency_rejects_negative_amount() -> None:
    with pytest.raises(ValueError):
        convert_currency(-5, "USD", "EUR")


def test_calculator_basic_math() -> None:
    assert calculator("(2 + 3) * 4") == 20.0


def test_calculator_blocks_code_injection() -> None:
    with pytest.raises(ValueError):
        calculator("__import__('os').system('rm -rf /')")
