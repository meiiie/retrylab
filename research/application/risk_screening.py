"""Frozen-validation failure-risk screening on private fixed-future predictions.

Only aggregate outputs are written. See locked_protocol.md for the estimand.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.metrics import roc_auc_score

REQUIRED = ["model", "split", "student_id", "pair_id", "y", "pH0", "pH1"]
STAGES = ("H0", "H1")
POLICIES = ("validation_recall_80", "validation_workload_30")
EXPECTED_MODELS = {"all_submissions", "first_attempt", "paired_target", "gru_ALL", "gru_FIRST"}
SEED = 20260926
EPS = 1e-12


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def environment():
    return {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__, "sklearn": sklearn.__version__}


def load_inputs(paths):
    frames = []
    for path in paths:
        frame = pd.read_csv(path, dtype={k: str for k in REQUIRED[:4]})
        if not set(REQUIRED).issubset(frame.columns):
            raise ValueError(f"Missing input columns in {path}: {set(REQUIRED)-set(frame.columns)}")
        frames.append(frame[REQUIRED])
    df = pd.concat(frames, ignore_index=True)
    if df.empty or df[REQUIRED].isna().any().any():
        raise ValueError("Empty input or missing required values")
    if not set(df.split).issubset({"validation", "confirmation"}):
        raise ValueError("Unexpected split name")
    if not set(df.y).issubset({0, 1}):
        raise ValueError("Labels must be binary accepted outcomes")
    probs = df[["pH0", "pH1"]].to_numpy(float)
    if not np.isfinite(probs).all() or (probs < 0).any() or (probs > 1).any():
        raise ValueError("Probabilities must be finite and within [0,1]")
    if df.duplicated(["model", "split", "student_id", "pair_id"]).any():
        raise ValueError("Duplicate model/pair rows")
    if (df.groupby(["split", "student_id", "pair_id"]).y.nunique() > 1).any():
        raise ValueError("Conflicting labels across model families")
    val_users = set(df.loc[df.split == "validation", "student_id"])
    con_users = set(df.loc[df.split == "confirmation", "student_id"])
    if val_users & con_users:
        raise ValueError("Validation and confirmation students overlap")
    return df.sort_values(REQUIRED[:4]).reset_index(drop=True)


def validation_digest(df):
    val = df[df.split == "validation"].sort_values(REQUIRED[:4])[REQUIRED]
    return hashlib.sha256(val.to_csv(index=False, float_format="%.17g", lineterminator="\n").encode()).hexdigest()


def fit_thresholds(frame, stage):
    risk = 1.0 - frame[f"p{stage}"].to_numpy(float)
    failure = 1 - frame.y.to_numpy(int)
    failures = np.sort(risk[failure == 1])[::-1]
    k = math.ceil(0.30 * len(risk))
    budget = float(np.sort(risk)[::-1][k-1])
    recall = None if len(failures) == 0 else float(failures[math.ceil(0.80 * len(failures))-1])
    return {
        "validation_recall_80": {"threshold": recall, "feasible": recall is not None, "target": 0.80, "tie_count": int((risk == recall).sum()) if recall is not None else 0},
        "validation_workload_30": {"threshold": budget, "feasible": True, "target": 0.30, "tie_count": int((risk == budget).sum()), "rank": k},
    }


def ratio(num, den):
    return None if den == 0 else float(num / den)


def screening_metrics(failure, risk, threshold):
    if threshold is None:
        return {"feasible": False}
    flags = risk >= threshold
    n_fail = int(failure.sum())
    flagged = int(flags.sum())
    flagged_fail = int((flags * failure).sum())
    n_nonfail = len(failure) - n_fail
    return {
        "feasible": True, "threshold": float(threshold), "pairs": len(failure),
        "failures": n_fail, "failure_prevalence": float(failure.mean()),
        "flagged": flagged, "flagged_failures": flagged_fail,
        "workload": flagged / len(failure),
        "failure_recall": ratio(flagged_fail, n_fail),
        "failure_miss_rate": ratio(n_fail - flagged_fail, n_fail),
        "ppv": ratio(flagged_fail, flagged),
        "nonfailure_flag_rate": ratio(flagged - flagged_fail, n_nonfail),
    }


def calibration_metrics(failure, risk):
    clipped = np.clip(risk, EPS, 1-EPS)
    bins = np.minimum((risk * 10).astype(int), 9)
    reliability = []
    ece = 0.0
    for b in range(10):
        mask = bins == b
        n = int(mask.sum())
        if n:
            avg_risk, avg_y = float(risk[mask].mean()), float(failure[mask].mean())
            ece += n / len(risk) * abs(avg_risk-avg_y)
        else:
            avg_risk = avg_y = None
        reliability.append({"lower": b/10, "upper": (b+1)/10, "pairs": n, "mean_risk": avg_risk, "failure_fraction": avg_y})
    return {
        "failure_auc": float(roc_auc_score(failure, risk)) if len(np.unique(failure)) == 2 else None,
        "brier": float(np.mean((risk-failure)**2)),
        "nll": float(np.mean(-failure*np.log(clipped)-(1-failure)*np.log(1-clipped))),
        "mean_risk": float(risk.mean()),
        "failure_prevalence": float(failure.mean()),
        "calibration_bias": float(risk.mean()-failure.mean()),
        "ece_10_equal_width": float(ece), "reliability_bins": reliability,
    }


def coverage(df):
    result = {"by_model": [], "pair_intersections": []}
    for (model, split), frame in df.groupby(["model", "split"]):
        result["by_model"].append({"model": model, "split": split, "pairs": len(frame), "students": frame.student_id.nunique(), "failure_prevalence": float(1-frame.y.mean())})
    for split, sf in df.groupby("split"):
        models = sorted(sf.model.unique())
        sets = {m: set(map(tuple, sf.loc[sf.model == m, ["student_id", "pair_id"]].to_numpy())) for m in models}
        for i, a in enumerate(models):
            for b in models[i+1:]:
                result["pair_intersections"].append({"split": split, "model_a": a, "model_b": b, "intersection": len(sets[a]&sets[b]), "only_a": len(sets[a]-sets[b]), "only_b": len(sets[b]-sets[a])})
    return result


def stage_aggregates(frame, stage, thresholds):
    failure = 1-frame.y.to_numpy(int)
    risk = 1-frame[f"p{stage}"].to_numpy(float)
    return {
        "calibration": calibration_metrics(failure, risk),
        "policies": {policy: screening_metrics(failure, risk, thresholds[policy]["threshold"]) for policy in POLICIES},
    }


def fit_lock(df, paths):
    if set(df.split) != {"validation"}:
        raise ValueError("Threshold-lock phase requires validation-only input: obtain validation file before confirmation append")
    models = {}
    for model, frame in df.groupby("model"):
        stages = {}
        for stage in STAGES:
            thresholds = fit_thresholds(frame, stage)
            stages[stage] = {"thresholds": thresholds, "validation": stage_aggregates(frame, stage, thresholds)}
        models[model] = {"pairs": len(frame), "students": frame.student_id.nunique(), "stages": stages}
    return {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "protocol_sha256": sha256(Path(__file__).with_name("locked_protocol.md")),
        "script_sha256": sha256(__file__), "environment": environment(),
        "inputs": [{"path": str(Path(p).resolve()), "sha256": sha256(p)} for p in paths],
        "validation_rows_sha256": validation_digest(df), "models": models,
        "expected_models_not_in_this_family_run": sorted(EXPECTED_MODELS-set(models)),
        "coverage": coverage(df),
        "parameters": {"recall_target": 0.80, "workload_target": 0.30, "ties": "include risk >= threshold", "bootstrap_seed": SEED, "bootstrap_samples": 1000, "ece_bins": 10, "nll_epsilon": EPS},
    }


def safe_divide(a, b):
    return np.divide(a, b, out=np.full(np.broadcast_shapes(a.shape, b.shape), np.nan), where=b != 0)


def bootstrap_stage(frame, stage, thresholds, codes, weights):
    n_students = weights.shape[1]
    risk = 1-frame[f"p{stage}"].to_numpy(float)
    failure = 1-frame.y.to_numpy(int)
    clipped = np.clip(risk, EPS, 1-EPS)
    bins = np.minimum((risk*10).astype(int), 9)
    columns = [np.ones(len(frame)), failure, risk, (risk-failure)**2, -failure*np.log(clipped)-(1-failure)*np.log(1-clipped)]
    for b in range(10):
        mask = (bins == b).astype(float)
        columns.extend([mask, mask*risk, mask*failure])
    for policy in POLICIES:
        threshold = thresholds[policy]["threshold"]
        flags = (risk >= threshold).astype(float) if threshold is not None else np.zeros(len(frame))
        columns.extend([flags, flags*failure])
    sums = np.zeros((n_students, len(columns)))
    np.add.at(sums, codes, np.column_stack(columns))
    totals = weights @ sums
    n, nf, sr, sb, sn = totals[:, :5].T
    ece = np.zeros(len(weights))
    for b in range(10):
        count, br, by = totals[:, 5+3*b:8+3*b].T
        ece += np.abs(br-by)/n
    stats = {"brier": sb/n, "nll": sn/n, "mean_risk": sr/n, "calibration_bias": (sr-nf)/n, "ece_10_equal_width": ece}
    policy_stats = {}
    for i, policy in enumerate(POLICIES):
        if thresholds[policy]["threshold"] is None:
            policy_stats[policy] = None
            continue
        flagged, flagged_fail = totals[:, 35+2*i:37+2*i].T
        policy_stats[policy] = {"workload": flagged/n, "failure_recall": safe_divide(flagged_fail,nf), "failure_miss_rate": safe_divide(nf-flagged_fail,nf), "ppv": safe_divide(flagged_fail,flagged), "nonfailure_flag_rate": safe_divide(flagged-flagged_fail,n-nf)}
    return {"calibration": stats, "policies": policy_stats}


def interval(values, point):
    finite = values[np.isfinite(values)]
    return {"difference_h1_minus_h0": float(point) if point is not None else None, "ci95": np.quantile(finite, [0.025,0.975]).tolist() if len(finite) else None, "valid_bootstrap_replicates": len(finite)}


def evaluate(df, lock, lock_path, paths, bootstrap=1000):
    if sha256(Path(__file__).with_name("locked_protocol.md")) != lock["protocol_sha256"]:
        raise ValueError("Protocol changed after threshold lock; an explicit recorded amendment is required")
    if sha256(__file__) != lock["script_sha256"]:
        raise ValueError("Analysis script changed after threshold lock; an explicit recorded amendment is required")
    if validation_digest(df) != lock["validation_rows_sha256"]:
        raise ValueError("Validation rows/predictions changed after the threshold lock")
    if set(df[df.split == "confirmation"].model) != set(lock["models"]):
        raise ValueError("Confirmation models do not match threshold lock")
    models = {}
    for model, frame in df[df.split == "confirmation"].groupby("model"):
        frame = frame.reset_index(drop=True)
        locked = lock["models"][model]
        agg, boot = {}, {}
        codes, students = pd.factorize(frame.student_id, sort=True)
        rng = np.random.default_rng(SEED)
        weights = rng.multinomial(len(students), np.full(len(students),1/len(students)), size=bootstrap)
        for stage in STAGES:
            thresholds = locked["stages"][stage]["thresholds"]
            agg[stage] = stage_aggregates(frame, stage, thresholds)
            boot[stage] = bootstrap_stage(frame, stage, thresholds, codes, weights)
        contrasts = {"calibration": {}, "policies": {}}
        for metric in boot["H0"]["calibration"]:
            contrasts["calibration"][metric] = interval(boot["H1"]["calibration"][metric]-boot["H0"]["calibration"][metric], agg["H1"]["calibration"][metric]-agg["H0"]["calibration"][metric])
        for policy in POLICIES:
            if any(boot[s]["policies"][policy] is None for s in STAGES):
                contrasts["policies"][policy] = {"feasible": False}
                continue
            contrasts["policies"][policy] = {}
            for metric in boot["H0"]["policies"][policy]:
                points = [agg[s]["policies"][policy][metric] for s in STAGES]
                delta = points[1]-points[0] if all(v is not None for v in points) else None
                contrasts["policies"][policy][metric] = interval(boot["H1"]["policies"][policy][metric]-boot["H0"]["policies"][policy][metric], delta)
        models[model] = {"pairs": len(frame), "students": len(students), "stages": agg, "paired_contrasts": contrasts}
    return {"created_utc": datetime.now(timezone.utc).isoformat(), "estimand": "retrospective oracle-target observed-failure screening; not intervention benefit or policy value", "threshold_lock_sha256": sha256(lock_path), "protocol_sha256": sha256(Path(__file__).with_name("locked_protocol.md")), "script_sha256": sha256(__file__), "environment": environment(), "inputs": [{"path": str(Path(p).resolve()), "sha256": sha256(p)} for p in paths], "bootstrap": {"replicates": bootstrap, "seed": SEED, "unit": "student", "paired": True, "refit_thresholds": False, "refit_models": False}, "coverage": coverage(df), "models": models, "expected_models_not_in_this_family_run": sorted(EXPECTED_MODELS-set(models))}


def self_test():
    fixture = pd.DataFrame({"y": [0,0,0,0,1,1], "pH0": [.1,.2,.2,.9,.1,.95], "pH1": [.1,.2,.2,.9,.1,.95]})
    fitted = fit_thresholds(fixture, "H0")
    assert abs(fitted["validation_recall_80"]["threshold"]-0.1) < 1e-12
    assert abs(fitted["validation_workload_30"]["threshold"]-0.9) < 1e-12
    stats = screening_metrics(1-fixture.y.to_numpy(), 1-fixture.pH0.to_numpy(), .9)
    assert stats["flagged"] == 2 and stats["flagged_failures"] == 1
    assert stats["failure_recall"] == .25 and stats["ppv"] == .5
    assert screening_metrics(np.array([0,0]),np.array([.2,.3]),.9)["ppv"] is None
    assert fit_thresholds(pd.DataFrame({"y": [1,1], "pH0": [.4,.8]}),"H0")["validation_recall_80"]["threshold"] is None
    fixture["student_id"] = ["a","a","b","b","c","c"]
    fixture["pair_id"] = list("123456")
    fixture["model"] = "fixture"
    fixture["split"] = "validation"
    before = validation_digest(fixture)
    combined = pd.concat([fixture, fixture.assign(split="confirmation",student_id="new",y=1,pH0=.99,pH1=.01)])
    assert validation_digest(combined) == before
    codes, students = pd.factorize(fixture.student_id,sort=True)
    bt = bootstrap_stage(fixture,"H0",fitted,codes,np.ones((1,len(students))))
    direct = stage_aggregates(fixture,"H0",fitted)
    for key, val in bt["calibration"].items():
        assert abs(val[0]-direct["calibration"][key]) < 1e-12
    for policy in POLICIES:
        for key,val in bt["policies"][policy].items():
            assert abs(val[0]-direct["policies"][policy][key]) < 1e-12
    assert (bootstrap_stage(fixture,"H1",fitted,codes,np.ones((1,len(students))))["calibration"]["nll"] == bt["calibration"]["nll"]).all()
    return {"passed": True, "checks": ["threshold ranks", "inclusive ties", "zero denominators", "no-failure infeasibility", "validation isolation", "bootstrap sufficient statistics", "identical H0/H1 pairing"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase",choices=["lock","evaluate","self-test"],required=True)
    parser.add_argument("--input",nargs="+",default=[])
    parser.add_argument("--lock",default="research/application/threshold_lock.json")
    parser.add_argument("--output",default="research/application/results.json")
    parser.add_argument("--bootstrap",type=int,default=1000)
    args = parser.parse_args()
    if args.phase == "self-test":
        print(json.dumps(self_test()))
        return
    self_test()
    df = load_inputs(args.input)
    if args.phase == "lock":
        if Path(args.lock).exists():
            raise FileExistsError("Refusing to overwrite a threshold lock; use a distinct explicitly recorded amendment")
        lock = fit_lock(df,args.input)
        write_json(args.lock,lock)
        print(json.dumps({"phase":"lock","path":args.lock,"sha256":sha256(args.lock),"models":list(lock["models"])}))
    else:
        lock = json.loads(Path(args.lock).read_text(encoding="utf-8"))
        result = evaluate(df,lock,args.lock,args.input,args.bootstrap)
        write_json(args.output,result)
        print(json.dumps({"phase":"evaluate","path":args.output,"models":list(result["models"])}))


if __name__ == "__main__":
    main()
