import json
from pathlib import Path
import sys
import shutil
import subprocess
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import harness


class HarnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "harness").mkdir()
        (self.root / "evidence.txt").write_text("historical result", encoding="utf-8")
        harness.write_json(self.root / "harness/protected.json", {"files": [
            {"path": "evidence.txt", "sha256": harness.digest(self.root / "evidence.txt")}]})
        harness.write_json(self.root / "harness/workboard.json", {"tasks": [
            {"id": "data", "status": "complete", "evidence": ["evidence.txt"]}]})
        (self.root / "producer.py").write_text(
            "from pathlib import Path\nimport sys\nPath(sys.argv[1], 'result.json').write_text('{}')\n",
            encoding="utf-8")
        self.protocol = {"id": "fixture", "question": "Does the runner preserve provenance?",
                         "data_scope": "fixture", "claim_scope": "software-only", "primary_metric": "exit",
                         "split": {"test_previously_inspected": True}, "selection": "none", "seeds": [1],
                         "inputs": ["evidence.txt"], "code": ["producer.py"], "output_files": ["result.json"]}
        harness.write_json(self.root / "protocol.json", self.protocol)

    def execute(self, name="fixture", command=None):
        return harness.run_experiment(name, "protocol.json", command or
                                      ["{python}", "producer.py", "{run}"], self.root)

    def test_detects_changed_historical_evidence(self):
        self.assertEqual(harness.verify_protected(self.root), [])
        (self.root / "evidence.txt").write_text("changed", encoding="utf-8")
        self.assertTrue(harness.verify_protected(self.root))
        with self.assertRaises(ValueError):
            self.execute()

    def test_rejects_traversal_and_absolute_paths(self):
        for value in ("../escape", str(self.root / "absolute"), ""):
            with self.assertRaises(ValueError):
                harness.within(self.root, value)
        with self.assertRaises(ValueError):
            self.execute("../escape")

    def test_run_snapshots_and_refuses_overwrite(self):
        record = self.execute()
        self.assertEqual(record["state"], "complete")
        self.assertEqual(harness.verify_run("fixture", self.root), [])
        with self.assertRaises(FileExistsError):
            self.execute()
        (self.root / "research/runs/fixture/result.json").write_text('{"edited":true}', encoding="utf-8")
        self.assertTrue(harness.verify_run("fixture", self.root))

    def test_failing_process_is_not_success(self):
        record = self.execute(command=["{python}", "-c", "raise SystemExit(7)"])
        self.assertEqual(record["state"], "failed")
        self.assertEqual(record["exit_code"], 7)
        self.assertEqual(record["missing_outputs"], ["result.json"])

    def test_source_mutation_fails_even_with_output(self):
        source = self.root / "producer.py"
        source.write_text(source.read_text() + "Path(__file__).write_text('# changed')\n", encoding="utf-8")
        record = self.execute()
        self.assertEqual(record["state"], "failed")
        self.assertIn("producer.py", record["changed_inputs"])

    def test_missing_output_fails_with_zero_exit(self):
        record = self.execute(command=["{python}", "-c", "pass"])
        self.assertEqual(record["state"], "failed")
        self.assertEqual(record["exit_code"], 0)

    def test_board_rejects_unsubstantiated_completion_and_cycles(self):
        self.assertTrue(harness.validate_board(self.root))
        path = self.root / "harness/workboard.json"
        harness.write_json(path, {"tasks": [{"id": "x", "status": "complete", "evidence": []}]})
        with self.assertRaises(ValueError):
            harness.validate_board(self.root)
        harness.write_json(path, {"tasks": [{"id": "x", "status": "planned", "depends_on": ["x"]}]})
        with self.assertRaises(ValueError):
            harness.validate_board(self.root)

    def test_protocol_requires_disclosure(self):
        self.protocol["split"] = {"test_previously_inspected": "no"}
        with self.assertRaises(ValueError):
            harness.validate_protocol(self.protocol, self.root)

    def test_metadata_output_collision_is_rejected(self):
        self.protocol["output_files"] = ["record.json"]
        with self.assertRaises(ValueError):
            harness.validate_protocol(self.protocol, self.root)

    def test_protected_mutation_during_run_fails(self):
        source = self.root / "producer.py"
        source.write_text(source.read_text() + "Path('evidence.txt').write_text('changed')\n", encoding="utf-8")
        record = self.execute()
        self.assertEqual(record["state"], "failed")
        self.assertTrue(record["protected_errors"])

    @unittest.skipUnless(shutil.which("git"), "Git is required only for the staged-index check")
    def test_staged_tampering_detected_even_if_working_file_restored(self):
        def git(*args):
            subprocess.run(["git", *args], cwd=self.root, capture_output=True, check=True)
        git("init")
        original = (self.root / "evidence.txt").read_bytes()
        (self.root / "evidence.txt").write_text("different staged evidence", encoding="utf-8")
        git("add", "evidence.txt")
        (self.root / "evidence.txt").write_bytes(original)
        self.assertEqual(harness.verify_protected(self.root), [])
        self.assertTrue(harness.verify_protected(self.root, staged=True))


if __name__ == "__main__":
    unittest.main()
