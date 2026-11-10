#!/usr/bin/env python3
"""Build synchronized LaTeX and editable Word manuscripts from manuscript.json."""
import json
import re
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT=Path(__file__).resolve().parents[1]
M=json.loads((ROOT/'manuscript.json').read_text())
REFS={r['key']:r for r in M['references']}
REPO='https://github.com/Kris-Liu773/ragen-sokoban-reproduction'
LABELS={}; counts={'section':0,'subsection':0,'figure':0,'table':0}; appendix=False
for b in M['blocks']:
    k=b['type']
    if k=='appendix':appendix=True;counts['section']=0
    if k=='h1':
        counts['section']+=1;counts['subsection']=0
        b['number']=chr(64+counts['section']) if appendix else str(counts['section'])
    if k=='h2':
        counts['subsection']+=1
        sec=chr(64+counts['section']) if appendix else str(counts['section'])
        b['number']=sec+'.'+str(counts['subsection'])
    if k in ('figure','table'):
        counts[k]+=1;b['number']=str(counts[k])
    if 'label' in b:LABELS[b['label']]=b['number']


def tex_escape(s):
    mapping={'\\':r'\textbackslash{}','&':r'\&','%':r'\%','$':r'\$','#':r'\#','_':r'\_',
        '{':r'\{','}':r'\}','~':r'\textasciitilde{}','^':r'\textasciicircum{}',
        '±':r'$\pm$','×':r'$\times$','“':'``','”':"''",'‘':'`','’':"'",'–':'--','—':'---'}
    return ''.join(mapping.get(c,c) for c in s)


TOKEN=re.compile(r'(\{cite:[^}]+\}|\{ref:[^}]+\}|\{repo\}|`[^`]+`|10\^-?\d+)')
def tex(s):
    out=[]
    for p in TOKEN.split(s):
        if p.startswith('{cite:'):out.append('\\citep{'+p[6:-1]+'}')
        elif p.startswith('{ref:'):out.append('\\ref{'+p[5:-1]+'}')
        elif p=='{repo}':out.append('\\footnote{\\url{'+REPO+'}}')
        elif p.startswith('`'):
            value=p[1:-1]
            out.append(('{\\scriptsize\\texttt{' if len(value)>35 else '\\texttt{')+tex_escape(value)+('}}' if len(value)>35 else '}'))
        elif p.startswith('10^'):out.append('$10^{'+p[3:]+'}$')
        else:out.append(tex_escape(p))
    return ''.join(out)


