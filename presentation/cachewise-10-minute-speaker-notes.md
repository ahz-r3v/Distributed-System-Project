# Ten-minute presentation speaker notes

10 slides · 10:00 planned speaking time · questions after the talk.

0:00–5:00: CacheWise paper and adapted replication (slides 1–5).
5:00–10:00: recovery costs, host methods, limitations and takeaways (slides 6–10).

The PowerPoint and PDF use the same layout. The PowerPoint includes these notes.
Timings are rehearsal targets, not a recording. No experiments were run to create this deck.

## 1. CacheWise replication and KV cache recovery

**0:00–0:20 · 20 seconds**

Hello everyone. This project asks how coding-agent servers can reuse previous computation when GPU memory is limited. We examine CacheWise scheduling and eviction, then look at restoring evicted KV state from host memory.

Evidence: Six-page report, abstract and §1

## 2. CacheWise: reuse prefixes across tool calls

**0:20–1:35 · 75 seconds**

CacheWise studies a pattern common in coding agents: a model request is followed by tool execution, then another request reusing much of the previous context. The KV cache stores attention keys and values, so keeping a prefix avoids processing it again during prefill. Tool waits create both an opportunity and memory pressure: inactive state is useful later but occupies GPU space now. CacheWise combines two mechanisms. Prefix-aware scheduling favors waiting requests needing fewer additional KV blocks. Predictive eviction uses tool metadata to estimate when inactive sessions will return and guide which cached state to retain. These mechanisms address request ordering and memory reclamation, respectively. The original paper also evaluates GPU–CPU offloading, so host offloading itself is not a new claim here. Our replication asks how the scheduling and eviction mechanisms behave in our adapted setup.

Evidence: CacheWise: Tiwari et al., arXiv:2606.16824v1; report §§1–3

## 3. Replication separates two decisions

**1:35–2:40 · 65 seconds**

We vary scheduling and eviction independently. The two schedulers are first-come, first-served and prefix-aware scheduling, which favors requests requiring less additional KV state. The two eviction policies are LRU and learned predictive eviction using tool names. All four combinations run in the same engine fork with fresh servers and identical selected inputs. Our testbed uses a 14-billion-parameter Qwen coding model in BF16 on one Blackwell GPU, with 287,696 KV token slots and 512-token prefill chunks. Cohort A has nested loads of ten, twenty, and thirty segments; B and C add two source-disjoint ten-segment cohorts. Four policies, five settings, and three repeats give sixty runs and 6,384 request executions. The primary metric sums model-request latencies within each session, excluding external tool waits.

Evidence: part1-coverage-comparison.json; report §3.1–3.2

## 4. Prefix / LRU has the lowest mean

**2:40–4:00 · 80 seconds**

This chart shows cohort A as the selected workload grows from ten to thirty concurrent segments. Lower is better. The blue and orange lines use FCFS; green and purple use prefix-aware scheduling. The largest separation comes from scheduling. Prefix-aware LRU reduces the FCFS/LRU mean by about 58 percent at ten segments, 62 percent at twenty, and 65 percent at thirty. The bars show the observed range of three repeats, not confidence intervals. The additional held-out B and C cohorts are included in the report table: prefix-aware LRU also has the lowest mean there, making five out of five settings. Increasing N adds new segments, so this is a nested workload sweep rather than a concurrency-only experiment with fixed composition. The result supports prefix-aware scheduling in this adapted replay; it does not establish a universal ranking across models or the entire trace population.

Evidence: frozen 60-run coverage study; report Table 1 and Figure 1a

## 5. Prediction depends on the scheduler

**4:00–5:00 · 60 seconds**

The predictive eviction result changes direction when we change the scheduler. Each point here compares predictive eviction against LRU within one matched repeat block. Values below zero mean predictive eviction is faster. Orange points use FCFS, and every orange point is below zero. Purple points use prefix-aware scheduling, and every purple point is above zero. Across settings, adding predictive eviction increases the prefix-aware mean by roughly ten to forty-three percent. The historical tool-duration oracle does not remove this local regression, so prediction accuracy alone does not explain it. There is also a responsiveness tradeoff: at A30, prefix/LRU improves the session mean but increases the average per-run request P99 from about 713 to 1,292 seconds. Scheduling should therefore be judged against both locality and latency objectives.

Evidence: matched coverage repeats and request tails; report Figure 1b and §3.3

