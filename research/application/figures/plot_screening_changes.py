"""Publication-style aggregate-only forest plot of frozen screening rules.

Reads only the completed aggregate result JSON files; does not fit a model,
recompute a threshold, read private predictions, or repeat screening analyses.
"""
from __future__ import annotations

import csv
import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


HERE = Path(__file__).resolve().parent
APPLICATION = HERE.parent
INPUTS = [APPLICATION / "results_logistic.json", APPLICATION / "results_gru.json"]
MODELS = [
    ("all_submissions", "Logistic: all submissions", "o", "#31688E"),
    ("first_attempt", "Logistic: first attempts", "s", "#31688E"),
    ("paired_target", "Logistic: paired targets", "D", "#31688E"),
    ("gru_ALL", "GRU: all submissions", "^", "#A85B28"),
    ("gru_FIRST", "GRU: first attempts", "v", "#A85B28"),
]
POLICIES = ["validation_recall_80", "validation_workload_30"]
METRICS = [("workload", "Flagged workload"), ("failure_recall", "Failure recall")]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    HERE.mkdir(parents=True, exist_ok=True)
    results = [json.loads(path.read_text(encoding="utf-8")) for path in INPUTS]
    all_models = {}
    for result in results:
        assert result["bootstrap"]["replicates"] == 1000
        assert result["bootstrap"]["paired"] is True
        assert result["bootstrap"]["refit_thresholds"] is False
        assert result["bootstrap"]["refit_models"] is False
        all_models.update(result["models"])
    assert set(all_models) == {m[0] for m in MODELS}
    for entry in all_models.values():
        assert entry["pairs"] == 69825 and entry["students"] == 1500

    rows = []
    for model, label, marker, color in MODELS:
        for policy in POLICIES:
            for metric, title in METRICS:
                contrast = all_models[model]["paired_contrasts"]["policies"][policy][metric]
                point = 100 * contrast["difference_h1_minus_h0"]
                low, high = [100 * value for value in contrast["ci95"]]
                assert np.isfinite([point, low, high]).all() and low <= point <= high
                assert contrast["valid_bootstrap_replicates"] == 1000
                rows.append({"model": model, "label": label, "rule": policy, "metric": metric, "difference_pp": point, "ci95_low_pp": low, "ci95_high_pp": high})
    data = {(r["model"], r["rule"], r["metric"]): r for r in rows}

    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 10,
        "axes.titlesize": 11, "axes.labelsize": 10,
        "xtick.labelsize": 9, "ytick.labelsize": 9.5,
        "svg.fonttype": "none", "svg.hashsalt": "aai-screening-2026-09-26",
        "savefig.facecolor": "white", "figure.facecolor": "white",
    })
    fig = plt.figure(figsize=(11.2, 7.1))
    positions = [
        [0.285, 0.555, 0.292, 0.260], [0.655, 0.555, 0.292, 0.260],
        [0.285, 0.195, 0.292, 0.260], [0.655, 0.195, 0.292, 0.260],
    ]
    for row, policy in enumerate(POLICIES):
        for col, (metric, title) in enumerate(METRICS):
            ax = fig.add_axes(positions[row * 2 + col])
            ax.set_axisbelow(True)
            ax.grid(axis="x", color="#E6E8EB", linewidth=0.7)
            ax.axvline(0, color="#444444", linestyle=(0, (3, 3)), linewidth=1.0, zorder=1)
            ax.axhline(2.5, color="#E8EAED", linewidth=0.7)
            for y, (model, label, marker, color) in enumerate(MODELS):
                rec = data[(model, policy, metric)]
                point, low, high = rec["difference_pp"], rec["ci95_low_pp"], rec["ci95_high_pp"]
                ax.errorbar(point, y, xerr=[[point-low], [high-point]], fmt=marker,
                            color=color, markeredgecolor=color, markersize=5.8,
                            elinewidth=1.4, capsize=2.8, capthick=1.1, zorder=3)
            ax.set_ylim(4.6, -0.6)
            ax.set_xlim(-1.05, 1.20)
            ax.set_xticks([-1.0, -0.5, 0.0, 0.5, 1.0])
            ax.set_xticklabels(["−1.0", "−0.5", "0", "+0.5", "+1.0"])
            ax.set_yticks(range(len(MODELS)))
            ax.set_yticklabels([m[1] for m in MODELS] if col == 0 else [])
            ax.tick_params(axis="y", length=0, pad=9)
            ax.tick_params(axis="x", length=3, color="#A0A0A0")
            for spine in ["top", "right", "left"]:
                ax.spines[spine].set_visible(False)
            ax.spines["bottom"].set_color("#B8BDC4")
            ax.set_title(title, pad=11, loc="left", fontweight="semibold")
            if row == 1:
                ax.set_xlabel("H1 − H0 (percentage points)", labelpad=7)

    fig.text(0.035, 0.965, "Retrospective screening: changes after observing resubmissions",
             fontsize=13, fontweight="semibold", ha="left", va="top")
    fig.text(0.035, 0.918, "Point estimates and 95% paired student bootstrap intervals; all five models use the same confirmation pairs.",
             fontsize=9.6, color="#454545", ha="left", va="top")
    fig.text(0.035, 0.858, "80% failure-recall rule\nselected on validation", fontsize=10,
             fontweight="semibold", linespacing=1.35, ha="left", va="top")
    fig.text(0.035, 0.498, "30% workload rule\nselected on validation", fontsize=10,
             fontweight="semibold", linespacing=1.35, ha="left", va="top")
    fig.text(0.035, 0.100, "Thresholds stay frozen: confirmation workload may differ from 30%. Workload changes must be interpreted together with detection.",
             fontsize=9.0, color="#333333", ha="left", va="top")
    fig.text(0.035, 0.071, "69,825 pairs · 1,500 students · 1,000 paired resamples. Nominal intervals; no multiplicity correction.",
             fontsize=9.0, color="#333333", ha="left", va="top")
    fig.text(0.035, 0.042, "The future target item is supplied to both checkpoints; these changes do not estimate an intervention effect.",
             fontsize=9.0, color="#333333", ha="left", va="top")

    png = HERE / "screening_changes.png"
    svg = HERE / "screening_changes.svg"
    fig.savefig(png, dpi=300, metadata={"Software": f"Matplotlib {matplotlib.__version__}"})
    fig.savefig(svg, metadata={"Date": None, "Creator": f"Matplotlib {matplotlib.__version__}"})
    plt.close(fig)
    table = HERE / "screening_changes_data.csv"
    with table.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "Aggregate-only publication-style screening-change figure; no fitting, threshold tuning, or screening rerun",
        "script": {"path": Path(__file__).name, "sha256": sha256(__file__)},
        "inputs": [{"path": "../"+path.name, "sha256": sha256(path)} for path in INPUTS],
        "outputs": [{"path": path.name, "sha256": sha256(path), "bytes": path.stat().st_size} for path in [png, svg, table, HERE / "caption.md"]],
        "environment": {"python": platform.python_version(), "matplotlib": matplotlib.__version__, "numpy": np.__version__},
        "figure": {"width_inches": 11.2, "height_inches": 7.1, "png_dpi": 300, "units": "percentage points", "contrast": "H1 minus H0", "intervals": "95% paired student bootstrap; fixed fitted models and validation thresholds; nominal, not multiplicity adjusted"},
        "checks": {"models": len(all_models), "points": len(rows), "confirmation_pairs_per_model": 69825, "students_per_model": 1500, "valid_bootstrap_replicates_per_interval": 1000, "all_points_and_intervals_finite": True},
    }
    (HERE / "figure_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"png": str(png), "svg": str(svg), "manifest": str(HERE / "figure_manifest.json"), "points": len(rows)}))


if __name__ == "__main__":
    main()
