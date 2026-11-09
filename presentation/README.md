# Ten-minute presentation

The whole-study deck accompanies the six-page report and covers CacheWise replication, recovery costs, and host offloading with fetch-aware scheduling.

- [Editable PowerPoint](cachewise-10-minute-talk.pptx)
- [Presentation PDF](cachewise-10-minute-talk.pdf)
- [Speaker notes](cachewise-10-minute-speaker-notes.md), also embedded in the PowerPoint
- Full spoken script: [editable Markdown](cachewise-10-minute-script.md) · [printable PDF](cachewise-10-minute-script.pdf)

The deck has ten 16:9 slides, with 10:00 of planned speaking time. Questions follow the talk.
The full script has about 1,100 spoken words, plus slide cues and transitions, following the same timing plan.
Italic instructions are delivery cues, not spoken text.
Rehearse once to adjust the pacing to your speaking speed.

| Slide | Topic | Time |
| --- | --- | --- |
| 1 | Study overview | 0:00–0:30 |
| 2 | Prefix reuse and recovery | 0:30–1:25 |
| 3 | Replication methodology | 1:25–2:30 |
| 4 | Main replication result | 2:30–3:50 |
| 5 | Scheduler interaction and tails | 3:50–4:55 |
| 6 | Host-cache architecture | 4:55–5:55 |
| 7 | Recovery cost and host results | 5:55–7:10 |
| 8 | Fetch-aware ordering | 7:10–8:30 |
| 9 | Scope and limitations | 8:30–9:20 |
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
It checks the 60-run count, request count, retained preemption, host capacity, 600-second schedule, and text/slide bounds.
It launches no experiment, model, replay, or correctness run.
`export_script.py` renders the hand-written Markdown script as a printable PDF; it does not change the deck or report.

The older [15-minute Part 1 outline](part1-15-minute-outline.md) remains as historical planning material; it is not used by this ten-minute whole-study deck.
