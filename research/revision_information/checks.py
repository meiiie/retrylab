"""Bounded synthetic integrity checks; no archive access, fitting, or performance.

Run: python research/revision_information/checks.py
All code snippets below are handled only as text or by ast.parse/tokenize.
"""
from __future__ import annotations

import ast
import hashlib
import json

import numpy as np
import pandas as pd

import features
from model_pipeline import EpisodeInputs, _labels


def _row(number: int, item: str, timestamp: str, code: str, grade: float) -> dict:
    try:
        tree = ast.parse(code)
        nodes = list(ast.walk(tree))
        valid = 1
    except SyntaxError:
        nodes, valid = [], 0
    return {
        "row_id": number, "user_id": "synthetic-user", "class_id": "synthetic-class",
        "assessment_id": "synthetic-assessment", "problem_id": item,
        "timestamp": timestamp, "source_path": "synthetic/" + item,
        "file_event_index": number, "event_type": "SUBMITION", "semester": "2016-2",
        "grade_percent": grade, "has_error": int(not np.isfinite(grade)),
        "code_text": code, "code_sections": 1,
        "code_sha256": hashlib.sha256(code.encode()).hexdigest(),
        "code_chars": len(code), "code_lines": len(code.splitlines()),
        "code_ast_valid": valid, "code_ast_nodes": len(nodes),
        "code_branches": sum(isinstance(n, ast.If) for n in nodes),
        "code_loops": sum(isinstance(n, (ast.For, ast.While)) for n in nodes),
        "code_functions": sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) for n in nodes),
    }


def _fixture():
    rows = [
        _row(0, "prior", "2020-01-01 11:59:00", "x = 0", 0),
        _row(1, "source", "2020-01-01 12:00:00", "x = (", np.nan),
        _row(2, "source", "2020-01-01 12:00:05", "x = 1", 0),
        _row(3, "source", "2020-01-01 12:00:10", "x = 2\nprint(x)", 100),
        _row(4, "target", "2020-01-01 12:00:20", "y = 9", 0),
    ]
    raw = pd.DataFrame(rows)
    frame, history = features.base.build_prefixes(raw)
    episode = frame.loc[frame.problem_id.eq("source")]
    tests = pd.DataFrame({
        "timestamp": ["2020-01-01 12:00:02", "2020-01-01 12:00:03"],
        "problem_id": ["source", "other"], "has_error": [1, 0],
    })
    return raw, frame, history, episode, tests


def _assert_features_equal(left, right):
    assert len(left) == len(right)
    for a, b in zip(left, right):
        assert list(a) == list(b)
        np.testing.assert_array_equal(list(a.values()), list(b.values()))


def _reject(call):
    try:
        call()
    except ValueError:
        return
    raise AssertionError("An invalid index/label fixture was accepted.")


