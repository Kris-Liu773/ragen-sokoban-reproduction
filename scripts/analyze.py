#!/usr/bin/env python3
"""Recompute published results from byte-preserved JSONL evidence; no GPU needed."""
import argparse
import csv
import gzip
import hashlib
import json
import re
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAMES = ['std_seed42', 'std_seed43', 'std_seed44', 'random_seed42',
         'random_seed43', 'random_seed44', 'penalty_seed42', 'nofilter_seed42']
RESUMED = {'random_seed43', 'nofilter_seed42'}


def rows(path):
    with gzip.open(path, 'rt', encoding='utf-8') as f:
        return [json.loads(line) for line in f if line.strip()]


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def csv_write(path, data):
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(data[0]))
        writer.writeheader()
        writer.writerows(data)


def verify_data(root):
    sources = json.loads((root / 'provenance/source_manifest.json').read_text())
    for item in sources:
        path = root / item['path']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item['published_sha256'], path
    manifest = json.loads((root / 'provenance/data_manifest.json').read_text())
    for item in manifest:
        path = root / item['path']
        compressed = path.read_bytes()
        assert hashlib.sha256(compressed).hexdigest() == item['sha256'], path
        raw = gzip.decompress(compressed)
        assert hashlib.sha256(raw).hexdigest() == item['raw_sha256'], path
        assert len(raw) == item['raw_bytes'], path
        assert len(raw.splitlines()) == item['records'], path
    return len(manifest)


def diagnose(episodes):
    turns = pairs = equal = answers = empty = executed = ineffective = 0
    thoughts = []
    action_counts_available = True
    for ep in episodes:
        for turn in ep['history']:
            turns += 1
            raw = turn.get('llm_raw_response', '')
            think = re.search(r'<think>(.*?)</think>', raw, re.S)
            answer = re.search(r'<answer>(.*?)</answer>', raw, re.S)
            if think:
                thoughts.append(think.group(1).strip())
            if answer:
                answers += 1
            if think and answer:
                pairs += 1
                equal += think.group(1).strip() == answer.group(1).strip()
            empty += not bool(turn.get('actions'))
            info = turn.get('info', {})
            action_counts_available &= 'actions_executed' in info
            executed += info.get('actions_executed', 0)
            ineffective += info.get('ineffective_actions', 0)
    keywords = sum(bool(re.search(r'\b(box(?:es)?|target(?:s)?|wall(?:s)?)\b', t, re.I)) for t in thoughts)
    return dict(episodes=len(episodes), turns=turns, complete_pairs=pairs,
                equal_pairs=equal, equal_fraction=equal/pairs if pairs else None,
                complete_answer_turns=answers, empty_action_turns=empty,
                actions_executed=executed if action_counts_available else None,
                ineffective_actions=ineffective if action_counts_available else None,
                ineffective_fraction=ineffective/executed if executed and action_counts_available else None,
                complete_thoughts=len(thoughts),
                mean_thought_words=statistics.mean(len(t.split()) for t in thoughts) if thoughts else None,
                keyword_thoughts=keywords,
                keyword_fraction=keywords/len(thoughts) if thoughts else None)


