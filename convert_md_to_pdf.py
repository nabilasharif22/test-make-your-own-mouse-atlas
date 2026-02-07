#!/usr/bin/env python3
"""
convert_md_to_pdf.py
Converts a Markdown or text file into a simple multi-page PDF using matplotlib.
Usage:
    python convert_md_to_pdf.py input.md [output.pdf]
"""
import sys
import textwrap
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt


def md_to_pdf(input_path, output_path, wrap_width=100, lines_per_page=45, fontsize=10):
    with open(input_path, 'r', encoding='utf-8') as fh:
        text = fh.read()

    # Split into lines and wrap
    lines = []
    for raw in text.splitlines():
        if raw.strip() == '':
            lines.append('')
        else:
            wrapped = textwrap.wrap(raw, width=wrap_width)
            if not wrapped:
                lines.append('')
            else:
                lines.extend(wrapped)

    # Paginate
    pages = [lines[i:i+lines_per_page] for i in range(0, len(lines), lines_per_page)]

    with PdfPages(output_path) as pdf:
        for page in pages:
            fig = plt.figure(figsize=(8.5, 11))
            fig.patch.set_facecolor('white')
            plt.axis('off')

            y = 1.0
            line_height = 1.0 / (lines_per_page + 2)
            for ln in page:
                y -= line_height
                plt.text(0.01, y, ln, fontsize=fontsize, family='monospace', va='top')

            plt.tight_layout()
            pdf.savefig(fig)
            plt.close(fig)

    return output_path


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python convert_md_to_pdf.py input.md [output.pdf]')
        sys.exit(1)
    inp = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else inp.rsplit('.', 1)[0] + '.pdf'
    try:
        outpath = md_to_pdf(inp, out)
        print(f'Wrote PDF: {outpath}')
    except Exception as e:
        print('Error:', e)
        sys.exit(2)
