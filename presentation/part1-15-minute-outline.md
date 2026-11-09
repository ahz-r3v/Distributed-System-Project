# CacheWise Replication: 15-Minute Presentation Outline

## Scope and central message

- **Presenter:** Part 1 owner; add your name, affiliation, and course details when building the slides.
- **Audience:** Distributed systems classmates; explain KV caching before introducing the policies.
- **Timing assumption:** 13 minutes of presentation plus 2 minutes of questions.
- **Scope:** Completed CacheWise replication and its implications for the next parts of the project.
- **Central message:** In our adapted setup, prefix-aware LRU has the lowest mean session serving time in every coverage setting. Predictive eviction helps FCFS, while adding it to prefix-aware scheduling increases the mean. Request tails expose a separate tradeoff.

Focus the main presentation on the completed **60-run coverage study**. Keep the historical six-policy experiment separate and available as backup. The paper now also analyzes reported host-DRAM restoration results in Parts 2 and 3; this Part 1 talk keeps that work to a brief handoff, while SSD support remains future work.

If the allocated 15 minutes excludes questions, add one minute to the KV-cache explanation and one minute to the results discussion, keeping the same slide sequence.

## Timed slide sequence

| Slide | Time window | Duration | Title | Main purpose |
| --- | --- | --- | --- | --- |
| 1 | 0:00–0:30 | 0:30 | CacheWise Replication: Scheduling, Eviction, and Tradeoffs | State the question and scope. |
| 2 | 0:30–1:30 | 1:00 | Why Coding Agents Need Prefix Reuse | Explain the serving problem. |
| 3 | 1:30–2:45 | 1:15 | Two Decisions: What Runs Next, and What Stays Cached? | Introduce the two mechanisms and four controls. |
| 4 | 2:45–4:00 | 1:15 | Our Adapted Replication Setup | Establish the testbed and comparison boundaries. |
| 5 | 4:00–5:15 | 1:15 | A Matched 60-Run Study | Explain workloads, repeats, and selection. |
| 6 | 5:15–6:00 | 0:45 | What We Measure and Validate | Define the main metric and evidence checks. |
| 7 | 6:00–7:30 | 1:30 | Prefix-Aware LRU Leads across Tested Loads | Present the concurrency results. |
| 8 | 7:30–8:30 | 1:00 | The Eviction Effect Persists across Cohorts | Show robustness and matched comparisons. |
| 9 | 8:30–9:45 | 1:15 | Evictions and Uncached Usage Follow the Ordering | Connect performance with cache measurements. |
| 10 | 9:45–10:45 | 1:00 | Mean Session Time and Request Tails Differ | Explain the P99 tradeoff. |
| 11 | 10:45–12:00 | 1:15 | What These Results Establish | Explain limits and the retained preemption. |
| 12 | 12:00–13:00 | 1:00 | Findings and the Next Recovery-Cost Question | Conclude and hand off to Parts 2 and 3. |
| 13 | 13:00–15:00 | 2:00 | Questions | Discuss scope, interpretation, and next steps. |
| **Total** | **0:00–15:00** | **15:00** | | **13:00 presentation + 2:00 questions** |

## Slide outlines

### 1. CacheWise Replication: Scheduling, Eviction, and Tradeoffs

- Introduce your role: reproducing and evaluating CacheWise mechanisms in Part 1.
- State the question: how do scheduling and eviction interact when GPU memory cannot retain every agent's prefix?
- Preview the finding: the scheduling benefit is strong in our setup; predictive eviction's effect depends on the scheduler.

**Visual:** Title and one simple agent → LLM → tool → LLM loop. Create this diagram when building the slides.

**Transition:** Explain why returning to the LLM makes cached prefixes valuable.

### 2. Why Coding Agents Need Prefix Reuse

- Define the KV cache as reusable attention state for an already processed prefix.
- An agent alternates between LLM requests and tool execution; its context grows between turns.
- Limited GPU memory can force cached prefixes out before the next turn returns.

**Visual:** One timeline showing two LLM turns separated by a tool wait, with a retained-cache path and an evicted-prefix recovery path. The prompt/output CDF in [the workload figure](../paper/figures/replication-workload.pdf), panel (a), is an optional supporting inset; avoid crowding the slide.

**Presenter emphasis:** The descriptive corpus has a median prompt length of 80,670 tokens and a median output of 26 tokens. These describe the broader deduplicated corpus, not the serving cohort. Use them only if showing the supporting CDF.

### 3. Two Decisions: What Runs Next, and What Stays Cached?

- Scheduling decides which waiting request runs next: FCFS follows arrival order; prefix-aware favors requests needing fewer additional KV blocks.
- Eviction decides which cached state to remove: LRU uses recency; learned predictive eviction uses tool information to estimate future reuse.
- Evaluate all four combinations so that the effect of one mechanism can be compared while holding the other fixed.

