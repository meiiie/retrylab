"""Inspect CodeBench archives as data; never extract or execute student code."""
import argparse
import collections
import datetime
import hashlib
import json
import pathlib
import re
import statistics
import tarfile


def summary(values):
    values = sorted(values)
    if not values:
        return {"n": 0}
    return {"n": len(values), "min": values[0], "median": statistics.median(values),
            "max": values[-1], "mean": statistics.mean(values)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=pathlib.Path)
    parser.add_argument("--out", type=pathlib.Path, default=pathlib.Path("research/codebench"))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    with args.archive.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    counts = collections.Counter()
    bytes_by_type = collections.Counter()
    classes, students, exercises, user_ids = set(), set(), set(), set()
    student_exercises = collections.defaultdict(set)
    event_types = collections.Counter()
    execution_fields = collections.Counter()
    error_types = collections.Counter()
    grade_values = collections.Counter()
    assessment_types = collections.Counter()
    assessment_fields = collections.Counter()
    assessment_windows = []
    sample_paths = collections.defaultdict(list)
    license_paths = []
    unsafe_paths = []
    execution_counts = []
    submission_counts = []
    time_min, time_max = None, None
    sampled_editor_events = collections.Counter()
    sampled_editor_files = 0
    metadata_examples = []
    text_encodings = collections.Counter()

    def decode_data(raw):
        try:
            decoded = raw.decode("utf-8")
            text_encodings["utf-8"] += 1
            return decoded
        except UnicodeDecodeError:
            text_encodings["cp1252_fallback"] += 1
            return raw.decode("cp1252", errors="replace")
    inventory = args.out / "archive_inventory_2016_1.tsv"
    with inventory.open("w", encoding="utf-8") as inv, tarfile.open(args.archive, "r|gz") as archive:
        inv.write("path\ttype\tsize_bytes\n")
        for member in archive:
            path = pathlib.PurePosixPath(member.name)
            if path.is_absolute() or ".." in path.parts or member.issym() or member.islnk():
                unsafe_paths.append(member.name)
            if not member.isfile():
                counts["directory_or_other"] += 1
                continue
            counts["files"] += 1
            parts = path.parts
            kind = "other"
            if "users" in parts:
                pos = parts.index("users")
                if pos and len(parts) > pos + 1:
                    classroom = "/".join(parts[:pos])
                    student = "/".join(parts[:pos + 2])
                    classes.add(classroom)
                    students.add(student)
                    user_ids.add(parts[pos + 1])
                    kind = parts[pos + 2] if len(parts) > pos + 2 else "other"
                    if kind in {"codes", "executions", "codemirror"}:
                        match = re.match(r"(\d+)_(\d+)\.", path.name)
                        if match:
                            exercise = match.group(2)
                            exercises.add(exercise)
                            student_exercises[student].add(exercise)
            elif "assessments" in parts or "assignments" in parts:
                kind = "assessments"
            counts[kind + "_files"] += 1
            bytes_by_type[kind] += member.size
            if len(sample_paths[kind]) < 3:
                sample_paths[kind].append(member.name)
            inv.write(f"{member.name}\t{kind}\t{member.size}\n")
            if any(word in path.name.lower() for word in ("license", "licence", "readme", "copyright", "terms")):
                license_paths.append(member.name)
            if kind == "executions":
                text = decode_data(archive.extractfile(member).read())
                headers = list(re.finditer(r"^==[ \t]*(TEST|SUBMITION)[ \t]*\((\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\)[ \t]*\r?$", text, re.MULTILINE))
                execution_counts.append(len(headers))
                local_submits = 0
                for i, match in enumerate(headers):
                    event = match.group(1).strip()
                    timestamp = match.group(2).strip()
                    time_min = min(time_min, timestamp) if time_min else timestamp
                    time_max = max(time_max, timestamp) if time_max else timestamp
                    event_types[event] += 1
                    chunk = text[match.end():headers[i+1].start() if i+1 < len(headers) else len(text)]
                    execution_fields.update(re.findall(r"^-- ([A-Z][A-Z ]+):", chunk, re.MULTILINE))
                    error_types.update(re.findall(r"\b([A-Za-z]+(?:Error|Exception)):", chunk))
                    if event.startswith("SUBMI"):
                        local_submits += 1
                        grade = re.search(r"^-- GRADE:\s*\r?\n\s*([\d.]+)%", chunk, re.MULTILINE)
                        grade_values[grade.group(1) if grade else "missing"] += 1
                submission_counts.append(local_submits)
            elif kind == "assessments":
                text = decode_data(archive.extractfile(member).read())
                pairs = dict(re.findall(r"^---- ([^:\r\n]+):\s*([^\r\n]*)", text, re.MULTILINE))
                assessment_fields.update(pairs.keys())
                assessment_types[pairs.get("type", "missing")] += 1
                assessment_windows.append({"path": member.name, "start": pairs.get("start"),
                                           "end": pairs.get("end"), "type": pairs.get("type"),
                                           "total_exercises": pairs.get("total_exercises"),
                                           "has_alternative_exercises": " or " in text})
                if len(metadata_examples) < 3:
                    metadata_examples.append({"path": member.name, "fields": pairs})
            elif kind == "codemirror" and sampled_editor_files < 20:
                sampled_editor_files += 1
                text = decode_data(archive.extractfile(member).read())
                for line in text.splitlines():
                    fields = line.split("#", 2)
                    if len(fields) >= 2:
                        sampled_editor_events[fields[1]] += 1
    manifest = {
        "source_page": "https://codebench.icomp.ufam.edu.br/dataset/",
        "download_url": "https://codebench.icomp.ufam.edu.br/dataset/files/cb_dataset_2016_1_v1.81.tar.gz",
        "dataset": "UFAM CodeBench", "version": "1.81", "semester": "2016-1",
        "listed_release_date": "2024-10-24", "http_last_modified": "Fri, 12 Aug 2022 10:58:34 GMT",
        "http_content_length": 174487574, "archive_path": str(args.archive.resolve()),
        "archive_size_bytes": args.archive.stat().st_size, "sha256": digest.hexdigest(),
        "audit_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "access": "Public direct HTTPS download; no login or terms acceptance prompt encountered",
        "license": "No explicit license found on landing page or named license/readme/terms archive files; redistribution rights not established",
        "student_code_executed": False, "archive_extracted": False,
    }
    result = {
        "manifest": manifest, "counts": dict(counts), "uncompressed_bytes_by_type": dict(bytes_by_type),
        "class_count_from_paths": len(classes), "student_class_records_from_paths": len(students),
        "unique_user_ids_from_paths": len(user_ids),
        "unique_exercise_ids_from_paths": len(exercises),
        "distinct_exercises_per_student_class": summary([len(v) for v in student_exercises.values()]),
        "execution_events": dict(event_types), "execution_record_field_occurrences": dict(execution_fields),
        "error_type_mentions": dict(error_types), "submission_grade_percent_counts": dict(grade_values),
        "execution_events_per_log": summary(execution_counts),
        "submission_events_per_log": summary(submission_counts),
        "first_execution_timestamp_lexical": time_min, "last_execution_timestamp_lexical": time_max,
        "assessment_types": dict(assessment_types), "assessment_fields": dict(assessment_fields),
        "assessment_windows": assessment_windows, "sample_paths": dict(sample_paths),
        "metadata_examples": metadata_examples, "named_license_or_readme_files": license_paths,
        "unsafe_archive_member_paths": unsafe_paths,
        "editor_event_sample": {"files_sampled": sampled_editor_files, "counts": dict(sampled_editor_events)},
        "decoded_text_files_by_encoding": dict(text_encodings),
        "limitations": [
            "Audit parses text records only; no student code is executed.",
            "Learner counts are unique semester/class/user paths, not deduplicated people across classes.",
            "No confirmed randomized logging policy or propensity scores.",
            "Source page samples show demographic user.data; those files were not read for this audit.",
            "Assessment availability can be partly reconstructed from start/end and exercise IDs, but this does not identify assignment probabilities.",
            "No exercise statement, expert misconception label, or KC tag is inferred merely from an exercise ID.",
            "Named-file scan cannot prove that license text is absent from every data file.",
        ],
    }
    (args.out / "download_manifest_2016_1.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (args.out / "audit_2016_1.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"manifest": manifest, "counts": dict(counts), "classes": len(classes),
                      "student_class_records": len(students), "unique_exercises": len(exercises),
                      "event_types": dict(event_types), "assessment_types": dict(assessment_types),
                      "license_files": license_paths}, indent=2))


if __name__ == "__main__":
    main()
