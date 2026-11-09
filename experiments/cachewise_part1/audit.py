"""Validate each four-policy block and collect only fully audited measurements."""

import argparse
import csv
import json
from pathlib import Path
import statistics
import sys

import numpy as np

from common import atomic_json, checksum, digest, first_use_tokens


def option(command, flag):
    return command[command.index(flag) + 1]


def normalize_command(command):
    command = list(command)
    for flag in ["--scheduling-policy", "--prefix-aware-max-wait-s",
                 "--kv-cache-eviction-policy", "--cachewise-predictor",
                 "--cachewise-bootstrap-path"]:
        if flag in command:
            index = command.index(flag)
            del command[index:index + 2]
    return command


def validate_full_counter(payload, requests):
    if payload["version"] != 1 or payload["pool_instances"] < 1:
        raise ValueError("Full engine counters were not installed")
    if payload["finished_requests"] != requests or payload["duplicate_finish_callbacks"]:
        raise ValueError("Full counters do not cover every completed request exactly once")
    if payload["eviction_checks"] < 1 or payload["allocated_blocks"] < 1:
        raise ValueError("No actual allocation observations")
    if not 0 <= payload["cached_blocks_evicted_for_allocation"] <= payload["allocated_blocks"]:
        raise ValueError("Impossible cache eviction count")
    if payload["cached_blocks_invalidated_elsewhere"] < 0:
        raise ValueError("Invalid cache invalidation count")


