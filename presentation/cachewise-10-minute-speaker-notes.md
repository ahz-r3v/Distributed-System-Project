# Ten-minute presentation speaker notes

13 slides · 10:00 planned speaking time · questions after the talk.

0:00–5:00: CacheWise paper and adapted replication (slides 1–8).
5:00–10:00: recovery costs, host methods, limitations and takeaways (slides 9–13).

The PowerPoint and PDF use the same layout. The PowerPoint includes these notes.
Timings are rehearsal targets, not a recording. No experiments were run to create this deck.

## 1. CacheWise replication and KV cache recovery

**0:00–0:15 · 15 seconds**

This project studies KV reuse for coding agents under limited GPU memory. We first examine CacheWise and its replication, then motivate and describe host-cache recovery.

Evidence: Six-page report, abstract and §1

## 2. What do the CacheWise traces contain?

**0:15–0:40 · 25 seconds**

CATraces records real Claude Code sessions: model requests, tool calls, timings, and token usage. The released content is redacted, so our replay preserves lengths and prefix growth with synthetic tokens. The next two slides use the original paper’s graphs to show why this workload needs special cache management.

Evidence: CacheWise v1 §§3–5; released-trace replay: report §3.1

## 3. CATraces: long inputs, short outputs

**0:40–1:20 · 40 seconds**

These are the original paper’s published prefill and decode distributions. A CDF shows the fraction of requests at or below a token length. Compare CATraces in red with the ShareGPT chat baseline in orange. The prefill curve is much farther right: agent prompts are much longer. The decode curve is farther left: outputs tend to be shorter. Reprocessing a large shared prefix can therefore be expensive even when little new text is generated. These are original-paper results, separate from our replay measurements.

Evidence: Cropped from Tiwari et al., CacheWise v1, Fig. 2 (PDF p. 4); CC BY 4.0

## 4. CATraces differ from traditional chat

**1:20–1:50 · 30 seconds**

ShareGPT is the chat baseline here. CATraces has many more turns in the left plot. On the right, follow blue CATraces versus purple ShareGPT: agent contexts grow much larger. One user task drives repeated model and tool calls, so KV must survive between requests and session completion matters alongside individual response latency.

Evidence: Cropped from Tiwari et al., CacheWise v1, Figs. 3 and 6 (PDF p. 4); CC BY 4.0

## 5. CacheWise predicts when a session returns

**1:50–2:45 · 55 seconds**

The scheduler serves the request with the fewest additional KV blocks: required state minus resident state. For eviction, CacheWise predicts tool-call duration from historical calls. The original paper embeds arguments with TF–IDF and clusters similar calls with KMeans, giving a duration distribution for each group. For a tool still running after elapsed time e, estimate the remaining time as E of D minus e, conditioned on D being greater than e. This accounts for the time already spent waiting. Evict unreferenced KV whose predicted reuse is farthest away, and refresh estimates as time passes. Our replication uses tool names only because arguments are redacted.

Evidence: Algorithm adapted from CacheWise v1 §§5.1–5.3; original-paper argument-aware predictor

## 6. Replication separates two decisions

**2:45–3:25 · 40 seconds**

We cross FCFS and prefix-aware scheduling with LRU and predictive eviction. All combinations use the same configuration and inputs. Our adapted setup uses a 14B Qwen coding model on one Blackwell GPU. A tests nested loads of ten, twenty, and thirty segments; B and C add separate held-out ten-segment workloads. Five settings, four policies, and three repeats give sixty runs and 6,384 request executions. The metric is mean summed model-request latency per session, excluding tool waits.

Evidence: part1-coverage-comparison.json; report §3.1–3.2

## 7. Prefix / LRU has the lowest mean

**3:25–4:20 · 55 seconds**

The green prefix/LRU line has the lowest mean at all three A loads. Compared with FCFS/LRU, the reduction is about 58, 62, and 65 percent as N rises. It also has the lowest mean in the B and C checks, making five settings out of five. Ranges show observed minima and maxima from three repeats, not confidence intervals. The load sweep adds segments, so concurrency and composition both change. These are our adapted replay results, separate from the preceding published workload graphs.

Evidence: frozen 60-run coverage study; report Table 3 and Figure 1a

## 8. Prediction depends on the scheduler

**4:20–5:00 · 40 seconds**

A is the nested load sweep; B and C are separate held-out workload checks with ten segments each. N means concurrent segments. Each dot compares predictive eviction against LRU in a matched repeat. Orange FCFS points are below zero, showing improvement. Purple prefix-aware points are above zero, showing regression. Prediction therefore depends on the scheduler across these workloads. Lower means do not guarantee lower request tails. We now turn to recovery after eviction.

