#!/usr/bin/env python3
"""Compile the checked-in LaTeX and create a self-contained source archive."""
import shutil
import subprocess
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LATEX=ROOT/'latex'
for command in [['pdflatex','-interaction=nonstopmode','-halt-on-error','main.tex'],
                ['bibtex','main'],
                ['pdflatex','-interaction=nonstopmode','-halt-on-error','main.tex'],
                ['pdflatex','-interaction=nonstopmode','-halt-on-error','main.tex']]:
    subprocess.run(command,cwd=LATEX,check=True)
shutil.copy2(LATEX/'main.pdf',ROOT/'Sokoban_RL_Paper.pdf')
with zipfile.ZipFile(ROOT/'Sokoban_RL_Paper_LaTeX.zip','w',zipfile.ZIP_DEFLATED) as z:
    z.writestr('main.tex',(LATEX/'main.tex').read_text().replace('../figures/','figures/'))
    z.write(LATEX/'references.bib','references.bib')
    for p in sorted((ROOT/'figures').glob('*.pdf')):z.write(p,'figures/'+p.name)
    z.writestr('README.txt',
        'Compile with pdfLaTeX and BibTeX:\n\n'
        'pdflatex main.tex\nbibtex main\npdflatex main.tex\npdflatex main.tex\n\n'
        'The archive contains all figure files and the bibliography.\n'
        'For Overleaf, upload the ZIP as a project and select main.tex as the main document.\n'
        'No institution-specific conference template or external images are required.\n')
print('Built Sokoban_RL_Paper.pdf and Sokoban_RL_Paper_LaTeX.zip')
