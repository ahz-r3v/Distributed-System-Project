"""Extract numeric manuscript inputs from the recorded CacheWise experiments.

Reads the experiment repository without changing it. Does not launch GPU jobs.
"""

import argparse
from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import json
from pathlib import Path
import statistics

import numpy as np


PROJECT = Path(__file__).resolve().parents[2]
EVIDENCE = PROJECT / "notes/experiment-evidence"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def distribution(values):
    values = np.sort(np.asarray(values, dtype=float))
    indices = np.unique(np.linspace(0, len(values) - 1, min(512, len(values)), dtype=int))
    return {
        "count": len(values),
        "median": float(np.median(values)),
        "p90": float(np.percentile(values, 90)),
        "minimum": float(values[0]),
        "maximum": float(values[-1]),
        "cdf_x": values[indices].tolist(),
        "cdf_y": ((indices + 1) / len(values)).tolist(),
    }


def prepare(source):
    workload_path = source / "runs/ccds-parallel-13943/comparison/workload.json"
    workload = json.loads(workload_path.read_text())
    report = json.loads((EVIDENCE / "consolidated-comparison.json").read_text())
    assert sha256(workload_path) == report["input_hashes"]["workload.json"]
    prompts, outputs, turns = [], [], []
    tools = defaultdict(list)
    sources = []
    counts = Counter()
    for path in sorted((source / "parsed_traces").glob("*/*/events.json")):
        relative = str(path.relative_to(source))
        checksum = sha256(path)
        assert checksum == workload["source_sha256"][relative], relative
        sources.append({"path": relative, "sha256": checksum})
        counts["source_traces"] += 1
        groups, unique_tools = defaultdict(list), {}
        for event in json.loads(path.read_text()):
            if event["event_type"] == "llm_call":
                groups[event["message_id"]].append(event)
                counts["llm_records"] += 1
            elif event["event_type"] == "tool_call":
                key = event["tool_use_id"]
                if key in unique_tools:
                    previous = unique_tools[key]
                    for field in ["tool_name", "associated_llm_call_id", "result_timestamp"]:
                        assert previous[field] == event[field], "Ambiguous repeated tool ID"
                    if datetime.fromisoformat(event["timestamp"]) < datetime.fromisoformat(previous["timestamp"]):
                        unique_tools[key] = event
                    counts["duplicate_tool_records"] += 1
                else:
                    unique_tools[key] = event
        counts["unique_llm_messages"] += len(groups)
        valid = set()
        for mid, records in groups.items():
            if any(r.get("model") == "<synthetic>" for r in records):
                counts["synthetic_messages_excluded"] += 1
                continue
            prompt = max(
                sum(r.get(k) or 0 for k in (
                    "input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"
                )) for r in records
            )
            output = max(r.get("output_tokens") or 0 for r in records)
            if prompt <= 0 or output <= 0:
                counts["nonpositive_messages_excluded"] += 1
                continue
            prompts.append(prompt)
            outputs.append(output)
            valid.add(mid)
        if valid:
            turns.append(len(valid))
        for event in unique_tools.values():
            if event["associated_llm_call_id"] not in valid:
                continue
            duration = event.get("execution_time_ms")
            if duration is None or duration <= 0:
                counts["unknown_or_nonpositive_tool_durations_excluded"] += 1
                continue
            tools[event["tool_name"]].append(duration / 1000)
    tool_boxes = []
    for name in sorted(tools, key=lambda name: (-len(tools[name]), name))[:6]:
        values = tools[name]
        p5, q1, median, q3, p95 = np.percentile(values, [5, 25, 50, 75, 95])
        tool_boxes.append({
            "label": name, "count": len(values), "whislo": float(p5),
            "q1": float(q1), "med": float(median), "q3": float(q3),
            "whishi": float(p95), "fliers": [],
        })
    selected = [s for s in workload["sessions"] if len(s["turns"]) >= 2][:10]
    raw = source / "runs/ccds-parallel-13943/comparison"
    manifest = json.loads((raw / "baseline-r0/manifest.json").read_text())
    selected_hash = hashlib.sha256(json.dumps(selected, sort_keys=True).encode()).hexdigest()
    assert selected_hash == manifest["selected_workload_sha256"]
    gaps = [t["delay_after_s"] for s in selected for t in s["turns"][:-1]]
    cohort = {
        "segments": len(selected),
        "source_sessions": len({s["source_session"] for s in selected}),
        "requests": sum(len(s["turns"]) for s in selected),
        "prompt_tokens": sum(t["prompt_tokens"] for s in selected for t in s["turns"]),
        "output_tokens": sum(t["output_tokens"] for s in selected for t in s["turns"]),
        "initial_prompt_tokens": sum(s["turns"][0]["prompt_tokens"] for s in selected),
        "transitions": len(gaps), "transitions_at_most_one_second": sum(t <= 1 for t in gaps),
        "maximum_recorded_gap_s": max(gaps),
    }
    unique_prompt = sum(
        s["turns"][0]["prompt_tokens"] + sum(
            current["prompt_tokens"] - previous["prompt_tokens"] - previous["output_tokens"]
            for previous, current in zip(s["turns"], s["turns"][1:])
        ) for s in selected
    )
    useful_tokens = unique_prompt + cohort["output_tokens"]
    metrics = []
    for row in report["runs"]:
        summary_path = raw / row["run"] / "summary.json"
        summary = json.loads(summary_path.read_text())
        assert summary["status"] == "complete" and not summary["errors"]
        requests = [r for s in summary["sessions"] for r in s["requests_detail"]]
        times = [r["latency_s"] for r in requests]
        assert len(requests) == cohort["requests"]
        assert np.isclose(statistics.mean(s["llm_time_s"] for s in summary["sessions"]),
                          row["mean_session_llm_time_s"], rtol=1e-12)
        metrics.append({
            "run": row["run"], "policy": row["policy"],
            "summary_sha256": sha256(summary_path),
            "request_p50_s": float(np.percentile(times, 50)),
            "request_p90_s": float(np.percentile(times, 90)),
            "request_p99_s": float(np.percentile(times, 99)),
            "maximum_request_s": max(times),
            "useful_tokens_per_s": useful_tokens / summary["elapsed_s"],
            "requests_per_s": len(requests) / summary["elapsed_s"],
        })
    corpus = {
        "scope": "Released source traces, including training traces, for descriptive analysis only; not the serving evaluation cohort.",
        "method": "One non-synthetic message per (source trace, message_id), positive prompt and output usage; prompt includes cache creation and reads; maximum observed usage per message. No model-length filter. Tools deduplicated by tool_use_id within source trace, requiring identical tool, parent message, and result time and retaining the earliest launch; positive completed durations associated with included messages. ECDF plots retain up to 512 observed ranks per distribution.",
        "counts": dict(counts), "source_files": sources,
        "prompt": distribution(prompts), "output": distribution(outputs),
        "turns": distribution(turns), "tool_boxes": tool_boxes,
        "serving_cohort": cohort,
        "workload_sha256": sha256(workload_path),
    }
    additional = {
        "source_report_sha256": sha256(EVIDENCE / "consolidated-comparison.json"),
        "method": "Linear-interpolated latency percentiles computed within each 83-request run; summarize the three per-run values by arithmetic mean. Useful work counts each new prompt token and output token once per segment; rates divide by whole-run elapsed time including tool waits.",
        "unique_prompt_tokens_per_run": unique_prompt,
        "useful_tokens_per_run": useful_tokens, "runs": metrics,
    }
    for name, data in [("workload-characterization.json", corpus),
                       ("replication-additional-metrics.json", additional)]:
        (EVIDENCE / name).write_text(json.dumps(data, indent=2) + "\n")
    print(json.dumps({"corpus_counts": corpus["counts"],
                      "prompt_median": corpus["prompt"]["median"],
                      "output_median": corpus["output"]["median"],
                      "turns_median": corpus["turns"]["median"],
                      "serving_cohort": cohort, "useful_tokens": useful_tokens}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    prepare(parser.parse_args().source_root.resolve())
