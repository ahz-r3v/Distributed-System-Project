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
Part 1 includes two figures with documented data sources and generation scripts:

- `replication-workload.pdf`: Deduplicated input/output lengths, message counts, and durations for common tools.
- `replication-serving.pdf`: Session times from the latest six-policy study and policy effects matched within each repeat block.

`prepare_replication_data.py` produces compact numeric evidence from the experiment repository; `plot_replication.py` can regenerate the figures using only the evidence saved in this repository.
See the Part 1 records in `notes/README.md` for commands, figure decisions, and remaining experiments.
`replication-figure-provenance.json` records checksums for inputs and the plotting script; `replication-paired-effects.csv` stores the per-repeat comparison values shown in the figure.
Existing job-10807 figures correspond to the earlier five-policy experiment and must not be reused as figures for the latest consolidated six-policy study.
Other proposed figures remain to be generated; do not fill them with fabricated data.
