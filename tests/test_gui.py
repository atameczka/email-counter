"""Tests for gui.py helpers. Skipped when tkinter is unavailable (headless CI)."""

from datetime import date

import pytest

try:
    import gui
except ModuleNotFoundError:  # tkinter not installed, e.g. headless CI runners
    gui = None

pytestmark = pytest.mark.skipif(gui is None, reason="tkinter not available")


def test_default_date_range_mid_month():
    assert gui.default_date_range(date(2024, 6, 15)) == (date(2024, 6, 1), date(2024, 6, 15))


def test_default_date_range_first_of_month():
    assert gui.default_date_range(date(2024, 6, 1)) == (date(2024, 6, 1), date(2024, 6, 1))


def test_default_date_range_defaults_to_today():
    first, today = gui.default_date_range()
    assert first.day == 1
    assert today == date.today()
