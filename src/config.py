"""
config.py - every setting for the project lives in this one file.

Nothing here is random and nothing reads the system clock.
That is what makes two runs with the same seed give identical files.
"""

# The seed makes the "random" choices repeatable.
DEFAULT_SEED = 20261022

# How many employees to create for each dataset size.
SCALES = {
    "starter": 500,
    "full": 5000,
}

# Salary history window and the fixed date of the pay review.
HISTORY_START = "2024-01-01"
HISTORY_END = "2026-11-30"
REVIEW_DATE = "2026-12-01"

# One set of pay bands per year.
BAND_YEARS = [2024, 2025, 2026]

# Band shape: minimum is 80% of the midpoint, maximum is 120%.
BAND_MIN_FACTOR = 0.80
BAND_MAX_FACTOR = 1.20

# Band midpoints rise by 4% each year.
BAND_YEARLY_UPLIFT = 0.04

# Band midpoints are rounded to the nearest 100 so they look realistic.
BAND_ROUND_TO = 100
