"""Local checks and append-only experiment runs; standard library only."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
APP_URL = "http://127.0.0.1:8773"  # the user's running app: the address the browser and demo suites require
SUITES = {
    "fast": [["-m", "unittest", "discover", "-s", "tools/tests", "-v"]],
    "policy": [["-m", "unittest", "discover", "-s", folder, "-v"] for folder in
               ("research/policy/tests", "research/catalog_policy/tests", "research/accoding_policy/tests")],
    "backend": [["-m", "unittest", "discover", "-s", "app/tests", "-p", pattern, "-v"]
                for pattern in ("test_engine.py", "test_realdata.py", "test_tutor.py")],
    # The classic checks load /classic and default to APP_URL; the studio checks default to development ports
    # (8782-8784), so they get the same address explicitly.
    "browser": [[f"app/tests/{name}.py"] for name in
                ("browser_check", "practice_browser_check", "practice_recovery_check", "policy_browser_check",
                 "realdata_browser_check")]
               + [[f"app/tests/{name}.py", "--url", APP_URL] for name in
                  ("studio_shell_check", "studio_learners_session_check", "studio_practice_eval_check",
                   "studio_tour_check", "studio_c_practice_check")],
    "demo": [["app/tests/demo_readiness_check.py", "--faults"],
             ["app/tests/launch_recovery_check.py"],
             ["app/tests/desktop_launch_check.py"]],
}


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def within(root, relative):
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError(f"Expected relative path: {relative!r}")
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or path == root.resolve():
        raise ValueError(f"Path escapes its root: {relative}")
    return path


def verify_protected(root=ROOT, staged=False):
    errors = []
    manifest = read_json(root / "harness/protected.json")
    for item in manifest["files"]:
        path = within(root, item["path"])
        if not path.is_file() or digest(path) != item["sha256"]:
            errors.append(f"Protected artifact missing/changed: {item['path']}")
    if staged:
        names = subprocess.run(["git", "diff", "--cached", "--name-only", "-z"], cwd=root,
                               capture_output=True, check=True).stdout.decode("utf-8").split("\0")
        for item in manifest["files"]:
            if item["path"] in names:
                blob = subprocess.run(["git", "show", ":" + item["path"]], cwd=root, capture_output=True)
                if blob.returncode or hashlib.sha256(blob.stdout).hexdigest() != item["sha256"]:
                    errors.append(f"Protected staged content changed/deleted: {item['path']}")
    return errors


def validate_board(root=ROOT):
    board = read_json(root / "harness/workboard.json")
    tasks = board["tasks"]
    ids = [t["id"] for t in tasks]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate task IDs")
    by_id = {t["id"]: t for t in tasks}
    for task in tasks:
        if task["status"] not in {"planned", "in_progress", "complete"}:
            raise ValueError(f"Unknown status: {task['id']}")
        for dependency in task.get("depends_on", []):
            if dependency not in by_id:
                raise ValueError(f"Missing dependency: {dependency}")
            if task["status"] == "complete" and by_id[dependency]["status"] != "complete":
                raise ValueError(f"Completed task has unfinished dependency: {task['id']}")
        evidence = task.get("evidence", [])
        if task["status"] == "complete" and not evidence:
            raise ValueError(f"Completion without evidence: {task['id']}")
        for name in evidence:
            if not within(root, name).is_file():
                raise ValueError(f"Missing evidence: {name}")
        for run_id in task.get("runs", []):
            errors = verify_run(run_id, root)
            if errors:
                raise ValueError(f"Invalid run evidence {run_id}: {'; '.join(errors)}")
    visited, stack = set(), set()

    def visit(key):
        if key in stack:
            raise ValueError("Task dependency cycle")
        if key in visited:
            return
        stack.add(key)
        for dependency in by_id[key].get("depends_on", []):
            visit(dependency)
        stack.remove(key)
        visited.add(key)

    for key in ids:
        visit(key)
    return board


def validate_protocol(protocol, root=ROOT):
    for field in ("id", "question", "data_scope", "claim_scope", "primary_metric", "split", "selection"):
        if not protocol.get(field):
            raise ValueError(f"Protocol requires {field}")
    if type(protocol["split"].get("test_previously_inspected")) is not bool:
        raise ValueError("Declare split.test_previously_inspected as a boolean")
    if not protocol.get("seeds") or not all(type(s) is int for s in protocol["seeds"]):
        raise ValueError("Declare integer seeds")
    for group in ("inputs", "code", "output_files"):
        if not isinstance(protocol.get(group), list):
            raise ValueError(f"Declare list {group}")
        if group != "inputs" and not protocol[group]:
            raise ValueError(f"Empty {group}")
        if len(protocol[group]) != len(set(protocol[group])):
            raise ValueError(f"Duplicate paths in {group}")
        for name in protocol[group]:
            path = within(root, name)
            normalized = path.relative_to(root.resolve())
            if group == "output_files" and (normalized.as_posix() in {"protocol.json", "record.json", "output.log", "runner.py"}
                                             or normalized.parts[0] == "source"):
                raise ValueError(f"Output collides with run provenance: {name}")
            if group != "output_files" and not path.is_file():
                raise ValueError(f"Missing {group} file: {name}")
    return protocol


def run_experiment(run_id, protocol_path, command, root=ROOT):
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", run_id):
        raise ValueError("Run ID must be 1–64 lowercase letters/digits, hyphen or underscore")
    if not command:
        raise ValueError("Experiment command is required after --")
    protocol_file = within(root, protocol_path)
    protocol = validate_protocol(read_json(protocol_file), root)
    errors = verify_protected(root)
    if errors:
        raise ValueError("; ".join(errors))
    run = root / "research/runs" / run_id
    run.mkdir(parents=True, exist_ok=False)
    write_json(run / "protocol.json", protocol)
    shutil.copy2(Path(__file__), run / "runner.py")
    input_names = list(dict.fromkeys([protocol_path, *protocol["inputs"], *protocol["code"]]))
    inputs = {name: digest(within(root, name)) for name in input_names}
    for name in protocol["code"]:
        destination = within(run / "source", name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(within(root, name), destination)
    args = [part.replace("{python}", sys.executable).replace("{run}", str(run)) for part in command]
    record = {"id": run_id, "state": "running", "started_utc": now(), "command": args,
              "cwd": str(root), "python": sys.version, "platform": platform.platform(),
              "protocol_sha256": digest(run / "protocol.json"), "inputs": inputs,
              "runner_sha256": digest(run / "runner.py"),
              "claim_scope": protocol["claim_scope"], "pid": os.getpid()}
    write_json(run / "record.json", record)
    failure, code = None, -1
    try:
        with (run / "output.log").open("w", encoding="utf-8") as log:
            result = subprocess.run(args, cwd=root, stdout=log, stderr=subprocess.STDOUT,
                                    timeout=protocol.get("timeout_seconds", 3600),
                                    env={**os.environ, "PYTHONUTF8": "1"})
            code = result.returncode
    except (OSError, subprocess.TimeoutExpired) as exc:
        failure = str(exc)
    changed = [name for name, hash_value in inputs.items()
               if not within(root, name).is_file() or digest(within(root, name)) != hash_value]
    errors = verify_protected(root)
    outputs, missing = {}, []
    for name in protocol["output_files"]:
        path = within(run, name)
        if path.is_file():
            outputs[name] = digest(path)
        else:
            missing.append(name)
    record.update({"finished_utc": now(), "exit_code": code, "error": failure,
                   "changed_inputs": changed, "protected_errors": errors,
                   "outputs": outputs, "missing_outputs": missing,
                   "state": "complete" if code == 0 and not (failure or changed or errors or missing) else "failed"})
    write_json(run / "record.json", record)
    return record


def verify_run(run_id, root=ROOT):
    run = within(root / "research/runs", run_id)
    record = read_json(run / "record.json")
    errors = []
    if record["state"] != "complete":
        errors.append(f"Run is {record['state']}")
    if digest(run / "protocol.json") != record["protocol_sha256"]:
        errors.append("Run protocol changed")
    if "runner_sha256" in record:
        if not (run / "runner.py").is_file() or digest(run / "runner.py") != record["runner_sha256"]:
            errors.append("Runner snapshot changed/missing")
    protocol = read_json(run / "protocol.json")
    if set(record.get("outputs", {})) != set(protocol["output_files"]):
        errors.append("Declared output set differs")
    for name, hash_value in record.get("outputs", {}).items():
        path = within(run, name)
        if not path.is_file() or digest(path) != hash_value:
            errors.append(f"Output changed/missing: {name}")
    for name in protocol["code"]:
        path = within(run / "source", name)
        if not path.is_file() or digest(path) != record["inputs"][name]:
            errors.append(f"Source snapshot changed/missing: {name}")
    return errors


def checks(suite, staged=False):
    started = time.monotonic()
    report = {"started_utc": now(), "suite": suite, "errors": [], "commands": []}
    try:
        report["errors"].extend(verify_protected(staged=staged))
        validate_board()
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as exc:
        report["errors"].append(str(exc))
    directory = ROOT / ".harness/reports" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    directory.mkdir(parents=True)
    selected = list(SUITES) if suite == "all" else [suite]
    if not report["errors"]:
        for name in selected:
            if name in {"browser", "demo"}:
                try:
                    with urllib.request.urlopen(f"{APP_URL}/api/health", timeout=3) as response:
                        if json.load(response).get("app") != "RetryLab":
                            raise ValueError("Unexpected application on port 8773")
                except (OSError, ValueError) as exc:
                    report["errors"].append(f"Browser prerequisite failed: {exc}. Start python app/launch.py --no-browser and retry.")
                    continue
            for index, arguments in enumerate(SUITES[name]):
                path = directory / f"{name}-{index}.log"
                command = [sys.executable, "-X", "utf8", *arguments]
                error, code = None, -1
                try:
                    with path.open("w", encoding="utf-8") as log:
                        code = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                              timeout=600).returncode
                except (OSError, subprocess.TimeoutExpired) as exc:
                    error = str(exc)
                report["commands"].append({"command": command, "exit_code": code,
                                           "error": error, "log": str(path)})
                if code != 0:
                    report["errors"].append(f"Failed {name}; see {path}")
    report["errors"].extend(verify_protected())
    report.update({"passed": not report["errors"], "seconds": round(time.monotonic() - started, 3)})
    write_json(directory / "report.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    sub.add_parser("doctor")
    sub.add_parser("status")
    check = sub.add_parser("check")
    check.add_argument("--suite", choices=[*SUITES, "all"], default="fast")
    check.add_argument("--staged", action="store_true")
    run = sub.add_parser("run")
    run.add_argument("run_id")
    run.add_argument("--protocol", required=True)
    verify = sub.add_parser("verify-run")
    verify.add_argument("run_id")
    arguments = sys.argv[1:]
    command = []
    if "--" in arguments:
        boundary = arguments.index("--")
        arguments, command = arguments[:boundary], arguments[boundary + 1:]
    args = parser.parse_args(arguments)
    try:
        if args.operation == "doctor":
            packages = {}
            for name in ("flask", "numpy", "pandas", "scikit-learn", "torch", "playwright"):
                try:
                    packages[name] = importlib.metadata.version(name)
                except importlib.metadata.PackageNotFoundError:
                    packages[name] = "not installed (optional suite dependency)"
            print(json.dumps({"root": str(ROOT), "python": sys.executable,
                              "git": shutil.which("git"), "node": shutil.which("node"),
                              "packages": packages, "protected_errors": verify_protected()}, indent=2))
            return 0 if not verify_protected() else 1
        if args.operation == "status":
            board = validate_board()
            print(board["objective"])
            for task in board["tasks"]:
                print(f"[{task['status']}] {task['id']}: {task['title']}")
            print("Next:", board["next_action"])
            return 0
        if args.operation == "check":
            return checks(args.suite, args.staged)
        if args.operation == "run":
            record = run_experiment(args.run_id, args.protocol, command)
            print(json.dumps(record, ensure_ascii=False, indent=2))
            return 0 if record["state"] == "complete" else 1
        errors = verify_run(args.run_id)
        print(json.dumps({"id": args.run_id, "passed": not errors, "errors": errors}, indent=2))
        return int(bool(errors))
    except (ValueError, OSError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
