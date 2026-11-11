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

# Band midpoints and salaries are rounded to the nearest 100.
BAND_ROUND_TO = 100

# ---------------------------------------------------------------
# Workforce mix (shares must add up to 1.0)
# ---------------------------------------------------------------
LEVEL_WEIGHTS = [("L1", 0.25), ("L2", 0.30), ("L3", 0.25), ("L4", 0.13), ("L5", 0.07)]
LOCATION_WEIGHTS = [("BLR", 0.25), ("HYD", 0.15), ("NYC", 0.12), ("SFO", 0.10),
                    ("LON", 0.12), ("BER", 0.08), ("DUB", 0.08), ("SGP", 0.10)]
RATING_WEIGHTS = [(1, 0.05), (2, 0.15), (3, 0.45), (4, 0.25), (5, 0.10)]

SHARE_HIRED_BEFORE_WINDOW = 0.70   # hired before 2024-01-01
SHARE_TERMINATED = 0.08
SHARE_PART_TIME_CHANGE = 0.06      # employees who change FTE at some point
SHARE_RETURN_TO_FULL_TIME = 0.30   # of those, how many go back to 1.0
SHARE_RELOCATION = 0.06
SHARE_KEEP_OLD_CURRENCY = 0.40     # relocated but still paid in the old currency
SHARE_CRITICAL_SKILL = 0.03
PROMOTION_CHANCE = 0.35            # for employees who are eligible
PART_TIME_FTES = [0.5, 0.6, 0.8]

# ---------------------------------------------------------------
# Documented pay policy: what compa-ratio the job-related factors predict
#   expected = base + per_year x years in level (capped)
#              + per_point x (rating - neutral) + premium
# ---------------------------------------------------------------
POLICY_BASE_RATIO = 0.90
POLICY_PER_TENURE_YEAR = 0.02
POLICY_TENURE_CAP_YEARS = 5
POLICY_PER_RATING_POINT = 0.03
POLICY_NEUTRAL_RATING = 3
POLICY_RATIO_FLOOR = 0.80
POLICY_RATIO_CEILING = 1.30

# Ordinary person-to-person variation around the policy (plus or minus).
NORMAL_NOISE = 0.05

# ---------------------------------------------------------------
# Review workflow rules
# ---------------------------------------------------------------
MIN_GROUP_SIZE = 5                 # smaller groups are widened
PROPOSAL_GAP_THRESHOLD = 0.05      # propose a raise when pay is this far below expected
OUTLIER_THRESHOLD = 0.08           # flag as unexplained when this far from expected
HR_APPROVAL_LIMIT_PCT = 10.0       # up to this, the HR partner can approve
COMMITTEE_REJECT_ABOVE_PCT = 20.0  # above this, the committee rejects (too large for one cycle)
REJECT_RATING_AT_OR_BELOW = 2      # no off-cycle raise for low performance ratings

# How far a recorded compa-ratio may differ from the recomputed one (rounding only).
RATIO_TOLERANCE = 0.0002

# ---------------------------------------------------------------
# Deliberate anomalies. Counts are for 5,000 employees and shrink
# in proportion for smaller datasets (never below the minimum).
# Each line is: (count at full scale, minimum count)
# ---------------------------------------------------------------
SHARE_OUTLIER_LOW = 0.02
SHARE_OUTLIER_HIGH = 0.01
OUTLIER_LOW_RANGE = (0.80, 0.92)   # pay multiplied by a number in this range
OUTLIER_HIGH_RANGE = (1.08, 1.22)
INJECT_EXPIRED_BAND = (40, 4)
INJECT_FTE_IGNORED = (40, 4)
INJECT_FX_MISSING = (30, 3)
INJECT_UNAPPROVED = (15, 3)
INJECT_BAD_GROUPS = (15, 3)
VALID_CUSTOM_GROUPS = (3, 1)       # mixed groups WITH a rationale (must not be flagged)

# ---------------------------------------------------------------
# Demographic groups and systemic disparity
# Groups are anonymous labels. They carry no real-world meaning.
# ---------------------------------------------------------------
DEMOGRAPHIC_GROUPS = ["Group A", "Group B"]
SHARE_GROUP_B = 0.45
DISADVANTAGED_GROUP = "Group B"
SYSTEMIC_PAY_MULTIPLIER = 0.90     # in the affected roles, this group is paid 10% less
# Number of affected roles. The minimum is 0 on purpose: with 500 employees
# there are too few people per role and level to compare groups at all.
INJECT_SYSTEMIC_ROLES = (3, 0)

# Detection rule: within one role, compare the two groups level by level.
SYSTEMIC_GAP_PCT = 5.0             # one group's median is at least this % lower
SYSTEMIC_MIN_GROUP_SIZE = 3        # people needed in EACH group at a level to compare it
SYSTEMIC_MIN_LEVELS = 3            # the gap must show at this many levels of the role
SYSTEMIC_MIN_LEVEL_SHARE = 0.75    # ...and at this share of the levels that could be compared
