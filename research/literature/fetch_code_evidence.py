"""Read pinned public repository files through GitHub CLI; never execute them."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess, json, base64, hashlib

BASE=Path(__file__).resolve().parent
REPOS={
    "oezyurty/ExRec": ["README.md", "exercise_recommender/envs/cluster_vector_env.py", "exercise_recommender/envs/all_kc_envs.py", "exercise_recommender/envs/kc_evolution_envs.py", "exercise_recommender/envs/worst_kc_envs.py", "exercise_recommender/envs/ground_truth_env.py", "exercise_recommender/wrappers/calibrationqdkt_wrapper.py"],
    "chanllon/UniER": ["README.md", "Path-level Exercise Recommendation/DLPR/EduSim/metrics/promotion.py"],
    "aims-foundations/dynamic-irt": ["README.md", "dynamic_models/temporal_eval/harness.py", "dynamic_models/temporal_eval/student_split.py", "dynamic_models/temporal_eval/metrics.py"],
    "umass-ml4ed/code-edit-representation": ["README.md"],
    "YangAzure/Code-DKT": ["README.md"],
}

def api(path):
    result=subprocess.run(["gh", "api", path],capture_output=True,check=True)
    return json.loads(result.stdout)

def repo_job(item):
    repo, paths=item
    try:
        commit=api(f"repos/{repo}/commits?until=2026-09-26T23:59:59Z&per_page=1")[0]
        sha=commit["sha"]
        record={"repository":repo,"sha":sha,"committer_date":commit["commit"]["committer"]["date"],"files":[]}
        for path in paths:
            try:
                obj=api(f"repos/{repo}/contents/{path}?ref={sha}")
                content=base64.b64decode(obj["content"])
                local=BASE/"code"/repo.replace("/","__")/path
                local.parent.mkdir(parents=True,exist_ok=True)
                local.write_bytes(content)
                record["files"].append({"path":path,"local_path":str(local.relative_to(BASE)),"sha256":hashlib.sha256(content).hexdigest(),"url":f"https://github.com/{repo}/blob/{sha}/{path}"})
            except Exception as exc:
                record["files"].append({"path":path,"error":str(exc)})
        return record
    except Exception as exc:
        return {"repository":repo,"error":str(exc)}

if __name__=="__main__":
    with ThreadPoolExecutor(max_workers=5) as pool:
        records=list(pool.map(repo_job,REPOS.items()))
    (BASE/"code_manifest.json").write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(records,ensure_ascii=True,indent=2))
