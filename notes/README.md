# Research records

Keep topic-selection notes, reading notes, discussion decisions, and experiment records here.
Use filenames such as `YYYY-MM-DD-topic.md`, and record sources and decisions for traceability.

## Project planning

| Item | Current status |
| --- | --- |
| Title and research questions | Working title: Beyond CacheWise; focus on replication, recomputation and offloading costs, and secondary-storage offloading methods |
| Report format | Official USENIX / OSDI two-column style, used for a course report |
| Language and length limit | English; length limit to be confirmed |
| Authors and section assignments | To be confirmed |
| Baselines, metrics, and data sources | Verified the six-policy, three-repeat, N=10 experiment from cachewise-coding-traces; offloading comparisons remain to be measured |
| Draft, review, and submission dates | To be scheduled |

## Current report outline

1. Replicate CacheWise: document differences between the original paper's environment and this project's environment, and report measured results and policy ablations.
2. Analyze recomputation and offloading: fix the scheduling and eviction policies, and compare recomputation, DRAM restore, and SSD restore for identical missing prefixes, including the complete read/write paths.
3. Propose and evaluate secondary-storage methods: first implement a synchronous block-offloading baseline, then use evidence to select optimizations such as asynchronous transfer, prefetching, and cost-based decisions.

Original source: [CacheWise v1](https://arxiv.org/abs/2606.16824v1), citation key `Tiwari2026CacheWise`.
Check Section 6.4 of the original paper to distinguish existing DRAM offloading from the proposed secondary-storage extension.
English writing prompts and planned figures and tables are in `paper/sections/`; the replication section contains measured results, while the offloading methods and their evaluation remain planned work.

## Verified experimental results (2026-11-08)

The main results use `/home/ws/cachewise-coding-traces/serving_experiment/results/2026-11-04/parallel-13943/consolidated-comparison.json`.
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
There are currently no completed DRAM/SSD offloading comparisons, complete eviction counts, or measurements of actual KV bytes transferred; these are evidence gaps for the next stage.

## Part 1 draft, figure choices, and remaining experiments

Part 1 now has a prose draft covering workload characterization, setup, metric definitions, the six-policy comparison, matched scheduling/eviction effects, oracle and queue-aging diagnostics, and replication limits.
The supporting KV-cache and CacheWise background is also drafted.
Parts 2 and 3 retain their existing plans; their proposed mechanisms and measurements are not claimed as completed work.
No new GPU jobs were launched for this revision.

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

The Part 2 owner needs matched recomputation, DRAM restore, and SSD write/restore timings for the same prefix states, including staging, file-cache controls, and contention.
The Part 3 owner needs an implemented offloading method, end-to-end comparisons against recomputation and simple offloading, and ablations of each optimization.
These are separate from the user's Part 1 replication scope.

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
The Introduction now connects this scope to the completed replication: its 18-run count, 1,494 request executions, and 43.22%, 10.94%, and 3.49% comparisons come from the consolidated results presented in Section 3.
It explicitly identifies the recovery model, candidate methods, and offloading evaluation as the framework and remaining experimental work, without claiming an SSD benefit.

## Record-keeping guidelines

- Reading notes: source link, citation key, problem, method, findings, limitations, and relevant page numbers.
- Discussion records: date, participants, topics, decisions, action items, and owners.
- Experiment records: hypothesis, code version, execution environment, parameters, commands, raw data location, and analysis.
- Clearly mark unverified information so it is not presented as an established fact in the report.