**Visual:** A 2×2 matrix, with scheduling on one axis and eviction on the other. Keep the four policy names and colors consistent with the existing figures. State that queue aging is disabled in the coverage study.

**Transition:** Explain the concrete environment in which these four combinations are tested.

### 4. Our Adapted Replication Setup

- Qwen2.5-Coder-14B-Instruct, BF16, one RTX Pro 6000 Blackwell Max-Q GPU per repeat block.
- KV budget: 17,981 blocks × 16 tokens = 287,696 tokens; 512-token prefill chunks.
- Redacted traces are replayed using synthetic token content and recorded token lengths; tool-name prediction uses a bootstrap from 34 training sources excluded from serving evaluation.

**Visual:** A compact setup card and a small memory-capacity illustration. In cohort A at N=30, initial prompt lengths sum to about 4.10 times the token capacity.

**Presenter emphasis:** Describe this as an adapted replication. Hardware, model, available text, and predictor inputs differ from the reference evaluation. FCFS/LRU is a control within the same engine fork, rather than a separate stock-vLLM baseline.

### 5. A Matched 60-Run Study

- Cohort A uses nested N=10, 20, and 30 selections; B and C add two N=10 workloads from source sessions disjoint from A, each other, and training.
- Four policies × five workload settings × three matched repeats = **60 runs and 6,384 requests**.
- Freeze metadata-based selection before outcomes; retain complete segments under declared runtime budgets and preserve selected recorded waits.

**Visual:** A five-setting study grid with the four-policy matrix beside it. Use [the workload table](../paper/figures/replication-coverage-workloads.tex) for counts, rather than placing every workload statistic on the slide.

**Presenter emphasis:** All policies within a repeat block share one physical GPU and receive identical requests, with fresh servers. The earlier six-policy experiment has different workloads/instrumentation and stays separate. Increasing N also changes workload composition.

### 6. What We Measure and Validate

- **Primary metric:** mean, across segments, of the sum of their LLM request latencies, averaged over three repeats; tool execution waits are excluded.
- **Supporting metrics:** request P99, useful-token goodput, cache hits, full allocation-eviction events, and reported uncached prompt usage.
- Verify request hashes/lengths, completion, counter coverage, and frozen inputs/environment. All requests complete without client errors; one preemption is retained and disclosed.

**Visual:** A small metric-definition diagram separating LLM request latency from external tool waits. Add the footer: “Three repeats; whiskers show observed ranges, not confidence intervals.”

**Transition:** Begin with the primary metric; return to tails and accounting after the main results.

### 7. Prefix-Aware LRU Leads across Tested Loads

- Show cohort A at N=10, 20, and 30 with all four policies.
- Prefix-aware LRU reduces mean session time relative to FCFS/LRU by about 58%, 62%, and 65%, respectively.
- At N=30, the mean falls from 1,997.35 seconds to 699.83 seconds. Adding predictive eviction to prefix-aware scheduling raises it to 777.53 seconds.

**Visual:** Enlarge panel (a) of [the coverage serving figure](../paper/figures/replication-coverage-serving.pdf). Highlight the green prefix/LRU curve and annotate one N=30 comparison.

**Presenter emphasis:** Lower is better. Explain the policy ordering, then give the N=30 example. These nested workloads add different segments as N grows, so the curve is not a concurrency-only experiment at fixed composition.

### 8. The Eviction Effect Persists across Cohorts

- Prefix-aware LRU has the lowest mean session time in all five coverage settings.
- Predictive eviction improves FCFS in all 15 matched comparisons, while raising mean time under prefix-aware scheduling in all 15.
- Relative to prefix-aware LRU, prefix-aware predictive eviction raises the setting means by 10.07–43.38%; the additional cohorts preserve the direction.

**Visual:** Enlarge panel (b) of [the coverage serving figure](../paper/figures/replication-coverage-serving.pdf). Explain the zero line and that negative values mean lower time. Identify B10/C10 as the additional cohorts.

**Presenter emphasis:** Each point compares policies within the same GPU repeat. Three repeats per setting support a descriptive result, not a population significance claim.

### 9. Evictions and Uncached Usage Follow the Ordering

- The new study counts every successful cached-block removal during allocation, separately from other invalidations.
- At N=30, mean allocation-eviction events per run are approximately 549k for FCFS/LRU, 202k for prefix-aware LRU, and 237k for prefix-aware predictive eviction.
- The setting-level eviction and uncached-usage orderings are consistent with the mean-time ordering; they do not identify the cause of the gap.

**Visual:** Enlarge panels (a) and (b) of [the coverage accounting figure](../paper/figures/replication-coverage-accounting.pdf). Keep the black first-use marks in panel (b), with a short explanation.

**Presenter emphasis:** Uncached usage includes first-use work. It is not exact redundant or physically executed prefill; eviction events are not transferred KV bytes. Explain only the key units and one N=30 comparison aloud.

