"""Extract attributed original-paper plots from a pinned PDF; no experiments.

Usage: python presentation/extract_cachewise_figures.py --pdf PATH
The PDF stays outside Git; cropped vector plots and PNG previews are tracked.
"""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from pypdf import PdfReader, PdfWriter
from pypdf.generic import RectangleObject

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ASSETS = HERE / 'assets'
SOURCE_SHA = '8787570ba7d61444aced8378af2069796d7e801920bc6b7476afabcc347aed3c'
SOURCE_URL = 'https://arxiv.org/pdf/2606.16824v1'
# Coordinates are PDF points measured from the top-left of page 4.
FIGURES = {
    '2': [54, 68, 560, 267],
    '3': [54, 287, 284, 400],
    '6': [318, 435, 560, 563],
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdf', type=Path, default=ROOT/'paper/build/cachewise-original-2606.16824v1.pdf')
    args = parser.parse_args()
    if sha(args.pdf) != SOURCE_SHA:
        raise ValueError('The source PDF differs from the verified arXiv v1; recheck pages and crops.')
    reader = PdfReader(args.pdf)
    assert len(reader.pages) == 14
    assert str(reader.metadata.get('/License', '')).rstrip('/') == 'http://creativecommons.org/licenses/by/4.0'
    ASSETS.mkdir(exist_ok=True)
    records = []
    for figure, rect in FIGURES.items():
        writer = PdfWriter()
        page = writer.add_page(reader.pages[3])
        height = float(page.mediabox.height)
        x0, y0, x1, y1 = rect
        clip = RectangleObject([x0, height-y1, x1, height-y0])
        page.mediabox = clip
        page.cropbox = clip
        writer.add_metadata({
            '/Title': f'CacheWise v1, original Figure {figure} (cropped from PDF page 4)',
            '/Author': 'Tiwari et al.', '/Source': SOURCE_URL,
            '/License': 'https://creativecommons.org/licenses/by/4.0/',
        })
        pdf = ASSETS/f'original-cachewise-figure{figure}.pdf'
        png = pdf.with_suffix('.png')
        with pdf.open('wb') as handle:
            writer.write(handle)
        subprocess.run(['mutool', 'draw', '-q', '-r', '180', '-o', str(png), str(pdf)], check=True)
        records.append({
            'figure': int(figure), 'source_pdf_page': 4, 'crop_top_left_points': rect,
            'files': {str(p.relative_to(ROOT)): sha(p) for p in [pdf, png]},
        })
    manifest = {
        'title': 'CacheWise: Understanding Workloads and Optimizing KVCache Management for Efficiently Serving LLM Coding Agents',
        'authors': ['Shubham Tiwari', 'Tapan Chugh', 'Nash Rickert', 'Simon Peter', 'Ratul Mahajan', 'Haiying Shen'],
        'version': 'arXiv:2606.16824v1', 'source_url': SOURCE_URL,
        'requested_download_url': 'https://arxiv.org/pdf/2606.16824',
        'source_pdf_sha256': SOURCE_SHA,
        'license': 'CC BY 4.0', 'license_url': 'https://creativecommons.org/licenses/by/4.0/',
        'changes': 'Cropped plots from the original PDF, excluding surrounding text/captions. Plot data, axes, and legends are unaltered. Slide captions are new and attribute the original paper. These are published results, not new or replicated measurements.',
        'script_sha256': sha(Path(__file__)), 'figures': records,
    }
    (ASSETS/'original-cachewise-figures.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print('Extracted original Figures 2, 3, and 6 from verified PDF page 4; no experiments executed.')


if __name__ == '__main__':
    main()
