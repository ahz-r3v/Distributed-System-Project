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
    ax.set(xlabel='Concurrent segments, N (nested cohort A)', ylabel='Mean session serving time (s)',
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
    ax.set(xticks=range(5), xticklabels=LABELS, ylabel='Predictive vs. LRU: time change (%)', ylim=(-18, 55))
    ax.legend(frameon=False, fontsize=12, loc='upper left')
    clean(ax)
    effects = saveplot(fig, 'replication-interaction')

    fig, ax = plt.subplots(figsize=(8, 4.3), layout='constrained')
    for offset, recovery, color in [(-.19, 'Recompute', BLUE), (.19, 'Host restore', GREEN)]:
        values = [r['session_s'] for r in host['primary_observations'] if r['recovery'] == recovery]
        bars = ax.bar(np.arange(2) + offset, values, width=.36, color=color, label=recovery)
        ax.bar_label(bars, labels=[f'{v:g}' for v in values], padding=7, fontsize=17, color=INK)
    ax.set(xticks=[0, 1], xticklabels=['N = 28', 'N = 36'], ylim=(0, 1300), ylabel='Mean session serving time (s)')
    ax.legend(frameon=False, fontsize=14, loc='upper left')
    clean(ax)
    recovery = saveplot(fig, 'host-recovery')

    fig, ax = plt.subplots(figsize=(8, 4.6), layout='constrained')
    names = ['LRU + FCFS', 'LRU + prefix', 'Predictive + prefix', '+ prefetch', '+ fetch-aware']
    values = [r['session_s'] for r in host['n36_policy_observations']]
    colors = [BLUE, GREEN, '#aa96bd', '#c5b6d2', PURPLE]
    for y, (v, c) in enumerate(zip(values, colors)):
        ax.barh(y, v, height=.58, color=c)
        ax.text(6, y, f'{v:g} s', va='center', color='#ffffff', fontweight='bold', fontsize=16)
    ax.scatter([175, 135], [2, 4], marker='D', s=80, facecolors='#ffffff', edgecolors=INK, linewidth=1.4, zorder=4, label='Additional observation')
    ax.set(yticks=range(5), yticklabels=names, xlim=(0, 250), xlabel='Mean session serving time (s)')
    ax.invert_yaxis()
    ax.legend(frameon=False, fontsize=12, loc='lower right', bbox_to_anchor=(1, -.31))
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
        self.title, self.section, self.seconds, self.notes, self.source = title, section, seconds, notes, source

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
        self.box(0, 0, 10, H, [BLUE, GREEN, PURPLE][min(2, (index-1)//4)])
        self.text(36, 20, 880, self.section.upper(), size=11, bold=True, color=MUTED)
        self.text(36, 47, 880, self.title, size=30, bold=True)
        self.line(36, 500, 924, 500, '#d9e0e8', 1)
        self.text(36, 513, 700, self.source or 'CacheWise Replication and Fetch-Aware KV Cache Recovery', size=9.5, color=MUTED)
        self.text(882, 510, 42, f'{index:02d}/10', size=11, color=MUTED)


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
             '10 slides · 10:00 planned speaking time · questions after the talk.', '',
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
        text = f'Slide {i}: {slide.title}\nTime: {timestamp(start)}–{timestamp(end)} ({slide.seconds} seconds)\n\n{slide.notes}\n\nEvidence: {slide.source}'
        page.notes_slide.notes_text_frame.text = text
        notes += [f'## {i}. {slide.title}', '', f'**{timestamp(start)}–{timestamp(end)} · {slide.seconds} seconds**', '', slide.notes, '', f'Evidence: {slide.source}', '']
        elapsed = end
        pdf.showPage()
    assert elapsed == 600 and len(slides) == 10
    prs.save(HERE / 'cachewise-10-minute-talk.pptx')
    pdf.save()
    (HERE / 'cachewise-10-minute-speaker-notes.md').write_text('\n'.join(notes))
    outputs = [HERE / ('cachewise-10-minute-talk.' + ext) for ext in ['pptx', 'pdf']]
    outputs += [HERE / 'cachewise-10-minute-speaker-notes.md'] + sorted(ASSETS.glob('*.png'))
    provenance = {
        'scope': 'Ten slides, 600 seconds of planned speaking time. Existing evidence only; no model execution or experiment.',
        'rendering': 'PDF and editable PPTX generated independently from the same validated layout; PDF is not an Office export. DejaVu Sans is used in both.',
        'inputs': {str(p.relative_to(ROOT)): sha(p) for p in [COVERAGE_INPUT, HOST_INPUT]},
        'script_sha256': sha(Path(__file__)),
        'outputs': {str(p.relative_to(ROOT)): sha(p) for p in outputs},
        'matplotlib_version': matplotlib.__version__,
    }
    (HERE / 'deck-provenance.json').write_text(json.dumps(provenance, indent=2)+'\n')
    print(f'Built {len(slides)} slides, editable PowerPoint, PDF, and {elapsed}-second speaker notes from archived evidence.')


def make_slides():
    load, effects, recovery, ablation = charts()
    slides = []

    def new(title, section, seconds, notes, source=''):
        s = Slide(title, section, seconds, notes, source)
        s.frame(len(slides) + 1)
        slides.append(s)
        return s

    s = new('CacheWise replication\nand KV cache recovery', 'Study overview', 30,
        'This work asks how a coding-agent server should manage reusable attention state when GPU memory is limited. I will cover three parts: our adapted CacheWise replication, the tradeoff between recomputing a prefix and restoring a saved copy, and a host-cache extension with fetch-aware scheduling. The main theme is that scheduling, eviction, and recovery need to be considered together. The measured recovery tier is host DRAM; SSD storage remains future work.')
    s.text(36, 155, 870, 'Serving coding agents under GPU memory pressure', size=24, color=MUTED)
    for x, n, title, body, color in [
        (36, '01', 'Replicate', 'Separate scheduling\nfrom eviction effects.', BLUE),
        (338, '02', 'Recover', 'Compare recomputation\nwith host restoration.', GREEN),
        (640, '03', 'Schedule', 'Make request priority\naware of host hits.', PURPLE)]:
        s.box(x, 268, 284, 176, '#ffffff', radius=9)
        s.text(x+20, 283, 244, n, size=14, color=color, bold=True)
        s.text(x+20, 315, 244, title, size=27, color=color, bold=True)
        s.text(x+20, 367, 244, body, size=17)

    s = new('The same prefix is useful again', 'Motivation', 55,
        'A coding agent does not issue unrelated prompts. It asks the model to act, waits for a tool, and then sends another request containing much of the previous context. Prefill computes attention keys and values for that context. If the prefix is still cached, the server can reuse it. While the tool runs, however, that cache occupies scarce GPU memory. Evicting it makes room for other sessions but creates recovery work when the agent returns. There are two recovery choices: recompute the missing prefix, or restore a compatible saved copy. Scheduling then determines which returning session receives memory first. That is why a good eviction policy cannot be judged independently of request ordering.',
        'Background: CacheWise (Tiwari et al., 2026); report §§1–2')
    for x, label, sub in [(36, 'Model request', 'Prefill + decode'), (350, 'Tool runs', 'GPU state competes for space'), (664, 'Next request', 'Old prefix + new context')]:
        s.box(x, 143, 260, 88, '#ffffff', radius=8)
        s.text(x+16, 155, 230, label, size=23, bold=True)
        s.text(x+16, 192, 230, sub, size=13.5, color=MUTED)
    s.line(301, 185, 340, 185, arrow=True)
    s.line(615, 185, 655, 185, arrow=True)
    s.text(36, 270, 405, 'When the agent returns…', size=24, bold=True)
    s.box(36, 326, 328, 45, '#dce9e3', radius=5)
    s.text(48, 335, 304, 'Reusable prefix', size=20, color=GREEN, bold=True)
    s.box(367, 326, 123, 45, '#e4dcf0', radius=5)
    s.text(381, 337, 99, '+ new', size=18, color=PURPLE, bold=True)
    s.text(36, 395, 455, 'GPU eviction creates a recovery decision.', size=20)
    for y, color, label, body in [(274, BLUE, 'Recompute', 'Run prefill again.'), (369, GREEN, 'Restore', 'Copy saved KV state back.')]:
        s.box(550, y, 374, 83, '#ffffff', radius=7)
        s.text(568, y+12, 338, label, size=22, color=color, bold=True)
        s.text(568, y+47, 338, body, size=17)

    s = new('Replication separates two decisions', 'Part 1 · Methodology', 65,
        'We vary scheduling and eviction independently. The two schedulers are first-come, first-served and prefix-aware scheduling, which favors requests requiring less additional KV state. The two eviction policies are LRU and learned predictive eviction using tool names. All four combinations run in the same engine fork with fresh servers and identical selected inputs. Our testbed uses a 14-billion-parameter Qwen coding model in BF16 on one Blackwell GPU, with 287,696 KV token slots and 512-token prefill chunks. Cohort A has nested loads of ten, twenty, and thirty segments; B and C add two source-disjoint ten-segment cohorts. Four policies, five settings, and three repeats give sixty runs and 6,384 request executions. The primary metric sums model-request latencies within each session, excluding external tool waits.',
        'Evidence: part1-coverage-comparison.json; report §3.1–3.2')
    s.text(36, 131, 544, 'Scheduler × eviction policy', size=20, bold=True)
    s.text(171, 173, 175, 'LRU', size=18, color=MUTED, bold=True)
    s.text(370, 173, 220, 'Predictive', size=18, color=MUTED, bold=True)
    for y, scheduler, p1, p2 in [(211, 'FCFS', 'FCFS / LRU', 'FCFS / predictive'), (304, 'Prefix-aware', 'Prefix / LRU', 'Prefix / predictive')]:
        s.text(36, y+21, 123, scheduler, size=15, bold=True)
        for x, text, color in [(169, p1, BLUE if y == 211 else GREEN), (372, p2, ORANGE if y == 211 else PURPLE)]:
            s.box(x, y, 191, 72, '#ffffff', stroke=color, radius=7)
            s.text(x+13, y+17, 165, text, size=17, color=color, bold=True)
    s.box(615, 135, 309, 245, '#ffffff', radius=8)
    s.text(635, 152, 269, 'Coverage study', size=22, bold=True)
    s.text(635, 199, 269, '5 settings × 3 repeats\n60 runs · 6,384 requests', size=18)
    s.text(635, 271, 269, '14B model · BF16\n287,696 KV token slots\n512-token prefill chunks', size=16, color=MUTED)
    s.box(36, 417, 888, 62, '#e9eef5', radius=7)
    s.text(52, 430, 856, 'Primary metric: mean session serving time, excluding tool waits.', size=20, bold=True)

    s = new('Prefix / LRU has the lowest mean', 'Part 1 · Main result', 80,
        'This chart shows cohort A as the selected workload grows from ten to thirty concurrent segments. Lower is better. The blue and orange lines use FCFS; green and purple use prefix-aware scheduling. The largest separation comes from scheduling. Prefix-aware LRU reduces the FCFS/LRU mean by about 58 percent at ten segments, 62 percent at twenty, and 65 percent at thirty. The bars show the observed range of three repeats, not confidence intervals. The additional held-out B and C cohorts are included in the report table: prefix-aware LRU also has the lowest mean there, making five out of five settings. Increasing N adds new segments, so this is a nested workload sweep rather than a concurrency-only experiment with fixed composition. The result supports prefix-aware scheduling in this adapted replay; it does not establish a universal ranking across models or the entire trace population.',
        'Evidence: frozen 60-run coverage study; report Table 1 and Figure 1a')
    s.box(36, 137, 625, 328, '#ffffff', radius=8)
    s.picture(44, 143, 609, 315, load)
    s.box(686, 145, 238, 303, '#ffffff', radius=8)
    s.text(704, 167, 202, '5 / 5', size=44, bold=True, color=GREEN)
    s.text(704, 228, 202, 'settings favor\nprefix / LRU', size=21, bold=True)
    s.text(704, 307, 202, '58–65% lower\nmean vs. FCFS / LRU\nin cohort A', size=18)
    s.text(44, 471, 880, 'Three repeats per cell. Ranges are observed minima/maxima; lower is better.', size=13.5, color=MUTED)

    s = new('Prediction depends on the scheduler', 'Part 1 · Interaction and tradeoff', 65,
        'The predictive eviction result changes direction when we change the scheduler. Each point here compares predictive eviction against LRU within one matched repeat block. Values below zero mean predictive eviction is faster. Orange points use FCFS, and every orange point is below zero. Purple points use prefix-aware scheduling, and every purple point is above zero. Across settings, adding predictive eviction increases the prefix-aware mean by roughly ten to forty-three percent. The historical tool-duration oracle does not remove this local regression, so prediction accuracy alone does not explain it. There is also a responsiveness tradeoff: at A30, prefix/LRU improves the session mean but increases the average per-run request P99 from about 713 to 1,292 seconds. Scheduling should therefore be judged against both locality and latency objectives.',
        'Evidence: matched coverage repeats and request tails; report Figure 1b and §3.3')
    s.box(36, 140, 625, 325, '#ffffff', radius=8)
    s.picture(44, 146, 609, 310, effects)
    s.box(686, 145, 238, 306, '#ffffff', radius=8)
    s.text(704, 164, 202, 'Mean ≠ tail', size=24, bold=True)
    s.text(704, 220, 202, 'A30 request P99\n(average of 3 runs)', size=16, color=MUTED)
    s.text(704, 286, 202, '713 s → 1,292 s', size=22, color=PURPLE, bold=True)
    s.text(704, 339, 202, 'FCFS / LRU →\nprefix / LRU', size=18)
    s.text(44, 471, 880, 'Dots are matched-repeat effects. Positive values mean slower serving.', size=13.5, color=MUTED)

    s = new('Preserve evicted KV in host DRAM', 'Parts 2–3 · Recovery method', 60,
        'The recovery extension is a separate Mini-SGLang implementation. One radix index records which prefix pages reside on the GPU and which have host copies. When memory is needed, dirty GPU pages are copied to pinned host DRAM. Clean inclusive copies can remain there, so a later GPU eviction does not require another save. When a request returns, a compatible host suffix is restored before prefill; if no copy survives, the engine recomputes. The implementation uses sixteen-token pages, locks and events to protect transfers, and predictive prefetch with a bounded per-step budget. In the recovery study the GPU pool holds twenty-four GiB of KV payload and the host tier adds thirty-six GiB. These are nominal cache payloads, excluding weights and other memory. No SSD path is implemented.',
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

    s = new('Host restoration reduces session time', 'Part 2 · Reported operating points', 75,
        'A simple cost test is whether saving, restoring, and managing the copy costs less than recomputation. Here we keep LRU and FCFS fixed and compare recomputation with on-demand host restoration. At twenty-eight concurrent episodes, reported mean session time falls from 821 to 90.7 seconds, a baseline-to-restoration ratio of about 9.1. At thirty-six it falls from 1,060 to 222 seconds, about 4.8. The reported prior-prefix deficit also drops sharply, supporting the interpretation that more reusable state survives. Two qualifications matter. First, restoration adds thirty-six GiB of host KV capacity to the common twenty-four-GiB GPU pool, so this is not an equal-total-memory algorithm comparison. Second, each bar is one reported run. This study also uses a different engine, smaller GPU pool, larger prefill chunks, and transformed replay inputs. We therefore keep it separate from the vLLM replication. The result demonstrates a favorable host-DRAM operating regime, not a measured SSD break-even curve.',
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

    s = new('Fetch-aware ordering discounts host hits', 'Part 3 · Scheduling extension', 80,
        'Ordinary prefix-aware ordering considers the GPU prefix. Fetch-aware ordering also recognizes that a host-resident prefix can be cheaper than recomputing a complete miss. The priority is new prefill tokens plus alpha times the additional host tokens, with alpha fixed to 0.05. Lower-cost requests go first. This is a heuristic, not a calibrated latency predictor. On the left are the reported N-equals-thirty-six host ablations at fixed tier capacities. LRU plus prefix scheduling takes 159 seconds, predictive plus prefix takes 158, adding prefetch alone takes 172, and the full fetch-aware combination takes 136. The diamonds show the additional observations: 175 seconds for predictive-prefix and 135 for the full combination. The two descriptive means are 166.5 and 135.5 seconds. These sparse, not verified matched observations favor the full combination, but do not isolate every component or establish statistical significance. Prefetch alone is not enough in this example.',
        'Evidence: Mini-SGLangs 3f9aee7; report Figure 3b and Eq. (3)')
    s.box(36, 136, 625, 332, '#ffffff', radius=8)
    s.picture(44, 140, 609, 324, ablation)
    s.box(686, 145, 238, 306, '#ffffff', radius=8)
    s.text(704, 164, 202, 'Priority cost', size=23, bold=True)
    s.text(704, 211, 202, 'new prefill tokens\n+ 0.05 × host tokens', size=18, color=PURPLE, bold=True)
    s.text(704, 286, 202, 'Mean of 2 observations\n166.5 s → 135.5 s', size=18)
    s.text(704, 365, 202, 'Sparse repetitions;\nno confidence interval.', size=16, color=MUTED)
    s.text(44, 475, 880, 'Bars: first observations. Diamonds: additional observations, not matched blocks.', size=13, color=MUTED)

    s = new('Keep the conclusions within the evidence', 'Scope and limitations', 50,
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
