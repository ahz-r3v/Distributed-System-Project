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
当前没有已完成的 DRAM/SSD 卸载对比、完整淘汰计数或实际 KV 传输字节数；这些是下一阶段证据缺口。

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

## 记录建议

- 阅读笔记：原文链接、引用键、问题、方法、结论、局限及关键页码。
- 讨论记录：日期、参与者、议题、决定、待办与负责人。
- 实验记录：假设、代码版本、运行环境、参数、执行命令、原始数据位置与分析。
- 对暂未核实的信息明确标注，避免在正文中误写为既定事实。
