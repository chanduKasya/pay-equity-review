"""
metrics.py - the pay calculations. Both the generator and the detector
use these same functions, so there is one definition of each formula.
"""

import config
import date_utils


def build_band_lookup(bands):
    """(role, level, location) -> list of that job's bands (one per year)."""
    lookup = {}
    for band in bands:
        key = (band["role_id"], band["level_id"], band["location_id"])
        if key not in lookup:
            lookup[key] = []
        lookup[key].append(band)
    return lookup


def build_rate_lookup(fx_rates):
    """(currency, year) -> units of that currency per 1 USD."""
    lookup = {}
    for fx in fx_rates:
        lookup[(fx["currency_code"], int(fx["rate_year"]))] = float(fx["units_per_usd"])
    return lookup


def find_band_for_date(role_id, level_id, location_id, date_text, band_lookup):
    """Return the band whose effective dates cover date_text, or None."""
    candidates = band_lookup.get((role_id, level_id, location_id), [])
    for band in candidates:
        if band["effective_from"] <= date_text <= band["effective_to"]:
            return band
    return None


def convert_currency(amount, from_currency, to_currency, year, rate_lookup):
    """Convert through USD using that year's rates."""
    if from_currency == to_currency:
        return float(amount)
    amount_usd = float(amount) / rate_lookup[(from_currency, year)]
    return amount_usd * rate_lookup[(to_currency, year)]


def normalised_salary(record, band, rate_lookup):
    """Full-time salary in the band's currency.
    Step 1: divide by FTE. Step 2: convert the currency."""
    full_time = float(record["annual_amount"]) / float(record["fte"])
    year = date_utils.year_of(record["effective_date"])
    return convert_currency(full_time, record["currency_code"],
                            band["currency_code"], year, rate_lookup)


def compa_ratio(record, band, rate_lookup):
    """Normalised salary divided by the band midpoint."""
    salary = normalised_salary(record, band, rate_lookup)
    return round(salary / float(band["band_mid"]), 4)


def band_position(record, band, rate_lookup):
    """0.0 = at band minimum, 1.0 = at band maximum."""
    salary = normalised_salary(record, band, rate_lookup)
    width = float(band["band_max"]) - float(band["band_min"])
    return round((salary - float(band["band_min"])) / width, 4)


def expected_compa_ratio(level_tenure_months, rating, premium_pct):
    """The compa-ratio that the documented job-related factors predict."""
    years = level_tenure_months / 12.0
    if years > config.POLICY_TENURE_CAP_YEARS:
        years = config.POLICY_TENURE_CAP_YEARS
    expected = config.POLICY_BASE_RATIO
    expected = expected + config.POLICY_PER_TENURE_YEAR * years
    expected = expected + config.POLICY_PER_RATING_POINT * (rating - config.POLICY_NEUTRAL_RATING)
    expected = expected + premium_pct / 100.0
    if expected < config.POLICY_RATIO_FLOOR:
        expected = config.POLICY_RATIO_FLOOR
    if expected > config.POLICY_RATIO_CEILING:
        expected = config.POLICY_RATIO_CEILING
    return round(expected, 4)


def median(values):
    ordered = sorted(values)
    count = len(ordered)
    middle = count // 2
    if count % 2 == 1:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def round_to_100(value):
    return int(round(value / config.BAND_ROUND_TO)) * config.BAND_ROUND_TO
