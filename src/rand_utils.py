"""
rand_utils.py - small random helpers.

Every helper is built only on rng.random(), which returns a number from
0.0 up to (not including) 1.0. Python guarantees that rng.random() gives the
same sequence for the same seed on every Python version, so the dataset is
identical on any machine.
"""

import random


def make_rng(seed, stage_number):
    """Each stage gets its own random stream. Changing one stage then
    does not shift the random numbers used by the other stages."""
    return random.Random(seed * 100 + stage_number)


def rand_int(rng, low, high):
    """Whole number from low to high, both included."""
    span = high - low + 1
    return low + int(rng.random() * span)


def rand_float(rng, low, high):
    """Decimal number from low to high."""
    return low + rng.random() * (high - low)


def pick(rng, items):
    """Pick one item from a list."""
    index = int(rng.random() * len(items))
    return items[index]


def pick_weighted(rng, weighted_items):
    """Pick from a list of (value, share) pairs. Shares add up to 1.0."""
    roll = rng.random()
    running_total = 0.0
    for value, share in weighted_items:
        running_total = running_total + share
        if roll < running_total:
            return value
    # Only reached through tiny rounding differences: return the last value.
    return weighted_items[-1][0]


def shuffled(rng, items):
    """Return a new list with the items in a random order."""
    keyed = []
    for position in range(len(items)):
        keyed.append((rng.random(), position, items[position]))
    keyed.sort()
    result = []
    for entry in keyed:
        result.append(entry[2])
    return result


def scaled_count(full_and_min, employee_count):
    """Shrink an anomaly count in proportion to the dataset size."""
    full_count, minimum = full_and_min
    value = int(round(full_count * employee_count / 5000.0))
    if value < minimum:
        value = minimum
    return value
