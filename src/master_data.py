"""
master_data.py - builds the parent (master) tables.

These tables are fixed lists, not random. Every other table refers to them,
so they must be created first.

Each function returns a list of dictionaries. One dictionary = one row.
"""

import config


def build_roles():
    """40 roles: 8 job families with 5 roles each."""
    # Each line is: role_id, role_name, job_family, base_mid_usd
    # base_mid_usd is the Level 1 midpoint salary in US dollars.
    raw = [
        ("SWE", "Software Engineer", "ENGINEERING", 70000),
        ("QAE", "QA Engineer", "ENGINEERING", 58000),
        ("DVO", "DevOps Engineer", "ENGINEERING", 72000),
        ("DTE", "Data Engineer", "ENGINEERING", 74000),
        ("SEC", "Security Engineer", "ENGINEERING", 76000),
        ("DSC", "Data Scientist", "DATA", 78000),
        ("DAN", "Data Analyst", "DATA", 60000),
        ("MLE", "Machine Learning Engineer", "DATA", 82000),
        ("BIA", "BI Analyst", "DATA", 58000),
        ("RSC", "Research Scientist", "DATA", 85000),
        ("PMG", "Product Manager", "PRODUCT", 80000),
        ("PDS", "Product Designer", "PRODUCT", 68000),
        ("UXR", "UX Researcher", "PRODUCT", 66000),
        ("TPM", "Technical Program Manager", "PRODUCT", 78000),
        ("PAN", "Product Analyst", "PRODUCT", 62000),
        ("AEX", "Account Executive", "SALES", 60000),
        ("SDR", "Sales Development Representative", "SALES", 45000),
        ("SEN", "Sales Engineer", "SALES", 70000),
        ("AMG", "Account Manager", "SALES", 58000),
        ("SOP", "Sales Operations Analyst", "SALES", 55000),
        ("MKM", "Marketing Manager", "MARKETING", 62000),
        ("CNT", "Content Strategist", "MARKETING", 52000),
        ("GRW", "Growth Marketer", "MARKETING", 60000),
        ("BRD", "Brand Designer", "MARKETING", 54000),
        ("EVT", "Events Coordinator", "MARKETING", 46000),
        ("FAN", "Financial Analyst", "FINANCE", 60000),
        ("ACC", "Accountant", "FINANCE", 52000),
        ("PYS", "Payroll Specialist", "FINANCE", 48000),
        ("TAX", "Tax Analyst", "FINANCE", 58000),
        ("AUD", "Internal Auditor", "FINANCE", 60000),
        ("HRB", "HR Business Partner", "PEOPLE", 60000),
        ("REC", "Recruiter", "PEOPLE", 52000),
        ("CMP", "Compensation Analyst", "PEOPLE", 60000),
        ("LND", "Learning Specialist", "PEOPLE", 52000),
        ("HRO", "HR Operations Specialist", "PEOPLE", 46000),
        ("CSM", "Customer Success Manager", "OPERATIONS", 56000),
        ("SUP", "Support Specialist", "OPERATIONS", 42000),
        ("ITA", "IT Administrator", "OPERATIONS", 54000),
        ("PRC", "Procurement Specialist", "OPERATIONS", 52000),
        ("FAC", "Facilities Coordinator", "OPERATIONS", 42000),
    ]

    roles = []
    for item in raw:
        row = {
            "role_id": item[0],
            "role_name": item[1],
            "job_family": item[2],
            "base_mid_usd": item[3],
        }
        roles.append(row)
    return roles


def build_levels():
    """5 levels. A higher level multiplies the midpoint salary."""
    raw = [
        ("L1", "Associate", 1, 1.00),
        ("L2", "Intermediate", 2, 1.30),
        ("L3", "Senior", 3, 1.70),
        ("L4", "Lead", 4, 2.20),
        ("L5", "Principal", 5, 2.90),
    ]

    levels = []
    for item in raw:
        row = {
            "level_id": item[0],
            "level_name": item[1],
            "level_rank": item[2],
            "mid_multiplier": item[3],
        }
        levels.append(row)
    return levels


