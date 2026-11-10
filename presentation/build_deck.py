"""Build a ten-minute deck and matching PDF from archived evidence only.

Install requirements-presentation.txt, then run from any working directory.
Text, diagrams and tables are editable PowerPoint objects; plots use PNG assets.
The PDF and PPTX share a layout description (no office software required).
"""

import hashlib
import json
import math
import statistics
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE
from pptx.dml.color import RGBColor
from pptx.util import Pt
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ASSETS = HERE / 'assets'
W, H = 960, 540
SLIDE_COUNT, FIRST_HALF_SLIDES = 12, 7
INK, MUTED, BG = '#172b40', '#526477', '#f7f9fc'
BLUE, ORANGE, GREEN, PURPLE = '#536e89', '#cf7934', '#238269', '#8661a6'
FONT_ROOT = Path('/usr/share/fonts/truetype/dejavu')
for name, filename in [('Deck', 'DejaVuSans.ttf'), ('Deck-Bold', 'DejaVuSans-Bold.ttf')]:
    pdfmetrics.registerFont(TTFont(name, str(FONT_ROOT / filename)))
POLICIES = ['baseline', 'eviction_only', 'prefix_only_no_aging', 'cachewise_no_aging']
NAMES = ['FCFS / LRU', 'FCFS / predictive', 'Prefix / LRU', 'Prefix / predictive']
COLORS = [BLUE, ORANGE, GREEN, PURPLE]
SETTINGS = ['a-n10', 'a-n20', 'a-n30', 'b-n10', 'c-n10']
LABELS = ['A10', 'A20', 'A30', 'B10', 'C10']
COVERAGE_INPUT = ROOT / 'notes/experiment-evidence/part1-coverage-comparison.json'
HOST_INPUT = ROOT / 'notes/experiment-evidence/host-dram-reported-results.json'
ORIGINAL_FIGURE_MANIFEST = ASSETS / 'original-cachewise-figures.json'
ORIGINAL_FIGURES = {n: ASSETS / f'original-cachewise-figure{n}.png' for n in [2, 3, 6]}
coverage = json.loads(COVERAGE_INPUT.read_text())
host = json.loads(HOST_INPUT.read_text())
rows = coverage['runs']
assert len(rows) == 60 and sum(r['requests'] for r in rows) == 6384
assert sum(r['preemptions'] for r in rows) == 1
assert host['host_kv_tokens'] * host['kv_bytes_per_token'] == 36 * 1024**3

plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 15,
                     'axes.labelsize': 16, 'axes.titlesize': 17,
                     'xtick.labelsize': 14, 'ytick.labelsize': 14,
                     'text.color': INK, 'axes.labelcolor': INK,
                     'xtick.color': MUTED, 'ytick.color': MUTED,
                     'axes.edgecolor': '#bac5d1', 'savefig.facecolor': '#ffffff'})


def clean(ax, axis='y'):
    ax.spines[['top', 'right']].set_visible(False)
    ax.grid(axis=axis, alpha=.17)
    ax.set_axisbelow(True)


def saveplot(fig, name):
    path = ASSETS / (name + '.png')
    fig.savefig(path, dpi=180, bbox_inches='tight', facecolor='#ffffff')
    plt.close(fig)
    return path


