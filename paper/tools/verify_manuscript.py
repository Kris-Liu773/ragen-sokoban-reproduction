#!/usr/bin/env python3
"""Check manuscript tables against recomputed evidence and validate source references."""
import csv
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
m=json.loads((ROOT/'manuscript.json').read_text())
def read_csv(name):
    with (ROOT/'analysis'/name).open(newline='') as f:return list(csv.DictReader(f))
tables={b['label']:b for b in m['blocks'] if b['type']=='table'}
results=read_csv('final_results.csv')
assert len(results)==len(tables['tab:results']['rows'])==8
for source,printed in zip(results,tables['tab:results']['rows']):
    assert printed[2]==f"{source['validation_success_count']} / 256"
    assert printed[3]==f"{source['test_success_count']} / 512"
    assert printed[4]==f"{100*float(source['test_success']):.2f}%"
    assert printed[1].endswith('*') == (source['resumed']=='True')
mapping={'StarPO-S':'std','Random':'random','Penalty':'penalty','No filter':'nofilter'}
diagnostics={r['run']:r for r in read_csv('test_thinking_diagnostics.csv')}
def run_name(label):
    method,seed=label.rsplit(' ',1)
    return mapping[method]+'_seed'+seed
for row in tables['tab:text']['rows']:
    d=diagnostics[run_name(row[0])]
    assert row[1]==f"{d['equal_pairs']} / {d['complete_pairs']}"
    expected=f"{100*float(d['equal_fraction']):.2f}%" if d['equal_fraction'] else 'Undefined'
    assert row[2]==expected
sense={r['run']:r for r in read_csv('board_sensitivity.csv')}
for row in tables['tab:sensitivity']['rows']:
    d=sense[run_name(row[0])]
    assert row[1]==d['solved'] and row[2]==f"{100*float(d['success']):.2f}%"
    assert d['episodes']=='490'
thinking=read_csv('validation_thinking.csv')
first={int(r['step']):r for r in thinking if r['run']=='std_seed42'}
assert f"{float(first[0]['mean_thought_words']):.2f}"=='25.07'
assert f"{float(first[200]['mean_thought_words']):.2f}"=='3.79'
assert (first[0]['equal_pairs'],first[0]['complete_pairs'])==('7','626')
assert (first[200]['equal_pairs'],first[200]['complete_pairs'])==('985','1009')
assert (first[0]['keyword_thoughts'],first[0]['complete_thoughts'])==('641','725')
assert (first[200]['keyword_thoughts'],first[200]['complete_thoughts'])==('0','1009')
audit=json.loads((ROOT/'analysis/paper_audit.json').read_text())
assert audit['board_audit']['test_unique_initial_boards']==486
assert audit['board_audit']['shared_initial_boards']==20
assert audit['board_audit']['test_episodes_matching_validation']==22
assert audit['validation_outcome_changes']['failure_to_success']==46
assert audit['validation_outcome_changes']['success_to_failure']==5
labels={b['label'] for b in m['blocks'] if 'label' in b}
refs={r['key'] for r in m['references']}
all_text=json.dumps(m)
assert set(re.findall(r'\{cite:([^}]+)\}',all_text))==refs
assert set(re.findall(r'\{ref:([^}]+)\}',all_text))<=labels
assert len(refs)==5
for b in m['blocks']:
    if b['type']=='figure':
        assert (ROOT/'figures'/(b['file']+'.pdf')).exists()
        assert (ROOT/'figures'/(b['file']+'.png')).exists()
print('Verified all 24 result/text/sensitivity rows, text denominators, board audit, five citations, and figure sources.')
