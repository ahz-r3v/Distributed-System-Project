# 研究记录

选题、阅读笔记、讨论结论与实验记录统一放在这里。
文件名建议使用 `YYYY-MM-DD-topic.md`，记录来源与决定，方便追溯。

## 项目待确定事项

| 项目 | 当前状态 |
| --- | --- |
| 论文题目与研究问题 | 暂定 Beyond CacheWise；围绕复现、重计算与卸载的代价、二级存储卸载方法 |
| 报告格式 | USENIX / OSDI 官方双栏样式；用于课程报告 |
| 写作语言与篇幅限制 | 待确认 |
| 作者与章节分工 | 待确认 |
| 基线、实验指标与数据来源 | 已核对 cachewise-coding-traces 的六策略、三轮、N=10 实验；卸载对比待测 |
| 初稿、审阅与提交时间 | 待安排 |

## 当前论文主线

1. 复现 CacheWise：记录原论文与本项目的环境差异，报告实际结果与策略消融。
2. 分析重计算与卸载：固定调度与淘汰策略，比较相同缺失前缀的重计算、DRAM 恢复和 SSD 恢复，计入完整读写路径。
3. 提出并评估二级存储方法：先实现同步分块卸载基线，再按证据选择异步传输、预取和代价决策等优化。

原论文来源：[CacheWise v1](https://arxiv.org/abs/2606.16824v1)，引用键 `Tiwari2026CacheWise`。
核对原文第 6.4 节，明确已有 DRAM 卸载与拟研究的二级存储扩展之间的边界。
英文写作提示及预期图表已放入 `paper/sections/`；复现章节已有实测结果，卸载方法与其评估仍为计划。

## 已核对的实验结果（2026-11-08）

主结果使用 `/home/ws/cachewise-coding-traces/serving_experiment/results/2026-11-04/parallel-13943/consolidated-comparison.json`。
这是六策略各三轮的统一实验，共 18 次完整运行、1,494 次请求；每轮内六策略共享同一 GPU，不同轮使用相同型号的不同 GPU。
已从原始 `summary.json` 的请求明细重新计算并核对全部 18 次运行的会话均值、token 数及加权缓存命中率。

- Prefix-aware LRU 的平均会话服务时间为 337.87 秒，learned CacheWise（无排队 aging override）为 349.67 秒，后者高 3.49%。
- FCFS 下 predictive eviction 将均值从 595.04 秒降至 529.97 秒；预测策略的效果取决于调度方式。
- 记录工具时长的 oracle 为 349.58 秒，与 learned 方法没有一致的实质差距；它不是全知最优淘汰策略。
- 移除本地 30 秒排队 aging override 后，均值从 599.14 秒降至 349.67 秒，但最大请求时延升高；最大值不能当成 P99。
- 只覆盖一个 N=10 cohort；区间是三轮实际范围，不是置信区间。未命中 token 包含首次 prefill，不能全部视作重复计算。

独立的 job-10807 `recompute-profile.json` 包含各长度三次未命中请求计时；例如 65,536 tokens 的中位客户端时延为 19.569 秒。
该计时不是独立 GPU prefill 时间，也不是卸载实验，不能直接证明 SSD 卸载更快。
早期 job-10807 的五策略结果与后续统一实验有不同的 terminal-session 处理，不应混用其比值。

紧凑原始结果、来源版本、校验值及范围说明保存在 `experiment-evidence/`。
历史统一实验没有完整淘汰计数，新增覆盖研究正在收集这些计数；当前仍没有已完成的 DRAM/SSD 卸载对比或实际 KV 传输字节数。

## Part 1 draft, figure choices, and remaining experiments

Part 1 now has a prose draft covering workload characterization, setup, metric definitions, the six-policy comparison, matched scheduling/eviction effects, oracle and queue-aging diagnostics, and replication limits.
The supporting KV-cache and CacheWise background is also drafted.
Parts 2 and 3 retain their existing plans; their proposed mechanisms and measurements are not claimed as completed work.
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

## 记录建议

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
Computed prompt tokens are checked against both server counters and completed-request usage.
First-use prompt tokens and excess computed tokens are reported separately; alignment and last-token overhead are not mislabeled as an exact recomputation count.
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

The full study is **running** as Slurm array **16293**, comprising 15 matched four-policy blocks and a maximum of three simultaneous single-GPU jobs.
Its first three tasks started on node06 and node07.
The requested steps 2 and 3 remain in progress until all 60 policy runs finish and the amended analysis below verifies their complete coverage.
The active full counters and metric extraction implement step 4; successful study-wide coverage still depends on completion of those runs.

Remote frozen study root: `/export/home4/wspang/cachewise-rerun/part1-coverage-20261108-v1` via the existing `ccds-ai` connection.
Compact artifacts are synchronized into the ignored local directory `experiments/cachewise_part1/results/cluster/`.
The active cluster collector rereads completion files after querying Slurm and allows a 120-second shared-filesystem visibility grace period.
It runs separately from the immutable GPU worker directory and does not change policy execution or submitted jobs.
No benchmark table in the manuscript has yet been replaced with unfinished measurements.

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
Local synchronization was updated to recognize the separate results, and the monitoring agent continues to check failures and process health.

Successful amended completion requires `results-observed/COMPLETE_WITH_PROTOCOL_DEVIATION`, a comparison status of `complete_with_protocol_deviation`, all 60 rows, and `original_protocol_fully_satisfied: false`.
The original strict `results/COMPLETE` marker must not be created for this execution.
The complete report should disclose this deviation and the remaining limit on computation accounting.

- 阅读笔记：原文链接、引用键、问题、方法、结论、局限及关键页码。
- 讨论记录：日期、参与者、议题、决定、待办与负责人。
- 实验记录：假设、代码版本、运行环境、参数、执行命令、原始数据位置与分析。
- 对暂未核实的信息明确标注，避免在正文中误写为既定事实。