def charts():
    fig, ax = plt.subplots(figsize=(8, 4.3), layout='constrained')
    for p, label, color, marker in zip(POLICIES, NAMES, COLORS, ['o', 's', '^', 'D']):
        groups = [[r['mean_session_serving_s'] for r in rows if r['setting'] == s and r['policy'] == p] for s in SETTINGS[:3]]
        means = np.array([statistics.mean(g) for g in groups])
        ax.errorbar([10, 20, 30], means, yerr=[means - np.array([min(g) for g in groups]), np.array([max(g) for g in groups]) - means],
                    color=color, marker=marker, lw=2.6, markersize=7, capsize=4, label=label)
    ax.set(xlabel='Initial concurrent segments, N', ylabel='Mean session serving time (s)',
           xticks=[10, 20, 30], ylim=(0, 2250))
    ax.legend(frameon=False, ncol=2, fontsize=12, loc='upper left')
    clean(ax)
    load = saveplot(fig, 'replication-load')

    fig, ax = plt.subplots(figsize=(8, 4.3), layout='constrained')
    index = {(r['setting'], r['repeat'], r['policy']): r for r in rows}
    for treatment, control, offset, color, label in [
        ('eviction_only', 'baseline', -.13, ORANGE, 'With FCFS'),
        ('cachewise_no_aging', 'prefix_only_no_aging', .13, PURPLE, 'With prefix-aware scheduling')]:
        for x, setting in enumerate(SETTINGS):
            values = [100 * (index[setting, repeat, treatment]['mean_session_serving_s'] /
                             index[setting, repeat, control]['mean_session_serving_s'] - 1) for repeat in range(3)]
            for dx, value in zip([-.035, 0, .035], values):
                ax.scatter(x + offset + dx, value, color=color, s=58, alpha=.9,
                           label=label if x == 0 and dx == -.035 else None)
    ax.axhline(0, color=INK, ls='--', lw=1)
    ax.set(xticks=range(5), xticklabels=['A\nN = 10', 'A\nN = 20', 'A\nN = 30', 'B\nN = 10', 'C\nN = 10'],
           xlabel='Workload group and concurrent segments',
           ylabel='Predictive vs. LRU: time change (%)', ylim=(-18, 55))
    ax.legend(frameon=False, fontsize=12, loc='upper left')
    clean(ax)
    effects = saveplot(fig, 'replication-interaction')

    fig, ax = plt.subplots(figsize=(8, 4.3), layout='constrained')
    for offset, recovery, color in [(-.19, 'Recompute', BLUE), (.19, 'Host restore', GREEN)]:
        values = [r['session_s'] for r in host['primary_observations'] if r['recovery'] == recovery]
        bars = ax.bar(np.arange(2) + offset, values, width=.36, color=color, label=recovery)
        ax.bar_label(bars, labels=[f'{v:g}' for v in values], padding=7, fontsize=17, color=INK)
    ax.set(xticks=[0, 1], xticklabels=['N = 28', 'N = 36'], ylim=(0, 1300), ylabel='Mean cumulative serving time\nper session (s)')
    ax.legend(frameon=False, fontsize=14, loc='upper left')
    clean(ax)
    recovery = saveplot(fig, 'host-recovery')

    fig, ax = plt.subplots(figsize=(8, 4.6), layout='constrained')
    names = ['Baseline\nFCFS + LRU', 'Scheduling only\nPrefix-aware + LRU',
             'Adapted CacheWise\nPrefix-aware + predictive', 'CacheWise + prefetch',
             'CacheWise + prefetch\n+ fetch-aware ordering']
    values = [r['session_s'] for r in host['n36_policy_observations']]
    colors = [BLUE, GREEN, '#aa96bd', '#c5b6d2', PURPLE]
    for y, (v, c) in enumerate(zip(values, colors)):
        ax.barh(y, v, height=.58, color=c)
        ax.text(6, y, f'{v:g} s', va='center', color='#ffffff', fontweight='bold', fontsize=16)
    ax.set(yticks=range(5), yticklabels=names, xlim=(0, 250), xlabel='Mean session serving time (s)')
    ax.tick_params(axis='y', labelsize=12)
    ax.invert_yaxis()
    clean(ax, 'x')
    ablation = saveplot(fig, 'host-ablation')
    return load, effects, recovery, ablation


def wrapped(text, width, size, bold=False):
    font = 'Deck-Bold' if bold else 'Deck'
    result = []
    for paragraph in text.split('\n'):
        words = paragraph.split()
        if not words:
            result.append('')
            continue
        line = words.pop(0)
        for word in words:
            if pdfmetrics.stringWidth(line + ' ' + word, font, size) <= width:
                line += ' ' + word
            else:
                result.append(line)
                line = word
        result.append(line)
    return result


class Slide:
    def __init__(self, title, section, seconds, notes, source=''):
        self.items = []
        self.title, self.section, self.seconds, self.notes, self.source = title, section, seconds, notes, source or 'Six-page report, abstract and §1'

    def box(self, x, y, w, h, fill='#ffffff', stroke=None, radius=0):
        self.items.append(dict(kind='box', x=x, y=y, w=w, h=h, fill=fill, stroke=stroke, radius=radius))

    def text(self, x, y, w, text, size=20, color=INK, bold=False, leading=1.23):
        lines = wrapped(text, w, size, bold)
        self.items.append(dict(kind='text', x=x, y=y, w=w, h=len(lines)*size*leading+3,
                               lines=lines, size=size, color=color, bold=bold, leading=leading))

    def line(self, x, y, x2, y2, color=MUTED, width=2, arrow=False):
        self.items.append(dict(kind='line', x=x, y=y, x2=x2, y2=y2, color=color, width=width, arrow=arrow))

    def picture(self, x, y, w, h, path):
        im = Image.open(path)
        scale = min(w / im.width, h / im.height)
        iw, ih = im.width * scale, im.height * scale
        self.items.append(dict(kind='image', x=x+(w-iw)/2, y=y+(h-ih)/2, w=iw, h=ih, path=path))

    def frame(self, index):
        self.box(0, 0, W, H, BG)
        self.box(0, 0, 10, H, BLUE if index <= FIRST_HALF_SLIDES else GREEN if index < SLIDE_COUNT else PURPLE)
        self.text(36, 20, 880, self.section.upper(), size=11, bold=True, color=MUTED)
        self.text(36, 47, 880, self.title, size=30, bold=True)
        self.line(36, 500, 924, 500, '#d9e0e8', 1)
        self.text(36, 513, 700, self.source or 'CacheWise Replication and Fetch-Aware KV Cache Recovery', size=9.5, color=MUTED)
        self.text(882, 510, 42, f'{index:02d}/{SLIDE_COUNT}', size=11, color=MUTED)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rgb(value):
    return RGBColor.from_string(value.lstrip('#'))


