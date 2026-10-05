"""Prefix-only predictive feasibility pilot; no learning-effect or policy-value claim."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


SEED = 26092026
HISTORY = [
    "difficulty_logit", "history_count", "history_accuracy", "last_result",
    "recent_5_accuracy", "recent_20_accuracy", "history_distinct_problems", "gap_seconds",
]
RETRY = [
    "seen_problem", "problem_attempt_count", "problem_accuracy", "problem_last_result",
    "problem_ever_accepted", "problem_gap_seconds",
]


def digest_user(value: str) -> int:
    return int(hashlib.sha256(("accoding-pilot-v1:" + value).encode()).hexdigest()[:16], 16)


def metrics(y, p, weights=None):
    if len(y) == 0 or (weights is not None and np.sum(weights) == 0):
        return {"auc": None, "log_loss": None, "brier": None, "average_precision": None}
    present = np.unique(y if weights is None else y[np.asarray(weights) > 0])
    return {
        "auc": float(roc_auc_score(y, p, sample_weight=weights)) if len(present) == 2 else None,
        "log_loss": float(log_loss(y, p, labels=[0, 1], sample_weight=weights)),
        "brier": float(brier_score_loss(y, p, sample_weight=weights)),
        "average_precision": float(average_precision_score(y, p, sample_weight=weights))
        if len(present) == 2 else None,
    }


def build_features(frame: pd.DataFrame):
    frame = frame.sort_values(["creator_id", "created_at", "id"], kind="stable").copy()
    frame.reset_index(drop=True, inplace=True)
    frame["y"] = frame.result.eq("AC").astype("int8")
    users = frame.groupby("creator_id", sort=False)
    problems = frame.groupby(["creator_id", "problem_id"], sort=False)
    n = users.cumcount()
    pn = problems.cumcount()
    frame["is_first"] = pn.eq(0)
    previous_success = users.y.cumsum() - frame.y
    previous_problem_success = problems.y.cumsum() - frame.y
    frame["prior_problem_accepted"] = previous_problem_success.gt(0)
    hashes = {u: digest_user(u) for u in frame.creator_id.unique()}
    buckets = frame.creator_id.map(lambda u: hashes[u] % 100)
    frame["split"] = np.select([buckets < 70, buckets < 85], ["train", "validation"], default="test")
    frame["fold"] = frame.creator_id.map(lambda u: (hashes[u] // 100) % 5)
    x = pd.DataFrame(index=frame.index)
    x["history_count"] = np.log1p(n)
    x["history_accuracy"] = (previous_success + 1) / (n + 2)
    x["last_result"] = users.y.shift().fillna(0.5)
    for width in (5, 20):
        x[f"recent_{width}_accuracy"] = users.y.transform(
            lambda s: s.shift().rolling(width, min_periods=1).mean()
        ).fillna(0.5)
    x["history_distinct_problems"] = np.log1p(
        frame.groupby("creator_id", sort=False).is_first.cumsum() - frame.is_first.astype(int)
    )
    x["gap_seconds"] = np.log1p(users.created_at.diff().dt.total_seconds().clip(0, 31536000).fillna(0))
    x["seen_problem"] = (pn > 0).astype(float)
    x["problem_attempt_count"] = np.log1p(pn)
    x["problem_accuracy"] = (previous_problem_success + 1) / (pn + 2)
    x["problem_last_result"] = problems.y.shift().fillna(0.5)
    x["problem_ever_accepted"] = previous_problem_success.gt(0).astype(float)
    x["problem_gap_seconds"] = np.log1p(
        problems.created_at.diff().dt.total_seconds().clip(0, 31536000).fillna(0)
    )
    train = frame.split.eq("train")

    def difficulty(reference, target):
        first = reference[reference.is_first]
        base = float(first.y.mean())
        table = first.groupby("problem_id").y.agg(["sum", "count"])
        rate = (table["sum"] + 20 * base) / (table["count"] + 20)
        probability = target.problem_id.map(rate).fillna(base).clip(1e-6, 1 - 1e-6)
        return np.log(probability / (1 - probability))

    x["difficulty_logit"] = 0.0
    for fold in range(5):
        mask = train & frame.fold.eq(fold)
        x.loc[mask, "difficulty_logit"] = difficulty(frame[train & ~frame.fold.eq(fold)], frame[mask])
    x.loc[~train, "difficulty_logit"] = difficulty(frame[train], frame[~train])
    assert np.isfinite(x.to_numpy()).all()
    return frame, x


def bootstrap_differences(frame, predictions, repetitions):
    test = frame[frame.split.eq("test")].copy()
    y = test.y.to_numpy()
    ids, unique_ids = pd.factorize(test.creator_id, sort=True)
    rng = np.random.default_rng(SEED)
    groups = {"all": np.ones(len(test), dtype=bool), "first_seen_problem": test.is_first.to_numpy(),
              "retry": ~test.is_first.to_numpy(),
              "retry_before_first_acceptance": (~test.is_first & ~test.prior_problem_accepted).to_numpy()}
    storage = {name: {metric: [] for metric in ("auc", "log_loss", "brier")} for name in groups}
    p0, p1 = predictions["history"], predictions["history_plus_same_item"]
    for _ in range(repetitions):
        counts = np.bincount(rng.integers(len(unique_ids), size=len(unique_ids)), minlength=len(unique_ids))
        weights = counts[ids]
        for name, mask in groups.items():
            a, b = metrics(y[mask], p0[mask], weights[mask]), metrics(y[mask], p1[mask], weights[mask])
            for metric in storage[name]:
                if a[metric] is not None and b[metric] is not None:
                    storage[name][metric].append(b[metric] - a[metric])
    return {
        "repetitions": repetitions, "unit": "held-out student", "seed": SEED,
        "contrast": "history_plus_same_item minus history; higher AUC / lower log-loss and Brier are better",
        "interval_type": "paired percentile bootstrap, nominal 95%, exploratory, no multiplicity adjustment",
        "intervals": {name: {key: {"lower": float(np.quantile(values, .025)) if values else None,
                                   "upper": float(np.quantile(values, .975)) if values else None}
                              for key, values in row.items()} for name, row in storage.items()},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--bootstrap", type=int, default=100)
    args = parser.parse_args()
    output = Path(__file__).resolve().parent
    required = ["id", "created_at", "creator_id", "problem_id", "result", "score"]
    frame = pd.read_csv(args.input, usecols=required, dtype={"creator_id": "string", "problem_id": "string", "result": "string"})
    original_count = len(frame)
    pending = frame.result.isin(["WT", "JG"])
    pending_count = int(pending.sum())
    frame = frame.loc[~pending].copy()
    frame["created_at"] = pd.to_datetime(frame.created_at, errors="coerce")
    missing = frame[["id", "creator_id", "problem_id", "created_at", "result"]].isna().any(axis=1)
    missing_count = int(missing.sum())
    frame = frame.loc[~missing].copy()
    duplicate_count = int(frame.id.duplicated().sum())
    frame = frame.drop_duplicates("id", keep="first")
    frame, x = build_features(frame)
    print(json.dumps({"stage": "features_ready", "rows": len(frame), "students": frame.creator_id.nunique()}), flush=True)
    train = frame.split.eq("train")
    test = frame.split.eq("test")
    predictions = {}
    rows = []
    columns = {"item_difficulty": ["difficulty_logit"], "history": HISTORY, "history_plus_same_item": HISTORY + RETRY}
    coefficients = {}
    for name, features in columns.items():
        model = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=500, random_state=SEED))
        model.fit(x.loc[train, features], frame.loc[train, "y"])
        p = model.predict_proba(x.loc[test, features])[:, 1]
        predictions[name] = p
        coefficients[name] = dict(zip(features, model[-1].coef_[0].tolist()))
        print(json.dumps({"stage": "model_fit", "model": name, "iterations": int(model[-1].n_iter_[0])}), flush=True)
        test_frame = frame.loc[test]
        subsets = {
            "all": np.ones(test.sum(), dtype=bool),
            "first_seen_problem": test_frame.is_first.to_numpy(),
            "retry": ~test_frame.is_first.to_numpy(),
            "retry_before_first_acceptance": (~test_frame.is_first & ~test_frame.prior_problem_accepted).to_numpy(),
            "after_prior_acceptance": test_frame.prior_problem_accepted.to_numpy(),
        }
        for subset, mask in subsets.items():
            y = test_frame.y.to_numpy()[mask]
            rows.append({"model": name, "subset": subset, "rows": int(mask.sum()),
                         "students": int(test_frame.loc[mask, "creator_id"].nunique()),
                         "acceptance_rate": float(y.mean()), **metrics(y, p[mask])})
    pd.DataFrame(rows).to_csv(output / "metrics.csv", index=False)
    print(json.dumps({"stage": "bootstrap_start", "repetitions": args.bootstrap}), flush=True)
    confidence = bootstrap_differences(frame, predictions, args.bootstrap)
    train_items = set(frame.loc[train, "problem_id"])
    report = {
        "status": "exploratory public-data predictive feasibility pilot; not SOTA, causal learning, or policy evaluation",
        "input": str(args.input.resolve()), "input_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
        "environment": {"python": platform.python_version(), "sklearn": sklearn.__version__, "pandas": pd.__version__, "numpy": np.__version__},
        "raw_rows": original_count, "excluded_pending_rows": pending_count, "excluded_missing_rows": missing_count,
        "duplicate_id_rows_removed": duplicate_count, "analyzed_rows": len(frame),
        "result_counts": frame.result.value_counts().to_dict(),
        "cohort_note": "Input extraction selects up to 1500 learners with >=20 distinct problems using complete traces; eligibility uses future information and limits the target population, not feature construction.",
        "target": "Current submission accepted (AC); all other finalized verdicts are failures.",
        "ordering": "created_at then numeric submission id within student; timestamps lack timezone; ties use submission id as a proxy for order",
        "timestamp_tie_rows": int(frame.duplicated(["creator_id", "created_at"], keep=False).sum()),
        "rows_after_prior_acceptance_same_problem": int(frame.prior_problem_accepted.sum()),
        "split": {part: {"students": int(group.creator_id.nunique()), "rows": len(group),
                          "first_seen_rows": int(group.is_first.sum())} for part, group in frame.groupby("split")},
        "split_rule": "sha256('accoding-pilot-v1:' + user_id), first 16 hex digits modulo 100: train<70, validation<85, test otherwise",
        "validation_usage": "Reserved, not used for fitting, tuning, calibration, or model selection in this fixed-configuration pilot.",
        "difficulty": "Train-user first attempts only, empirical-Bayes smoothing with 20 pseudo-observations at training prevalence. Five student folds for train features; full training set for validation/test; unknown item falls back to train prevalence.",
        "test_rows_with_unseen_item": int((test & ~frame.problem_id.isin(train_items)).sum()),
        "features": columns, "current_fields_excluded": ["result", "score", "code_length", "current code"],
        "model": "StandardScaler fitted on training rows + L2 logistic regression C=1, max_iter=500; no tuning, class weighting, or per-student sample weighting",
        "metrics": rows, "bootstrap": confidence, "standardized_coefficients": coefficients,
        "limitations": [
            "Student split only; does not estimate prospective time/cohort generalization or unseen-item generalization.",
            "Train-user item parameters can incorporate events later in calendar time than a test prediction; only individual histories are prefix-only.",
            "Gap features use the current query/submission timestamp. This is submission-time outcome prediction; remove gaps for exercise-selection-time prediction when the future submission timestamp is unknown.",
            "First attempt means first observed finalized submission in this public extract, not guaranteed first exposure in the student's life.",
            "Submission-ID ordering within tied student timestamps is a convention, not verified subsecond chronology; a sensitivity analysis should exclude tied blocks or update after the whole block.",
            "Non-AC verdicts include execution/infrastructure errors; the target is an operational judge outcome, not ground-truth competence.",
            "Retries on the same problem include returns after intervening problems and submissions after acceptance.",
            "All rows have equal training/evaluation weight; retry-heavy students influence point estimates more. Student bootstrap accounts for dependence, not this weighting choice.",
            "Current code and learning-outcome labels are unavailable; feature improvements cannot establish causal transfer or quality of exercise recommendations.",
            "Different subset AUCs are not directly comparable measures of problem difficulty or model quality because label distributions and sample compositions differ.",
            "No propensity or randomized policy assumptions are used or verified.",
        ],
    }
    (output / "pilot_summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": "complete", "metrics": rows, "bootstrap": confidence}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
