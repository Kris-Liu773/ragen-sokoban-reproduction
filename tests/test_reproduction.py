"""CPU evidence checks and configuration guardrails for the public launcher."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import analyze
import run


class EvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name)
        analyze.verify_data(ROOT)
        analyze.analyze(ROOT, cls.out)
        cls.evidence = json.loads((cls.out/'evidence.json').read_text())

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_final_counts_and_continuations(self):
        summary = self.evidence['summary']
        self.assertEqual([r['test_success_count'] for r in summary], [98,119,120,39,0,28,112,0])
        self.assertEqual([r['validation_success_count'] for r in summary], [54,55,54,21,0,23,52,0])
        for name, rows in self.evidence['all_metrics'].items():
            self.assertEqual(rows[-1]['step'],200)
            self.assertEqual(len({r['step'] for r in rows}),len(rows),name)

    def test_reasoning_denominators_and_missing_values(self):
        stats=self.evidence['thinking_by_step']
        first=stats[0]
        last=next(s for s in stats if s['run']=='std_seed42' and s['step']==200)
        self.assertEqual((first['keyword_thoughts'],first['complete_thoughts']),(641,725))
        self.assertEqual((last['equal_pairs'],last['complete_pairs']),(985,1009))
        self.assertIsNone(first['actions_executed'])
        for d in self.evidence['test_diagnostics']:
            if d['run'] in analyze.RESUMED:
                self.assertEqual(d['actions_executed'],0)
                self.assertEqual(d['complete_pairs'],0)
                self.assertIsNone(d['equal_fraction'])

    def test_reported_means(self):
        groups=self.evidence['test_group_summary']
        self.assertAlmostEqual(groups['std_seed']['mean']*100,21.940104166666668)
        self.assertAlmostEqual(groups['random_seed']['mean']*100,4.361979166666666)


class LauncherTests(unittest.TestCase):
    def test_variants_and_heldout_reward_are_controlled(self):
        for name in run.RUNS:
            c=run.build_config(name,Path('/model'),Path('/output'),'train',None,200)
            self.assertEqual(c['actor_rollout_ref']['actor']['optim']['lr'],1e-6)
            self.assertEqual(c['critic']['optim']['lr'],1e-5)
            self.assertEqual(c['es_manager']['train']['env_groups'],8)
            self.assertEqual(c['es_manager']['train']['group_size'],16)
            rollout=c['actor_rollout_ref']['rollout']
            self.assertEqual(rollout['rollout_filter_type'],'random' if name.startswith('random') else 'std')
            self.assertEqual(rollout['rollout_filter_ratio'],1.0 if name.startswith('nofilter') else .25)
            self.assertEqual(c['es_manager']['ineffective_action_penalty'],-.1 if name.startswith('penalty') else 0)
            e=run.build_config(name,Path('/model'),Path('/output'),'evaluate',Path('/checkpoint'),200)
            self.assertTrue(e['trainer']['val_only'])
            self.assertEqual(e['es_manager']['val']['env_groups'],512)
            self.assertEqual(e['es_manager']['val']['seed_start'],2000000)
            self.assertEqual(e['es_manager']['ineffective_action_penalty'],0)
            self.assertEqual(e['trainer']['resume_mode'],'resume_path')


if __name__=='__main__':unittest.main()