def write_outputs(slides):
    prs = Presentation()
    prs.slide_width, prs.slide_height = Pt(W), Pt(H)
    prs.core_properties.title = 'CacheWise Replication and Fetch-Aware KV Cache Recovery'
    prs.core_properties.subject = 'Ten-minute presentation of the six-page report'
    prs.core_properties.author = ''
    prs.core_properties.keywords = 'KV cache, replication, host DRAM, fetch-aware scheduling'
    pdf_path = HERE / 'cachewise-10-minute-talk.pdf'
    pdf = canvas.Canvas(str(pdf_path), pagesize=(W, H), pageCompression=1)
    pdf.setTitle(prs.core_properties.title)
    pdf.setAuthor('')
    notes = ['# Ten-minute presentation speaker notes', '',
             f'{SLIDE_COUNT} slides · 10:00 planned speaking time · questions after the talk.', '',
             '0:00–5:00: CacheWise paper and adapted replication (slides 1–7).',
             '5:00–10:00: recovery costs, host methods, limitations and takeaways (slides 8–12).', '',
             'The PowerPoint and PDF use the same layout. The PowerPoint includes these notes.',
             'Timings are rehearsal targets, not a recording. No experiments were run to create this deck.', '']
    elapsed = 0
    for i, slide in enumerate(slides, 1):
        page = prs.slides.add_slide(prs.slide_layouts[6])
        # Frame items were inserted first, so content draws above them.
        for item in slide.items:
            kind = item['kind']
            if kind in ('box', 'text', 'image'):
                assert item['x'] >= 0 and item['y'] >= 0
                assert item['x'] + item['w'] <= W + .1, (i, item)
                assert item['y'] + item['h'] <= H + .1, (i, item)
            if kind == 'box':
                shape = page.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if item['radius'] else MSO_SHAPE.RECTANGLE,
                                              Pt(item['x']), Pt(item['y']), Pt(item['w']), Pt(item['h']))
                shape.fill.solid(); shape.fill.fore_color.rgb = rgb(item['fill'])
                if item['stroke']:
                    shape.line.color.rgb = rgb(item['stroke']); shape.line.width = Pt(1)
                else:
                    shape.line.fill.background()
                if item['radius']:
                    shape.adjustments[0] = .08
                pdf.setFillColor(HexColor(item['fill']))
                pdf.setStrokeColor(HexColor(item['stroke'] or item['fill']))
                pdf.roundRect(item['x'], H-item['y']-item['h'], item['w'], item['h'], item['radius'], stroke=bool(item['stroke']), fill=1)
            elif kind == 'text':
                shape = page.shapes.add_textbox(Pt(item['x']), Pt(item['y']), Pt(item['w']), Pt(item['h']))
                tf = shape.text_frame
                tf.clear(); tf.word_wrap = False; tf.auto_size = MSO_AUTO_SIZE.NONE
                tf.margin_top = tf.margin_bottom = tf.margin_left = tf.margin_right = 0
                tf.vertical_anchor = MSO_ANCHOR.TOP
                for j, line in enumerate(item['lines']):
                    p = tf.paragraphs[0] if j == 0 else tf.add_paragraph()
                    p.text = line
                    p.font.name = 'DejaVu Sans'; p.font.size = Pt(item['size'])
                    p.font.bold = item['bold']; p.font.color.rgb = rgb(item['color'])
                    p.space_before = p.space_after = Pt(0)
                    p.line_spacing = Pt(item['size'] * item['leading'])
                    font = 'Deck-Bold' if item['bold'] else 'Deck'
                    assert pdfmetrics.stringWidth(line, font, item['size']) <= item['w'] + .1, (i, line)
                    pdf.setFillColor(HexColor(item['color'])); pdf.setFont(font, item['size'])
                    pdf.drawString(item['x'], H-item['y']-item['size']*.96-j*item['size']*item['leading'], line)
            elif kind == 'image':
                page.shapes.add_picture(str(item['path']), Pt(item['x']), Pt(item['y']), width=Pt(item['w']), height=Pt(item['h']))
                pdf.drawImage(str(item['path']), item['x'], H-item['y']-item['h'], item['w'], item['h'])
            elif kind == 'line':
                shape = page.shapes.add_connector(1, Pt(item['x']), Pt(item['y']), Pt(item['x2']), Pt(item['y2']))
                shape.line.color.rgb = rgb(item['color']); shape.line.width = Pt(item['width'])
                pdf.setStrokeColor(HexColor(item['color'])); pdf.setLineWidth(item['width'])
                pdf.line(item['x'], H-item['y'], item['x2'], H-item['y2'])
                if item['arrow']:
                    theta = math.atan2(item['y2'] - item['y'], item['x2'] - item['x'])
                    points = [(item['x2'], item['y2'])] + [(item['x2'] - 9*math.cos(theta+a), item['y2']-9*math.sin(theta+a)) for a in [-.5, .5]]
                    builder = page.shapes.build_freeform(Pt(points[0][0]), Pt(points[0][1]))
                    builder.add_line_segments([(Pt(x), Pt(y)) for x, y in points[1:]], close=True)
                    triangle = builder.convert_to_shape()
                    triangle.fill.solid(); triangle.fill.fore_color.rgb = rgb(item['color']); triangle.line.fill.background()
                    pdf.setFillColor(HexColor(item['color']))
                    path = pdf.beginPath(); path.moveTo(points[0][0], H-points[0][1])
                    for x, y in points[1:]: path.lineTo(x, H-y)
                    path.close(); pdf.drawPath(path, stroke=0, fill=1)
        start, end = elapsed, elapsed + slide.seconds
        timestamp = lambda n: f'{n//60}:{n%60:02d}'
        source_label = slide.source.removeprefix('Evidence: ')
        note_title = slide.title.replace('\n', ' ')
        text = f'Slide {i}: {note_title}\nTime: {timestamp(start)}–{timestamp(end)} ({slide.seconds} seconds)\n\n{slide.notes}\n\nEvidence: {source_label}'
        page.notes_slide.notes_text_frame.text = text
        notes += [f'## {i}. {note_title}', '', f'**{timestamp(start)}–{timestamp(end)} · {slide.seconds} seconds**', '', slide.notes, '', f'Evidence: {source_label}', '']
        elapsed = end
        pdf.showPage()
    assert elapsed == 600 and len(slides) == SLIDE_COUNT
    assert sum(slide.seconds for slide in slides[:FIRST_HALF_SLIDES]) == 300
    assert sum(slide.seconds for slide in slides[FIRST_HALF_SLIDES:]) == 300
    prs.save(HERE / 'cachewise-10-minute-talk.pptx')
    pdf.save()
    (HERE / 'cachewise-10-minute-speaker-notes.md').write_text('\n'.join(notes))
    outputs = [HERE / ('cachewise-10-minute-talk.' + ext) for ext in ['pptx', 'pdf']]
    outputs += [HERE / 'cachewise-10-minute-speaker-notes.md'] + [
        ASSETS / f'{name}.png' for name in ['replication-load', 'replication-interaction', 'host-recovery', 'host-ablation']]
    provenance = {
        'scope': 'Twelve slides, 600 seconds of planned speaking time. Existing evidence only; no model execution or experiment.',
        'time_allocation_seconds': {'cachewise_paper_and_replication_slides_1_to_7': 300,
                                    'recovery_methods_and_wrapup_slides_8_to_12': 300},
        'rendering': 'PDF and editable PPTX generated independently from the same validated layout; PDF is not an Office export. DejaVu Sans is used in both.',
        'inputs': {str(p.relative_to(ROOT)): sha(p) for p in [COVERAGE_INPUT, HOST_INPUT, ORIGINAL_FIGURE_MANIFEST, *ORIGINAL_FIGURES.values()]},
        'script_sha256': sha(Path(__file__)),
        'outputs': {str(p.relative_to(ROOT)): sha(p) for p in outputs},
        'matplotlib_version': matplotlib.__version__,
    }
    (HERE / 'deck-provenance.json').write_text(json.dumps(provenance, indent=2)+'\n')
    print(f'Built {len(slides)} slides, editable PowerPoint, PDF, and {elapsed}-second speaker notes from archived evidence.')


