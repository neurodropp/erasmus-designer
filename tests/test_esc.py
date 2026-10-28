import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import brain

class ESCScopeTests(unittest.TestCase):
    def cli(self,*args): return subprocess.run([sys.executable,str(brain.ROOT/'scripts/brain.py'),*args],capture_output=True,text=True)
    def test_base_esc50_search_infers_esc(self):
        p=self.cli('search','quality label','--action','ESC50','--json'); self.assertEqual(p.returncode,0,p.stderr)
        r=json.loads(p.stdout); self.assertEqual(r['program'],'ESC')
        self.assertFalse(any(h['source'] in ('programme-2026','expert-2026') for h in r['hits']))
    def test_sector_esc_search_infers_esc(self):
        p=self.cli('search','solidarity','--sector','ESC','--layer','evidence','--json'); self.assertEqual(p.returncode,0,p.stderr)
        r=json.loads(p.stdout); self.assertEqual(r['program'],'ESC'); self.assertTrue(r['hits'])
        self.assertTrue(all(h['program'] in ('ESC','SHARED') for h in r['hits']))
    def test_inconsistent_program_sector_is_rejected(self):
        self.assertNotEqual(self.cli('search','solidarity','--sector','ESC','--program','ERASMUS').returncode,0)
    def test_allocation_does_not_use_new_expert_rubric(self):
        p=self.cli('search','award criteria','--action','ESC51','--layer','evidence','--json','--limit','50')
        self.assertEqual(p.returncode,0,p.stderr); self.assertFalse(any(h['source']=='esc-expert-2026' for h in json.loads(p.stdout)['hits']))
    def test_route_specific_general_sources(self):
        p=self.cli('dossier','--action','ESC30'); self.assertEqual(p.returncode,0,p.stderr)
        r=json.loads(p.stdout); self.assertTrue(r['general_sources']); self.assertTrue(all(s['id'].startswith('esc-') for s in r['general_sources']))
        self.assertEqual(r['action']['award_criteria']['criteria'][0]['max_points'],40)
        self.assertTrue(all('/revisions/' in path for s in r['evidence'] for path in s['files']))
        experts=[s for s in r['general_sources'] if s['id']=='esc-expert-2026']
        self.assertEqual([s['pages'] for s in experts],[[3,14],[26,28]])
    def test_esc50_role_changes_scoring_mode(self):
        routes=brain.load('actions.json'); host=next(a for a in routes if a['code']=='ESC50-HOST-SUPPORT'); lead=next(a for a in routes if a['code']=='ESC50-LEAD')
        self.assertEqual(host['award_criteria']['scoring_mode'],'pass-fail'); self.assertEqual(lead['award_criteria']['total_max_points'],100)
    def test_attached_guides_complete(self):
        self.assertEqual(len(list((brain.ROOT/'sources/esc-programme-2026/pages').glob('*.md'))),148)
        self.assertEqual(len(list((brain.ROOT/'sources/esc-expert-2026/pages').glob('*.md'))),28)

if __name__=='__main__': unittest.main()
