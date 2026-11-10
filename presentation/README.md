# Ten-minute presentation

The whole-study deck accompanies the six-page report and covers CacheWise replication, recovery costs, and host offloading with fetch-aware scheduling.

- [Editable PowerPoint](cachewise-10-minute-talk.pptx)
- [Presentation PDF](cachewise-10-minute-talk.pdf)
- [Speaker notes](cachewise-10-minute-speaker-notes.md), also embedded in the PowerPoint
- Full spoken script: [editable Markdown](cachewise-10-minute-script.md) · [printable PDF](cachewise-10-minute-script.pdf)

The deck has twelve 16:9 slides, with 10:00 of planned speaking time.
The first five minutes cover the CacheWise paper and adapted replication (slides 1–7); the next five cover recovery costs, host methods, limitations and takeaways (slides 8–12).
The opening slide introduces the project and its central question.
Slide 2 introduces the released coding-agent traces and explains why prefix reuse matters.
Slides 3–4 reproduce original-paper graphs showing prefill/decode lengths, turn counts, and context growth compared with chat workloads.
Slide 5 explains prefix-aware scheduling and tool-duration prediction, including argument clustering, elapsed-time conditioning, and eviction order.
It distinguishes the original argument-aware predictor from our tool-name-only replication.
The policy matrix highlights adapted CacheWise as prefix-aware scheduling plus predictive eviction, with the baseline and single-component ablations labeled.
Host-recovery results motivate offloading before the host-cache architecture is introduced.
Timing guidance stays in the notes and script.
Questions follow the talk.
The full script has about 1,150 spoken words, plus slide cues and transitions, following the same timing plan.
Italic instructions are delivery cues, not spoken text.
Rehearse once to adjust the pacing to your speaking speed.

| Slide | Topic | Time |
| --- | --- | --- |
| 1 | Project introduction | 0:00–0:15 |
| 2 | What CATraces records | 0:15–0:40 |
| 3 | Original prefill/decode distributions | 0:40–1:25 |
| 4 | Turns and context growth versus chat | 1:25–2:00 |
| 5 | Scheduling and tool-duration prediction algorithm | 2:00–3:05 |
| 6 | CacheWise, baseline, and component ablations | 3:05–3:50 |
| 7 | Main replication result | 3:50–5:00 |
| 8 | Motivation: recovery cost and host results | 5:00–6:15 |
| 9 | Host-cache architecture | 6:15–7:15 |
| 10 | Fetch-aware ordering | 7:15–8:35 |
| 11 | Scope and limitations | 8:35–9:20 |
| 12 | Takeaways | 9:20–10:00 |

The PowerPoint uses editable text and native shapes; charts are high-resolution images rendered from archived measurements.
The PDF and PowerPoint are generated from the same layout description. The PDF is not an Office export.
The PDF embeds DejaVu Sans; install that font when editing the PowerPoint to preserve the layout.
Names and course details can be added to the title slide when supplied.

## Original-paper figures

Figures 2, 3, and 6 are reproduced as attributed crops from the verified CacheWise v1 PDF.
They describe the original paper’s workloads and are separate from our replication plots.
See [source, license, extraction instructions and checksums](ORIGINAL_PAPER.md).
The original PDF is downloaded locally to `paper/build/cachewise-original-2606.16824v1.pdf` and is not committed.

## Rebuilding

On Linux with Python and DejaVu Sans installed:

```sh
python -m venv /tmp/cachewise-slides-venv
/tmp/cachewise-slides-venv/bin/python -m pip install -r presentation/requirements-presentation.txt
/tmp/cachewise-slides-venv/bin/python presentation/build_deck.py
/tmp/cachewise-slides-venv/bin/python presentation/export_script.py
```

The generator reads the frozen coverage JSON, rounded host-study snapshot, and verified original-figure assets.
It creates four chart images, PowerPoint, PDF, speaker notes, and `deck-provenance.json` with input/script/output checksums.
It checks the 60-run count, request count, retained preemption, host capacity, 600-second schedule, equal 300-second halves, and text/slide bounds.
It launches no experiment, model, replay, or correctness run.
`export_script.py` renders the hand-written Markdown script as a printable PDF; it does not change the deck or report.

The older [15-minute Part 1 outline](part1-15-minute-outline.md) remains as historical planning material; it is not used by this ten-minute whole-study deck.