def build_latex():
    out=ROOT/'latex';out.mkdir(exist_ok=True)
    pre=r'''\documentclass[10pt,twocolumn,letterpaper]{article}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{times}
\renewcommand{\ttdefault}{cmtt}
\renewcommand{\sfdefault}{cmss}
\usepackage[margin=0.72in,columnsep=0.26in]{geometry}
\usepackage{graphicx,booktabs,array,tabularx}
\usepackage[round,authoryear]{natbib}
\usepackage[colorlinks=true,allcolors=black,breaklinks=true]{hyperref}
\usepackage{url}
\urlstyle{same}
\makeatletter
\newenvironment{staticfigure}{\par\medskip\noindent\begin{minipage}{\linewidth}\def\@captype{figure}}{\end{minipage}\par\medskip}
\newenvironment{statictable}{\par\medskip\noindent\begin{minipage}{\linewidth}\def\@captype{table}}{\end{minipage}\par\medskip}
\makeatother
\setlength{\parindent}{1em}
\setlength{\parskip}{0pt}
\setlength{\textfloatsep}{12pt plus 2pt minus 2pt}
\setlength{\floatsep}{10pt plus 2pt minus 2pt}
\setlength{\dbltextfloatsep}{13pt plus 2pt minus 2pt}
\setlength{\abovecaptionskip}{5pt}
\setlength{\belowcaptionskip}{3pt}
\renewcommand{\topfraction}{0.88}
\renewcommand{\bottomfraction}{0.75}
\renewcommand{\textfraction}{0.10}
\renewcommand{\dbltopfraction}{0.88}
\setcounter{topnumber}{4}
\setcounter{dbltopnumber}{4}
\emergencystretch=2em
\raggedbottom
\date{}
'''
    pre+='\\hypersetup{pdftitle={'+tex_escape(M['title'])+'},pdfauthor={'+', '.join(M['authors'])+'}}\n'
    pre+='\\title{\\LARGE\\bfseries '+tex_escape(M['title'])+'}\n'
    pre+='\\author{'+r' \quad '.join(M['authors'][:3])+r'\\[3pt]'+r' \quad '.join(M['authors'][3:])+'}\n'
    pre+=r'''\begin{document}
\twocolumn[\begin{@twocolumnfalse}
\maketitle
\vspace{-1.9em}
\begin{abstract}
'''+tex(M['abstract'])+r'''
\end{abstract}
\vspace{1em}
\end{@twocolumnfalse}]
'''
    parts=[pre]
    in_appendix=False
    for b in M['blocks']:
        t=b['type']
        if t=='h1':
            if b['label']=='app:diagnostics':parts.append('\\clearpage\n')
            parts.append('\\section{'+tex(b['text'])+'}\\label{'+b['label']+'}\n')
        elif t=='h2':parts.append('\\subsection{'+tex(b['text'])+'}\n')
        elif t=='p':parts.append(tex(b['text'])+'\n\n')
        elif t=='code':parts.append('\\begin{quote}\\scriptsize\\ttfamily\\raggedright\n'+'\\\\\n'.join(tex_escape(s) if s else '\\mbox{}' for s in b['text'].splitlines())+'\n\\end{quote}\n')
        elif t=='figure':
            env='staticfigure' if in_appendix else ('figure*' if b.get('wide') else 'figure')
            placement='' if in_appendix else '[t]'
            parts.append('\\begin{'+env+'}'+placement+'\n\\centering\n\\includegraphics[width=\\linewidth]{../figures/'+b['file']+'.pdf}\n\\caption{'+tex(b['caption'])+'}\\label{'+b['label']+'}\n\\end{'+env+'}\n')
        elif t=='table':
            env='statictable' if in_appendix else ('table*' if b.get('wide') else 'table');tot=sum(b['widths'])
            placement='' if in_appendix else '[t]'
            cols=''.join('>{\\raggedright\\arraybackslash}p{\\dimexpr '+f'{w/tot:.6f}'+r'\linewidth-2\tabcolsep\relax}' for w in b['widths'])
            parts.append('\\begin{'+env+'}'+placement+'\n\\centering\n\\caption{'+tex(b['caption'])+'}\\label{'+b['label']+'}\n{'+('\\small' if b.get('wide') or in_appendix else '\\footnotesize')+'\n\\setlength{\\tabcolsep}{4pt}\n\\renewcommand{\\arraystretch}{1.17}\n\\begin{tabular}{'+cols+'}\n\\toprule\n')
            parts.append(' & '.join('\\textbf{'+tex(s)+'}' for s in b['columns'])+r' \\ \midrule'+'\n')
            for row in b['rows']:parts.append(' & '.join(tex(str(s)) for s in row)+r' \\'+'\n')
            parts.append('\\bottomrule\n\\end{tabular}}\n\\end{'+env+'}\n')
        elif t=='references':parts.append('\\newpage\n\\bibliographystyle{plainnat}\n\\bibliography{references}\n')
        elif t=='appendix':
            in_appendix=True
            parts.append('\\onecolumn\n\\appendix\n')
    parts.append('\\end{document}\n')
    (out/'main.tex').write_text(''.join(parts))
    bib=[]
    for r in M['references']:
        field='journal' if r['type']=='article' else 'booktitle'
        bib.append('@'+r['type']+'{'+r['key']+',\n  author = {'+r['authors']+'},\n  title = {{'+r['title']+'}},\n  year = {'+r['year']+'},\n  '+field+' = {'+r['venue']+'},\n  url = {'+r['url']+'}\n}\n')
    (out/'references.bib').write_text('\n'.join(bib))


