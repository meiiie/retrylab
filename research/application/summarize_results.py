"""Export publication-safe aggregate tables from completed application results."""
import csv
import json
from pathlib import Path


def pct(value):
    return "NA" if value is None else f"{100*value:.2f}%"


def interval_pp(contrast):
    point, ci = contrast["difference_h1_minus_h0"], contrast["ci95"]
    if point is None or ci is None:
        return "NA"
    return f"{100*point:+.3f} [{100*ci[0]:+.3f}, {100*ci[1]:+.3f}]"


def main():
    folder = Path(__file__).resolve().parent
    rows = []
    lines = ["# Completed retrospective screening results", "", "All targets are observed future first-encounter items supplied to both checkpoints. Thresholds are frozen from validation. These measurements do not establish recommendation or intervention benefit.", "", "Differences are H1 minus H0; intervals are paired student bootstrap 95%. Workload and recall must be interpreted jointly. Interval units below are percentage points.", ""]
    for path in sorted(folder.glob("results_*.json")):
        result = json.loads(path.read_text(encoding="utf-8"))
        lines.extend([f"## {path.stem}", "", "| Model / rule | Workload H0 → H1 | Failure recall H0 → H1 | PPV H0 → H1 | Δ workload [95%], pp | Δ recall [95%], pp |", "|---|---:|---:|---:|---:|---:|"])
        for model, entry in result["models"].items():
            for policy in ("validation_recall_80", "validation_workload_30"):
                a, b = [entry["stages"][stage]["policies"][policy] for stage in ("H0", "H1")]
                if not a["feasible"] or not b["feasible"]:
                    lines.append(f"| {model} / {policy} | infeasible | | | | |")
                    continue
                con = entry["paired_contrasts"]["policies"][policy]
                lines.append(f"| {model} / {policy} | {pct(a['workload'])} → {pct(b['workload'])} | {pct(a['failure_recall'])} → {pct(b['failure_recall'])} | {pct(a['ppv'])} → {pct(b['ppv'])} | {interval_pp(con['workload'])} | {interval_pp(con['failure_recall'])} |")
                for stage in ("H0", "H1"):
                    record = entry["stages"][stage]["policies"][policy]
                    rows.append({"source": path.name, "model": model, "stage": stage, "policy": policy, "students": entry["students"], **record})
        lines.append("")
    if not rows:
        raise RuntimeError("No completed application results")
    with (folder / "screening_metrics.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (folder / "results_table.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"aggregate_rows": len(rows), "table": str(folder / "results_table.md")}))


if __name__ == "__main__":
    main()