def run_checks() -> dict:
    import run_experiment as runner

    raw, frame, history, episode, tests = _fixture()
    prehistory = history.loc[episode.index[0]]
    calculate = lambda ep, prior, test: features.episode_features(ep, prior, -0.25, 0.4, test)
    reference = calculate(episode, prehistory, tests)
    m0, endpoint, intermediate = reference

    outside = pd.DataFrame({
        "timestamp": ["2020-01-01 11:59:59", "2020-01-01 12:00:10",
                      "2020-01-01 12:00:10", "2020-01-01 12:00:11",
                      "2020-01-01 12:00:21"],
        "problem_id": ["source", "source", "other", "source", "target"],
        "has_error": [1, 1, 1, 1, 1],
    })
    _assert_features_equal(reference, calculate(episode, prehistory, pd.concat([tests, outside])))
    within = pd.concat([tests, pd.DataFrame({"timestamp": ["2020-01-01 12:00:09"],
                                           "problem_id": ["source"], "has_error": [0]})])
    inside_features = calculate(episode, prehistory, within)[0]
    assert inside_features["source_TEST_count_log"] == np.log1p(2)
    assert inside_features["source_TEST_error_fraction"] == 0.5

    mutated = raw.copy()
    target = mutated.problem_id.eq("target")
    mutated.loc[target, "grade_percent"] = 100
    mutated.loc[target, "timestamp"] = "2020-01-02 12:00:20"
    mutated.loc[target, "code_text"] = "raise RuntimeError('THIS TEXT MUST NEVER EXECUTE')"
    mutated.loc[target, features.STRUCTURE] = 999
    changed_frame, changed_history = features.base.build_prefixes(mutated)
    changed_episode = changed_frame.loc[changed_frame.problem_id.eq("source")]
    _assert_features_equal(reference, calculate(changed_episode, changed_history.loc[changed_episode.index[0]], tests))

    assert len(episode) == 3 and np.isnan(episode.iloc[0].grade_percent)
    assert m0["source_submission_count_log"] == np.log1p(3)
    assert m0["first_missing"] == 1 and m0["first_error"] == 1
    assert m0["all_missing_fraction"] == 1 / 3
    assert m0["middle_missing_fraction"] == 0
    assert endpoint["first_code_code_ast_valid"] == 0
    assert endpoint["final_code_code_ast_valid"] == 1
    assert np.isfinite(list(m0.values()) + list(endpoint.values()) + list(intermediate.values())).all()

    changed_middle = episode.copy()
    middle_index = changed_middle.index[1]
    changed_code = "x = 12345\nwhile x > 0:\n    x -= 1"
    changes = _row(2, "source", "2020-01-01 12:00:05", changed_code, 0)
    for key in ["code_text", "code_sha256", *features.STRUCTURE]:
        changed_middle.at[middle_index, key] = changes[key]
    new_features = calculate(changed_middle, prehistory, tests)
    _assert_features_equal(reference[:2], new_features[:2])
    assert new_features[2] != intermediate

    numeric = pd.DataFrame([{**m0, **endpoint, **intermediate}] * 2, index=["episode-b", "episode-a"])
    batch = EpisodeInputs(
        numeric, pd.Series(["source", "source"], index=numeric.index),
        pd.Series(["target", "target"], index=numeric.index),
        pd.Series([episode.iloc[0].code_text] * 2, index=numeric.index),
        pd.Series([episode.iloc[-1].code_text] * 2, index=numeric.index),
        pd.Series([[episode.iloc[1].code_text]] * 2, index=numeric.index),
        pd.Series(["synthetic-a", "synthetic-b"], index=numeric.index),
    )
    batch.validate(numeric.columns)
    y = pd.Series([0, 1], index=numeric.index)
    np.testing.assert_array_equal(_labels(y, batch, "Synthetic"), [0, 1])
    selected = features.subset(batch, pd.Index(["episode-a"]))
    selected.validate(numeric.columns)
    assert selected.user_id.iloc[0] == "synthetic-b"
    assert selected.numeric.index.tolist() == ["episode-a"]
    wrong_inputs = dict(vars(batch))
    wrong_inputs["final_code"] = batch.final_code.iloc[::-1]
    _reject(lambda: EpisodeInputs(**wrong_inputs).validate(numeric.columns))
    _reject(lambda: _labels(y.iloc[::-1], batch, "Synthetic"))
    _reject(lambda: _labels(pd.Series([np.nan, 1], index=numeric.index), batch, "Synthetic"))

    known_loss = runner.loss(np.array([0.0, 1.0]), np.array([0.25, 0.75]))
    np.testing.assert_allclose(known_loss, -np.log(0.75))
    assert np.isfinite(runner.loss(np.array([0.0, 1.0]), np.array([1.0, 0.0]))).all()
    differences = np.array([1.0, 3.0, 10.0])
    groups = np.array(["a", "b"])
    users = np.array(["a", "a", "b"])
    # One deterministic resample with each student once reproduces both estimands.
    contrast = runner.contrast(users, differences, np.array([[1, 1]]), groups)
    assert contrast["pair_weighted"]["mean"] == 14 / 3
    assert contrast["pair_weighted"]["lower"] == 14 / 3
    assert contrast["equal_student_weighted"]["mean"] == 6
    assert contrast["equal_student_weighted"]["lower"] == 6

    return {
        "synthetic_checks_passed": True,
        "checks": ["TESTs at/after H1 and before H0 do not alter source features",
                   "TEST strictly inside source window affects intended nuisance summaries",
                   "Target code/time/label mutation does not alter source features or prehistory",
                   "Missing-grade and AST-invalid source snapshots remain represented",
                   "Intermediate code mutation changes intermediate features only",
                   "Episode, code, subset, and label index alignment enforced",
                   "Finite clipped-log loss and paired/equal-student arithmetic verified"],
        "real_data_read": False, "model_fit": False, "source_program_execution": False,
    }


if __name__ == "__main__":
    print(json.dumps(run_checks(), indent=2))
