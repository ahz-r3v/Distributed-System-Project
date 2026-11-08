# CacheWise Part 1 coverage study

This suite extends the historical single-cohort study with a concurrency sweep,
two additional held-out cohorts, and complete cached-block eviction accounting.
It covers Part 1 only. It does not evaluate KV offloading.

The registered design is `cachewise_part1/protocol.json`; the actual frozen
segment identifiers, exclusions, source groups, and input hashes are in
`cachewise_part1/selection.json`. The current execution and validation records
are described in `../notes/README.md` and archived under
`../notes/experiment-evidence/part1-coverage-*.json`.

## Design

The four policies cross FCFS/prefix-aware scheduling with LRU/predictive eviction.
Prefix-aware queue aging is disabled. Cohort A has nested N=10/20/30 selections;
B and C each have ten complete segments from ten new source sessions. There
are three matched repeats per setting, giving 15 four-policy blocks, 60 policy
runs, and 6,384 planned request executions. All policies in one repeat block
execute sequentially on the same physical GPU with a fresh server per policy.

Selection uses metadata and seeded identifier ordering, never policy outcomes.
Each segment has 2–20 turns, at most 300 seconds of recorded waits, at most
1,000,000 summed prompt tokens, and at most 8,192 output tokens. Segments and
selected waits are preserved without truncation, clipping, or rescaling.
The resulting population is a runtime-bounded adapted workload. Historical
N=10 results remain a separate experiment.

## Observed preemption and the analysis amendment

The registered zero-preemption condition was not satisfied: A-N20, repeat 0
completed all four policies with the correct 150 requests and 27,809 output
tokens per policy, but prefix-aware/predictive eviction had one real preemption.
The original worker rejected that block. Its failure, all raw results, the
protocol, and the executing worker code are preserved.

`part1-preemption-audit-amendment.json` records a **post hoc validation
correction**, not an execution change. Nonnegative integer preemption counts are
reported as outcomes rather than suppressed or selectively rerun. All remaining
request-integrity, configuration, full-counter, source, package, model, and
hardware requirements still apply. This amendment is specific to the current
registered study and does not mean its original protocol was fully satisfied.

The engine's `request_prefill_kv_computed` histogram is derived from
completed-request prompt-minus-cached usage. The independent analysis labels it
`reported_uncached_prompt_tokens`; it cannot establish all computation lost or
repeated during preemption. Extra prefill work from preemption remains unknown
when preemptions occur. Client performance and full cached-block eviction counts
remain available, subject to the same complete-run checks.

`audit_cachewise_part1_observed.py` reuses passed registered audits and independently
checks every nonzero-preemption block without rewriting its raw artifacts.
It writes separate audits under `results-observed/`. The collector's
`--observed-preemptions` option selects this analysis; only one collector should
run for that output directory. Its final marker is
`results-observed/COMPLETE_WITH_PROTOCOL_DEVIATION`, and its comparison status is
`complete_with_protocol_deviation` with 60 rows and
`original_protocol_fully_satisfied: false`. The strict original study must not be
marked `COMPLETE` when its zero-preemption requirement failed.

## Preparing another isolated execution

Use an isolated study directory; do not overwrite the registered study or edit
its worker files while jobs are active. The layout expected by the runners is:

```text
study/
  .venv/                    # validated engine environment, or its symlink
  src/vllm-cachewise/        # exact engine checkout, including local patches
  serving_experiment/       # validated run_job/replay/inspection helpers
  part1/                    # copy of cachewise_part1 worker files
  prepared/                 # frozen workloads, protocol, selection, bootstrap
  control/                  # launch_cachewise_part1.py and collect_cachewise_part1.py
  logs/
  results/
```

The historical prepared input is read from the source repository. To create a
new frozen selection in a previously nonexistent output directory:

```sh
python experiments/cachewise_part1/prepare.py \
  --source-root /home/ws/cachewise-coding-traces \
  --output experiments/cachewise_part1/generated/prepared
```

