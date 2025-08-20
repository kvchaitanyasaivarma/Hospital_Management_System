#!/usr/bin/env python3
import json, os, sys, hashlib, datetime


def load_semgrep(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def safe_parse_message(msg):
    msg = (msg or "").strip()
    # Expect the message to be a single JSON object with dcx_entry
    try:
        parsed = json.loads(msg)
        if isinstance(parsed, dict) and "dcx_entry" in parsed:
            return parsed["dcx_entry"]
    except Exception:
        pass
    return None


def stable_key(entry, repo):
    # Stable identity using repo + dataset + variable + classification + (file scope)
    dataset = entry.get("dataset", "").strip()
    variable = entry.get("variable", "").strip()
    classification = entry.get("classification", "").strip()
    location = entry.get("location", "").strip()  # file:line
    file_path = location.split(":")[0] if ":" in location else location
    raw = f"{repo}|{dataset}|{variable}|{classification}|{file_path}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def env_meta():
    return {
        "repo": os.getenv("GITHUB_REPOSITORY") or os.getenv("CI_PROJECT_PATH") or "",
        "branch": os.getenv("GITHUB_HEAD_REF") or os.getenv("GITHUB_REF_NAME") or "",
        "commit": os.getenv("GITHUB_SHA") or os.getenv("CI_COMMIT_SHA") or "",
        "pr_number": os.getenv("GITHUB_EVENT_NUMBER") or os.getenv("PR_NUMBER") or "",
        "generated_at": datetime.datetime.utcnow().replace(microsecond=0).isoformat()
        + "Z",
        "runner": "dcx_catalog.py@v0.1",
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: dcx_catalog.py semgrep.json > dcx_catalog.json", file=sys.stderr)
        sys.exit(2)
    sem = load_semgrep(sys.argv[1])
    meta = env_meta()
    repo = meta["repo"]

    entries = []
    keys = set()
    results = sem.get("results", [])
    for r in results:
        extra = r.get("extra", {})
        msg = extra.get("message", "")
        entry = safe_parse_message(msg)
        if not entry:
            continue

        # Normalize fields
        entry["dataset"] = entry.get("dataset", "").strip() or "unknown_dataset"
        entry["variable"] = entry.get("variable", "").strip() or "unknown_variable"
        entry["type"] = entry.get("type", "").strip() or "unknown"
        entry["classification"] = (
            entry.get("classification", "").strip() or "unspecified"
        )
        entry["subclass"] = entry.get("subclass", "").strip() or ""
        entry["location"] = entry.get("location", "").strip() or f"{r.get('path','')}:?"
        entry["source"] = entry.get("source", "").strip() or r.get("check_id", "")

        # Ambiguity heuristic
        warnings = []
        if entry["type"] == "unknown":
            warnings.append("Unknown type — manual review suggested.")
        if (
            entry["dataset"].startswith("application_")
            and entry["classification"] != "application"
        ):
            warnings.append("Classification/dataset mismatch.")
        entry["warnings"] = warnings

        key = stable_key(entry, repo)
        if key in keys:
            # duplicate → skip; could merge in future
            continue
        keys.add(key)
        entries.append(entry)

    catalog = {**meta, "entries": entries, "count": len(entries)}
    json.dump(catalog, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
