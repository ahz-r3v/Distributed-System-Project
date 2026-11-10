# Original CacheWise paper and reused figures

Shubham Tiwari, Tapan Chugh, Nash Rickert, Simon Peter, Ratul Mahajan, and Haiying Shen.
*CacheWise: Understanding Workloads and Optimizing KVCache Management for Efficiently Serving LLM Coding Agents.*
arXiv:2606.16824v1, 15 June 2026.

- [Original PDF requested by the user](https://arxiv.org/pdf/2606.16824)
- [Pinned v1 PDF](https://arxiv.org/pdf/2606.16824v1)
- [HTML and algorithm description](https://arxiv.org/html/2606.16824v1#S5)
- License: [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/), verified in the PDF metadata
- Downloaded PDF SHA-256: `8787570ba7d61444aced8378af2069796d7e801920bc6b7476afabcc347aed3c`
- Local full-text copy: `paper/build/cachewise-original-2606.16824v1.pdf` (ignored build directory)

## Figures in the presentation

| Original figure | PDF page | Content | Talk slide |
| --- | --- | --- | --- |
| 2 | 4 | Prefill and decode CDFs, including CATraces and the ShareGPT chat baseline | 3 |
| 3 | 4 | Turn-count distributions across workloads | 4 |
| 6 | 4 | Context-length growth across turns | 4 |

The images are crops of the original vector PDF plots. Graph data, axes, and legends are unaltered.
Surrounding manuscript text and overall figure captions are excluded; presentation captions credit the paper and explain the observations.
These are **original-paper results**, separate from this project's adapted replication and host-restoration measurements.
The slides reproduce them under CC BY 4.0 with attribution.

`assets/original-cachewise-figures.json` records the source PDF hash, license, crop coordinates, and output hashes.
Cropped PDFs and their PNG previews are retained in `assets/`.
The presentation builder checks their hashes before use.

To reproduce the crops, with the presentation requirements and `mutool` installed:

```sh
mkdir -p paper/build
curl --fail --location https://arxiv.org/pdf/2606.16824v1 -o paper/build/cachewise-original-2606.16824v1.pdf
python presentation/extract_cachewise_figures.py
```

The extractor requires the verified PDF hash; a different PDF requires inspecting the version and crop locations again.
Normal deck builds use the tracked figure assets and do not download the paper.

## Algorithm explanation

The algorithm slide follows Sections 5.1–5.3 of the original paper:

- Schedule by the fewest additional KV blocks, using resident-prefix overlap.
- Group historical tool durations using tool names and TF–IDF/KMeans representations of arguments.
- For a still-running call with elapsed time `e`, estimate remaining duration as `E[D − e | D > e]` within the relevant duration distribution.
- Evict unreferenced KV whose predicted reuse is farthest away and refresh estimates as tool execution progresses.

The original paper needs the relative reuse order, rather than perfectly accurate completion times.
Our replication uses tool names only because argument contents are redacted; the slide and script state this adaptation.
No new model execution, replay, or experiment is used to make these presentation revisions.
