#!/usr/bin/env python3
import json, sys, hashlib


def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def key(e):
    # cross-run identity: dataset+variable+classification+filePath (not line)
    loc = e.get("location", "")
    file_path = loc.split(":")[0] if ":" in loc else loc
    raw = f"{e.get('dataset','')}|{e.get('variable','')}|{e.get('classification','')}|{file_path}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def index(entries):
    return {key(e): e for e in entries}


def diff(prev, curr):
    prev_idx = index(prev)
    curr_idx = index(curr)
    added_keys = [k for k in curr_idx.keys() if k not in prev_idx]
    removed_keys = [k for k in prev_idx.keys() if k not in curr_idx]
    modified = []
    for k in curr_idx.keys() & prev_idx.keys():
        a, b = prev_idx[k], curr_idx[k]
        # consider modified if any of these fields changed
        watched = ["type", "subclass", "location", "source"]
        if any(a.get(f) != b.get(f) for f in watched):
            modified.append(k)
    return {
        "added": [curr_idx[k] for k in added_keys],
        "removed": [prev_idx[k] for k in removed_keys],
        "modified": [curr_idx[k] for k in modified],
        "summary": f"+{len(added_keys)} / ~{len(modified)} / -{len(removed_keys)}",
    }


def main():
    if len(sys.argv) < 3:
        print(
            "Usage: dcx_delta.py prev_catalog.json curr_catalog.json > dcx_delta.json",
            file=sys.stderr,
        )
        sys.exit(2)
    prev = load(sys.argv[1]) if sys.argv[1] != "-" else {"entries": []}
    curr = load(sys.argv[2])
    out = diff(prev.get("entries", []), curr.get("entries", []))
    json.dump(out, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