def audit_block(root, output, setting, repeat, smoke=False):
    sys.path.insert(0, str(root / "serving_experiment"))
    from inspect_traces import audit_repeats, metric, records
    from replay import select_sessions

    prepared = root / "prepared"
    protocol = json.loads((prepared / "protocol.json").read_text())
    selection = json.loads((prepared / "selection.json").read_text())
    workload_path = prepared / f"{setting['id']}.json"
    workload = json.loads(workload_path.read_text())
    selected = select_sessions(workload, 2 if smoke else setting["sessions"],
                               2 if smoke else 0, 32768 if smoke else 0)
    expected_requests = sum(len(s["turns"]) for s in selected)
    expected_prompt = sum(t["prompt_tokens"] for s in selected for t in s["turns"])
    expected_output = sum(t["output_tokens"] for s in selected for t in s["turns"])
    first_use = first_use_tokens(selected)
    expected_runs = {f"{p}-r{repeat}" for p in protocol["policies"]}
    found_runs = {p.parent.name for p in output.glob("*-r*/manifest.json")}
    if found_runs != expected_runs:
        raise ValueError("Missing, extra, or incomplete policy runs")
    audit = audit_repeats(output)
    environment = json.loads((output / "environment.json").read_text())
    if environment["vllm_revision"] != protocol["engine_revision"]:
        raise ValueError("Unexpected engine base revision")
    if checksum(output / "workload.json") != checksum(workload_path):
        raise ValueError("Executed workload differs from frozen selection")
    if checksum(output / "bootstrap.jsonl") != selection["bootstrap_sha256"]:
        raise ValueError("Predictor bootstrap changed")
    commands, gpu_uuids, rows = [], set(), []
    for policy in protocol["policies"]:
        name = f"{policy}-r{repeat}"
        path = output / name
        manifest = json.loads((path / "manifest.json").read_text())
        if manifest["selected_workload_sha256"] != digest(selected):
            raise ValueError("Manifest uses different selected segments")
        if not manifest["mark_terminal_idle"] or manifest["delay_scale"] != 1 or manifest["oracle"]:
            raise ValueError("Replay treatment differs from frozen protocol")
        result = audit["runs"][name]
        if result["requests"] != expected_requests or result["prompt_tokens"] != expected_prompt:
            raise ValueError("Incomplete request execution")
        if result["output_tokens"] != expected_output or result["preemptions"] != 0:
            raise ValueError("Wrong output lengths or request preemption")
        if result["failed_metric_snapshots"]:
            raise ValueError("Failed server metric snapshot")
        command = json.loads((output / f"{name}-command.json").read_text())
        prefix = policy in {"prefix_only_no_aging", "cachewise_no_aging"}
        predictive = policy in {"eviction_only", "cachewise_no_aging"}
        expected_options = {
            "--scheduling-policy": "prefix_aware" if prefix else "fcfs",
            "--kv-cache-eviction-policy": "predictive" if predictive else "lru",
            "--num-gpu-blocks-override": str(protocol["kv_blocks"]),
            "--max-num-batched-tokens": str(protocol["prefill_chunk_tokens"]),
            "--max-num-seqs": str(protocol["max_sequences"]),
            "--max-model-len": str(protocol["max_model_length"]),
            "--tensor-parallel-size": "1", "--dtype": protocol["dtype"],
            "--kv-cache-metrics-sample": "0.01",
        }
        for flag, expected in expected_options.items():
            if option(command, flag) != expected:
                raise ValueError(f"Incorrect {flag} for {policy}")
        if Path(command[1]).name != "server.py":
            raise ValueError("Full-counter wrapper was not executed")
        if prefix and option(command, "--prefix-aware-max-wait-s") != "0":
            raise ValueError("Queue aging unexpectedly enabled")
        if predictive and option(command, "--cachewise-predictor") != "tool_name":
            raise ValueError("Predictor changed")
        commands.append(normalize_command(command))
        with (output / f"{name}-gpu.csv").open() as handle:
            gpu_rows = list(csv.DictReader(handle, skipinitialspace=True))
        if not gpu_rows:
            raise ValueError("Missing physical GPU observations")
        uuids = {row["uuid"].strip() for row in gpu_rows}
        if len(uuids) != 1:
            raise ValueError("A run used more than one physical GPU")
        gpu_uuids.update(uuids)
        snapshots = records(path / "metrics.jsonl")
        final_metrics = snapshots[-1]["text"]
        if metric(final_metrics, "vllm:e2e_request_latency_seconds_count") != expected_requests:
            raise ValueError("Server request metric is incomplete")
        ends = [r for r in records(path / "requests.jsonl") if r["event"] == "request_end"]
        computed = sum(r["usage"]["prompt_tokens"] - r["usage"]["prompt_tokens_details"]["cached_tokens"] for r in ends)
        if metric(final_metrics, "vllm:request_prefill_kv_computed_tokens_sum") != computed:
            raise ValueError("Server compute counter does not match completed-request usage")
        counters = [json.loads(p.read_text()) for p in output.glob(f"{name}-full-counters-*.json")]
        active = [p for p in counters if p["finished_requests"] > 0]
        if len(active) != 1:
            raise ValueError("Expected exactly one active TP=1 scheduler counter stream")
        validate_full_counter(active[0], expected_requests)
        queue = [r for p in output.glob(f"{name}-queue-*.jsonl") for r in records(p)]
        if prefix:
            if len({r["request_id"] for r in queue}) != expected_requests:
                raise ValueError("Queue observer did not cover every request")
            if any(r["max_wait_s"] != 0 or r["aging_choice"] for r in queue):
                raise ValueError("Queue aging treatment changed")
        elif queue:
            raise ValueError("FCFS unexpectedly used prefix-aware queue")
        summary = json.loads((path / "summary.json").read_text())
        latencies = [r["latency_s"] for r in ends]
        row = {
            "setting": setting["id"], "repeat": repeat, "policy": policy,
            "sessions": len(selected), "requests": expected_requests,
            "physical_gpu_uuid": next(iter(uuids)),
            "mean_session_serving_s": statistics.mean(s["llm_time_s"] for s in summary["sessions"]),
            "elapsed_s": summary["elapsed_s"],
            "useful_tokens_per_s": first_use["useful_tokens"] / summary["elapsed_s"],
            "requests_per_s": expected_requests / summary["elapsed_s"],
            "request_p50_s": float(np.percentile(latencies, 50)),
            "request_p90_s": float(np.percentile(latencies, 90)),
            "request_p99_s": float(np.percentile(latencies, 99)),
            "maximum_request_s": max(latencies),
            "ttft_p50_s": float(np.percentile([r["ttft_s"] for r in ends], 50)),
            "prompt_tokens": expected_prompt, "output_tokens": expected_output,
            "prompt_cache_hit_fraction": (expected_prompt - computed) / expected_prompt,
            "computed_prompt_tokens": computed,
            "first_use_prompt_tokens": first_use["first_use_prompt_tokens"],
            "excess_computed_prompt_tokens": computed - first_use["first_use_prompt_tokens"],
            "alignment_and_last_token_attribution": "Included in excess; not isolated as exact redundant recomputation.",
            "full_cached_block_evictions": active[0]["cached_blocks_evicted_for_allocation"],
            "cached_block_invalidations_outside_allocation": active[0]["cached_blocks_invalidated_elsewhere"],
            "full_counter_finished_requests": active[0]["finished_requests"],
            "metric_snapshots": result["metric_snapshots"], "preemptions": 0,
        }
        rows.append(row)
    if len(gpu_uuids) != 1 or any(c != commands[0] for c in commands):
        raise ValueError("Policies do not share physical GPU and common server settings")
    atomic_json(output / "part1-audit.json", {
        "status": "passed", "smoke": smoke, "setting": setting["id"],
        "repeat": repeat, "protocol_sha256": selection["protocol_sha256"],
        "source_manifest_sha256": checksum(output / "part1-source-manifest.json"),
        "engine_patch_sha256": checksum(output / "vllm-source.patch"),
        "packages_sha256": checksum(output / "packages.txt"),
        "model_snapshot_sha256": checksum(output / "model_snapshot.txt"),
        "environment": environment, "runs": rows,
    })
    print(json.dumps({"status": "passed", "setting": setting["id"], "repeat": repeat,
                      "runs": len(rows), "requests": expected_requests}, indent=2))


