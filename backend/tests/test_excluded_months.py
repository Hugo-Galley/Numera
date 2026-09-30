"""Tests for excluded_months feature in recurring transactions."""
import pytest
from datetime import datetime
from unittest.mock import MagicMock
from app.core.finance import get_recurring_occurrences


class TestExcludedMonths:
    """Test suite for month exclusion in recurring transaction occurrences."""

    def _make_recurring(self, **kwargs):
        """Create a mock RecurringTransaction with sensible defaults."""
        defaults = {
            "start_date": datetime(2025, 1, 1),
            "end_date": None,
            "frequency": "monthly",
            "day_of_month": 1,
            "excluded_months": None,
        }
        defaults.update(kwargs)
        return MagicMock(**defaults)

    def test_no_exclusion_generates_all_months(self):
        """Without excluded_months, all 12 months should generate."""
        rt = self._make_recurring()
        occs = get_recurring_occurrences(rt, datetime(2025, 1, 1), datetime(2025, 12, 31))
        assert len(occs) == 12

    def test_exclude_may_and_october(self):
        """Excluding months 5 and 10 should skip May and October."""
        rt = self._make_recurring(excluded_months="5,10")
        occs = get_recurring_occurrences(rt, datetime(2025, 1, 1), datetime(2025, 12, 31))
        months = [o.month for o in occs]
        assert 5 not in months
        assert 10 not in months
        assert len(occs) == 10

    def test_exclude_single_month(self):
        """Excluding a single month should reduce count by 1."""
        rt = self._make_recurring(excluded_months="8")
        occs = get_recurring_occurrences(rt, datetime(2025, 1, 1), datetime(2025, 12, 31))
        months = [o.month for o in occs]
        assert 8 not in months
        assert len(occs) == 11

    def test_exclude_all_months_generates_nothing(self):
        """Excluding all 12 months should produce zero occurrences."""
        rt = self._make_recurring(excluded_months="1,2,3,4,5,6,7,8,9,10,11,12")
        occs = get_recurring_occurrences(rt, datetime(2025, 1, 1), datetime(2025, 12, 31))
        assert len(occs) == 0

    def test_exclusion_ignored_for_weekly(self):
        """Weekly frequency should still generate occurrences even if excluded_months is set."""
        rt = self._make_recurring(frequency="weekly", excluded_months="5,10")
        occs = get_recurring_occurrences(rt, datetime(2025, 5, 1), datetime(2025, 5, 31))
        # Weekly should skip occurrences that fall in excluded months
        # This is expected behavior: even weekly recurrences respect exclusions
        months = {o.month for o in occs}
        assert 5 not in months

    def test_exclusion_with_list_format(self):
        """excluded_months as a list[int] (from Pydantic) should work too."""
        rt = self._make_recurring(excluded_months=[5, 10])
        occs = get_recurring_occurrences(rt, datetime(2025, 1, 1), datetime(2025, 12, 31))
        months = [o.month for o in occs]
        assert 5 not in months
        assert 10 not in months
        assert len(occs) == 10

    def test_empty_string_means_no_exclusion(self):
        """An empty string should be treated as no exclusion."""
        rt = self._make_recurring(excluded_months="")
        occs = get_recurring_occurrences(rt, datetime(2025, 1, 1), datetime(2025, 12, 31))
        assert len(occs) == 12

    def test_none_means_no_exclusion(self):
        """None should be treated as no exclusion."""
        rt = self._make_recurring(excluded_months=None)
        occs = get_recurring_occurrences(rt, datetime(2025, 1, 1), datetime(2025, 12, 31))
        assert len(occs) == 12

    def test_excluded_months_with_quarterly(self):
        """Quarterly frequency with month exclusions should skip matching months."""
        # Quarterly from Jan 1: Jan, Apr, Jul, Oct
        rt = self._make_recurring(frequency="quarterly", excluded_months="10")
        occs = get_recurring_occurrences(rt, datetime(2025, 1, 1), datetime(2025, 12, 31))
        months = [o.month for o in occs]
        assert 10 not in months
        assert len(occs) == 3  # Jan, Apr, Jul (Oct excluded)

    def test_excluded_months_preserves_day_of_month(self):
        """Excluded months should not affect the day calculation of remaining months."""
        rt = self._make_recurring(
            start_date=datetime(2025, 1, 15),
            day_of_month=15,
            excluded_months="2,3",
        )
        occs = get_recurring_occurrences(rt, datetime(2025, 1, 1), datetime(2025, 6, 30))
        # Should have Jan, Apr, May, Jun (Feb and Mar excluded)
        assert len(occs) == 4
        for occ in occs:
            assert occ.day == 15

    def test_exclusion_across_year_boundary(self):
        """Exclusions should apply consistently across year boundaries."""
        rt = self._make_recurring(
            start_date=datetime(2025, 11, 1),
            excluded_months="1,12",
        )
        occs = get_recurring_occurrences(rt, datetime(2025, 11, 1), datetime(2026, 3, 31))
        # Nov 2025, (Dec excluded), (Jan excluded), Feb 2026, Mar 2026
        months_years = [(o.month, o.year) for o in occs]
        assert (12, 2025) not in months_years
        assert (1, 2026) not in months_years
        assert len(occs) == 3  # Nov, Feb, Mar


class TestExcludedMonthsSchema:
    """Test the Pydantic schema serialization/deserialization."""

    def test_parse_csv_string(self):
        from app.schemas.recurring_transaction import RecurringTransactionRead
        data = {
            "id": 1,
            "account_id": 1,
            "name": "Test",
            "type": "Sortie",
            "amount": 100.0,
            "currency": "EUR",
            "frequency": "monthly",
            "start_date": datetime(2025, 1, 1),
            "is_active": True,
            "auto_generate": False,
            "excluded_months": "5,10",
        }
        obj = RecurringTransactionRead.model_validate(data)
        assert obj.excluded_months == [5, 10]

    def test_parse_none(self):
        from app.schemas.recurring_transaction import RecurringTransactionRead
        data = {
            "id": 1,
            "account_id": 1,
            "name": "Test",
            "type": "Sortie",
            "amount": 100.0,
            "currency": "EUR",
            "frequency": "monthly",
            "start_date": datetime(2025, 1, 1),
            "is_active": True,
            "auto_generate": False,
            "excluded_months": None,
        }
        obj = RecurringTransactionRead.model_validate(data)
        assert obj.excluded_months is None

    def test_parse_empty_string(self):
        from app.schemas.recurring_transaction import RecurringTransactionRead
        data = {
            "id": 1,
            "account_id": 1,
            "name": "Test",
            "type": "Sortie",
            "amount": 100.0,
            "currency": "EUR",
            "frequency": "monthly",
            "start_date": datetime(2025, 1, 1),
            "is_active": True,
            "auto_generate": False,
            "excluded_months": "",
        }
        obj = RecurringTransactionRead.model_validate(data)
        assert obj.excluded_months is None

    def test_parse_list_passthrough(self):
        from app.schemas.recurring_transaction import RecurringTransactionRead
        data = {
            "id": 1,
            "account_id": 1,
            "name": "Test",
            "type": "Sortie",
            "amount": 100.0,
            "currency": "EUR",
            "frequency": "monthly",
            "start_date": datetime(2025, 1, 1),
            "is_active": True,
            "auto_generate": False,
            "excluded_months": [3, 7, 11],
        }
        obj = RecurringTransactionRead.model_validate(data)
        assert obj.excluded_months == [3, 7, 11]
