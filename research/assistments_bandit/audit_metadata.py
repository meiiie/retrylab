"""Audit public OSF metadata only; never download participant-level datasets."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
SOURCES = {
    "project": "https://api.osf.io/v2/nodes/zuwf7/",
    "root_files": "https://api.osf.io/v2/nodes/zuwf7/files/osfstorage/",
    "empirical_data_files": "https://api.osf.io/v2/nodes/zuwf7/files/osfstorage/63d7dbe986b9820305baa892/",
}


def fetch_metadata(pair):
    name, url = pair
    request = Request(url, headers={"User-Agent": "AcademicDatasetMetadataAudit/1.0"})
    with urlopen(request, timeout=60) as response:
        body = response.read()
    return name, url, hashlib.sha256(body).hexdigest(), json.loads(body)


def main():
    output = {
        "audited_at_utc": datetime.now(timezone.utc).isoformat(),
        "project_url": "https://osf.io/zuwf7/",
        "paper_doi": "https://doi.org/10.1145/3565472.3592955",
        "scope": "Public metadata and publicly documented schema only",
        "participant_records_downloaded": 0,
        "raw_data_use_status": "Not acquired; optional candidate outside the current core study",
        "sources": [],
        "files": [],
        "schema_source": "https://osf.io/download/yavp9/",
        "license_source": "https://osf.io/download/g3ebk/",
        "license_assessment": {
            "type": "ASSISTments Data Terms of Use, effective 2020-10-30",
            "standard_open_license_verified": False,
            "conditions_observed": [
                "Cite ASSISTments and the specific dataset",
                "No commercial use or reference",
                "Make outcomes freely and openly available",
                "No de-anonymization",
                "No raw-data redistribution; collaborators access original source",
                "Indemnification clause",
            ],
        },
        "task": {
            "domain": "School mathematics",
            "action": "Support video recommendation, not selection of the next programming exercise",
            "observed_reward_definition": "Next problem correct on the first try without additional support",
            "long_term_learning_outcome": False,
        },
        "ope_assessment": {
            "explicit_chosen_action_propensity_in_documented_log_schema": False,
            "epsilon_in_model_history": True,
            "algorithm_and_randomization_flag_in_log": True,
            "per_decision_candidate_set_in_documented_log_schema": False,
            "exact_propensity_reconstruction_verified": False,
            "remaining_requirements": [
                "Recover candidate availability at each decision",
                "Verify random sampling and tie-breaking rules",
                "Join each recommendation to the exact pre-decision model state",
                "Handle model-update delays and missing history dates",
                "Identify algorithm-mixture probability if pooling policies",
                "Audit selection caused by missing next-problem reward",
                "Use pre-decision features and account for repeated students/assignments",
            ],
        },
        "programming_alternative": {
            "name": "RoboMission 2019-12",
            "author_schema_url": "https://raw.githubusercontent.com/adaptive-learning/adaptive-learning-research/master/data/robomission-2019-12/README.md",
            "author_download_folder": "https://drive.google.com/drive/u/0/folders/1WLtWBSfNnLfy-gTF0fPvDKZ-Mge19Qg2",
            "documented_sizes_approximate": {"events": 2600000, "attempts": 160000, "problems": 85},
            "documented_tables": {
                "events.csv": ["id", "event_order", "timestamp", "event_type", "student", "problem", "attempt", "program", "correct", "tools"],
                "attempts.csv": ["id", "student", "problem", "problemset", "start", "solved", "time", "n_edits", "n_executions", "program"],
                "problems.csv": ["id", "name", "statement", "solution", "context", "problemset", "level1", "level2", "level3"],
            },
            "documented_program_format": "MiniCode, condensed RoboCode/Blockly representation",
            "explicit_propensity_in_documented_schema": False,
            "per_decision_candidate_set_in_documented_schema": False,
            "repository_license": "GPL-3.0",
            "separately_hosted_dataset_license_verified": False,
            "license_caution": "Repository/application license must not be assumed to license separately hosted learner data",
            "participant_records_downloaded": 0,
            "recommended_status": "Relevant process-rich programming candidate; not required for current study",
        },
    }
    with ThreadPoolExecutor(max_workers=3) as pool:
        for name, url, sha256, payload in pool.map(fetch_metadata, SOURCES.items()):
            output["sources"].append({"name": name, "url": url, "response_sha256": sha256})
            if name == "project":
                attributes = payload["data"]["attributes"]
                output["project"] = {key: attributes.get(key) for key in (
                    "title", "description", "public", "date_created", "date_modified")}
            else:
                for item in payload["data"]:
                    attributes = item["attributes"]
                    output["files"].append({
                        "source_group": name,
                        "name": attributes["name"],
                        "kind": attributes["kind"],
                        "bytes": attributes.get("size"),
                        "download_url": item["links"].get("download"),
                        "downloaded": False,
                    })
                if payload.get("links", {}).get("next"):
                    output.setdefault("warnings", []).append(f"Unfollowed metadata pagination: {name}")
    destination = ROOT / "audit.json"
    destination.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(destination), "metadata_sources": len(output["sources"]),
                      "listed_files_and_folders": len(output["files"]),
                      "participant_records_downloaded": 0}, indent=2))


if __name__ == "__main__":
    main()