### 10. Mean Session Time and Request Tails Differ

- A policy can improve average accumulated session time while making some individual requests wait longer.
- At N=30, average per-run P99 request latency is 712.53 seconds for FCFS/LRU and 1,292.43 seconds for prefix-aware LRU.
- The same direction appears at N=20; the study does not establish a fairness guarantee or evaluate a newly tuned aging rule.

**Visual:** Enlarge panel (c) of [the coverage accounting figure](../paper/figures/replication-coverage-accounting.pdf). Highlight the N=20 and N=30 groups; label the values as request P99, not session mean or maximum.

**Transition:** State the scope and measurement limits before concluding.

### 11. What These Results Establish

- Results apply to synthetic-token replays with a 14B model, tool-name prediction, runtime-bounded complete segments, and three repeats per setting.
- N=30 contains 30 segments from 23 sources; the nested sweep changes composition as well as concurrency.
- One preemption in A/N=20, repeat 0, prefix-aware/predictive violates the original zero-preemption condition. A documented post hoc audit amendment retains it and all original results while enforcing the remaining integrity checks.
- Additional prefill caused by that event remains unmeasured. The cause of predictive eviction's regression is unresolved; predictor-key alignment and CPU/GPU profiling are follow-up diagnostics.

**Visual:** Four short statements under “Workload,” “Coverage,” “Preemption,” and “Accounting.” Keep the technical audit details in backup.

**Presenter emphasis:** Clearly acknowledge the deviation; do not describe every run as satisfying the original protocol or attribute the entire result to predictor error.

### 12. Findings and the Next Recovery-Cost Question

- Prefix-aware scheduling with LRU delivers the lowest mean session time across the tested settings.
- Predictive eviction's effect depends on the scheduler; average performance and request tails require separate evaluation.
- Full eviction events and uncached usage show remaining recovery-related activity, with the stated accounting limits.

**Visual:** Three takeaway lines and one handoff question: **“When does restoring KV state from secondary storage cost less than recomputing a prefix?”**

**Presenter emphasis:** Parts 2 and 3 analyze existing host-DRAM restoration observations and fetch-aware scheduling in a separate Mini-SGLang artifact. SSD support and full storage write/restore measurements remain future work. Part 1 does not prove secondary-storage offloading is cheaper; host offloading is already part of CacheWise's evaluated scope.

### 13. Questions

Keep the three takeaways and the recovery-cost question visible. Use the backup material below when a question needs more detail.

## Backup slides — outside the timed sequence

| Backup | Topic | Evidence and purpose |
| --- | --- | --- |
| B1 | Historical six-policy experiment | [Historical serving figure](../paper/figures/replication-serving.pdf). Explain the initial 18 runs, oracle and queue-aging diagnostics, and why their absolute values are separate from the coverage study. |
| B2 | Complete coverage results | [Five-setting results table](../paper/figures/replication-coverage-results.tex) and [run-level CSV](../notes/experiment-evidence/part1-coverage-measurements.csv). Answer questions about exact values, goodput, or repeat variability. |
| B3 | Predictor preparation | [Replication discussion](../paper/sections/03-cachewise-replication.tex). Individual-tool bootstrap keys can differ from runtime parallel-batch keys; its isolated performance impact has not been measured. |
| B4 | Preemption and computation accounting | [Audit amendment](../notes/experiment-evidence/part1-preemption-audit-amendment.json) and [completion provenance](../notes/experiment-evidence/part1-coverage-completion.json). Fourteen blocks passed the original strict audit; all 15 passed the separately declared amended analysis. No run was discarded or repeated to remove the event. |
| B5 | Reproduction and environment | [Experiment instructions](../experiments/README.md), [protocol](../experiments/cachewise_part1/protocol.json), and [figure provenance](../paper/figures/replication-coverage-provenance.json). Show model/engine versions, selection rules, and how to regenerate the figures. |

## Slide-building and rehearsal notes

- Use one main message per slide; show enlarged figure panels instead of screenshots of full paper pages.
- Keep the four policy colors consistent: blue FCFS/LRU, orange FCFS/predictive, green prefix/LRU, purple prefix/predictive.
- Use rounded numbers in speech, with precise values and units on the slide or in backup.
- State early that the main metric excludes tool waits, then explicitly distinguish it from request P99.
- Keep the single-preemption disclosure visible in the results notes and explain it on slide 11.
- Reach slide 7 by minute 6 and the conclusion by minute 12. If running late, shorten setup detail and move the cache-accounting example to backup; retain the main findings, tail tradeoff, and preemption disclosure.
- Cite the CacheWise paper when introducing its mechanisms, and add a short project-data source note to result slides. The paper's verified citation is in [the shared bibliography](../paper/references.bib).
- Figure crops, diagrams, and actual slides are planned assets at this stage. This file provides the structure; the existing paper figures are linked above for reuse.