def make_slides():
    original = json.loads(ORIGINAL_FIGURE_MANIFEST.read_text())
    assert original['version'] == 'arXiv:2606.16824v1' and original['license'] == 'CC BY 4.0'
    for figure in original['figures']:
        for path, expected in figure['files'].items():
            assert sha(ROOT / path) == expected, path
    load, effects, recovery, ablation = charts()
    slides = []

    def new(title, section, seconds, notes, source=''):
        s = Slide(title, section, seconds, notes, source)
        s.frame(len(slides) + 1)
        slides.append(s)
        return s

    s = new('CacheWise replication\nand KV cache recovery', 'Introduction', 15,
        'This project studies KV reuse for coding agents under limited GPU memory. We first examine CacheWise and its replication, then motivate and describe host-cache recovery.')
    s.text(36, 161, 870, 'Replicating CacheWise and evaluating host-DRAM recovery', size=22, color=MUTED)
    s.box(36, 270, 888, 144, '#ffffff', radius=9)
    s.text(56, 286, 848, 'CENTRAL QUESTION', size=13, color=BLUE, bold=True)
    s.text(56, 322, 848, 'How can coding agents reuse previous computation\nwhen GPU memory is limited?', size=27, bold=True)

    s = new('What do the CacheWise traces contain?', 'Part 1 · Coding-agent traces', 25,
        'CATraces records real Claude Code sessions: model requests, tool calls, timings, and token usage. The released content is redacted, so our replay preserves lengths and prefix growth with synthetic tokens. The next two slides use the original paper’s graphs to show why this workload needs special cache management.',
        'CacheWise v1 §§3–5; released-trace replay: report §3.1')
    for x, title, body, detail in [
        (36, 'CATraces: real coding sessions',
         'Claude Code interaction logs\nModel requests + tool calls\nTiming + prompt / output lengths',
         'Released content is redacted; replay\npreserves lengths and prefix growth.'),
        (489, 'Reuse across turns',
         'Growing, shared prompt prefixes\nLong inputs with short outputs\nTool waits between requests',
         'Requests arrive in sessions,\nwith repeated opportunities for reuse.')]:
        s.box(x, 137, 435 if x == 489 else 430, 198, '#ffffff', radius=8)
        s.text(x+18, 153, 394, title, size=21, bold=True)
        s.text(x+18, 196, 394, body, size=17.5)
        s.text(x+18, 282, 394, detail, size=14.5, color=MUTED)
    s.box(36, 361, 888, 116, '#e9eef5', radius=8)
    s.text(54, 375, 852, 'Why prefix-aware scheduling can help', size=22, bold=True, color=GREEN)
    s.text(54, 418, 852, 'Reuse a resident prefix → less new prefill → fewer additional KV blocks.\nA smaller active working set can reduce eviction pressure.', size=18)

    s = new('CATraces: long inputs, short outputs', 'Part 1 · Original paper: workload shape', 45,
        'These are the original paper’s published prefill and decode distributions. A CDF shows the fraction of requests at or below a token length. Compare CATraces in red with the ShareGPT chat baseline in orange. The prefill curve is much farther right: agent prompts are much longer. The decode curve is farther left: outputs tend to be shorter. Reprocessing a large shared prefix can therefore be expensive even when little new text is generated. These are original-paper results, separate from our replay measurements.',
        'Cropped from Tiwari et al., CacheWise v1, Fig. 2 (PDF p. 4); CC BY 4.0')
    s.box(36, 124, 888, 323, '#ffffff', radius=8)
    s.picture(43, 126, 874, 317, ORIGINAL_FIGURES[2])
    s.text(36, 451, 888, 'CATraces (red) vs. ShareGPT chat (orange): longer prefill, shorter decode.', size=17, bold=True)
    s.text(36, 478, 888, 'CDF = fraction of requests at or below the token length. Published results, not our replay.', size=12.5, color=MUTED)

    s = new('CATraces differ from traditional chat', 'Part 1 · Original paper: sessions and context', 35,
        'ShareGPT is the chat baseline here. CATraces has many more turns in the left plot. On the right, follow blue CATraces versus purple ShareGPT: agent contexts grow much larger. One user task drives repeated model and tool calls, so KV must survive between requests and session completion matters alongside individual response latency.',
        'Cropped from Tiwari et al., CacheWise v1, Figs. 3 and 6 (PDF p. 4); CC BY 4.0')
    for x, title, number in [(36, 'More turns per session (Fig. 3)', 3), (489, 'Growing context across turns (Fig. 6)', 6)]:
        s.text(x, 133, 435, title, size=18, bold=True)
        s.box(x, 177, 435, 224, '#ffffff', radius=8)
        s.picture(x+8, 182, 419, 214, ORIGINAL_FIGURES[number])
    s.box(36, 420, 888, 63, '#e9eef5', radius=8)
    s.text(53, 431, 854, 'One task drives many model/tool turns; growing KV prefixes compete for memory.\nSession completion matters alongside individual request latency.', size=17)

    s = new('CacheWise predicts when a session returns', 'Part 1 · Scheduling and tool-duration prediction', 65,
        'The scheduler serves the request with the fewest additional KV blocks: required state minus resident state. For eviction, CacheWise predicts tool-call duration from historical calls. The original paper embeds arguments with TF–IDF and clusters similar calls with KMeans, giving a duration distribution for each group. For a tool still running after elapsed time e, estimate the remaining time as E of D minus e, conditioned on D being greater than e. This accounts for the time already spent waiting. Evict unreferenced KV whose predicted reuse is farthest away, and refresh estimates as time passes. Our replication uses tool names only because arguments are redacted.',
        'Algorithm adapted from CacheWise v1 §§5.1–5.3; original-paper argument-aware predictor')
    s.box(36, 137, 300, 288, '#ffffff', stroke=GREEN, radius=8)
    s.text(54, 155, 264, 'Schedule requests', size=22, color=GREEN, bold=True)
    s.text(54, 205, 264, 'Additional KV blocks\n= required − resident', size=21, bold=True)
    s.text(54, 280, 264, 'Serve the smallest\nadditional-block cost first.', size=18)
    s.text(54, 357, 264, 'Uses current GPU\nprefix overlap.', size=16, color=MUTED)
    s.box(355, 137, 569, 288, '#ffffff', stroke=PURPLE, radius=8)
    s.text(373, 155, 533, 'Predict duration → order evictions', size=21, color=PURPLE, bold=True)
    s.box(373, 198, 165, 62, '#e9eef5', radius=5)
    s.text(386, 207, 139, 'Tool name +\narguments', size=16, bold=True)
    s.line(541, 228, 560, 228, color=PURPLE, arrow=True)
    s.box(566, 198, 340, 62, '#eee8f5', radius=5)
    s.text(581, 207, 310, 'TF–IDF → trained KMeans\nHistorical duration samples', size=16, bold=True)
    s.text(373, 280, 533, 'Condition on the tool still running:', size=17, bold=True)
    s.text(373, 316, 533, 'r = E[D − e | D > e]', size=25, color=PURPLE, bold=True)
    s.text(373, 365, 533, 'Evict unreferenced KV with largest r;\nrefresh predictions as time passes.', size=17)
    s.box(36, 444, 888, 39, '#e9eef5', radius=6)
    s.text(51, 455, 858, 'D = total duration; e = elapsed time. Replication: tool names only (arguments redacted).', size=14)

    s = new('CacheWise combines scheduling and eviction', 'Part 1 · Replication methodology', 50,
        'Rows identify the scheduler and columns identify the eviction policy. The bottom-right cell is adapted CacheWise, combining prefix-aware scheduling with predictive eviction. The top-left cell is the FCFS/LRU baseline; the remaining cells isolate scheduling or eviction. The testbed panel gives the model, GPU, precision, KV pool, and prefill configuration. N segments start as a group, and each continues through its recorded turns; N does not mean a constant number of in-flight requests. Five settings, four policies, and three repeats give sixty runs and 6,384 request executions. The metric excludes external tool waits.',
        'Evidence: four-policy replication; report Tables 1–3 and §3')
    s.text(36, 131, 123, 'Scheduler\n(rows)', size=15.5, bold=True)
    s.text(169, 131, 394, 'Eviction policy (columns)', size=17, bold=True)
    s.text(171, 173, 175, 'LRU', size=18, color=MUTED, bold=True)
    s.text(370, 173, 220, 'Predictive', size=18, color=MUTED, bold=True)
    for y, scheduler, p1, p2 in [
        (211, 'FCFS', 'Baseline\nFCFS + LRU', 'Eviction only\nFCFS + predictive'),
        (304, 'Prefix-aware', 'Scheduling only\nPrefix + LRU', 'CacheWise (both)\nPrefix + predictive')]:
        s.text(36, y+21, 123, scheduler, size=15, bold=True)
        for x, label, color in [(169, p1, BLUE if y == 211 else GREEN), (372, p2, ORANGE if y == 211 else PURPLE)]:
            s.box(x, y, 191, 72, '#eee8f5' if x == 372 and y == 304 else '#ffffff', stroke=color, radius=7)
            s.text(x+13, y+14, 165, label, size=15.5, color=color, bold=True)
    s.text(169, 391, 430, 'Bottom-right: adapted CacheWise uses both components.', size=12.5, color=MUTED)
    s.box(615, 135, 309, 277, '#ffffff', radius=8)
    s.text(635, 152, 269, 'Testbed', size=22, bold=True)
    s.text(635, 194, 269, 'Qwen2.5-Coder-14B-Instruct', size=14.5, bold=True)
    s.text(635, 224, 269, '1 × RTX PRO 6000 Blackwell\nMax-Q GPU', size=14.5)
    s.text(635, 275, 269, 'BF16 · tensor parallelism 1', size=14)
    s.text(635, 308, 269, 'KV: 287,696 tokens (17,981 × 16)', size=13.5)
    s.text(635, 338, 269, 'Prefill chunk: 512 tokens', size=14)
    s.text(635, 369, 269, 'Max sequence length: 131,072', size=12.5)
    s.text(635, 390, 269, 'Max scheduled sequences: 32', size=12.5)
    s.box(36, 424, 888, 61, '#e9eef5', radius=7)
    s.text(52, 434, 856, 'Coverage: 5 settings × 4 policies × 3 repeats = 60 runs · 6,384 requests', size=16, bold=True)
    s.text(52, 464, 856, 'Metric: mean summed model-request latency per session, excluding tool waits.', size=14.5)

    s = new('Prefix / LRU has the lowest mean', 'Part 1 · Main result', 65,
        'The green prefix/LRU line is the scheduling-only ablation and has the lowest mean at all three tested loads. Adapted CacheWise is the purple prefix/predictive line. Scheduling-only reduces time versus FCFS/LRU by about 58, 62, and 65 percent as N rises. Scheduling-only also has the lowest mean in two additional held-out workloads, making five settings out of five. Ranges show observed minima and maxima from three repeats, not confidence intervals. The load sweep adds segments, so concurrency and composition both change. These are our adapted replay results, separate from the preceding published workload graphs.',
        'Evidence: frozen 60-run coverage study; report Table 3 and Figure 1a')
    s.box(36, 137, 625, 328, '#ffffff', radius=8)
    s.picture(44, 143, 609, 315, load)
    s.box(686, 145, 238, 303, '#ffffff', radius=8)
    s.text(704, 167, 202, '5 / 5', size=44, bold=True, color=GREEN)
    s.text(704, 228, 202, 'settings favor\nprefix / LRU', size=21, bold=True)
    s.text(704, 307, 202, '58–65% lower\nmean vs. FCFS / LRU\nin the load sweep', size=18)
    s.text(44, 471, 880, 'Three repeats per cell. Ranges are observed minima/maxima; lower is better.', size=13.5, color=MUTED)

    s = new('Host restoration reduces session time', 'Part 2 · Motivation for KV offloading', 75,
        'After the CacheWise replication, we turn to recovery after eviction. Scheduling can limit churn, but useful state may still leave the GPU. Saving it in host memory allows restoration instead of repeating prefill. A simple cost test is whether saving, restoring, and managing the copy costs less than recomputation. Each bar is the mean across sessions of summed request latency, including queueing, prefill, and decoding, but excluding tool waits. Here we keep LRU and FCFS fixed and compare recomputation with on-demand host restoration. At twenty-eight concurrent episodes, reported mean session time falls from 821 to 90.7 seconds, a baseline-to-restoration ratio of about 9.1. At thirty-six it falls from 1,060 to 222 seconds, about 4.8. The reported prior-prefix deficit also drops sharply, supporting the interpretation that more reusable state survives. Two qualifications matter. First, restoration adds thirty-six GiB of host KV capacity to the common twenty-four-GiB GPU pool, so this is not an equal-total-memory algorithm comparison. Second, each bar is one reported run. This study also uses a different engine, smaller GPU pool, larger prefill chunks, and transformed replay inputs. We therefore keep it separate from the vLLM replication. The result demonstrates a favorable host-DRAM operating regime, not a measured SSD break-even curve.',
        'Evidence: host-dram-reported-results.json; report Figure 3a and §6')
    s.text(36, 104, 888, 'Recovery tradeoff: save + restore + management < recomputation', size=17, color=MUTED)
    s.box(36, 137, 625, 328, '#ffffff', radius=8)
    s.picture(44, 143, 609, 315, recovery)
    s.box(686, 145, 238, 306, '#ffffff', radius=8)
    s.text(704, 164, 202, '9.1× / 4.8×', size=30, color=GREEN, bold=True)
    s.text(704, 216, 202, 'reported time ratios\nat N = 28 / 36', size=18)
    s.text(704, 289, 202, '+36 GiB host KV\n24 GiB GPU KV fixed', size=18, bold=True)
    s.text(704, 366, 202, 'One observation\nper bar', size=18, color=MUTED)
    s.text(44, 471, 880, 'Separate Mini-SGLang study. Added-capacity comparison; lower is better.', size=13.5, color=MUTED)

    s = new('Preserve evicted KV in host DRAM', 'Part 3 · Host-cache design', 60,
        'These recovery observations motivate offloading. Here is how the Mini-SGLang host cache implements the save-and-restore path. One radix index records which prefix pages reside on the GPU and which have host copies. When memory is needed, dirty GPU pages are copied to pinned host DRAM. Clean inclusive copies can remain there, so a later GPU eviction does not require another save. When a request returns, a compatible host suffix is restored before prefill; if no copy survives, the engine recomputes. The implementation uses sixteen-token pages, locks and events to protect transfers, and predictive prefetch with a bounded per-step budget. In the recovery study the GPU pool holds twenty-four GiB of KV payload and the host tier adds thirty-six GiB. These are nominal cache payloads, excluding weights and other memory. No SSD path is implemented.',
        'Implementation: Mini-SGLangs 3f9aee7; report Figure 2 and §5')
    s.box(180, 132, 600, 67, '#ffffff', stroke='#bac5d1', radius=8)
    s.text(202, 143, 556, 'Request queue + radix prefix index', size=24, bold=True)
    s.text(202, 176, 556, 'Track GPU / host residency; select the next request', size=15, color=MUTED)
    s.line(260, 201, 260, 242, arrow=True)
    s.line(700, 201, 700, 242, arrow=True)
    for x, title, body, color, fill in [(75, 'GPU KV cache', '24 GiB · 16-token pages', BLUE, '#e5edf5'), (555, 'Pinned host KV cache', '36 GiB · inclusive clean copies', GREEN, '#e3efe8')]:
        s.box(x, 249, 330, 108, fill, radius=8)
        s.text(x+18, 268, 294, title, size=24, bold=True, color=color)
        s.text(x+18, 311, 294, body, size=16)
    s.text(420, 253, 126, 'Save dirty KV', size=13, color=BLUE)
    s.line(410, 286, 548, 286, color=BLUE, arrow=True)
    s.text(420, 302, 126, 'Restore / fetch', size=13, color=GREEN)
    s.line(548, 333, 410, 333, color=GREEN, arrow=True)
    for x, title, body in [(36, 'On demand', 'Restore before prefill.'), (338, 'Prefetch', 'Overlap predicted reuse.'), (640, 'Fallback', 'Recompute on a miss.')]:
        s.box(x, 394, 284, 83, '#ffffff', radius=6)
        s.text(x+16, 406, 252, title, size=20, bold=True)
        s.text(x+16, 443, 252, body, size=15.5, color=MUTED)

    s = new('Fetch-aware ordering discounts host hits', 'Part 3 · Scheduling extension', 80,
        'Every bar uses the same GPU and host cache capacities and can restore KV on demand. Read each full configuration on the left. The baseline uses FCFS and LRU. The scheduling-only row replaces FCFS with prefix-aware ordering: requests with more reusable GPU KV need less new prefill and go first. Adapted CacheWise also adds predictive eviction. CacheWise with prefetch keeps both components and restores host KV before the predicted session return, rather than waiting for its next request. The final row keeps prefetch and adds fetch-aware ordering: it recognizes host-resident prefixes as cheaper than full recomputation. Its priority is new prefill tokens plus 0.05 times additional host tokens, a heuristic with lower cost served first. The first reported session times are 222, 159, 158, 172, and 136 seconds. Prefetch alone does not improve this observation. The final combination is promising, but sparse repetitions do not isolate each component or establish statistical significance.',
        'Evidence: Mini-SGLangs 3f9aee7; report Figure 3b and Eq. (3)')
    s.text(36, 104, 888, 'Fetch-aware priority = new prefill tokens + 0.05 × additional host tokens', size=16, color=MUTED)
    s.box(36, 136, 625, 332, '#ffffff', radius=8)
    s.picture(44, 140, 609, 324, ablation)
    s.box(686, 145, 238, 306, '#ffffff', radius=8)
    s.text(704, 158, 202, 'What changes?', size=21, bold=True)
    s.text(704, 201, 202, 'Prefix-aware', size=17, color=GREEN, bold=True)
    s.text(704, 229, 202, 'Order by GPU reuse;\nless new prefill first.', size=14.5)
    s.text(704, 285, 202, 'Prefetch', size=17, color=PURPLE, bold=True)
    s.text(704, 313, 202, 'Restore host KV\nbefore session return.', size=14.5)
    s.text(704, 369, 202, 'Fetch-aware', size=17, color=PURPLE, bold=True)
    s.text(704, 397, 202, 'Also discount host hits\nwhen ordering requests.', size=14.5)
    s.text(44, 475, 880, 'N = 36, host restoration in every row. First reported runs; sparse repetitions.', size=13, color=MUTED)

    s = new('Keep the conclusions within the evidence', 'Scope and limitations', 45,
        'There are three boundaries to keep in mind. The replication uses synthetic content and runtime-bounded selected segments; increasing the load also changes the workload. One real preemption violated the original zero-preemption rule. It remains in the results under a disclosed post hoc audit amendment, and its extra computation is unmeasured. The host study is a separate replay with added backing capacity and mostly single-run observations. We reproduce its rounded reported values rather than claim an independent request-level audit. Finally, the implemented recovery tier is pinned host DRAM. SSD support would need complete storage writes and reads, bounded staging, compatibility metadata, and failure handling. We cannot infer an SSD speedup from these DRAM results.',
        'Limitations: report §§3.2, 6.1 and 7')
    for x, color, title, body in [
        (36, BLUE, 'Replication', 'Synthetic replay and selected segments.\n\nOne retained preemption; extra prefill work unmeasured.'),
        (338, GREEN, 'Host results', 'Separate engine and replay.\n\nAdded host capacity; most configurations run once.'),
        (640, PURPLE, 'SSD extension', 'Not implemented or measured.\n\nNeeds full I/O, staging, metadata and recovery.')]:
        s.box(x, 150, 284, 280, '#ffffff', radius=8)
        s.box(x, 150, 284, 6, color)
        s.text(x+20, 178, 244, title, size=23, bold=True, color=color)
        s.text(x+20, 235, 244, body, size=18)
    s.text(36, 455, 888, 'Interpret both studies separately; retain the declared protocol deviation.', size=18, bold=True)

    s = new('Three takeaways', 'Conclusion · Questions', 40,
        'The first takeaway is that scheduling dominates the mean improvement in our adapted replication: prefix-aware LRU wins all five settings, while predictive eviction changes direction with the scheduler. The second is that retaining KV in host memory can avoid substantial recovery work for long prefixes, with large reported improvements when host capacity is added. The third is that host residency should inform request ordering. Fetch-aware scheduling is promising here, but the policy evidence is much smaller than the replication study. The completed scope is replication and host-DRAM recovery. SSD performance remains future work. Thank you; I am happy to take questions.',
        'Full results and qualifications: six-page report; archived evidence in repository')
    for y, n, title, body, color in [
        (139, '01', 'Scheduling and eviction interact.', 'Prefix / LRU has the lowest mean in all five replication settings.', BLUE),
        (252, '02', 'Host copies can avoid costly recovery.', 'Large reported gains include the added 36 GiB backing tier.', GREEN),
        (365, '03', 'Order requests by recovery cost.', 'Fetch-aware results are promising; SSD evaluation remains future work.', PURPLE)]:
        s.box(36, y, 888, 95, '#ffffff', radius=8)
        s.text(54, y+19, 60, n, size=28, bold=True, color=color)
        s.text(125, y+15, 775, title, size=24, bold=True)
        s.text(125, y+57, 775, body, size=16, color=MUTED)
    return slides


if __name__ == '__main__':
    ASSETS.mkdir(exist_ok=True)
    write_outputs(make_slides())
