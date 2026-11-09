"""Collect the submitted study, allowing job-completion/filesystem races."""

import argparse
from contextlib import redirect_stdout
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback


def completion_poll(collect_ready, read_queue):
    if collect_ready():
        return True, ""
    queue = read_queue()
    # A job may finish between the first file read and the scheduler request.
    if not queue.strip() and collect_ready():
        return True, queue
    return False, queue


def monitor(root, job, observed_preemptions=False):
    sys.path.insert(0, str(root / "part1"))
    if observed_preemptions:
        from audit_cachewise_part1_observed import collect
    else:
        from audit import collect
    from common import atomic_json
    results = root / ("results-observed" if observed_preemptions else "results")
    results.mkdir(exist_ok=True)

    def ready():
        with redirect_stdout(io.StringIO()):
            return collect(root)

    def queue():
        result = subprocess.run(["squeue", "--noheader", "--jobs", str(job),
                                 "--format=%i|%T|%R"], capture_output=True, text=True)
        if result.returncode and "Invalid job id" not in result.stderr:
            raise RuntimeError(result.stderr.strip())
        return result.stdout.strip()

    deadline = time.monotonic() + 168 * 3600
    terminal_since, previous = None, None
    while time.monotonic() < deadline:
        complete, current_queue = completion_poll(ready, queue)
        if complete:
            atomic_json(root / "launch-status.json", {
                "state": "complete_with_protocol_deviation" if observed_preemptions else "complete",
                "array_job": job, "completed_policy_runs": 60,
                "original_protocol_fully_satisfied": not observed_preemptions,
            })
            print("All 60 runs collected and audited" + (" with the recorded protocol deviation." if observed_preemptions else "."), flush=True)
            return
        progress = json.loads((results / "progress.json").read_text())
        signature = (progress["completed_blocks"], current_queue)
        if signature != previous:
            print(json.dumps({"time_utc": datetime.now(timezone.utc).isoformat(),
                              "completed_blocks": progress["completed_blocks"],
                              "completed_policy_runs": progress["completed_policy_runs"],
                              "queue": current_queue}), flush=True)
            previous = signature
        if not current_queue:
            accounting = subprocess.check_output([
                "sacct", "-X", "-j", str(job), "--noheader", "--parsable2",
                "--format=JobIDRaw,State,ExitCode",
            ], text=True)
            atomic_json(results / "array-accounting.json", {"text": accounting})
            states = [line.split("|")[1].split()[0] for line in accounting.splitlines() if line]
            if states and all(s in {"COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "NODE_FAIL", "OUT_OF_MEMORY"} for s in states):
                if ready():
                    continue
                terminal_since = terminal_since or time.monotonic()
                if time.monotonic() - terminal_since >= 120:
                    raise RuntimeError("Array ended, but some blocks did not pass their audit")
        else:
            terminal_since = None
        time.sleep(30)
    raise TimeoutError("Collection timed out; submitted GPU jobs were not cancelled")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--array-job", required=True)
    parser.add_argument("--observed-preemptions", action="store_true",
                        help="Use the separately recorded audit amendment and results directory")
    args = parser.parse_args()
    try:
        monitor(args.root.resolve(), args.array_job, args.observed_preemptions)
    except Exception:
        results = args.root / ("results-observed" if args.observed_preemptions else "results")
        results.mkdir(exist_ok=True)
        (results / "CONTROLLER_FAILED.txt").write_text(traceback.format_exc())
        raise