## 6. Preserve evicted KV in host DRAM

**5:00–6:00 · 60 seconds**

The first five minutes covered CacheWise and our replication. The recovery extension is a separate Mini-SGLang implementation. One radix index records which prefix pages reside on the GPU and which have host copies. When memory is needed, dirty GPU pages are copied to pinned host DRAM. Clean inclusive copies can remain there, so a later GPU eviction does not require another save. When a request returns, a compatible host suffix is restored before prefill; if no copy survives, the engine recomputes. The implementation uses sixteen-token pages, locks and events to protect transfers, and predictive prefetch with a bounded per-step budget. In the recovery study the GPU pool holds twenty-four GiB of KV payload and the host tier adds thirty-six GiB. These are nominal cache payloads, excluding weights and other memory. No SSD path is implemented.

Evidence: Implementation: Mini-SGLangs 3f9aee7; report Figure 2 and §5

## 7. Host restoration reduces session time

**6:00–7:15 · 75 seconds**

A simple cost test is whether saving, restoring, and managing the copy costs less than recomputation. Here we keep LRU and FCFS fixed and compare recomputation with on-demand host restoration. At twenty-eight concurrent episodes, reported mean session time falls from 821 to 90.7 seconds, a baseline-to-restoration ratio of about 9.1. At thirty-six it falls from 1,060 to 222 seconds, about 4.8. The reported prior-prefix deficit also drops sharply, supporting the interpretation that more reusable state survives. Two qualifications matter. First, restoration adds thirty-six GiB of host KV capacity to the common twenty-four-GiB GPU pool, so this is not an equal-total-memory algorithm comparison. Second, each bar is one reported run. This study also uses a different engine, smaller GPU pool, larger prefill chunks, and transformed replay inputs. We therefore keep it separate from the vLLM replication. The result demonstrates a favorable host-DRAM operating regime, not a measured SSD break-even curve.

Evidence: host-dram-reported-results.json; report Figure 3a and §6

## 8. Fetch-aware ordering discounts host hits

**7:15–8:35 · 80 seconds**

Ordinary prefix-aware ordering considers the GPU prefix. Fetch-aware ordering also recognizes that a host-resident prefix can be cheaper than recomputing a complete miss. The priority is new prefill tokens plus alpha times the additional host tokens, with alpha fixed to 0.05. Lower-cost requests go first. This is a heuristic, not a calibrated latency predictor. On the left are the reported N-equals-thirty-six host ablations at fixed tier capacities. LRU plus prefix scheduling takes 159 seconds, predictive plus prefix takes 158, adding prefetch alone takes 172, and the full fetch-aware combination takes 136. The diamonds show the additional observations: 175 seconds for predictive-prefix and 135 for the full combination. The two descriptive means are 166.5 and 135.5 seconds. These sparse, not verified matched observations favor the full combination, but do not isolate every component or establish statistical significance. Prefetch alone is not enough in this example.

Evidence: Mini-SGLangs 3f9aee7; report Figure 3b and Eq. (3)

## 9. Keep the conclusions within the evidence

**8:35–9:20 · 45 seconds**

There are three boundaries to keep in mind. The replication uses synthetic content and runtime-bounded selected segments; increasing the load also changes the workload. One real preemption violated the original zero-preemption rule. It remains in the results under a disclosed post hoc audit amendment, and its extra computation is unmeasured. The host study is a separate replay with added backing capacity and mostly single-run observations. We reproduce its rounded reported values rather than claim an independent request-level audit. Finally, the implemented recovery tier is pinned host DRAM. SSD support would need complete storage writes and reads, bounded staging, compatibility metadata, and failure handling. We cannot infer an SSD speedup from these DRAM results.

Evidence: Limitations: report §§3.2, 6.1 and 7

## 10. Three takeaways

**9:20–10:00 · 40 seconds**

The first takeaway is that scheduling dominates the mean improvement in our adapted replication: prefix-aware LRU wins all five settings, while predictive eviction changes direction with the scheduler. The second is that retaining KV in host memory can avoid substantial recovery work for long prefixes, with large reported improvements when host capacity is added. The third is that host residency should inform request ordering. Fetch-aware scheduling is promising here, but the policy evidence is much smaller than the replication study. The completed scope is replication and host-DRAM recovery. SSD performance remains future work. Thank you; I am happy to take questions.

Evidence: Full results and qualifications: six-page report; archived evidence in repository