def analyze(root, out):
    out.mkdir(parents=True, exist_ok=True)
    original, merged = {}, {}
    for name in NAMES:
        base = root / 'data/training' / name
        original[name] = rows(base / 'original/metrics.jsonl.gz')
        merged[name] = list(original[name])
        if name in RESUMED:
            last = max(r['step'] for r in original[name])
            merged[name] += [dict(r, resumed=True) for r in rows(base/'resumed/metrics.jsonl.gz') if r['step'] > last]
        assert merged[name][-1]['step'] == 200, name
    summary, diagnostics = [], []
    for name in NAMES:
        stage = 'heldout_original_seed42' if name == 'std_seed42' else (
            'heldout_resumed_' + name if name in RESUMED else 'heldout_' + name)
        base = root / 'data/evaluation' / stage
        episodes = rows(base/'validation_trajectories.jsonl.gz')
        assert sorted(ep['seed'] for ep in episodes) == list(range(2000000, 2000512)), name
        assert {ep['step'] for ep in episodes} == {200}, name
        metric = rows(base/'metrics.jsonl.gz')[-1]
        solved = sum(bool(ep['metrics']['SimpleSokoban/success']) for ep in episodes)
        assert solved == round(metric['val/SimpleSokoban/success']*512), name
        val = next(r for r in reversed(merged[name]) if 'val/SimpleSokoban/success' in r)
        summary.append(dict(run=name, update=200, resumed=name in RESUMED,
            validation_success_count=round(val['val/SimpleSokoban/success']*256), validation_n=256,
            validation_success=val['val/SimpleSokoban/success'], test_success_count=solved,
            test_n=512, test_success=solved/512, test_reward=metric['val/test_score/unknown'],
            test_result_path=str(base.relative_to(root))))
        diagnostics.append(dict(run=name, **diagnose(episodes)))
    common, groups = {}, {}
    for prefix in ['std_seed', 'random_seed']:
        vals = [next(r['val/SimpleSokoban/success'] for r in original[n] if r['step']==190)
                for n in NAMES if n.startswith(prefix)]
        common[prefix] = dict(step=190, values=vals, mean=statistics.mean(vals), sample_sd=statistics.stdev(vals))
        vals = [r['test_success'] for r in summary if r['run'].startswith(prefix)]
        groups[prefix] = dict(n_seeds=3, values=vals, mean=statistics.mean(vals), sample_sd=statistics.stdev(vals))
    first = rows(root/'data/training/std_seed42/original/validation_trajectories.jsonl.gz')
    by_step = defaultdict(list)
    for ep in first:
        by_step[ep['step']].append(ep)
    thinking = []
    for step, episodes in sorted(by_step.items()):
        assert len(episodes) == 256 and sorted(e['seed'] for e in episodes) == list(range(123,379))
        thinking.append(dict(run='std_seed42', step=step, **diagnose(episodes)))
    for name in ['std_seed43','std_seed44']:
        episodes = rows(root/'data/training'/name/'original/validation_trajectories.jsonl.gz')
        thinking.append(dict(run=name, step=200, **diagnose([e for e in episodes if e['step']==200])))
    cases = [ep for ep in first if ep['step'] in [0,200] and ep['seed'] in [123,125]]
    instability = {}
    for name in sorted(RESUMED):
        instability[name] = {key:dict(final=merged[name][-1].get(key),
            maximum=max(r[key] for r in merged[name] if r.get(key) is not None))
            for key in ['actor/pg_loss','actor/grad_norm','rollout/in_group_std']}
    evidence = dict(summary=summary, test_group_summary=groups, common_190=common,
                    test_diagnostics=diagnostics, thinking_by_step=thinking,
                    all_metrics=merged, instability=instability)
    dump(out/'evidence.json', evidence)
    dump(out/'case_studies.json', cases)
    csv_write(out/'final_results.csv', summary)
    csv_write(out/'test_thinking_diagnostics.csv', diagnostics)
    csv_write(out/'validation_thinking.csv', thinking)
    long = [dict(run=n, **r) for n in NAMES for r in merged[n]]
    keys = sorted({k for row in long for k in row})
    csv_write(out/'all_training_metrics.csv', [{k:r.get(k) for k in keys} for r in long])
    print(json.dumps({'runs':len(summary), 'solved':[r['test_success_count'] for r in summary],
                      'test_group_summary':groups, 'output':str(out)}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--out', type=Path, default=ROOT/'results')
    parser.add_argument('--verify', action='store_true', help='Verify compressed and raw SHA-256 first')
    args = parser.parse_args()
    if args.verify:
        print(f'Verified {verify_data(args.root)} evidence files.')
    analyze(args.root, args.out)