Evidence: matched coverage repeats; report Figure 1b and §3.3

## 9. Host restoration reduces session time

**5:00–6:15 · 75 seconds**

After the CacheWise replication, we turn to recovery after eviction. Scheduling can limit churn, but useful state may still leave the GPU. Saving it in host memory allows restoration instead of repeating prefill. A simple cost test is whether saving, restoring, and managing the copy costs less than recomputation. Here we keep LRU and FCFS fixed and compare recomputation with on-demand host restoration. At twenty-eight concurrent episodes, reported mean session time falls from 821 to 90.7 seconds, a baseline-to-restoration ratio of about 9.1. At thirty-six it falls from 1,060 to 222 seconds, about 4.8. The reported prior-prefix deficit also drops sharply, supporting the interpretation that more reusable state survives. Two qualifications matter. First, restoration adds thirty-six GiB of host KV capacity to the common twenty-four-GiB GPU pool, so this is not an equal-total-memory algorithm comparison. Second, each bar is one reported run. This study also uses a different engine, smaller GPU pool, larger prefill chunks, and transformed replay inputs. We therefore keep it separate from the vLLM replication. The result demonstrates a favorable host-DRAM operating regime, not a measured SSD break-even curve.

Evidence: host-dram-reported-results.json; report Figure 3a and §6

## 10. Preserve evicted KV in host DRAM

**6:15–7:15 · 60 seconds**

These recovery observations motivate offloading. Here is how the Mini-SGLang host cache implements the save-and-restore path. One radix index records which prefix pages reside on the GPU and which have host copies. When memory is needed, dirty GPU pages are copied to pinned host DRAM. Clean inclusive copies can remain there, so a later GPU eviction does not require another save. When a request returns, a compatible host suffix is restored before prefill; if no copy survives, the engine recomputes. The implementation uses sixteen-token pages, locks and events to protect transfers, and predictive prefetch with a bounded per-step budget. In the recovery study the GPU pool holds twenty-four GiB of KV payload and the host tier adds thirty-six GiB. These are nominal cache payloads, excluding weights and other memory. No SSD path is implemented.

Evidence: Implementation: Mini-SGLangs 3f9aee7; report Figure 2 and §5

## 11. Fetch-aware ordering discounts host hits

**7:15–8:35 · 80 seconds**

Ordinary prefix-aware ordering considers the GPU prefix. Fetch-aware ordering also recognizes that a host-resident prefix can be cheaper than recomputing a complete miss. The priority is new prefill tokens plus alpha times the additional host tokens, with alpha fixed to 0.05. Lower-cost requests go first. This is a heuristic, not a calibrated latency predictor. On the left are the reported N-equals-thirty-six host ablations at fixed tier capacities. LRU plus prefix scheduling takes 159 seconds, predictive plus prefix takes 158, adding prefetch alone takes 172, and the full fetch-aware combination takes 136. The diamonds show the additional observations: 175 seconds for predictive-prefix and 135 for the full combination. The two descriptive means are 166.5 and 135.5 seconds. These sparse, not verified matched observations favor the full combination, but do not isolate every component or establish statistical significance. Prefetch alone is not enough in this example.

Evidence: Mini-SGLangs 3f9aee7; report Figure 3b and Eq. (3)

## 12. Keep the conclusions within the evidence

**8:35–9:20 · 45 seconds**

There are three boundaries to keep in mind. The replication uses synthetic content and runtime-bounded selected segments; increasing the load also changes the workload. One real preemption violated the original zero-preemption rule. It remains in the results under a disclosed post hoc audit amendment, and its extra computation is unmeasured. The host study is a separate replay with added backing capacity and mostly single-run observations. We reproduce its rounded reported values rather than claim an independent request-level audit. Finally, the implemented recovery tier is pinned host DRAM. SSD support would need complete storage writes and reads, bounded staging, compatibility metadata, and failure handling. We cannot infer an SSD speedup from these DRAM results.

Evidence: Limitations: report §§3.2, 6.1 and 7

## 13. Three takeaways

**9:20–10:00 · 40 seconds**

The first takeaway is that scheduling dominates the mean improvement in our adapted replication: prefix-aware LRU wins all five settings, while predictive eviction changes direction with the scheduler. The second is that retaining KV in host memory can avoid substantial recovery work for long prefixes, with large reported improvements when host capacity is added. The third is that host residency should inform request ordering. Fetch-aware scheduling is promising here, but the policy evidence is much smaller than the replication study. The completed scope is replication and host-DRAM recovery. SSD performance remains future work. Thank you; I am happy to take questions.

Evidence: Full results and qualifications: six-page report; archived evidence in repository
