from pathlib import Path
import random
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import benchmark as b


class PolicyTests(unittest.TestCase):
    def test_repair_without_learning_cannot_improve_probe(self):
        for seed in range(50):
            student = b.Student(b.World("repair", 0, .9, 0), seed)
            initial = student.probe_expectation()
            for action in [0, 0, 2, 2, 4, 4, 1, 1]:
                student.step(action)
            self.assertEqual(student.probe_expectation(), initial)

    def test_policy_never_uses_exhausted_action(self):
        model = b.LearnerModel(.1, .2, .1, .5)
        counts = [2, 2, 1, 0, 2, 0]
        for policy in ("random", "curriculum", "weakest", "challenge", "q"):
            action, _ = b.choose(policy, model, [.2, .4, .6], counts, 3, random.Random(1), {})
            self.assertIn(action, [2, 3, 5])

    def test_outcome_is_not_used_before_prediction(self):
        model = b.LearnerModel(.1, .2, .1, .5)
        p0, posterior0 = model.predict_update([.3] * 3, [0] * 6, 0, 0)
        p1, posterior1 = model.predict_update([.3] * 3, [0] * 6, 0, 1)
        self.assertEqual(p0, p1)
        self.assertNotEqual(posterior0, posterior1)

    def test_model_update_does_not_mutate_history(self):
        model = b.LearnerModel(.1, .2, .1, .5)
        prior, counts = [.3] * 3, [0] * 6
        model.predict_update(prior, counts, 1, 1)
        self.assertEqual(prior, [.3] * 3)
        self.assertEqual(counts, [0] * 6)

    def test_training_is_finite_and_reproducible(self):
        model = b.LearnerModel(.1, .2, .1, .5)
        first = b.train_q(model, 11, 20, 8)
        self.assertEqual(first, b.train_q(model, 11, 20, 8))
        self.assertTrue(any(any(value != 0 for value in row) for row in first.values()))

    def test_trace_exposes_decision_and_honest_fallback(self):
        model = b.LearnerModel(.1, .2, .1, .5)
        result, trace = b.rollout(b.TRAIN_WORLD, model, "q", 17, 8, {}, True)
        self.assertEqual(result["fallback_fraction"], 1)
        self.assertEqual(len(trace), 8)
        for step in trace:
            self.assertIn(step["selected"], step["eligible"])


if __name__ == "__main__":
    unittest.main()
