"""
policy_fit.py - estimates the pay policy from the data.

The detector must not be told the generator's pay formula. Instead it learns
the pattern from the employees themselves with a linear regression:

    compa-ratio = base
                + a x years in level (counted up to a cap)
                + b x (rating - 3)
                + c x documented premium

"Least squares" finds the base, a, b and c that make the predictions as close
as possible to the real compa-ratios. Only the Python standard library is used.

Two details make the estimate reliable:
  1. The tenure cap is not known, so every whole number of years from 2 to 10
     is tried and the one that fits best is kept.
  2. Real outliers would drag the fitted line towards themselves. So the
     line is fitted once, the people furthest from it are set aside, and
     the line is fitted again on everyone else.
"""

RATING_MIDPOINT = 3          # the middle of the 1-5 rating scale
CAP_CANDIDATES = [2, 3, 4, 5, 6, 7, 8, 9, 10]
TRIM_WIDTH = 3.0             # set aside points more than 3 "typical distances" away


def solve_linear_system(matrix, vector):
    """Solve matrix x = vector by Gaussian elimination.
    matrix is a list of rows. Returns the list x."""
    size = len(vector)
    # Work on copies so the caller's lists are not changed.
    rows = []
    for i in range(size):
        rows.append(list(matrix[i]) + [vector[i]])

    for column in range(size):
        # Pick the row with the largest value in this column (more accurate).
        best_row = column
        for row in range(column + 1, size):
            if abs(rows[row][column]) > abs(rows[best_row][column]):
                best_row = row
        rows[column], rows[best_row] = rows[best_row], rows[column]

        pivot = rows[column][column]
        if abs(pivot) < 1e-12:
            raise ValueError("The factors do not vary enough to estimate a policy")

        # Remove this column from every row below.
        for row in range(column + 1, size):
            factor = rows[row][column] / pivot
            for k in range(column, size + 1):
                rows[row][k] = rows[row][k] - factor * rows[column][k]

    # Back-substitution: solve from the last row upwards.
    solution = [0.0] * size
    for row in range(size - 1, -1, -1):
        total = rows[row][size]
        for k in range(row + 1, size):
            total = total - rows[row][k] * solution[k]
        solution[row] = total / rows[row][row]
    return solution


def least_squares(feature_rows, targets):
    """Ordinary least squares through the normal equations:
    (X-transpose X) coefficients = X-transpose y."""
    count = len(feature_rows[0])
    xtx = []
    for i in range(count):
        xtx.append([0.0] * count)
    xty = [0.0] * count
    for features, target in zip(feature_rows, targets):
        for i in range(count):
            xty[i] = xty[i] + features[i] * target
            for j in range(count):
                xtx[i][j] = xtx[i][j] + features[i] * features[j]
    return solve_linear_system(xtx, xty)


def make_features(level_tenure_months, rating, premium_pct, tenure_cap):
    years = level_tenure_months / 12.0
    if years > tenure_cap:
        years = tenure_cap
    return [1.0, years, float(rating - RATING_MIDPOINT), premium_pct / 100.0]


def predict(coefficients, features):
    total = 0.0
    for i in range(len(coefficients)):
        total = total + coefficients[i] * features[i]
    return total


def median(values):
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def fit_with_cap(people, tenure_cap):
    """Fit, set aside the far-away points, fit again.
    Returns (coefficients, typical distance, number of people used)."""
    feature_rows = []
    targets = []
    for person in people:
        feature_rows.append(make_features(person["level_tenure_months"], person["rating"],
                                          person["premium_pct"], tenure_cap))
        targets.append(person["compa_ratio"])

    # First pass: everyone.
    coefficients = least_squares(feature_rows, targets)
    distances = []
    for features, target in zip(feature_rows, targets):
        distances.append(abs(target - predict(coefficients, features)))
    typical = median(distances)

    # Second pass: leave out the people furthest from the line.
    kept_rows = []
    kept_targets = []
    for features, target, distance in zip(feature_rows, targets, distances):
        if distance <= TRIM_WIDTH * typical:
            kept_rows.append(features)
            kept_targets.append(target)
    coefficients = least_squares(kept_rows, kept_targets)

    distances = []
    for features, target in zip(feature_rows, targets):
        distances.append(abs(target - predict(coefficients, features)))
    return coefficients, median(distances), len(kept_rows)


def fit_policy(people):
    """Try each tenure cap and keep the one whose line fits best.
    people is a list of dictionaries with compa_ratio, level_tenure_months,
    rating and premium_pct. Returns a dictionary describing the policy."""
    best = None
    for tenure_cap in CAP_CANDIDATES:
        coefficients, typical, used = fit_with_cap(people, tenure_cap)
        if best is None or typical < best["typical_distance"]:
            best = {
                "tenure_cap_years": tenure_cap,
                "base_ratio": coefficients[0],
                "per_tenure_year": coefficients[1],
                "per_rating_point": coefficients[2],
                "per_premium_unit": coefficients[3],
                "typical_distance": typical,
                "people_used": used,
                "people_total": len(people),
            }
    return best


def expected_ratio(policy, level_tenure_months, rating, premium_pct):
    features = make_features(level_tenure_months, rating, premium_pct, policy["tenure_cap_years"])
    coefficients = [policy["base_ratio"], policy["per_tenure_year"],
                    policy["per_rating_point"], policy["per_premium_unit"]]
    return round(predict(coefficients, features), 4)
