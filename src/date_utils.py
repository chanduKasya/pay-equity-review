"""
date_utils.py - date helpers. Dates are stored as text "YYYY-MM-DD".
"""

import datetime


def to_date(text):
    return datetime.date(int(text[0:4]), int(text[5:7]), int(text[8:10]))


def to_text(date_value):
    return date_value.isoformat()


def add_days(text, days):
    return to_text(to_date(text) + datetime.timedelta(days=days))


def days_between(start_text, end_text):
    return (to_date(end_text) - to_date(start_text)).days


def months_between(start_text, end_text):
    """Whole months from start to end. 2024-01-15 to 2024-03-14 is 1 month."""
    start = to_date(start_text)
    end = to_date(end_text)
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day < start.day:
        months = months - 1
    if months < 0:
        months = 0
    return months


def year_of(text):
    return int(text[0:4])
