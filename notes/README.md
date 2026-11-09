# Research records

Keep topic-selection notes, reading notes, discussion decisions, and experiment records here.
Use filenames such as `YYYY-MM-DD-topic.md`, and record sources and decisions for traceability.

## Project planning

| Item | Current status |
| --- | --- |
| Title and research questions | CacheWise Replication and Fetch-Aware KV Cache Recovery; adapted replication and reported GPU–host restoration/scheduling behavior |
| Report format | Official USENIX / OSDI two-column style, used for a course report |
| Language and length limit | English; length limit to be confirmed |
| Authors and section assignments | To be confirmed |
| Baselines, metrics, and data sources | Verified historical/coverage replication evidence; separate Mini-SGLang host observations are mapped to a pinned artifact revision and retained as reported results |
| Draft, review, and submission dates | To be scheduled |

## Current report outline

1. Replicate CacheWise: document differences between the original paper's environment and this project's environment, and report measured results and policy ablations.
2. Analyze recomputation and offloading: fix the scheduling and eviction policies, and compare recomputation, DRAM restore, and SSD restore for identical missing prefixes, including the complete read/write paths.
3. Propose and evaluate secondary-storage methods: first implement a synchronous block-offloading baseline, then use evidence to select optimizations such as asynchronous transfer, prefetching, and cost-based decisions.

