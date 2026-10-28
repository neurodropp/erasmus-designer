import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import brain

def cli(*args):
    return subprocess.run([sys.executable,str(ROOT/'scripts/brain.py'),*args],capture_output=True,text=True,cwd=ROOT)

class ScopeTests(unittest.TestCase):
    def test_unavailable_route(self):
        self.assertNotEqual(cli('dossier','--action','KA210','--sector','HED').returncode,0)
    def test_wrong_year_never_substitutes(self):
        self.assertNotEqual(cli('dossier','--action','KA220-YOU','--year','2025').returncode,0)
    def test_suffix_infers_sector(self):
        p=cli('dossier','--action','KA220-SPO'); self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(json.loads(p.stdout)['national_sources'],[])
    def test_central_action_does_not_use_national_funding_rules(self):
        p=cli('dossier','--action','ERASMUS-MUNDUS')
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(json.loads(p.stdout)['national_sources'],[])
    def test_hed_mobility_rules_do_not_become_ka220_rules(self):
        s=next(s for s in brain.load('sources.json') if s['id']=='indire-hed-2026')
        for page,code in [(2,'KA131'),(7,'KA131'),(8,'KA171'),(9,'KA220-HED')]:
            codes,_=brain.page_tags(s,page,brain.load('actions.json'))
            self.assertEqual(codes,[code])
    def test_school_mobility_does_not_retrieve_adult_national_pages(self):
        p=cli('search','priorita','--action','KA122-SCH','--layer','evidence','--json','--limit','50')
        self.assertEqual(p.returncode,0,p.stderr)
        ids={x['id'] for x in json.loads(p.stdout)['hits']}
        self.assertNotIn('indire-sch-adu-2026:p0007',ids)
        self.assertNotIn('indire-sch-adu-2026:p0008',ids)
    def test_youth_national_priority_does_not_leak_to_ka210(self):
        meta={'source':'aig-priorities-2026','sectors':['YOU'],'actions':['KA220']}
        self.assertFalse(brain.applicable(meta,'KA210-YOU','YOU'))
    def test_sport_does_not_use_national_expert_rubric(self):
        p=cli('search','assessment award criteria','--action','KA220-SPO','--layer','evidence','--json','--limit','50')
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertFalse(any(h['source']=='expert-2026' for h in json.loads(p.stdout)['hits']))
    def test_budget_common_expert_pages_cover_national_ka2(self):
        s=next(s for s in brain.load('sources.json') if s['id']=='expert-2026')
        codes,sectors=brain.page_tags(s,70,brain.load('actions.json'))
        self.assertIn('KA220-ADU',codes); self.assertIn('KA210-YOU',codes); self.assertNotIn('KA220-SPO',codes)
    def test_known_threshold_is_retrievable(self):
        for q in ('KA220 minimum points','soglia minimo punteggio'):
            p=cli('search',q,'--action','KA220','--sector','ADU','--layer','evidence','--json','--limit','8')
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertIn('programme-2026:p0242',{h['id'] for h in json.loads(p.stdout)['hits']},q)
    def test_missing_index_is_reported(self):
        old_db=brain.DB; old_dump=brain.dump
        try:
            brain.DB=ROOT/'index/nonexistent-test.sqlite'; brain.dump=lambda *a:None
            self.assertEqual(brain.check(None),1)
        finally: brain.DB=old_db; brain.dump=old_dump
    def test_guide_is_complete(self):
        self.assertEqual(len(list((ROOT/'sources/programme-2026/pages').glob('*.md'))),456)
        self.assertEqual(len(list((ROOT/'sources/expert-2026/pages').glob('*.md'))),85)
        self.assertIn('70 points',(ROOT/'sources/programme-2026/pages/page-0242.md').read_text())

if __name__=='__main__': unittest.main()