def build_locations():
    """8 locations in 5 currencies. geo_factor is the local pay level
    compared with the US baseline of 1.00."""
    raw = [
        ("BLR", "Bengaluru", "India", "INR", 0.30),
        ("HYD", "Hyderabad", "India", "INR", 0.28),
        ("NYC", "New York", "United States", "USD", 1.00),
        ("SFO", "San Francisco", "United States", "USD", 1.10),
        ("LON", "London", "United Kingdom", "GBP", 0.85),
        ("BER", "Berlin", "Germany", "EUR", 0.75),
        ("DUB", "Dublin", "Ireland", "EUR", 0.80),
        ("SGP", "Singapore", "Singapore", "SGD", 0.80),
    ]

    locations = []
    for item in raw:
        row = {
            "location_id": item[0],
            "city": item[1],
            "country": item[2],
            "currency_code": item[3],
            "geo_factor": item[4],
        }
        locations.append(row)
    return locations


def build_fx_rates():
    """Synthetic exchange rates: how many units of a currency equal 1 USD.
    These are made-up fixed values, not real market data."""
    # currency -> list of rates for 2024, 2025, 2026 (same order as BAND_YEARS)
    raw = {
        "USD": [1.00, 1.00, 1.00],
        "INR": [83.00, 84.50, 86.00],
        "GBP": [0.79, 0.78, 0.77],
        "EUR": [0.92, 0.93, 0.91],
        "SGD": [1.34, 1.33, 1.32],
    }

    fx_rates = []
    for currency_code in raw:
        rates = raw[currency_code]
        for i in range(len(config.BAND_YEARS)):
            row = {
                "currency_code": currency_code,
                "rate_year": config.BAND_YEARS[i],
                "units_per_usd": rates[i],
            }
            fx_rates.append(row)
    return fx_rates


def build_bands(roles, levels, locations, fx_rates):
    """One pay band for every role x level x location x year.
    40 x 5 x 8 x 3 = 4,800 bands.

    Midpoint formula:
        base_mid_usd x level multiplier x geo_factor
        x yearly uplift x exchange rate, rounded to the nearest 100
    """
    # Build a lookup so we can find a rate quickly: (currency, year) -> rate
    rate_lookup = {}
    for fx in fx_rates:
        key = (fx["currency_code"], fx["rate_year"])
        rate_lookup[key] = fx["units_per_usd"]

    bands = []
    for role in roles:
        for level in levels:
            for location in locations:
                for year in config.BAND_YEARS:
                    years_since_start = year - config.BAND_YEARS[0]
                    uplift = (1 + config.BAND_YEARLY_UPLIFT) ** years_since_start

                    mid_usd = role["base_mid_usd"] * level["mid_multiplier"]
                    mid_usd = mid_usd * location["geo_factor"] * uplift

                    currency_code = location["currency_code"]
                    rate = rate_lookup[(currency_code, year)]
                    mid_local = mid_usd * rate

                    # Round to the nearest 100.
                    band_mid = int(round(mid_local / config.BAND_ROUND_TO)) * config.BAND_ROUND_TO
                    band_min = int(round(band_mid * config.BAND_MIN_FACTOR))
                    band_max = int(round(band_mid * config.BAND_MAX_FACTOR))

                    band_id = "BAND-" + role["role_id"] + "-" + level["level_id"]
                    band_id = band_id + "-" + location["location_id"] + "-" + str(year)

                    row = {
                        "band_id": band_id,
                        "role_id": role["role_id"],
                        "level_id": level["level_id"],
                        "location_id": location["location_id"],
                        "band_year": year,
                        "currency_code": currency_code,
                        "band_min": band_min,
                        "band_mid": band_mid,
                        "band_max": band_max,
                        "effective_from": str(year) + "-01-01",
                        "effective_to": str(year) + "-12-31",
                    }
                    bands.append(row)
    return bands
