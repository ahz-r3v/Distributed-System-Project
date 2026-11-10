# Ten-minute presentation

The whole-study deck accompanies the six-page report and covers CacheWise replication, recovery costs, and host offloading with fetch-aware scheduling.

- [Editable PowerPoint](cachewise-10-minute-talk.pptx)
- [Presentation PDF](cachewise-10-minute-talk.pdf)
- [Speaker notes](cachewise-10-minute-speaker-notes.md), also embedded in the PowerPoint
- Full spoken script: [editable Markdown](cachewise-10-minute-script.md) · [printable PDF](cachewise-10-minute-script.pdf)

The deck has ten 16:9 slides, with 10:00 of planned speaking time.
The first five minutes cover the CacheWise paper and adapted replication (slides 1–5); the next five cover recovery costs, host methods, limitations and takeaways (slides 6–10).
The opening slide introduces the project and its central question.
Slide 2 explains the original paper’s motivation, prefix-aware scheduling, and predictive eviction before the replication results.
Timing guidance stays in the notes and script.
Questions follow the talk.
The full script has about 1,100 spoken words, plus slide cues and transitions, following the same timing plan.
Italic instructions are delivery cues, not spoken text.
Rehearse once to adjust the pacing to your speaking speed.

| Slide | Topic | Time |
| --- | --- | --- |
| 1 | Project introduction and central question | 0:00–0:20 |
| 2 | CacheWise paper: motivation and mechanisms | 0:20–1:35 |
| 3 | Adapted replication methodology | 1:35–2:40 |
| 4 | Main replication result | 2:40–4:00 |
| 5 | Scheduler interaction and tails | 4:00–5:00 |
| 6 | Host-cache architecture | 5:00–6:00 |
| 7 | Recovery cost and host results | 6:00–7:15 |
| 8 | Fetch-aware ordering | 7:15–8:35 |
| 9 | Scope and limitations | 8:35–9:20 |
| 10 | Takeaways | 9:20–10:00 |

The PowerPoint uses editable text and native shapes; charts are high-resolution images rendered from archived measurements.
The PDF and PowerPoint are generated from the same layout description. The PDF is not an Office export.
The PDF embeds DejaVu Sans; install that font when editing the PowerPoint to preserve the layout.
Names and course details can be added to the title slide when supplied.

## Rebuilding

On Linux with Python and DejaVu Sans installed:

```sh
python -m venv /tmp/cachewise-slides-venv
/tmp/cachewise-slides-venv/bin/python -m pip install -r presentation/requirements-presentation.txt
/tmp/cachewise-slides-venv/bin/python presentation/build_deck.py
/tmp/cachewise-slides-venv/bin/python presentation/export_script.py
```

The generator reads the frozen coverage JSON and rounded host-study snapshot.
It creates four chart images, PowerPoint, PDF, speaker notes, and `deck-provenance.json` with input/script/output checksums.
It checks the 60-run count, request count, retained preemption, host capacity, 600-second schedule, equal 300-second halves, and text/slide bounds.
It launches no experiment, model, replay, or correctness run.
`export_script.py` renders the hand-written Markdown script as a printable PDF; it does not change the deck or report.

The older [15-minute Part 1 outline](part1-15-minute-outline.md) remains as historical planning material; it is not used by this ten-minute whole-study deck.