For the registered execution, use the existing frozen prepared files rather
than regenerating their registration timestamp. The selector refuses to replace
an existing output directory. Verify its protocol, selector, workload, and
bootstrap hashes against the saved selection before deployment.

The validated runner must support `--repeat-start`, `--queue-diagnostics`, and
`--mark-terminal-idle`. The runner used in this execution has SHA-256
`7ba2edcbc8c45a2e3b9a4320c24c2467504f9087a05c4fcb98db72526c7c6c31`.
The engine base and model revision are fixed in the protocol; the current
engine patch hash and package/model snapshots are preserved in the validation
evidence. A compatible inference environment, model weights, and the cluster's
Slurm module are prerequisites.

`smoke.slurm` runs engine tests, worker tests, and four short functional replays.
After submitting it on the cluster, run the launcher with the study root and
validation job ID:

```sh
python control/launch_cachewise_part1.py \
  --root /absolute/path/to/study --validation-job VALIDATION_JOB_ID
```

The launcher waits for both successful Slurm completion and the matching passed
smoke audit. It records the intended submission and launches the 15-task array
with at most three concurrent single-GPU jobs. Its persistent lock prevents
accidental duplicate submission. The scripts request one node explicitly and
exclude node10–11; a multi-node `--nodelist` must not be substituted for a choice
of eligible nodes.

## Collection and completion

The launcher collects results automatically. An existing array can instead be
observed by the independent collector; do not run duplicate collectors:

```sh
python control/collect_cachewise_part1.py \
  --root /absolute/path/to/study --array-job EXISTING_ARRAY_JOB_ID
```

The current execution uses that collector with `--observed-preemptions`, the
independent analyzer in `control/`, and the recorded amendment copied to
`study/preemption-audit-amendment.json`. Its original collector was retained as
provenance and stopped after the amended collector was verified. GPU jobs and
the frozen worker bundle were not modified. The local puller recognizes both
strict and amended completion markers and retains their distinct statuses.

Each block verifies actual request hashes and lengths, server configuration,
physical GPU, input/source hashes, runtime packages, request completion, and
full counter coverage. Prefix cache removals during allocation and other cache
invalidations are counted separately. Computed prompt tokens are checked against
request usage; first-use and excess computation retain alignment and last-token
uncertainty. These counts do not measure KV bytes transferred.

Raw runner `COMPLETE` files do not establish study completion. A block requires
`AUDITED_COMPLETE`; the final cross-block audit additionally checks engine,
packages, model, worker signatures, and GPU model/memory/driver. Only then does
the collector write `results/COMPLETE`, `measurements.csv`, and a
`part1-comparison.json` with status `complete` and 60 rows. Partial status lives
in `results/progress.json`. Failures are retained as `*-failed.txt` or
`CONTROLLER_FAILED.txt`; a failed study is never silently reduced to successful
rows.

To fetch compact artifacts over the existing `ccds-ai` connection:

```sh
python experiments/pull_cachewise_part1.py \
  --remote-root /export/home4/wspang/cachewise-rerun/part1-coverage-20261108-v1 \
  --output experiments/cachewise_part1/results/cluster --watch
```

This reads the cluster without modifying its experiment. Large replay payloads,
model weights, and engine checkouts are excluded. Generated inputs and local
result mirrors are ignored by Git.

## Local validation

```sh
python -m pytest experiments/cachewise_part1/tests experiments/tests -q
bash -n experiments/cachewise_part1/environment.sh \
  experiments/cachewise_part1/smoke.slurm experiments/cachewise_part1/array.slurm
```

The independent `check_cachewise_part1_counters.py` probe uses the real engine
`BlockPool` with synthetic hash metadata, exercising successful allocation
evictions and other invalidations without model execution. Validation evidence
is functional validation and must not be reported as benchmark findings.