Original source: [CacheWise v1](https://arxiv.org/abs/2606.16824v1), citation key `Tiwari2026CacheWise`.
Check Section 6.4 of the original paper to distinguish existing DRAM offloading from the proposed secondary-storage extension.
The manuscript contains the completed adapted replication and an analysis of the existing reported Mini-SGLang host-DRAM results. SSD support remains future work.

## Verified experimental results (2026-11-08)

The historical six-policy results use `/home/ws/cachewise-coding-traces/serving_experiment/results/2026-11-04/parallel-13943/consolidated-comparison.json`; the new coverage study is reported separately below.
This consolidated experiment includes three repeats for each of six policies, totaling 18 complete runs and 1,494 requests; the six policies use the same GPU within each repeat block, while different blocks use different GPUs of the same model.
Session means, token counts, and weighted cache-hit rates for all 18 runs were recalculated and verified from request-level records in the original `summary.json` files.

- Prefix-aware LRU has a mean session serving time of 337.87 seconds, versus 349.67 seconds for learned CacheWise without the queue-aging override; the latter is 3.49% higher.
- Under FCFS, predictive eviction reduces the mean from 595.04 seconds to 529.97 seconds; its effect depends on the scheduler.
- The oracle using recorded tool durations reaches 349.58 seconds, without a consistent substantial gap from the learned method; it is not an omniscient optimal eviction policy.
- Removing the local 30-second queue-aging override reduces the mean from 599.14 seconds to 349.67 seconds but increases maximum request latency; the maximum must not be treated as P99.
- Only one N=10 cohort is covered; intervals show the observed range across three repeats, not confidence intervals. Uncached tokens include first-time prefill and cannot all be counted as recomputation.

The separate job-10807 `recompute-profile.json` contains three uncached-request timings at each length; for example, the median client-observed latency for 65,536 tokens is 19.569 seconds.
These timings are neither isolated GPU prefill measurements nor offloading experiments, and cannot directly establish that SSD offloading is faster.
The earlier five-policy job-10807 results use different terminal-session handling from the later consolidated experiment; ratios from the two studies should not be mixed.

Compact raw results, source versions, checksums, and scope notes are stored in `experiment-evidence/`.
The historical consolidated experiment lacks complete eviction counts; the coverage study has completed and archived those counts. The separate Mini-SGLang artifact reports host-DRAM restoration and transferred bytes, while SSD I/O remains unimplemented.

## Part 1 draft, figure choices, and remaining experiments

Part 1 now has a prose draft covering workload characterization, setup, metric definitions, the six-policy comparison, matched scheduling/eviction effects, oracle and queue-aging diagnostics, and replication limits.
The supporting KV-cache and CacheWise background is also drafted.
This paragraph records the initial Part 1 writing revision. The later manuscript update incorporates the separate reported host-DRAM study into Parts 2 and 3, as documented below.
No new GPU jobs were launched for that prose-and-figures revision; the subsequent execution study is recorded below.

### Figure decisions

| Existing graph | Decision for Part 1 | Reason |
| --- | --- | --- |
| Session-completion comparison | Include, redrawn from the consolidated six-policy study | Central performance result. The existing job-10807 plot represents a different five-policy experiment. |
| Scheduling and eviction ablations | Include matched effects beside the main comparison | Separates the scheduling benefit from the scheduler-dependent eviction effect. |
| Prefill/decode length CDFs | Include corrected versions in one workload figure | Count unique messages and include cache-creation tokens in full prompt length. Full prompt length is not the number of tokens actually recomputed on every request. |
| Turn-count CDF | Include corrected version in the workload figure | Count unique message IDs rather than repeated event records. |
| Tool-duration distribution | Include the six most frequent tools in the workload figure | Deduplicate tool IDs, retaining the earliest launch for a matching result; use seconds and identify omitted unknown/nonpositive durations. Individual tool duration is not the return interval of a parallel tool batch. |
| Context-evolution curves | Defer | The current script takes a running maximum and extends each trace's last value beyond its end. A replacement should use actual observed contexts and report how many traces remain at each turn. |
| Session-duration CDF | Optional appendix after replotting | Source-trace duration includes pauses and differs from session serving time. The current view ends near the 80th percentile; show the full tail if retained. |
| User-versus-tool initiation CDF | Defer pending a definition correction | The current script counts individual tool calls and human pauses, then labels these as LLM requests. Parallel tool calls need to be grouped into actual next-turn events. |
| Six-panel serving-efficiency figure | Optional appendix, regenerated from the latest study | The older figure includes an unavailable-eviction panel and older results. Current goodput and per-run latency percentiles were recovered offline and are summarized in the text. |
| Earlier memory-pressure comparison | Optional separate diagnostic | Different run/configuration and limited repetitions; do not merge its bars or ratios with the main study. |
| Uncached recomputation profile | Handoff to Part 2 | Useful compute-side evidence for the recovery-cost analysis; does not measure offloading. |

The two selected figures are `paper/figures/replication-workload.pdf` and `paper/figures/replication-serving.pdf`.
The corrected descriptive population contains 11,388 non-synthetic messages with positive prompt and output usage from 80 of 94 source traces; it includes training traces and must not be called the serving test cohort.
The smaller serving cohort still has ten segments, eight source sessions, and 83 requests per run.

### Experiments to prioritize for Part 1

The existing data is sufficient for a bounded adapted-replication report.
The following follow-ups are needed for stronger coverage or more specific mechanism claims, rather than to make the existing measurements valid.
This table records the priorities before the coverage execution: the concurrency sweep, two additional cohorts, and full eviction instrumentation are now complete, subject to the computation-accounting limit documented below.

| Priority | Follow-up | Question answered | Practical design |
| --- | --- | --- | --- |
| First | Concurrency sweep | Does the scheduling/eviction ordering persist as load increases? | Evaluate the four core FCFS/prefix-aware by LRU/predictive cases at N=20 and N=30, with three matched repeat blocks per load. This adds 24 full runs if the existing N=10 cohort and preparation remain comparable; otherwise rerun N=10 too, for 36 new runs. Extend to N=40/50 when feasible. |
| First | Additional held-out cohorts | Is the result specific to the selected short-wait workload? | Add at least two prespecified N=10 cohorts, keeping source sessions disjoint from training and preferably from one another. Four core policies by three repeats gives 12 runs per new cohort. Use the same cohort for all policies. |
| During those runs | Complete eviction and computation accounting | Is improvement associated with fewer evictions or less repeated prefill? | Record cumulative cached-block evictions rather than 1% lifetime samples, computed prompt tokens, and first-use token counts. Keep counter semantics and instrumentation identical across policies. Label block alignment and last-token handling separately; do not convert eviction estimates into claims of actual transferred bytes. |
| Targeted diagnostic | Align predictor bootstrap and runtime keys | Does the individual-tool versus parallel-batch preparation mismatch affect prediction and serving? | Build training examples from complete tool batches using training sessions only. At fixed load compare original learned prediction, batch-aligned prediction, and prefix-aware LRU with three matched repeats: nine runs. Check key coverage and prediction errors offline first. |

For the concurrency sweep, declare cohort-selection and runtime-budget rules before inspecting policy outcomes.
The unmodified first 20 eligible segments contain a verified 178,164-second tool wait, so a naive sweep may spend roughly two days waiting for one tool return.
Either preserve that workload with an appropriate runtime allowance, or define and report a feasible held-out cohort rule and all exclusions in advance.
Do not silently clip delays or select sessions because they give a desired result.
If delays are rescaled, report that as a separate adapted workload with fresh matched controls.

Exclusive CPU scheduling and GPU execution profiling is optional for the present performance comparison, but required before attributing the gap to scheduler overhead or reproducing the original overhead claim.
Request-stage residence times overlap and cannot replace those measurements.
A matched reference-baseline comparison is also needed before claiming the original InferCept comparison has been reproduced; the current main study does not include it, and the older local InferCept adaptation differs from the paper's baseline.
Argument-clustering sweeps cannot reconstruct the paper's argument-aware predictor from identical redacted argument strings.

The existing scheduling/eviction, oracle, and aging controls do not need to be repeated simply to add another graph.
Re-run controls when workload preparation, engine configuration, instrumentation, or training changes so each new comparison remains matched.

### Handoff to Parts 2 and 3

The original handoff requested recovery measurements and an implemented offloading method beyond Part 1.
The current report incorporates the existing Mini-SGLang GPU–host implementation and reported comparisons, while keeping that study separate from the vLLM replication.
An SSD path, controlled storage costs, and persistent recovery remain future work; they are not additional experiments scheduled for this writing revision.

### Reproducing this revision's offline analysis

From the report repository, use a Python environment with NumPy and Matplotlib:

```sh
python paper/figures/prepare_replication_data.py --source-root /home/ws/cachewise-coding-traces
python paper/figures/plot_replication.py
```

The first command reads the source repository without modifying it or starting inference.
It checks source-trace and workload hashes, regenerates `workload-characterization.json`, and derives `replication-additional-metrics.json` from the original 18 request summaries.
The second command only requires the saved numeric evidence and regenerates vector figures, PNG previews, paired-effect CSV values, and figure provenance.

## Offloading literature and research scope

The [2026-11-09 related-work notes](2026-11-09-offloading-related-work.md) record verified primary sources, publication versions, claim boundaries, and the controlled comparisons needed for the secondary-storage study.
The Introduction connects this scope to the historical 18-run experiment and the separate 60-run coverage study with 6,384 request executions, both presented in Section 3.
Its 10.07%-43.38% predictive-eviction increase under prefix-aware scheduling comes from the five coverage-setting means; the text preserves the request-tail tradeoff and declared preemption-related protocol deviation.
It explicitly identifies the recovery model, candidate methods, and offloading evaluation as the framework and remaining experimental work, without claiming an SSD benefit.

## Coverage study execution and results

### Part 1 execution protocol frozen on 2026-11-08

The requested steps 1--4 are implemented in `experiments/cachewise_part1/`.
`protocol.json` defines the design and `selection.json` records the cohorts and exclusions fixed before new policy outcomes are collected.
The selector only reads trace metadata and identifiers; no historical policy latency or cache-hit measurements are used for selection.

Eligible segments are complete held-out segments with 2--20 turns, at most 300 seconds of total recorded waiting, at most 1,000,000 summed prompt tokens, and at most 8,192 output tokens.
These declared runtime budgets leave 252 eligible segments from 43 source sessions.
No selected segment is truncated and no selected delay is clipped or rescaled.
The study therefore measures a runtime-bounded subset of the release, not the unfiltered trace population.

| Setting | Complete segments | Source sessions | Requests per policy run | Recorded wait sum |
| --- | ---: | ---: | ---: | ---: |
| A, N=10 | 10 | 10 | 57 | 46.35 s |
| A, N=20 | 20 | 20 | 150 | 402.30 s |
| A, N=30 | 30 | 23 | 226 | 839.92 s |
| B, N=10 | 10 | 10 | 49 | 106.00 s |
| C, N=10 | 10 | 10 | 50 | 278.05 s |

A uses nested prefixes of a fixed segment ordering; B and C use disjoint source sessions, separate from A, training, and the historical serving cohort.
The four core policies are FCFS/LRU, FCFS/predictive, prefix-aware/LRU, and prefix-aware/predictive, with queue aging disabled in the prefix-aware cases.
Three matched repeats per setting give 60 full runs and 6,384 planned request executions.
New N=10 controls are included because workload selection and instrumentation differ from the historical study.
Historical measurements are retained separately.

The passive observer counts every successful cached-block hash removal during allocation, distinguishing cache invalidation outside allocation and excluding unsuccessful removals or fresh blocks.
It leaves the policy result and allocation order unchanged and keeps the existing 1% lifetime sampling as a separate diagnostic.
The original plan checked the engine's named computed-prefill metric against completed-request usage.
Inspection during the preemption repair established that these are the same usage-derived accounting, rather than independent execution measurements.
The final analysis reports uncached usage and first-use prompt tokens separately; alignment and last-token overhead and extra preemption work prevent an exact recomputation claim.
Per-run P50/P90/P99, maxima, TTFT, goodput, cache hits, preemptions, source hashes, and physical GPU identity are audited.

The suite uses isolated copies of the existing runner and engine, a fresh server per policy, at most three GPU jobs concurrently, and one physical GPU for all four policies within each repeat block.
A four-policy GPU smoke test and engine tests gate the main array.
Raw replay completion alone is insufficient: a block needs `AUDITED_COMPLETE`, and the overall study only receives a completion marker after all 60 policy runs pass the final cross-block audit.

Local validation: eleven tests passed for deterministic/disjoint selection, full-segment exclusion without delay clipping, first-use accounting, real-versus-fresh eviction counting, failed allocation, forked-process reset, incomplete/duplicate counter rejection, single-node resource requests, validation-gated launching, and a scheduler-completion race.
Shell syntax checks and whitespace checks passed.

GPU validation **passed** in Slurm job **16289**: 74 engine tests, nine tests in the frozen worker bundle, and all four two-segment smoke replays with request/token/configuration/full-counter audits.
Two later controller tests bring the local total to eleven; they do not alter the frozen GPU worker sources.
A separate CPU-only probe using the real engine `BlockPool` verified exactly two allocation evictions and one invalidation outside allocation.
The smoke replays and metadata probe are functional validation, not results for the main serving study.

The full execution **finished at 19:26 UTC on 2026-11-08** as Slurm array **16293**: 15 matched four-policy blocks, 60 policy runs, and 6,384 completed requests, with no client errors.
The requested concurrency sweep and two additional held-out cohorts are complete.
Fourteen blocks passed the registered strict audit; the remaining block failed its zero-preemption assumption after one real preemption, as documented below.
All 15 blocks passed the separately recorded amended analysis, including the final cross-block source, package, model, and hardware consistency checks.
The final status is `complete_with_protocol_deviation`; the original protocol was not fully satisfied.
Full eviction counts and request-level usage/cache/latency measurements are available for every run; extra computation caused by preemption remains unmeasured.

Remote frozen study root: `/export/home4/wspang/cachewise-rerun/part1-coverage-20261108-v1` via the existing `ccds-ai` connection.
Compact artifacts are synchronized into the ignored local directory `experiments/cachewise_part1/results/cluster/`.
The cluster collector reread completion files after querying Slurm and allowed a 120-second shared-filesystem visibility grace period.
It ran separately from the immutable GPU worker directory and did not change policy execution or submitted jobs.
The collector, local synchronizer, and monitoring process exited after verifying completion; no jobs from this study remain active.
Compact final results are archived below and incorporated into the manuscript and two new coverage figures.
The historical figures and their numeric evidence remain a separate study.

For an immediate compact-results refresh:

```sh
python experiments/pull_cachewise_part1.py \
  --remote-root /export/home4/wspang/cachewise-rerun/part1-coverage-20261108-v1 \
  --output experiments/cachewise_part1/results/cluster
```

`results/COMPLETE` and `part1-comparison.json` with status `complete` and 60 audited rows denote successful completion; `progress.json` reports partial progress.
Those are the original strict criteria; the observed preemption below requires a distinct amended completion status for this execution.
The array submission record, protocol hash, passed smoke audit, and counter probe are preserved in `notes/experiment-evidence/part1-coverage-launch.json` and `part1-coverage-validation.json`.
The launch record is historical status at submission, rather than a completion claim.

Setup history is retained on the cluster: job 16280 was cancelled while pending after a required-node-list setting requested four nodes; it consumed no run time.
Job 16283 passed the engine and worker tests but stopped before inference because the initial copied runner lacked repeat-index support.
The final validation uses the already validated parallel runner with SHA-256 `7ba2edcbc8c45a2e3b9a4320c24c2467504f9087a05c4fcb98db72526c7c6c31` and the unchanged engine patch SHA-256 `0289afa28f92c1db66684923d69336d833a4a52f89af84c62cb57f9bcdcf03ad`.
Neither setup attempt contributes performance results; the registered workload and predictor bootstrap were not changed.

### Monitoring repair and declared protocol deviation (2026-11-08)

At 14:56 UTC, task 3 (A-N20, repeat 0) finished all four policy replays without client errors, but its worker audit rejected one real preemption in prefix-aware/predictive eviction.
All policies completed 150 requests, 6,458,386 prompt tokens, and 27,809 output tokens with matching request hashes and lengths.
Complete eviction counters cover every request without duplicate completion callbacks.
The failure was the registered zero-preemption assumption, rather than a replay or engine crash.

The monitoring repair preserves the original protocol, worker signatures, raw results, and rejection.
It does not change execution settings or rerun a policy until preemption disappears.
`experiments/part1-preemption-audit-amendment.json` records the post hoc correction at 15:06 UTC, before any N=30 or additional-cohort block completed.
An identical archived copy is in `experiment-evidence/part1-preemption-audit-amendment.json`.
Actual preemptions are retained as outcomes, and all other integrity and environment requirements remain enforced.

Inspection also confirmed that the engine's request-level computed-prefill histogram is derived from prompt-minus-cached usage.
The amended analysis calls it `reported_uncached_prompt_tokens`; neither the server/request agreement nor the first-use difference measures all extra execution caused by preemption.
That extra work is recorded as unknown when preemptions occur.
No exact redundant-computation claim should be made from those counters.

The independent analyzer, `experiments/audit_cachewise_part1_observed.py`, writes separate results under `results-observed/` and never rewrites original replay artifacts.
Passed strict audits are retained as evidence; blocks rejected for preemption undergo independent request/archive, token, configuration, full-counter, and source checks.
Unrelated failures, wrong output lengths, missing counters, and noninteger/negative preemption counts are still rejected.
All original worker, runner, and prepared-input hashes were checked unchanged after the first amended analysis.
Twenty local tests passed, including nine regression cases for these amendment boundaries.

At 15:13 UTC, all six A-N10/A-N20 blocks (24 policy runs) had been validated under this recorded amendment, with one observed preemption; the original strict audit passed 20 of those runs.
The three N=30 tasks were running, with the additional cohorts still queued.
This is a progress snapshot, not a completed-study finding.
The amended collector is process 3678117; the replaced collector's code/state and process record are preserved in the remote `control/` directory.
Local synchronization was updated to recognize the separate results, and the monitoring agent continued checking failures and process health until final completion.

Successful amended completion requires `results-observed/COMPLETE_WITH_PROTOCOL_DEVIATION`, a comparison status of `complete_with_protocol_deviation`, all 60 rows, and `original_protocol_fully_satisfied: false`.
The original strict `results/COMPLETE` marker must not be created for this execution.
The complete report should disclose this deviation and the remaining limit on computation accounting.

### Completed coverage results

The final marker was written at `2026-11-08T19:26:08.302837+00:00` and synchronized locally before the monitoring agent closed its checks.
The archived comparison contains exactly 60 unique setting/repeat/policy rows, 6,384 requests, and 1,011,600 generated output tokens.
CSV and JSON measurements agree; all 15 block audits share the same protocol, engine patch, package, model snapshot, worker-source, analyzer, and amendment hashes.
The frozen worker, runner, and prepared-input signatures were checked unchanged after the complete execution.
The single preemption occurred in A-N20, repeat 0, prefix-aware/predictive eviction.
Its original Slurm validation failure and traceback are retained in the completion provenance.

Mean session serving time in seconds, averaged over the three matched repeats:

| Setting | FCFS/LRU | FCFS/predictive | Prefix-aware/LRU | Prefix-aware/predictive |
| --- | ---: | ---: | ---: | ---: |
| A, N=10 | 547.35 | 481.73 | 227.78 | 256.60 |
| A, N=20 | 1,352.30 | 1,281.92 | 517.33 | 589.80 |
| A, N=30 | 1,997.35 | 1,929.49 | 699.83 | 777.53 |
| B, N=10 | 447.56 | 417.72 | 256.59 | 282.42 |
| C, N=10 | 630.52 | 600.22 | 265.62 | 380.83 |

These are descriptive results for the registered runtime-bounded cohorts.
They retain all repetitions, including the observed preemption, and must remain separate from the historical six-policy study.
Observed repeat ranges in the saved rows are not confidence intervals, and the usage-derived token counts do not establish exact executed recomputation.

- `experiment-evidence/part1-coverage-comparison.json`: all 60 numeric rows, frozen selection, and declared amendment.
- `experiment-evidence/part1-coverage-measurements.csv`: the same run-level measurements in tabular form.
- `experiment-evidence/part1-coverage-completion.json`: completion checks, block audit references/hashes, environments, frozen source hashes, and original rejection.

### Coverage results incorporated into the report (2026-11-09)

Section 3 now reports the frozen cohort-selection rule, all five workloads, the
60-run results, and the audit deviation separately from the historical study.
The abstract, contribution summary, threats to validity, and conclusion reflect
the expanded Part 1 evidence. At that revision the offloading sections remained plans; the subsequent host-study writing update is recorded below.

`paper/figures/plot_coverage.py` generates two new publication figures and two
numeric-evidence-derived LaTeX tables:

- `replication-coverage-serving.pdf`: nested A-cohort load curves and matched
  predictive-versus-LRU effects for both schedulers across all settings.
- `replication-coverage-accounting.pdf`: full allocation-eviction counts,
  completed-request uncached usage with first-use references, and P99 request
  latency, with observed repeat ranges.

Prefix-aware LRU has the lowest mean session serving time in all five settings.
Predictive eviction helps FCFS in all 15 matched comparisons and raises time
under prefix-aware scheduling in all 15. These are descriptive findings from
three repeats per setting, not population significance claims.
At N=20 and N=30, prefix-aware LRU improves mean session time but has higher
request P99 than FCFS/LRU; the text and figures explicitly retain this tradeoff.
The one preemption is retained, and reported uncached tokens are not relabeled
as all executed or redundant computation.

To regenerate the new figures, tables, numeric summary, matched effects, and
hash provenance using only this repository's archived evidence:

```sh
python paper/figures/plot_coverage.py
```

## Host-study writing completion

The report is now framed as **CacheWise Replication and Fetch-Aware KV Cache Recovery**.
Its completed recovery scope is GPU–host DRAM; SSD storage remains future work.
The introduction, related-work scope, methods, evaluation, discussion, and conclusion
have been made consistent with the existing implementation and reported results.
No new experiment, replay, correctness run, or benchmark was launched for this writing revision.

`experiment-evidence/host-dram-reported-results.json` is a compact transcription
of rounded values already reported in the manuscript and the Mini-SGLang artifact
at revision `3f9aee7362004126e937ba88085ff72f9ad6083a`.
Every plotted observation maps to an upstream JSON path and Git blob identifier.
The snapshot does not claim an independent audit of all 43 raw result files.
Main baseline/restoration cells each have one observation; the N=36 policy comparison
shows both available observations and does not infer confidence intervals or matched blocks.

The upstream prose's 37.5 GiB host-capacity label was corrected by arithmetic:
196,608 token slots × 196,608 bytes/token = 38,654,705,664 bytes = **36 GiB**.
That is nominal KV tensor payload, not measured total process memory.
The same payload calculation gives 24 GiB for the GPU KV pool.
The reported time/throughput observations were not altered.

Source inspection clarified the fetch-aware score's `d_i` (input-prompt tokens)
and the prefetch exchange guard's `tau` (estimated seconds until the candidate returns).
It also clarified that the host artifact's `recomputed_tokens` is a prior-prefix
deficit estimate, including alignment effects, and that its percentile definition
differs from the vLLM study. No physical recomputation count or exclusive GPU-time
claim is inferred from it.

`paper/figures/plot_host_results.py` renders an architecture diagram, a two-panel
restoration comparison, a policy/repetition comparison, and the corresponding
LaTeX table and CSV directly from those reported observations.
Input/script/output hashes are in `paper/figures/host-figure-provenance.json`.
The original vLLM evidence and figures are unchanged.
Regenerate these writing artifacts with:

```sh
python paper/figures/plot_host_results.py
```

The review PDF omits author identities rather than displaying fictional names.
Actual author names, affiliations/student IDs, and the course page limit still
need to be supplied before submission.

## Part 1 presentation planning

The Part 1 owner will present the completed adapted replication using the
[15-minute presentation outline](../presentation/part1-15-minute-outline.md).
It budgets 13 minutes for the talk and 2 minutes for questions, maps the current
coverage figures to slides, and keeps historical results and detailed audit
material in backup. Parts 2 and 3 appear as a short research handoff.

## Record-keeping guidelines

- Reading notes: source link, citation key, problem, method, findings, limitations, and relevant page numbers.
- Discussion records: date, participants, topics, decisions, action items, and owners.
- Experiment records: hypothesis, code version, execution environment, parameters, commands, raw data location, and analysis.
- Clearly mark unverified information so it is not presented as an established fact in the report.

## Six-page report and ten-minute presentation (2026-11-09)

The concise report is six pages including references, using the unchanged USENIX style, two columns, and 10 pt body text.
Repeated background, setup descriptions, historical tables, and metric-by-metric plots were reduced.
The report contains three figures and one compact results table:

| Included item | Purpose |
| --- | --- |
| Coverage serving figure | Load-sweep means and matched predictive-eviction effects |
| Compact coverage table | Absolute means for all five settings, including B/C |
| Host architecture | Implemented save/restore path and nominal capacities |
| Consolidated host figure | Recovery comparison and policy ablation with additional observations |

Corpus, historical six-policy, coverage accounting, and separate host figures and tables remain in `paper/figures/` as supporting artifacts.
The older uncached timing profile remains archived but is omitted because it cannot be combined with the host study into a controlled recovery ratio.
Historical oracle/aging and request-tail findings remain in the text.
The preemption amendment, metric definitions, added-capacity qualification, sparse host repetitions, and unimplemented SSD scope are retained.

`paper/figures/plot_compact_results.py` verifies the frozen coverage evidence through the existing loader, then generates the compact table and consolidated host figure.
Its input/script/output hashes are in `paper/figures/compact-figure-provenance.json`.
Existing detailed figure generators remain unchanged.

`presentation/` contains the whole-study PowerPoint and PDF, ten-slide timing plan, embedded and Markdown speaker notes, chart assets, and generation source.
Plots are redrawn at larger type sizes from the same evidence.
The slide timings total 600 seconds, excluding questions; rehearse to adjust pacing.
This revision executes document builds and rendering only, with no new experiments, replays, model calls, or correctness runs.
