import unittest
from app.services.risk_engine import calculate_risk, level_from_score, severity_from_risk_level


def R(**kw):
    base = dict(temperature=22, smoke_level=0, co_level=0, flame_detected=False,
                fire_status="none", occupants_count=0, exit_blocked=False)
    base.update(kw)
    return calculate_risk(**base)


class WeightedScore(unittest.TestCase):
    def test_normal_room_is_safe(self):
        r = R()
        self.assertEqual(r["risk_score"], 0.0)
        self.assertEqual(r["risk_level"], "Safe")
        self.assertEqual(r["overrides_applied"], [])

    def test_max_inputs_cap_at_100(self):
        r = R(temperature=500, smoke_level=100, co_level=1000, flame_detected=True,
              fire_status="active", occupants_count=50, exit_blocked=True)
        self.assertEqual(r["risk_score"], 100.0)

    def test_breakdown_sums_to_weighted_score(self):
        r = R(temperature=90, smoke_level=50, co_level=60, fire_status="smoke",
              occupants_count=4, exit_blocked=True)
        self.assertAlmostEqual(sum(r["score_breakdown"].values()), r["weighted_score"], delta=0.35)

    def test_each_component_max(self):
        self.assertEqual(R(temperature=150)["score_breakdown"]["temperature"], 25.0)
        self.assertEqual(R(smoke_level=100)["score_breakdown"]["smoke"], 25.0)
        self.assertEqual(R(co_level=200)["score_breakdown"]["co"], 15.0)
        self.assertEqual(R(fire_status="active")["score_breakdown"]["fire_status"], 20.0)
        self.assertEqual(R(occupants_count=10)["score_breakdown"]["occupancy"], 10.0)
        self.assertEqual(R(exit_blocked=True)["score_breakdown"]["blocked_exit"], 5.0)


class Bands(unittest.TestCase):
    def test_boundaries(self):
        for score, lvl in [(0, "Safe"), (30, "Safe"), (30.1, "Moderate"), (60, "Moderate"),
                           (60.1, "High Risk"), (80, "High Risk"), (80.1, "Critical"), (100, "Critical")]:
            self.assertEqual(level_from_score(score), lvl, score)

    def test_severity_follows_band(self):
        self.assertEqual(severity_from_risk_level("Critical"), "Critical")
        self.assertEqual(severity_from_risk_level("High Risk"), "High")
        self.assertEqual(severity_from_risk_level("Moderate"), "Moderate")
        self.assertEqual(severity_from_risk_level("Safe"), "Low")


class Overrides(unittest.TestCase):
    def test_flame_with_cool_reading_is_at_least_high(self):
        r = R(flame_detected=True)
        self.assertGreaterEqual(r["risk_score"], 61)
        self.assertIn(r["risk_level"], ("High Risk", "Critical"))
        self.assertTrue(r["overrides_applied"])

    def test_flame_plus_active_is_critical_even_if_sensors_cool(self):
        r = R(flame_detected=True, fire_status="active")
        self.assertEqual(r["risk_level"], "Critical")

    def test_lethal_co_is_critical(self):
        self.assertEqual(R(co_level=200)["risk_level"], "Critical")
        self.assertNotEqual(R(co_level=199)["risk_level"], "Critical")

    def test_extreme_heat_is_high(self):
        self.assertGreaterEqual(R(temperature=120)["risk_score"], 61)
        self.assertEqual(R(temperature=119)["overrides_applied"], [])

    def test_override_never_lowers_score(self):
        r = R(temperature=150, smoke_level=100, co_level=200, flame_detected=True, fire_status="active")
        self.assertGreaterEqual(r["risk_score"], r["weighted_score"])

    def test_override_not_reported_when_weighted_already_higher(self):
        r = R(temperature=150, smoke_level=100, co_level=200, fire_status="active")
        self.assertEqual(r["overrides_applied"], [])

    def test_cooking_smoke_alone_does_not_trigger_override(self):
        r = R(temperature=35, smoke_level=60)
        self.assertEqual(r["overrides_applied"], [])
        self.assertNotEqual(r["risk_level"], "Critical")

    def test_contained_fire_no_override(self):
        self.assertEqual(R(fire_status="contained")["overrides_applied"], [])


class MissingData(unittest.TestCase):
    def test_missing_sensors_flagged(self):
        r = R(temperature=None, smoke_level=None)
        self.assertEqual(r["data_quality"], "partial")
        self.assertTrue(any("missing" in f for f in r["contributing_factors"]))

    def test_missing_with_flame_still_overrides(self):
        r = R(temperature=None, smoke_level=None, flame_detected=True)
        self.assertGreaterEqual(r["risk_score"], 61)


class Monotonic(unittest.TestCase):
    def test_score_never_decreases_with_temperature(self):
        prev = -1
        for t in range(0, 300, 5):
            s = R(temperature=t)["risk_score"]
            self.assertGreaterEqual(s, prev)
            prev = s


if __name__ == "__main__":
    unittest.main()