def word_runs(p,text):
    for token in TOKEN.split(text):
        if not token:continue
        if token.startswith('{cite:'):
            p.add_run('('+REFS[token[6:-1]]['citation']+')')
        elif token.startswith('{ref:'):p.add_run(LABELS[token[5:-1]])
        elif token=='{repo}':
            from docx.opc.constants import RELATIONSHIP_TYPE
            rel=p.part.relate_to(REPO,RELATIONSHIP_TYPE.HYPERLINK,is_external=True)
            link=OxmlElement('w:hyperlink');link.set(qn('r:id'),rel)
            run=OxmlElement('w:r');props=OxmlElement('w:rPr');color=OxmlElement('w:color');color.set(qn('w:val'),'000000');props.append(color);run.append(props)
            textnode=OxmlElement('w:t');textnode.text='online';run.append(textnode);link.append(run);p._p.append(link)
        elif token.startswith('`'):
            r=p.add_run(token[1:-1]);r.font.name='Courier New';r.font.size=Pt(8.5 if len(token)>35 else 9.5)
        elif token.startswith('10^'):
            p.add_run('10');r=p.add_run(token[3:]);r.font.superscript=True
        else:p.add_run(token)


def style_font(style,size,bold=False):
    style.font.name='Times New Roman';style.font.size=Pt(size);style.font.bold=bold;style.font.color.rgb=RGBColor(0,0,0)
    style._element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),'Times New Roman')
    style._element.get_or_add_rPr().rFonts.set(qn('w:ascii'),'Times New Roman')
    style._element.get_or_add_rPr().rFonts.set(qn('w:hAnsi'),'Times New Roman')
    rf=style._element.get_or_add_rPr().rFonts
    for attr in list(rf.attrib):
        if 'Theme' in attr:del rf.attrib[attr]


