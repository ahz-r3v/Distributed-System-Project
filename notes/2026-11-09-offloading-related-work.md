# Offloading related work and research scope

Date: 2026-11-09. Target: `paper/sections/02-related-work.tex`, subsection "Related Offloading Systems and Research Gap".
This revision supplies literature evidence and research positioning; it does not add an offloading implementation or experimental results.

## Primary sources checked

Conference versions take precedence over earlier preprints. Preprints are pinned to the versions read.
Page numbers below refer to printed paper pages, except where explicitly marked as PDF pages.

| Citation key | Verified source and location | Evidence used and limits |
| --- | --- | --- |
| `Abhyankar2024InferCept` | [ICML 2024 / PMLR](https://proceedings.mlr.press/v235/abhyankar24a.html), Sections 4.1-4.4, PDF pp. 6-7 | Preserve on GPU, swap to CPU, or discard according to estimated memory waste; pipeline and chunk swap/recomputation. Interruption-duration estimates already inform retention. Do not claim that tool-aware recovery is new. |
| `Gao2024CachedAttention` | [USENIX ATC 2024](https://www.usenix.org/conference/atc24/presentation/gao-bin-cost), Sections 3.2-3.3, pp. 115-117 | GPU/DRAM/disk hierarchy, asynchronous saving, layer-wise loading, and scheduler look-ahead for prefetch/eviction. Fetching/eviction granularity is a conversation. Earlier arXiv versions use the name AttentionStore; cite the final CachedAttention paper. |
| `Qin2025Mooncake` | [FAST 2025](https://www.usenix.org/conference/fast25/presentation/qin), Sections 3.2 and 4, pp. 158-162 | Distributed hashed blocks, inactive-block LRU, RDMA transfers, and cache/load-aware global scheduling. The architecture includes SSD resources; this is not evidence that every reported gain is from SSD access. |
| `Liu2025LMCache` | [arXiv v2, 5 December 2025](https://arxiv.org/abs/2510.09665v2), [HTML Sections 4-7](https://arxiv.org/html/2510.09665v2) | CPU/local/remote storage backends, batched transfers, layer-wise overlap, queued-request prefetch, and controller APIs. These are reusable infrastructure rather than one universal placement policy. Author order follows arXiv abstract metadata, which differs from the HTML title block. |
| `Jin2025Cake` | [ICML 2025 / PMLR](https://proceedings.mlr.press/v267/jin25d.html), Section 4, PDF pp. 3-5 | Compute prefix chunks forward and load cached chunks backward concurrently. This motivates treating pure compute/restore as baselines. The bibliography uses PMLR's author name Zhuoqing Mao; the PDF renders Z. Morley Mao. |
| `Xie2026Strata` | [OSDI 2026](https://www.usenix.org/conference/osdi26/presentation/xie-zhiqiang), Sections 4.2-4.4, pp. 5-8; Section 5.3.5, p. 12 | GPU-assisted transfers, delay-hit handling, cache-aware batches, configurable writing, and default LRU. The final paper includes a disk-caching experiment on a separate H20-storage platform; do not describe it as DRAM-only. |
| `Qiu2026Tutti` | [arXiv v1, 5 May 2026](https://arxiv.org/abs/2605.03375v1), [HTML Sections 3.1-3.3](https://arxiv.org/html/2605.03375v1) | GPU-native objects and asynchronous GPU I/O; profiled slack windows address compute and read/write contention. Cite as a preprint, not the placeholder conference/year printed in its template. |
| `Tumkur2026Placement` | [arXiv v1, 14 September 2026](https://arxiv.org/abs/2609.16215v1), [HTML Sections III, V, VI](https://arxiv.org/html/2609.16215v1) | Calibrated discrete-event simulation of placement and prefetching. Capacity gains and policy effects are distinct. Results are bounded by workload construction and batch-one simulation; they are not measured SSD serving results for our engine. |
| `Tiwari2026CacheWise` | [arXiv v1, 15 June 2026](https://arxiv.org/abs/2606.16824v1), [HTML Section 6.4](https://arxiv.org/html/2606.16824v1) | Already evaluates GPU/CPU swapping. The project's extension concerns a secondary-storage tier, not the first addition of any offloading to CacheWise. |

## Research question and evidence boundary

The question is when SSD offloading pays for the adapted coding-agent workload at bounded GPU and DRAM capacity, and whether reuse estimates improve recovery beyond simpler offloading controls.
The proposed contribution is an empirical characterization and, only if implemented and validated, a workload-specific policy.
No claim of being the first SSD tier, asynchronous transfer mechanism, prefetcher, or cost-aware recovery decision is justified by this survey.

The experimental comparison should:

- Hold request scheduling and GPU eviction fixed while comparing recomputation, DRAM restoration, and SSD restoration for identical missing prefixes.
- Include writes, reads, staging copies, management, queueing, and contention; distinguish device I/O from operating-system file-cache hits.
- Report total work separately from critical-path delay. Measure the interval until the next model request after a tool batch, rather than assuming one tool's duration is the available window.
- Compare synchronous offloading, asynchronous offloading without reuse estimates, and any proposed reuse-guided policy at matching tier capacities and on the same workload.
- Identify the simplified serial recovery model as a baseline; Cake already establishes a combined compute/load alternative.
- Report unfavorable regimes and predictor overhead or wasted transfers as well as improvements.

The existing replicated serving results and uncached-request timings do not establish an SSD benefit.
Sections 4-6 still need the corresponding implementation, measurements, and ablations before those claims can be made.
