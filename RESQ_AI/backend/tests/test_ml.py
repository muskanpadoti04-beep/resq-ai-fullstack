import json, os, unittest
from ml import gbdt
from ml.features import FEATURE_NAMES, make_features, HORIZON_MIN
from ml.data_gen import gen_episode, label_episode, build_dataset, split
import random

HERE = os.path.join(os.path.dirname(__file__), "..", "ml")
MODEL = json.load(open(os.path.join(HERE, "model.json")))
REPORT = json.load(open(os.path.join(HERE, "report.json")))


def reading(**kw):
    b = dict(temperature=22, smoke=1, co=1, flame=False, fire_status="none", occupants=2, exit_blocked=False)
    b.update(kw); return b


class ModelFile(unittest.TestCase):
    def test_metadata(self):
        for k in ("model_version", "target", "horizon_minutes", "decision_threshold", "trained_on", "checksum"):
            self.assertIn(k, MODEL)
        self.assertEqual(MODEL["horizon_minutes"], HORIZON_MIN)
        self.assertIn("SYNTHETIC", MODEL["trained_on"])
        self.assertEqual(MODEL["features"], FEATURE_NAMES)

    def test_probability_range_and_ordering(self):
        calm = gbdt.predict_proba(MODEL, make_features(reading(), reading()))
        fire = gbdt.predict_proba(MODEL, make_features(
            reading(temperature=90, smoke=60, co=80, flame=True, fire_status="active"),
            reading(temperature=60, smoke=30, co=40, fire_status="smoke")))
        for p in (calm, fire):
            self.assertTrue(0.0 <= p <= 1.0)
        self.assertLess(calm, MODEL["decision_threshold"])
        self.assertGreater(fire, MODEL["decision_threshold"])

    def test_rising_trend_raises_forecast(self):
        cur = reading(temperature=50, smoke=30, co=20, fire_status="smoke")
        flat = gbdt.predict_proba(MODEL, make_features(cur, cur))
        rising = gbdt.predict_proba(MODEL, make_features(cur, reading(temperature=30, smoke=5, co=2)))
        self.assertGreaterEqual(rising, flat)


class Data(unittest.TestCase):
    def test_labels_have_both_classes_and_deterministic(self):
        rng = random.Random(1)
        fire = label_episode(gen_episode("gradual_fire", rng))
        calm = label_episode(gen_episode("normal", random.Random(1)))
        self.assertTrue(any(y for _, y, _ in fire))
        self.assertFalse(any(y for _, y, _ in calm))
        a = label_episode(gen_episode("sudden_fire", random.Random(5)))
        b = label_episode(gen_episode("sudden_fire", random.Random(5)))
        self.assertEqual(a, b)

    def test_split_is_by_episode_no_leakage(self):
        eps = build_dataset(n_per_kind=10)
        tr, va, te = split(eps)
        ids = [set(e["id"] for e in s) for s in (tr, va, te)]
        self.assertFalse(ids[0] & ids[1] or ids[0] & ids[2] or ids[1] & ids[2])
        self.assertEqual(sum(len(i) for i in ids), len(eps))


class Report(unittest.TestCase):
    def test_report_matches_model_and_has_required_metrics(self):
        self.assertEqual(REPORT["checksum"], MODEL["checksum"])
        t = REPORT["test"]["at_threshold"]
        for k in ("precision", "recall", "f1", "fp_false_alarms", "fn_missed"):
            self.assertIn(k, t)
        self.assertIn("calibration_bins", REPORT["test"])
        self.assertIn("early_warning_test", REPORT)

    def test_beats_naive_base_rate_on_brier(self):
        self.assertLess(REPORT["test"]["brier"], REPORT["test"]["brier_always_base_rate"])


if __name__ == "__main__":
    unittest.main()
