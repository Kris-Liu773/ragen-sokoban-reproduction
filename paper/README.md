# Research manuscript

**Task Success and Written Reasoning in Sokoban Reinforcement Learning**

Yihao Tao, Bowu, Jintao Wang, Runhu, and Haotian Liu.

- [Read the PDF](Sokoban_RL_Paper.pdf): eight pages, with a two-column main text and two single-column appendix pages.
- [Edit the Word document](Sokoban_RL_Paper.docx): the same text, figures, and tables in a single-column layout; ten pages in the verified rendering. Word pagination can vary with installed fonts.
- [Download the self-contained LaTeX project](Sokoban_RL_Paper_LaTeX.zip): upload the ZIP to Overleaf, or compile `main.tex` with pdfLaTeX and BibTeX.
- [Browse the LaTeX source](latex/main.tex) and [bibliography](latex/references.bib).

The manuscript covers eight update-200 models, the three-seed selection comparison, two zero-action failures, an exploratory action penalty, and the relationship between task success and written reasoning. It uses the original experiment records and source code. No additional GPU training was performed to prepare the manuscript.

## Additional analysis in the manuscript

An exact initial-board audit finds 486 distinct grids among the 512 test seeds. Twenty grids also occur in validation, accounting for 22 test episodes. Removing those episodes leaves 490 seed-indexed evaluations and preserves the StarPO-S versus random-selection ordering. This post hoc check does not establish that all test layouts are disjoint from training, and it retains duplicate boards within the remaining test set.

The paper also distinguishes complete thought spans from complete thought-answer pairs, and distinguishes serialized training-sequence length from assistant-segment length. These definitions are needed to interpret the recorded metrics correctly.

## Rebuild

From this directory, with Python 3.12 and a TeX installation containing the standard `article`, PSNFSS/Times, `geometry`, `graphicx`, `booktabs`, `array`, `tabularx`, `natbib`, `hyperref`, and `url` packages:

```bash
python -m pip install -r requirements-paper.txt
python tools/build_evidence.py
python tools/verify_manuscript.py
python tools/build_manuscript.py
python tools/compile_paper.py
```

The evidence builder finds the experiment repository automatically when this folder is `paper/` inside that repository, or when it sits beside a checkout named `ragen-sokoban-reproduction`. Otherwise supply `--repo /path/to/ragen-sokoban-reproduction`.

`manuscript.json` is the shared text source used by the builder. Direct edits to Word or LaTeX do not update that source automatically. To keep all formats synchronized, edit it and rebuild. The LaTeX ZIP uses a flat `main.tex` entry point and includes all PDF figures; no Python installation is needed just to compile that ZIP.

`analysis/` contains recomputed result tables, text diagnostics, selected raw cases, and the additional board audit. `figures/` contains vector PDF and high-resolution PNG versions of all five figures. `tools/verify_manuscript.py` checks the reported result, text-agreement, and sensitivity tables against the evidence. The original compressed logs remain in the main repository's `data/` directory.

## References

The manuscript cites RAGEN for the existing framework and prior findings, Qwen2.5 for the model, HybridFlow for the veRL backend, PPO for policy optimization, and GAE for advantage estimation. Bibliographic details were checked against the original papers and the ICLR 2016 / EuroSys 2025 conference records. No citation is used to claim that these papers established our particular numerical results.
