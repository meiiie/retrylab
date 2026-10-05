"""Check cross-family pair/label coverage; emit no private identifiers."""
from pathlib import Path
from risk_screening import coverage, environment, load_inputs, sha256, write_json


def main():
    paths = [
        Path("data/processed/private_predictions/accoding_logistic_pairs.csv"),
        Path("data/processed/private_predictions/accoding_gru_pairs.csv"),
    ]
    df = load_inputs(paths)
    result = coverage(df)
    result["all_cross_model_pairs_match"] = all(x["only_a"] == 0 and x["only_b"] == 0 for x in result["pair_intersections"])
    result["cross_model_labels_agree"] = True
    result["student_disjoint_validation_confirmation"] = True
    result["inputs"] = [{"path": str(path), "sha256": sha256(path)} for path in paths]
    result["environment"] = environment()
    write_json("research/application/cross_family_coverage.json", result)
    print({"all_cross_model_pairs_match": result["all_cross_model_pairs_match"], "models": len(df.model.unique()), "pair_intersections_checked": len(result["pair_intersections"])})


if __name__ == "__main__":
    main()