def collect(root):
    selection = json.loads((root / "prepared/selection.json").read_text())
    completed, pending = [], []
    for task in selection["tasks"]:
        path = root / "results" / task["setting"] / f"repeat-{task['repeat']}"
        if not (path / "AUDITED_COMPLETE").is_file():
            pending.append(task)
            continue
        report = json.loads((path / "part1-audit.json").read_text())
        if report["status"] != "passed" or report["protocol_sha256"] != selection["protocol_sha256"]:
            raise ValueError("Invalid completed audit")
        completed.append(report)
    status = {"completed_blocks": len(completed), "total_blocks": len(selection["tasks"]),
              "completed_policy_runs": sum(len(r["runs"]) for r in completed),
              "pending": pending}
    atomic_json(root / "results/progress.json", status)
    if pending:
        print(json.dumps(status, indent=2))
        return False
    for key in ["engine_patch_sha256", "packages_sha256", "model_snapshot_sha256", "source_manifest_sha256"]:
        if len({r[key] for r in completed}) != 1:
            raise ValueError(f"Different {key} across repeat blocks")
    for field in ["vllm_revision", "python", "model"]:
        if len({r["environment"][field] for r in completed}) != 1:
            raise ValueError(f"Different {field} across repeat blocks")
    hardware = []
    for block in completed:
        devices = list(csv.DictReader(block["environment"]["gpu"].splitlines(), skipinitialspace=True))
        if len(devices) != 1:
            raise ValueError("GPU allocation is not a single visible device")
        hardware.append(tuple(devices[0][k] for k in ["name", "driver_version", "memory.total [MiB]"]))
    if len(set(hardware)) != 1:
        raise ValueError("Different GPU model, memory, or driver across blocks")
    rows = [row for block in completed for row in block["runs"]]
    with (root / "results/measurements.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)
    atomic_json(root / "results/part1-comparison.json", {
        "status": "complete", "protocol_sha256": selection["protocol_sha256"],
        "selection": selection, "runs": rows,
        "scope": "Three matched repeats per setting; observed repeat ranges are not confidence intervals. Runtime-bounded complete segments; no offloading measurements.",
    })
    (root / "results/COMPLETE").write_text("All 60 policy runs passed the study audit.\n")
    print(json.dumps(status, indent=2))
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(0 if collect(args.root.resolve()) else 2)
