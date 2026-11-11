"""The regression must recover a known straight-line rule exactly."""

import policy_fit


def test_solver_on_a_small_system():
    # 2x + y = 5 and x + 3y = 10 has the solution x = 1, y = 3.
    solution = policy_fit.solve_linear_system([[2.0, 1.0], [1.0, 3.0]], [5.0, 10.0])
    assert abs(solution[0] - 1.0) < 1e-9
    assert abs(solution[1] - 3.0) < 1e-9


def make_people():
    people = []
    for months in [0, 6, 12, 24, 36, 48, 60, 84, 120]:
        for rating in [1, 2, 3, 4, 5]:
            for premium in [0, 10]:
                years = min(months / 12.0, 4)
                ratio = 0.85 + 0.03 * years + 0.02 * (rating - 3) + premium / 100.0
                people.append({"level_tenure_months": months, "rating": rating,
                               "premium_pct": premium, "compa_ratio": ratio})
    return people


def test_fit_recovers_a_known_policy():
    policy = policy_fit.fit_policy(make_people())
    assert policy["tenure_cap_years"] == 4
    assert abs(policy["base_ratio"] - 0.85) < 1e-6
    assert abs(policy["per_tenure_year"] - 0.03) < 1e-6
    assert abs(policy["per_rating_point"] - 0.02) < 1e-6
    assert abs(policy["per_premium_unit"] - 1.0) < 1e-6


def test_fit_is_not_dragged_by_a_few_outliers():
    people = make_people()
    for position in range(0, len(people), 30):
        people[position] = dict(people[position], compa_ratio=people[position]["compa_ratio"] * 0.6)
    policy = policy_fit.fit_policy(people)
    assert abs(policy["base_ratio"] - 0.85) < 0.005
    assert abs(policy["per_tenure_year"] - 0.03) < 0.002
