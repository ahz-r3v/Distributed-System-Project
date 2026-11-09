# Figures

Store figures used in the report here, together with editable source files or generation scripts.
Prefer vector PDF figures; use PNG for screenshots.
Do not commit the compiled report at `paper/build/main.pdf`; PDF files used as figures may be committed.

Include a figure with `\includegraphics{system-architecture.pdf}`, and add `\caption{...}` and `\label{fig:architecture}`.

For each experimental figure, record the input data location, version, generation command, and execution environment so other authors can reproduce it.

## Planned figures and tables

| Section | Figure or table | Required evidence |
| --- | --- | --- |
| CacheWise replication | Setup and result comparison between the original paper and the replication | Locations in the original paper, actual configurations, raw results, and uncertainty |
| CacheWise replication | Session serving time, eviction overhead, and recomputation overhead across concurrency levels | Repeated experiments for each policy under the same workload |
| Cost analysis | Recomputation, DRAM restore, and SSD restore time curves and break-even regions | Identical missing prefixes, complete write/read paths, and controlled file caching |
| Offloading methods | GPU–DRAM–SSD architecture and block lifecycle | Data paths and state transitions consistent with the implementation |
| Method evaluation | End-to-end results, ablation plots, and sensitivity plots | Results for each storage method under a fixed policy, plus I/O and resource overhead |

The report includes a six-policy results table and a separate uncached-request timing table; source snapshots and checksums are in `notes/experiment-evidence/`.
Part 1 includes four figures with documented data sources and generation scripts:

- `replication-workload.pdf`: Deduplicated input/output lengths, message counts, and durations for common tools.
- `replication-serving.pdf`: Session times from the historical six-policy study and policy effects matched within each repeat block.
- `replication-coverage-serving.pdf`: Coverage-study concurrency curves and matched predictive-eviction effects across all five settings.
- `replication-coverage-accounting.pdf`: Full allocation-eviction events, completed-request uncached prompt usage, and per-run P99 request latency across all five settings.

`prepare_replication_data.py` produces compact numeric evidence from the experiment repository; `plot_replication.py` can regenerate the figures using only the evidence saved in this repository.
See the Part 1 records in `notes/README.md` for commands, figure decisions, and remaining experiments.
`replication-figure-provenance.json` records checksums for inputs and the plotting script; `replication-paired-effects.csv` stores the per-repeat comparison values shown in the figure.
Existing job-10807 figures correspond to the earlier five-policy experiment and must not be reused as figures for the latest consolidated six-policy study.
Other proposed figures remain to be generated; do not fill them with fabricated data.

## Completed coverage study

Run `python paper/figures/plot_coverage.py` from the repository root with NumPy
and Matplotlib installed. It uses only archived evidence in this repository;
no cluster access or inference job is required.

The generator verifies comparison/completion/CSV/amendment hashes, all 60
registered setting/repeat/policy rows, the 6,384-request total, workload/token
accounting, and the retained single preemption. It produces vector PDFs, PNG
previews, the workload/results LaTeX tables used by the paper, a numeric summary,
and a CSV of matched effects. `replication-coverage-provenance.json` records input,
script, and output hashes plus library versions.

All points are equal-weight three-repeat means unless individual repeats are
shown. Whiskers span observed minima and maxima; they are not confidence
intervals. Percentage changes in the matched-effects CSV compare policies in
the same GPU block; prose/table comparisons use ratios of the corresponding
three-repeat means. First-use marks count prompt growth once per segment,
excluding prior output already counted as generated tokens.

The coverage study remains separate from the historical six-policy study.
Its final status is `complete_with_protocol_deviation`: A20 repeat 0 has one
preemption under prefix-aware/predictive eviction. The original rejection is
preserved. Uncached usage is not all executed prefill, additional preemption
work is unknown, and eviction-event counts are not bytes transferred.

## Host-DRAM recovery figures

`python paper/figures/plot_host_results.py` creates:

- `host-cache-architecture.pdf`: implemented queue/radix index, GPU cache,
  pinned-host cache, and the offload/restore paths.
- `host-restoration-results.pdf`: existing reported LRU+FCFS recovery timings
  and prior-prefix deficit estimates at N=28 and N=36.
- `host-policy-ablation.pdf`: reported N=36 component observations and both
  available observations for the predictive-prefix and CacheWise-Fetch policies.
- `host-restoration-table.tex`, `host-reported-observations.csv`, PNG previews,
  and `host-figure-provenance.json` with input/script/output hashes.

The input is `notes/experiment-evidence/host-dram-reported-results.json`.
It contains rounded values from the existing manuscript and the versioned
Mini-SGLang artifact, with per-observation file/blob mappings. Generating these
figures executes no model, replay, correctness experiment, or benchmark.
The single-run bars have no uncertainty intervals; the two N=36 observations
are plotted individually and are not asserted to be matched GPU blocks.
The figures use **36 GiB nominal host KV payload**, computed from the recorded
token capacity and bytes per token; the input documents the upstream 37.5 GiB
label discrepancy. These results do not evaluate SSD storage and must not be
pooled with the vLLM replication.