def build_word():
    d=Document();sec=d.sections[0]
    sec.page_width=Inches(8.5);sec.page_height=Inches(11)
    sec.top_margin=Inches(.75);sec.bottom_margin=Inches(.70)
    sec.left_margin=Inches(.83);sec.right_margin=Inches(.83);sec.footer_distance=Inches(.32)
    style_font(d.styles['Normal'],11)
    pf=d.styles['Normal'].paragraph_format;pf.space_after=Pt(4);pf.line_spacing=1.04;pf.widow_control=True
    for name,size in [('Title',18),('Heading 1',13),('Heading 2',11.5)]:
        style_font(d.styles[name],size,True)
        p=d.styles[name].paragraph_format;p.space_before=Pt(10 if name!='Title' else 0);p.space_after=Pt(5);p.keep_with_next=True
    style_font(d.styles['Caption'],9.5);d.styles['Caption'].font.italic=False
    d.styles['Caption'].paragraph_format.space_after=Pt(7)
    d.core_properties.title=M['title'];d.core_properties.author=', '.join(M['authors'])
    d.core_properties.subject='Empirical study of rollout selection and written reasoning in Sokoban RL'
    d.core_properties.keywords='RAGEN, StarPO-S, Sokoban, reinforcement learning, written reasoning'
    d.core_properties.comments=''
    title=d.add_paragraph(M['title'],'Title');title.alignment=WD_ALIGN_PARAGRAPH.CENTER
    p=d.add_paragraph(', '.join(M['authors']));p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.space_after=Pt(12)
    p=d.add_paragraph();p.add_run('Abstract').bold=True;p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.keep_with_next=True
    p=d.add_paragraph();word_runs(p,M['abstract']);p.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY;p.paragraph_format.space_after=Pt(10)
    in_appendix=False
    for b in M['blocks']:
        t=b['type']
        if t in ('h1','h2'):
            p=d.add_paragraph(b['number']+'  '+b['text'],'Heading 1' if t=='h1' else 'Heading 2')
            if in_appendix:p.paragraph_format.space_before=Pt(7)
            if b.get('label')=='app:diagnostics':p.paragraph_format.page_break_before=True
        elif t=='p':
            p=d.add_paragraph();word_runs(p,b['text']);p.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
            if in_appendix:
                p.paragraph_format.line_spacing=1.0
                p.paragraph_format.space_after=Pt(3)
                for r in p.runs:
                    if r.font.size is None:r.font.size=Pt(10)
        elif t=='figure':
            p=d.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.keep_with_next=True
            p.add_run().add_picture(str(ROOT/'figures'/f"{b['file']}.png"),width=Inches((5.9 if in_appendix else 6.55) if b.get('wide') else 3.7))
            p=d.add_paragraph(style='Caption');p.add_run('Figure '+b['number']+'. ').bold=True;word_runs(p,b['caption'])
        elif t=='table':
            p=d.add_paragraph(style='Caption');p.add_run('Table '+b['number']+'. ').bold=True;word_runs(p,b['caption']);p.paragraph_format.keep_with_next=True
            table=d.add_table(rows=1,cols=len(b['columns']));table.alignment=WD_TABLE_ALIGNMENT.CENTER;table.autofit=False
            widths=[6.8*w/sum(b['widths']) for w in b['widths']]
            for i,w in enumerate(widths):table.columns[i].width=Inches(w)
            props=table._tbl.tblPr
            borders=OxmlElement('w:tblBorders')
            for side in ['top','left','bottom','right','insideH','insideV']:
                el=OxmlElement('w:'+side);el.set(qn('w:val'),'single');el.set(qn('w:sz'),'4');el.set(qn('w:color'),'D9D9D9');borders.append(el)
            props.append(borders)
            for idx,vals in enumerate([b['columns']]+b['rows']):
                row=table.rows[0] if idx==0 else table.add_row()
                trPr=row._tr.get_or_add_trPr();trPr.append(OxmlElement('w:cantSplit'))
                if idx==0:trPr.append(OxmlElement('w:tblHeader'))
                for col,(cell,val) in enumerate(zip(row.cells,vals)):
                    cell.width=Inches(widths[col]);cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
                    cp=cell._tc.get_or_add_tcPr();m=OxmlElement('w:tcMar')
                    for side in ('top','bottom','left','right'):
                        el=OxmlElement('w:'+side);el.set(qn('w:w'),'45' if side in ('top','bottom') else '70');el.set(qn('w:type'),'dxa');m.append(el)
                    cp.append(m)
                    if idx==0:
                        shade=OxmlElement('w:shd');shade.set(qn('w:fill'),'EFEFEF');cp.append(shade)
                    p=cell.paragraphs[0];p.paragraph_format.space_after=Pt(0);p.paragraph_format.line_spacing=1.0
                    p.paragraph_format.keep_with_next=idx<len(b['rows'])
                    p.alignment=WD_ALIGN_PARAGRAPH.LEFT if col==0 or b['label']=='tab:config' else WD_ALIGN_PARAGRAPH.CENTER
                    word_runs(p,str(val))
                    for r in p.runs:r.font.size=Pt(9.5);r.bold=idx==0
            p=d.add_paragraph();p.paragraph_format.space_after=Pt(1);p.paragraph_format.space_before=Pt(0);p.paragraph_format.line_spacing=1;p.add_run().font.size=Pt(2)
        elif t=='code':
            p=d.add_paragraph();p.paragraph_format.left_indent=Inches(.23);p.paragraph_format.keep_together=True
            p.paragraph_format.space_after=Pt(7);r=p.add_run(b['text']);r.font.name='Courier New';r.font.size=Pt(9)
        elif t=='references':
            d.add_paragraph('References','Heading 1')
            for r in sorted(M['references'],key=lambda r:r['citation']):
                p=d.add_paragraph();p.paragraph_format.left_indent=Inches(.18);p.paragraph_format.first_line_indent=Inches(-.18)
                p.paragraph_format.keep_together=True
                p.add_run(r['display']+' ('+r['year']+'). '+r['title']+'. ')
                p.add_run(r['venue']+'. ').italic=True;p.add_run(r['url'])
                for run in p.runs:run.font.size=Pt(10)
        elif t=='appendix':
            in_appendix=True;d.add_page_break()
    p=sec.footer.paragraphs[0];p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    run=p.add_run();field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE');run._r.addnext(field)
    # The default Word template can contribute theme fonts and a blue title rule.
    for border in list(d.styles.element.iter(qn('w:pBdr'))):border.getparent().remove(border)
    for border in list(d.element.iter(qn('w:pBdr'))):border.getparent().remove(border)
    d.save(ROOT/'Sokoban_RL_Paper.docx')


if __name__=='__main__':
    build_latex();build_word()
    print('Wrote latex/main.tex, latex/references.bib, and Sokoban_RL_Paper.docx')
