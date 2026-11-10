"""Render the presentation script as a printable PDF; no experiment execution."""

from html import escape
from pathlib import Path
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer

HERE = Path(__file__).resolve().parent
FONT_DIR = Path('/usr/share/fonts/truetype/dejavu')
for name, file in [('Script', 'DejaVuSans.ttf'), ('Script-Bold', 'DejaVuSans-Bold.ttf'),
                   ('Script-Italic', 'DejaVuSans-Oblique.ttf')]:
    pdfmetrics.registerFont(TTFont(name, str(FONT_DIR / file)))
pdfmetrics.registerFontFamily('Script', normal='Script', bold='Script-Bold', italic='Script-Italic')
styles = {
    'title': ParagraphStyle('title', fontName='Script-Bold', fontSize=17, leading=22, spaceAfter=10),
    'heading': ParagraphStyle('heading', fontName='Script-Bold', fontSize=12, leading=16, spaceBefore=10, spaceAfter=6),
    'body': ParagraphStyle('body', fontName='Script', fontSize=10.5, leading=14.5, spaceAfter=7, alignment=TA_LEFT),
    'time': ParagraphStyle('time', fontName='Script-Bold', fontSize=9, leading=12, textColor=colors.HexColor('#238269'), spaceAfter=6),
    'cue': ParagraphStyle('cue', fontName='Script-Italic', fontSize=9, leading=12, textColor=colors.HexColor('#526477'), spaceAfter=8),
}


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont('Script', 8)
    canvas.setFillColor(colors.HexColor('#526477'))
    canvas.drawString(46, 29, 'Ten-minute presentation script · delivery cues are not spoken')
    canvas.drawRightString(A4[0]-46, 29, str(doc.page))
    canvas.restoreState()


def main():
    source = (HERE / 'cachewise-10-minute-script.md').read_text()
    blocks = re.split(r'\n(?=## Slide )', source)
    story = []
    words = []
    for i, block in enumerate(blocks):
        group = []
        for paragraph in block.strip().split('\n\n'):
            text = ' '.join(paragraph.splitlines())
            if text.startswith('# '):
                key, text = 'title', text[2:]
            elif text.startswith('## '):
                key, text = 'heading', text[3:]
            elif text.startswith('**') and text.endswith('**'):
                key, text = 'time', text[2:-2]
            elif text.startswith('*') and text.endswith('*'):
                key, text = 'cue', text[1:-1]
            else:
                key = 'body'
                if i:
                    words.extend(text.split())
            group.append(Paragraph(escape(text), styles[key]))
        story.extend(group if i == 0 else [KeepTogether(group)])
        story.append(Spacer(1, 5))
    doc = SimpleDocTemplate(str(HERE / 'cachewise-10-minute-script.pdf'), pagesize=A4,
                            leftMargin=46, rightMargin=46, topMargin=42, bottomMargin=45,
                            title='Ten-minute presentation script: CacheWise and KV cache recovery', author='')
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(f'Rendered script for {len(blocks)-1} slides; {len(words):,} spoken words, excluding cues and timings.')


if __name__ == '__main__':
    main()
