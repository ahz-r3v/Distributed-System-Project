"""Run one frozen four-policy GPU block using the existing validated runner."""

import argparse
from contextlib import contextmanager
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback

from common import atomic_json, checksum


def source_signature(root):
    paths = [p for p in (root / "part1").rglob("*")
             if p.is_file() and p.suffix in {".py", ".slurm", ".sh", ".json"}]
    paths.extend((root / "serving_experiment").glob("*.py"))
    paths.extend((root / "prepared").glob("*.json"))
    paths.append(root / "prepared/bootstrap.jsonl")
    return {str(p.relative_to(root)): checksum(p) for p in sorted(paths)}


def main(args):
    root = args.root.resolve()
    prepared = root / "prepared"
    protocol = json.loads((prepared / "protocol.json").read_text())
    selection = json.loads((prepared / "selection.json").read_text())
    if checksum(prepared / "protocol.json") != selection["protocol_sha256"]:
        raise ValueError("Frozen protocol changed")
    if args.smoke:
        setting, repeat = {"id": "smoke", "sessions": 2}, 0
        output = root / "results/smoke"
    else:
        task = selection["tasks"][args.task_index]
        assert task["task"] == args.task_index
        setting = next(s for s in selection["settings"] if s["id"] == task["setting"])
        repeat = task["repeat"]
        output = root / "results" / setting["id"] / f"repeat-{repeat}"
    output.parent.mkdir(parents=True, exist_ok=True)
    before = source_signature(root)
    sys.path.insert(0, str(root / "serving_experiment"))
    runner = importlib.import_module("run_job")
    original_serve = runner.serve

    @contextmanager
    def observed_serve(directory, name, command, env, base_url):
        actual = list(command)
        assert Path(actual[1]).name == "server_queue_diagnostics.py"
        actual[1] = str(root / "part1/server.py")
        env = {**env, "CACHEWISE_FULL_COUNTERS": str(directory / f"{name}-full-counters")}
        atomic_json(directory / f"{name}-command.json", actual)
        with original_serve(directory, name, actual, env, base_url):
            yield

    original_run = subprocess.run

    def timed_run(command, *positional, **kwargs):
        if isinstance(command, list) and any(str(x).endswith("/replay.py") for x in command):
            command = [*command, "--request-timeout", str(protocol["request_timeout_seconds"])]
            atomic_json(output / f"{command[command.index('--policy')+1]}-replay-command.json", command)
        return original_run(command, *positional, **kwargs)

    runner.serve = observed_serve
    subprocess.run = timed_run
    sys.argv = [
        "run_job.py", "--root", str(root), "--output", str(output),
        "--workload", str(prepared / f"{setting['id']}.json"),
        "--sessions", str(setting["sessions"]), "--repeats", "1",
        "--repeat-start", str(repeat), "--queue-diagnostics", "--mark-terminal-idle",
        "--port", str(20000 + int(os.environ.get("SLURM_JOB_ID", "0")) % 30000),
        "--num-gpu-blocks", str(protocol["kv_blocks"]),
        "--policies", *protocol["policies"],
    ]
    if args.smoke:
        sys.argv.append("--smoke")
    try:
        runner.main()
    finally:
        subprocess.run = original_run
        runner.serve = original_serve
    after = source_signature(root)
    if before != after:
        raise ValueError("Frozen inputs or runner source changed during the block")
    packages_after = subprocess.check_output([
        str(Path.home() / ".local/bin/uv"), "pip", "freeze", "--python", sys.executable,
    ], text=True)
    if packages_after != (output / "packages.txt").read_text():
        raise ValueError("Shared runtime package versions changed during the block")
    atomic_json(output / "part1-source-manifest.json", before)
    atomic_json(output / "part1-task.json", {
        "setting": setting["id"], "repeat": repeat,
        "protocol_sha256": selection["protocol_sha256"],
        "selection_sha256": checksum(prepared / "selection.json"),
        "smoke": args.smoke,
    })
    from audit import audit_block

    audit_block(root, output, setting, repeat, args.smoke)
    (output / "AUDITED_COMPLETE").write_text("All four policies passed the Part 1 audit.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--task-index", type=int)
    group.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    try:
        main(args)
    except Exception:
        failure = args.root / "results" / ("smoke-failed.txt" if args.smoke else f"task-{args.task_index}-failed.txt")
        failure.parent.mkdir(parents=True, exist_ok=True)
        failure.write_text(traceback.format_exc())
        raise
