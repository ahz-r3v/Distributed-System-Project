"""Fetch compact study progress/results without downloading large raw traces."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import time


def pull(args):
    args.output.mkdir(parents=True, exist_ok=True)
    ssh = ("ssh -o BatchMode=yes -o ConnectTimeout=15 "
           "-o StrictHostKeyChecking=accept-new "
           "-o UserKnownHostsFile=/tmp/cachewise-known-hosts")
    command = [
        "rsync", "-az", "--prune-empty-dirs", "--timeout=45", "-e", ssh,
        "--exclude=src/", "--exclude=.venv", "--exclude=serving_experiment/",
        "--exclude=part1/", "--exclude=prepared/", "--exclude=setup-history/",
        "--exclude=logs/", "--exclude=control/", "--exclude=**/runner_source/",
        "--include=*/", "--include=STAGED.json", "--include=resource-correction.json",
        "--include=runner-correction.json", "--include=*submission*.json",
        "--include=launch-status.json", "--include=CONTROLLER_FAILED.txt",
        "--include=preemption-audit-amendment.json",
        "--include=progress.json", "--include=part1-comparison.json",
        "--include=measurements.csv", "--include=part1-audit.json",
        "--include=part1-source-manifest.json", "--include=part1-task.json",
        "--include=*-full-counters-*.json", "--include=array-accounting.json",
        "--include=COMPLETE", "--include=AUDITED_COMPLETE",
        "--include=COMPLETE_WITH_PROTOCOL_DEVIATION", "--include=OBSERVED_AUDIT_COMPLETE",
        "--include=MONITOR_FAILED.txt", "--include=*-failed.txt", "--exclude=*",
        f"ccds-ai:{args.remote_root.rstrip('/')}/", str(args.output) + "/",
    ]
    previous = None
    failures = 0
    while True:
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode:
            failures += 1
            print(json.dumps({"time_utc": datetime.now(timezone.utc).isoformat(),
                              "sync_error": result.stderr.strip(), "consecutive_errors": failures}), flush=True)
            if not args.watch:
                return result.returncode
            time.sleep(60)
            continue
        failures = 0
        observed = args.output / "results-observed"
        progress_path = observed / "progress.json"
        if not progress_path.exists():
            progress_path = args.output / "results/progress.json"
        progress = json.loads(progress_path.read_text()) if progress_path.exists() else {}
        key = (progress.get("completed_blocks"), progress.get("completed_policy_runs"))
        if key != previous:
            print(json.dumps({"time_utc": datetime.now(timezone.utc).isoformat(),
                              "progress": progress}), flush=True)
            previous = key
        if (args.output / "results/COMPLETE").exists():
            comparison = json.loads((args.output / "results/part1-comparison.json").read_text())
            if comparison["status"] != "complete" or len(comparison["runs"]) != 60:
                raise ValueError("Completion marker does not match all 60 audited runs")
            print("All 60 audited runs are now available locally.", flush=True)
            return 0
        if (observed / "COMPLETE_WITH_PROTOCOL_DEVIATION").exists():
            comparison = json.loads((observed / "part1-comparison.json").read_text())
            if (comparison["status"] != "complete_with_protocol_deviation"
                    or len(comparison["runs"]) != 60
                    or comparison["original_protocol_fully_satisfied"]):
                raise ValueError("Amended completion marker does not match all 60 audited runs")
            print("All 60 runs are available locally with the recorded protocol deviation.", flush=True)
            return 0
        if (observed / "CONTROLLER_FAILED.txt").exists():
            print("Amended collection needs attention; see results-observed/CONTROLLER_FAILED.txt.", flush=True)
            return 1
        if (args.output / "results/MONITOR_FAILED.txt").exists():
            print("Remote collection needs attention; see MONITOR_FAILED.txt.", flush=True)
            return 1
        if (args.output / "results/CONTROLLER_FAILED.txt").exists():
            print("Remote controller needs attention; see CONTROLLER_FAILED.txt.", flush=True)
            return 1
        if not args.watch:
            return 0
        time.sleep(60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote-root", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--watch", action="store_true")
    raise SystemExit(pull(parser.parse_args()))
