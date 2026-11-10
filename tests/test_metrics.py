"""Hand-calculated examples for every pay formula."""

import date_utils
import metrics

BAND = {
    "band_id": "BAND-SWE-L3-NYC-2026", "role_id": "SWE", "level_id": "L3", "location_id": "NYC",
    "currency_code": "USD", "band_min": "80000", "band_mid": "100000", "band_max": "120000",
    "effective_from": "2026-01-01", "effective_to": "2026-12-31",
}
OLD_BAND = dict(BAND, band_id="BAND-SWE-L3-NYC-2025", effective_from="2025-01-01", effective_to="2025-12-31")
RATES = {("USD", 2026): 1.0, ("INR", 2026): 86.0, ("GBP", 2026): 0.77}


def record(amount, fte="1.00", currency="USD", date="2026-04-01"):
    return {"annual_amount": str(amount), "fte": fte, "currency_code": currency, "effective_date": date}


def test_compa_ratio_at_midpoint_is_one():
    assert metrics.compa_ratio(record(100000), BAND, RATES) == 1.0


def test_compa_ratio_divides_by_fte():
    # Half-time on 45,000 is 90,000 full-time, so the ratio is 0.90 and not 0.45.
    assert metrics.compa_ratio(record(45000, fte="0.50"), BAND, RATES) == 0.9


def test_compa_ratio_converts_currency():
    # 8,600,000 INR at 86 per USD is 100,000 USD.
    assert metrics.compa_ratio(record(8600000, currency="INR"), BAND, RATES) == 1.0


def test_fte_and_currency_together():
    # 0.8 FTE paid 61,600 GBP -> 77,000 GBP full-time -> 100,000 USD.
    assert metrics.compa_ratio(record(61600, fte="0.80", currency="GBP"), BAND, RATES) == 1.0


def test_band_position_boundaries():
    assert metrics.band_position(record(80000), BAND, RATES) == 0.0
    assert metrics.band_position(record(100000), BAND, RATES) == 0.5
    assert metrics.band_position(record(120000), BAND, RATES) == 1.0
    assert metrics.band_position(record(70000), BAND, RATES) < 0     # below the band


def test_band_is_chosen_by_effective_date():
    lookup = metrics.build_band_lookup([OLD_BAND, BAND])
    assert metrics.find_band_for_date("SWE", "L3", "NYC", "2025-12-31", lookup)["band_id"] == "BAND-SWE-L3-NYC-2025"
    assert metrics.find_band_for_date("SWE", "L3", "NYC", "2026-01-01", lookup)["band_id"] == "BAND-SWE-L3-NYC-2026"
    assert metrics.find_band_for_date("SWE", "L3", "NYC", "2027-01-01", lookup) is None


def test_expected_ratio_follows_the_policy():
    assert metrics.expected_compa_ratio(0, 3, 0) == 0.90          # base
    assert metrics.expected_compa_ratio(24, 3, 0) == 0.94         # +0.02 per year
    assert metrics.expected_compa_ratio(120, 3, 0) == 1.00        # tenure capped at 5 years
    assert metrics.expected_compa_ratio(0, 5, 0) == 0.96          # +0.03 per rating point
    assert metrics.expected_compa_ratio(0, 1, 0) == 0.84
    assert metrics.expected_compa_ratio(0, 3, 10) == 1.00         # documented premium
    assert metrics.expected_compa_ratio(120, 5, 20) == 1.26


def test_months_between_counts_whole_months():
    assert date_utils.months_between("2024-01-15", "2024-03-14") == 1
    assert date_utils.months_between("2024-01-15", "2024-03-15") == 2
    assert date_utils.months_between("2023-12-01", "2026-12-01") == 36
    assert date_utils.months_between("2026-05-01", "2026-01-01") == 0


def test_median():
    assert metrics.median([3, 1, 2]) == 2
    assert metrics.median([4, 1, 2, 3]) == 2.5
