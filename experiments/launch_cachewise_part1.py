"""Launch the registered array only after successful GPU validation, then collect.

Run this on the cluster login server with its Slurm module loaded. It never
submits the array if validation fails, and its persistent lock prevents a
second controller from silently submitting duplicate work.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback


def validation_ready(state, audit_path, marker_path, protocol_hash):
    if state in {"FAILED", "CANCELLED", "TIMEOUT", "NODE_FAIL", "OUT_OF_MEMORY"}:
        raise RuntimeError(f"GPU validation ended as {state}; main array not submitted")
    if state != "COMPLETED" or not marker_path.is_file() or not audit_path.is_file():
        return False
    audit = json.loads(audit_path.read_text())
    if (audit["status"] != "passed" or not audit["smoke"]
            or audit["protocol_sha256"] != protocol_hash or len(audit["runs"]) != 4):
        raise ValueError("GPU validation audit does not match this study")
    return True


def launch(root, validation_job):
    lock = root / "CONTROLLER_LOCK"
    with lock.open("x") as handle:
        handle.write(str(os.getpid()) + "\n")
    sys.path.insert(0, str(root / "part1"))
    from common import atomic_json, checksum

    selection = json.loads((root / "prepared/selection.json").read_text())
    protocol = json.loads((root / "prepared/protocol.json").read_text())
    if checksum(root / "prepared/protocol.json") != selection["protocol_sha256"]:
        raise ValueError("Registered protocol changed")
    record_path = root / "array-submission.json"
    if record_path.exists():
        raise FileExistsError("Array already submitted; use its existing monitor")
    atomic_json(root / "launch-status.json", {
        "state": "waiting_for_gpu_validation", "validation_job": validation_job,
        "planned_full_runs": selection["full_runs"], "controller_pid": os.getpid(),
    })
    previous = None
    while True:
        raw = subprocess.check_output([
            "sacct", "-X", "-j", str(validation_job), "--noheader", "--parsable2",
            "--format=State",
        ], text=True).strip()
        state = raw.splitlines()[0].split("|")[0].split()[0] if raw else "UNKNOWN"
        if state != previous:
            print(f"Validation job {validation_job}: {state}", flush=True)
            previous = state
        if validation_ready(state, root / "results/smoke/part1-audit.json",
                            root / "results/smoke/AUDITED_COMPLETE", selection["protocol_sha256"]):
            break
        time.sleep(15)
    command = [
        "sbatch", "--parsable", "--nodes=1", "--ntasks=1",
        "--gres=gpu:nvidia_rtx_pro_6000_blackwell:1", "--cpus-per-task=16",
        f"--array=0-{len(selection['tasks'])-1}%{protocol['max_concurrent_gpu_jobs']}",
        f"--dependency=afterok:{validation_job}",
        "--export=ALL,CACHEWISE_STUDY_ROOT=" + str(root), "--chdir=" + str(root),
        "--output=" + str(root / "logs/coverage-%A-%a.out"), str(root / "part1/array.slurm"),
    ]
    # Record the exact intention before the external mutation; never auto-retry it.
    atomic_json(root / "launch-status.json", {"state": "submitting_array", "command": command})
    job = subprocess.check_output(command, text=True).strip().split(";")[0]
    atomic_json(record_path, {
        "job_id": job, "validation_job": validation_job, "command": command,
        "submitted_at_utc": datetime.now(timezone.utc).isoformat(),
        "controller_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "protocol_sha256": selection["protocol_sha256"],
    })
    atomic_json(root / "launch-status.json", {
        "state": "array_submitted", "array_job": job, "validation_job": validation_job,
        "planned_full_runs": selection["full_runs"], "controller_pid": os.getpid(),
    })
    print(f"Submitted 15 single-GPU blocks as array {job}, at most three concurrent.", flush=True)
    from collect_cachewise_part1 import monitor

    monitor(root, job)
    atomic_json(root / "launch-status.json", {"state": "complete", "array_job": job,
                                              "completed_policy_runs": 60})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--validation-job", required=True)
    args = parser.parse_args()
    try:
        launch(args.root.resolve(), args.validation_job)
    except Exception:
        (args.root / "results/CONTROLLER_FAILED.txt").write_text(traceback.format_exc())
        raise
