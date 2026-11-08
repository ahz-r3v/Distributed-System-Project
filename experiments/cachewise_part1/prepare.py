"""Freeze cohorts using trace metadata, before observing new policy outcomes."""

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

from common import atomic_json, checksum, digest, first_use_tokens


HERE = Path(__file__).resolve().parent


def rank(seed, category, name):
    return hashlib.sha256(f"{seed}:{category}:{name}".encode()).hexdigest()


def exclusion_reasons(session, rules, training):
    turns = session["turns"]
    reasons = []
    if session["source_session"] in training:
        reasons.append("training_source")
    if not rules["minimum_turns"] <= len(turns) <= rules["maximum_turns"]:
        reasons.append("turn_budget")
    if sum(t["delay_after_s"] for t in turns) > rules["maximum_total_recorded_wait_seconds"]:
        reasons.append("recorded_wait_budget")
    if sum(t["prompt_tokens"] for t in turns) > rules["maximum_summed_prompt_tokens"]:
        reasons.append("prompt_work_budget")
    if sum(t["output_tokens"] for t in turns) > rules["maximum_summed_output_tokens"]:
        reasons.append("output_work_budget")
    return reasons


def round_robin(groups, sources, seed):
    queues = {
        source: sorted(groups[source], key=lambda s: rank(seed, "segment", s["id"]))
        for source in sorted(sources, key=lambda s: rank(seed, "order", s))
    }
    result = []
    for index in range(max(map(len, queues.values()))):
        result.extend(rows[index] for rows in queues.values() if index < len(rows))
    return result


def build(workload, protocol, historical_sources):
    rules, seed = protocol["selection"], protocol["selection_seed"]
    training = set(workload["training_sessions"])
    groups = defaultdict(list)
    excluded = []
    for session in workload["sessions"]:
        reasons = exclusion_reasons(session, rules, training)
        if reasons:
            excluded.append({"segment": session["id"], "source": session["source_session"],
                             "reasons": reasons})
        else:
            groups[session["source_session"]].append(session)
    historical = set(groups) & set(historical_sources)
    remaining = sorted(set(groups) - historical, key=lambda s: rank(seed, "source", s))
    if len(remaining) < 20:
        raise ValueError("Need twenty new eligible sources for disjoint B/C cohorts")
    sources = {"a": historical | set(remaining[:-20]),
               "b": set(remaining[-20:-10]), "c": set(remaining[-10:])}
    assert not sources["a"] & sources["b"]
    assert not sources["a"] & sources["c"]
    assert not sources["b"] & sources["c"]
    settings, selected_workloads = [], {}
    for setting in protocol["settings"]:
        selected = round_robin(groups, sources[setting["cohort"]], seed)[:setting["sessions"]]
        if len(selected) != setting["sessions"]:
            raise ValueError(f"Not enough complete segments for {setting['id']}")
        assert not {s["source_session"] for s in selected} & training
        selected_workloads[setting["id"]] = {**workload, "sessions": selected}
        settings.append({
            **setting, "segment_ids": [s["id"] for s in selected],
            "source_sessions": sorted({s["source_session"] for s in selected}),
            "selected_workload_sha256": digest(selected),
            "requests": sum(len(s["turns"]) for s in selected),
            "prompt_tokens": sum(t["prompt_tokens"] for s in selected for t in s["turns"]),
            "initial_prompt_tokens": sum(s["turns"][0]["prompt_tokens"] for s in selected),
            "recorded_wait_sum_s": sum(t["delay_after_s"] for s in selected for t in s["turns"][:-1]),
            **first_use_tokens(selected),
        })
    smoke = sorted(
        (s for rows in groups.values() for s in rows
         if all(t["prompt_tokens"] + t["output_tokens"] <= 32768 for t in s["turns"][:2])
         and s["turns"][0]["delay_after_s"] <= 5),
        key=lambda s: rank(seed, "smoke", s["id"]),
    )[:2]
    if len(smoke) != 2:
        raise ValueError("Need two short validation segments")
    selected_workloads["smoke"] = {**workload, "sessions": smoke}
    tasks = [{"task": index, "setting": setting["id"], "repeat": repeat}
             for index, (setting, repeat) in enumerate(
                 (setting, repeat) for setting in settings
                 for repeat in range(protocol["repeats"]))]
    return selected_workloads, {
        "settings": settings, "tasks": tasks,
        "source_groups": {k: sorted(v) for k, v in sources.items()},
        "eligible_sources": len(groups), "eligible_segments": sum(map(len, groups.values())),
        "excluded_segments": excluded,
        "exclusion_reason_counts": dict(Counter(r for x in excluded for r in x["reasons"])),
        "full_runs": len(tasks) * len(protocol["policies"]),
    }


def prepare(source, output):
    if output.exists():
        raise FileExistsError("Refusing to replace a frozen selection")
    protocol_path = HERE / "protocol.json"
    protocol = json.loads(protocol_path.read_text())
    original = source / "runs/ccds-parallel-13943/comparison"
    workload_path = original / "workload.json"
    if checksum(workload_path) != protocol["reference_workload_sha256"]:
        raise ValueError("Original prepared workload changed")
    workload = json.loads(workload_path.read_text())
    manifest = json.loads((original / "baseline-r0/manifest.json").read_text())
    historical_sources = set(manifest["source_sessions"])
    workloads, selection = build(workload, protocol, historical_sources)
    output.mkdir(parents=True)
    shutil.copyfile(protocol_path, output / "protocol.json")
    shutil.copyfile(original / "bootstrap.jsonl", output / "bootstrap.jsonl")
    selection.update({
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "protocol_sha256": checksum(protocol_path),
        "original_workload_sha256": checksum(workload_path),
        "bootstrap_sha256": checksum(original / "bootstrap.jsonl"),
        "historical_source_sessions": sorted(historical_sources),
        "selector_sha256": checksum(Path(__file__)),
        "outcome_data_used_for_selection": False,
    })
    for name, data in workloads.items():
        atomic_json(output / f"{name}.json", data)
    atomic_json(output / "selection.json", selection)
    print(json.dumps({"full_runs": selection["full_runs"],
                      "eligible_sources": selection["eligible_sources"],
                      "settings": selection["settings"]}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.source_root.resolve(), args.output.resolve())
