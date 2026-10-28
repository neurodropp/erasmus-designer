"""Behavioral bootstrap tests with an observable isolated subprocess CLI.

No installed LWC binary or production Wiki is invoked.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ENGINE = Path(__file__).resolve().parents[1]

FAKE_CLI = r'''#!/usr/bin/env python3
import json, sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
path=root/'fake-state.json'; state=json.loads(path.read_text())
args=sys.argv[1:]; draft=None
if args[:1]==['--changeset']:
    draft=args[1];args=args[2:]
stdin=sys.stdin.read()
entry={'draft':draft,'args':args,'stdin':stdin}
state['calls'].append(entry)
def finish(value=None, error=None):
    path.write_text(json.dumps(state,ensure_ascii=False))
    if error:
        print(error,file=sys.stderr);sys.exit(1)
    print(json.dumps(value,ensure_ascii=False));sys.exit(0)
command=' '.join(args[:2])
if state.get('fail')==command: finish(error='injected failure: '+command)
space=state['draft'] if draft else state['live']
if command=='changeset show':
    if state.get('discarded') or state.get('committed'):finish(error='no draft')
    finish({'status':'draft','changeset_id':'fixture-identity','name':args[2]})
if command=='changeset commit':
    state['map_at_commit']=(root/'index/lwc-source-map.json').read_text()
    state['live']=json.loads(json.dumps(state['draft']));state['committed']=True
    if state.get('corrupt_after_commit'):
        state['live']['sources'][str(state['corrupt_after_commit'])]['content']='wrong committed body'
    finish({'status':'committed','changeset_id':'fixture-identity','name':args[2],'post_revision':'observed-fixture-post-revision'})
if command=='changeset discard':
    state['discarded']=True;state['draft']={};finish({'status':'discarded'})
if command in ('purpose set','schema set'):finish({'ok':True})
if command=='source add':
    content=Path(args[2]).read_text();ident=next((int(k) for k,v in space['sources'].items() if v['content']==content),None)
    if ident is None:
        ident=max([99]+[int(k) for k in space['sources']])+1
        space['sources'][str(ident)]={'id':ident,'content':content,'title':args[args.index('--title')+1]}
        space['jobs'][str(ident)]='pending'
    finish({'source':space['sources'][str(ident)]})
if command=='source show':
    source=space['sources'].get(args[2])
    if not source:finish(error='source unavailable live/draft')
    finish({'source':source,'window':{'has_more':False}})
if command=='page list':
    offset=int(args[args.index('--offset')+1]);limit=int(args[args.index('--limit')+1])
    pages=[{'slug':k} for k in sorted(space['pages'])]
    finish({'pages':pages[offset:offset+limit],'limit':limit,'offset':offset,'has_more':offset+limit<len(pages)})
if command=='page show':finish({'page':space['pages'][args[2]]})
if command=='page put':
    slug=args[2];support=[int(args[i+1]) for i,x in enumerate(args) if x=='--source']
    def opt(name):return args[args.index(name)+1]
    space['pages'][slug]={'slug':slug,'title':opt('--title'),'kind':opt('--kind'),'summary':opt('--summary'),'body':stdin,'source_ids':support,'provenance':['source-grounded'],'created_at':'fixture-created','updated_at':'fixture-updated'}
    state['history'].append(slug)
    finish({'ok':True})
if command=='ingest list':finish({'jobs':[{'source_id':int(k),'status':v} for k,v in space['jobs'].items()]})
if command in ('ingest claim','ingest analyze','ingest complete'):
    space['jobs'][args[2]]={'ingest claim':'analyzing','ingest analyze':'analyzing','ingest complete':'completed'}[command]
    finish({'ok':True})
if args==['lint']:finish({'blocking_total':state.get('lint_blocking',0),'total':0})
finish(error='unexpected fake CLI command '+repr(args))
'''


def sha(data):
    return hashlib.sha256(data).hexdigest()


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        for name in ('scripts', 'config', 'index', 'wiki/actions', 'wiki/templates', 'audits/input', 'history'):
            (self.root / name).mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ENGINE / 'scripts/sync_lwc.py', self.root / 'scripts/sync_lwc.py')
        (self.root / 'scripts/lwc').write_text(FAKE_CLI)
        (self.root / 'scripts/lwc').chmod(0o755)
        keys = ('programme-2026', 'expert-2026', 'esc-programme-2026', 'esc-expert-2026', 'template-ka220-user')
        self.sources = [{'id':k,'title':k,'year':2026,'program':'ESC' if k.startswith('esc-') else 'ERASMUS','kind':'user-template' if k.startswith('template') else 'programme-guide','url':'https://example.org/public.pdf','path':'raw/'+k+'.pdf','actions':[],'sectors':[]} for k in keys]
        for s in self.sources:
            folder = self.root / 'sources' / s['id']; folder.mkdir(parents=True)
            (folder / 'full.md').write_text('public fixture text '+s['id']+'\n')
            (folder / 'metadata.json').write_text(json.dumps({'pages':1,'original_sha256':'fixture-original'}))
        (self.root / 'config/sources.json').write_text(json.dumps(self.sources))
        (self.root / 'config/actions.json').write_text(json.dumps([{'code':'ESC30','program':'ESC','year':2026,'programme_source':'esc-programme-2026','expert_source':'esc-expert-2026','expert_pages':[22,25]}]))
        (self.root / 'config/wiki-purpose.md').write_text('Public fixture purpose\n')
        (self.root / 'config/wiki-schema.md').write_text('Public fixture schema\n')
        (self.root / 'wiki/actions/esc30.md').write_text('# Solidarity fixture\n\n[Programme](source-esc-programme-2026.md) [Experts](source-esc-expert-2026.md)\n')
        (self.root / 'wiki/templates/ka220-question-playbook.md').write_text('# Public playbook fixture\n\n[Template](source-template-ka220-user.md) [Programme](source-programme-2026.md) [Experts](source-expert-2026.md)\n')
        self.support = {'esc30':['esc-programme-2026','esc-expert-2026'],'ka220-question-playbook':['programme-2026','expert-2026','template-ka220-user']}
        self.old_map = {'programme-2026':1,'expert-2026':2}
        self.map = self.root / 'index/lwc-source-map.json'
        self.map.write_text(json.dumps(self.old_map))
        self.before_map = self.map.read_bytes()
        live={'sources':{str(v):{'id':v,'content':(self.root/'sources'/k/'full.md').read_text(),'title':k} for k,v in self.old_map.items()},'pages':{},'jobs':{'1':'completed','2':'completed'}}
        self.state={'live':live,'draft':json.loads(json.dumps(live)),'calls':[],'history':['immutable-original-version']}
        self.state_path=self.root/'fake-state.json';self.save_state()
        self.manifest_path=self.root/'audits/input/manifest.json';self.write_manifest()
        self.history_path=self.root/'history/old-receipt.json';self.history_path.write_bytes(b'{"frozen":"old byte history"}\n')
        self.old_history=self.history_path.read_bytes()

    def tearDown(self):
        self.tmp.cleanup()

    def save_state(self):
        self.state_path.write_text(json.dumps(self.state))

    def read_state(self):
        self.state=json.loads(self.state_path.read_text());return self.state

    def write_manifest(self):
        self.manifest={'schema_version':'bootstrap-support-manifest-v1','config_sha256':{n:sha((self.root/'config'/n).read_bytes()) for n in ('sources.json','actions.json','wiki-purpose.md','wiki-schema.md')},'sources':{s['id']:{'data_classification':'public','sha256':sha((self.root/'sources'/s['id']/'full.md').read_bytes()),'metadata_sha256':sha((self.root/'sources'/s['id']/'metadata.json').read_bytes())} for s in self.sources},'pages':{p.stem:{'path':str(p.relative_to(self.root)),'data_classification':'public','sha256':sha(p.read_bytes()),'sources':self.support[p.stem]} for p in (self.root/'wiki').rglob('*.md')}}
        self.save_manifest()

    def save_manifest(self):
        self.manifest_path.write_text(json.dumps(self.manifest))

    def invoke(self, *args):
        return subprocess.run([sys.executable,str(self.root/'scripts/sync_lwc.py'),*args],cwd=self.root,text=True,capture_output=True)

    def stage(self):
        return self.invoke('stage','--changeset','fixture','--manifest','audits/input/manifest.json','--out','audits/candidate')

    def successful_stage(self):
        result=self.stage();self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(self.map.read_bytes(),self.before_map)
        return json.loads((self.root/'audits/candidate/candidate.json').read_text())

    def publish(self):
        path=self.root/'audits/candidate/candidate.json'
        return self.invoke('publish-map','--candidate','audits/candidate/candidate.json','--expected-candidate-sha256',sha(path.read_bytes()))

    def assert_no_mutations(self):
        self.assertFalse(any(' '.join(c['args'][:2]) in ('source add','page put','purpose set','schema set','ingest claim','changeset commit') for c in self.read_state()['calls']))
        self.assertEqual(self.map.read_bytes(),self.before_map)
        self.assertEqual(self.history_path.read_bytes(),self.old_history)

    def test_legacy_blind_bootstrap_is_refused_before_cli(self):
        result=self.invoke('--changeset','fixture')
        self.assertNotEqual(result.returncode,0);self.assert_no_mutations();self.assertEqual(self.read_state()['calls'],[])

    def test_missing_page_support_refused_before_mutations(self):
        del self.manifest['pages']['ka220-question-playbook'];self.save_manifest()
        result=self.stage();self.assertEqual(result.returncode,1);self.assertIn('Incomplete per-page',result.stderr);self.assert_no_mutations()

    def test_unknown_support_refused_before_mutations(self):
        self.manifest['pages']['esc30']['sources'].append('missing-exact-evidence');self.save_manifest()
        result=self.stage();self.assertEqual(result.returncode,1);self.assertIn('page support',result.stderr);self.assert_no_mutations()

    def test_generic_erasmus_support_cannot_replace_esc(self):
        self.manifest['pages']['esc30']['sources']=['programme-2026','expert-2026'];self.save_manifest()
        result=self.stage();self.assertEqual(result.returncode,1);self.assert_no_mutations()

    def test_route_support_required_even_without_markdown_links(self):
        (self.root/'wiki/actions/esc30.md').write_text('# Solidarity fixture\n')
        self.support['esc30']=['programme-2026','expert-2026'];self.write_manifest()
        result=self.stage();self.assertEqual(result.returncode,1);self.assertIn('program-aware',result.stderr);self.assert_no_mutations()

    def test_private_input_refused_before_cli(self):
        self.manifest['sources']['template-ka220-user']['data_classification']='project-private';self.save_manifest()
        result=self.stage();self.assertEqual(result.returncode,1);self.assertIn('Private',result.stderr);self.assert_no_mutations();self.assertEqual(self.read_state()['calls'],[])

    def test_changed_source_input_refused_before_cli(self):
        (self.root/'sources/esc-programme-2026/full.md').write_text('altered')
        result=self.stage();self.assertEqual(result.returncode,1);self.assertIn('hash mismatch',result.stderr);self.assert_no_mutations()

    def test_failure_before_commit_and_discard_leave_active_map_and_history(self):
        self.state['fail']='page put';self.save_state()
        result=self.stage();self.assertEqual(result.returncode,1);self.assertIn('injected failure',result.stderr)
        self.assertFalse((self.root/'audits/candidate/candidate.json').exists())
        self.assertEqual(self.map.read_bytes(),self.before_map)
        subprocess.run([str(self.root/'scripts/lwc'),'changeset','discard','fixture'],cwd=self.root,check=True,capture_output=True)
        self.assertEqual(self.map.read_bytes(),self.before_map);self.assertEqual(self.history_path.read_bytes(),self.old_history)
        self.assertNotIn('changeset commit',[' '.join(c['args'][:2]) for c in self.read_state()['calls']])

    def test_esc_and_playbook_exact_sets_stage_until_verified_commit(self):
        candidate=self.successful_stage();mapping=candidate['mapping']
        staged=self.read_state()['draft']['pages']
        self.assertEqual(staged['esc30']['source_ids'],[mapping[k] for k in self.support['esc30']])
        self.assertEqual(staged['ka220-question-playbook']['source_ids'],[mapping[k] for k in self.support['ka220-question-playbook']])
        self.assertFalse(self.read_state().get('committed'))
        result=self.publish();self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(self.map.read_text()),mapping)
        self.assertEqual(self.read_state()['map_at_commit'],self.before_map.decode())
        receipt=json.loads((self.root/'audits/candidate/commit-receipt.json').read_text());self.assertEqual(receipt['status'],'committed')
        self.assertEqual((self.root/'audits/candidate/active-map-before.bytes').read_bytes(),self.before_map)
        self.assertEqual(self.history_path.read_bytes(),self.old_history)
        self.assertEqual(self.read_state()['history'][0],'immutable-original-version')
        calls=self.read_state()['calls'];commit=next(i for i,c in enumerate(calls) if c['args'][:2]==['changeset','commit'])
        for ident in mapping.values():
            self.assertTrue(any(c['draft'] is None and c['args']==['source','show',str(ident)] for c in calls[commit+1:]))

    def test_commit_failure_keeps_active_map(self):
        self.successful_stage();self.read_state();self.state['fail']='changeset commit';self.save_state()
        result=self.publish();self.assertEqual(result.returncode,1);self.assertEqual(self.map.read_bytes(),self.before_map)
        self.assertFalse((self.root/'audits/candidate/commit-receipt.json').exists())

    def test_postcommit_live_identity_mismatch_keeps_old_map_and_receipt(self):
        candidate=self.successful_stage();self.read_state();self.state['corrupt_after_commit']=candidate['mapping']['esc-programme-2026'];self.save_state()
        result=self.publish();self.assertEqual(result.returncode,1);self.assertIn('live source mismatch',result.stderr)
        self.assertTrue(self.read_state()['committed']);self.assertEqual(self.map.read_bytes(),self.before_map)
        self.assertTrue((self.root/'audits/candidate/commit-receipt.json').exists())

    def test_candidate_hash_mismatch_refuses_commit(self):
        self.successful_stage();path=self.root/'audits/candidate/candidate.json'
        result=self.invoke('publish-map','--candidate','audits/candidate/candidate.json','--expected-candidate-sha256','0'*64)
        self.assertEqual(result.returncode,1);self.assertIn('Candidate hash',result.stderr);self.assertFalse(self.read_state().get('committed'))

    def test_active_map_changed_after_stage_refuses_commit(self):
        self.successful_stage();self.map.write_text('{"programme-2026":999}')
        result=self.publish();self.assertEqual(result.returncode,1);self.assertIn('Active map changed',result.stderr)
        self.assertFalse(self.read_state().get('committed'));self.assertEqual(self.map.read_text(),'{"programme-2026":999}')

    def test_live_source_identity_mismatch_refuses_stage_before_mutations(self):
        self.state['live']['sources']['1']['content']='wrong historical identity'
        self.state['draft']=json.loads(json.dumps(self.state['live']));self.save_state()
        result=self.stage();self.assertEqual(result.returncode,1);self.assertIn('Active source identity differs',result.stderr);self.assert_no_mutations()

    def test_changed_draft_refuses_commit(self):
        self.successful_stage();self.read_state();self.state['draft']['pages']['esc30']['source_ids']=[1,2];self.save_state()
        result=self.publish();self.assertEqual(result.returncode,1);self.assertIn('pages changed',result.stderr);self.assertFalse(self.read_state().get('committed'))

    def test_live_richer_page_blocks_before_writes(self):
        page={'slug':'esc30','body':'# Richer maintained live content\n','source_ids':[90,91],'provenance':['reviewed-by-agent'],'title':'Live'}
        self.state['live']['pages']['esc30']=page;self.state['draft']=json.loads(json.dumps(self.state['live']));self.save_state()
        result=self.stage();self.assertEqual(result.returncode,1);self.assertIn('Enriched',result.stderr);self.assert_no_mutations()
        self.assertEqual(self.read_state()['live']['pages']['esc30'],page)

    def test_identical_existing_page_preserves_complete_evidence_metadata_history(self):
        # Use all pre-existing source identities, including the playbook template.
        mapping={s['id']:i+1 for i,s in enumerate(self.sources)}
        self.map.write_text(json.dumps(mapping));self.before_map=self.map.read_bytes()
        self.state['live']['sources']={str(v):{'id':v,'content':(self.root/'sources'/k/'full.md').read_text(),'title':k} for k,v in mapping.items()}
        self.state['live']['jobs']={str(v):'completed' for v in mapping.values()}
        original={'slug':'ka220-question-playbook','body':(self.root/'wiki/templates/ka220-question-playbook.md').read_text(),'source_ids':[mapping[k] for k in self.support['ka220-question-playbook']],'title':'Original curated title','summary':'Original reviewed summary','provenance':['source-grounded','reviewed-agent','exact-template-records'],'created_at':'frozen-old-created','updated_at':'frozen-old-updated','links':['exact-historical-link']}
        self.state['live']['pages']['ka220-question-playbook']=original
        self.state['live']['pages']['untargeted-rich-page']={'slug':'untargeted-rich-page','body':'Kept intact','source_ids':[1],'provenance':['historical-curation']}
        self.state['draft']=json.loads(json.dumps(self.state['live']));self.save_state()
        self.successful_stage();result=self.publish();self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(self.read_state()['live']['pages']['ka220-question-playbook'],original)
        self.assertNotIn('ka220-question-playbook',self.read_state()['history'])
        self.assertEqual(self.read_state()['live']['pages']['untargeted-rich-page']['body'],'Kept intact')
        self.assertEqual(self.history_path.read_bytes(),self.old_history)

    def test_incomplete_playbook_set_refused(self):
        (self.root/'wiki/templates/ka220-question-playbook.md').write_text('# Playbook\n')
        self.support['ka220-question-playbook']=['programme-2026','expert-2026'];self.write_manifest()
        result=self.stage();self.assertEqual(result.returncode,1);self.assertIn('playbook evidence',result.stderr);self.assert_no_mutations()

    def test_blocking_lint_never_produces_publishable_candidate(self):
        self.state['lint_blocking']=1;self.save_state()
        result=self.stage();self.assertEqual(result.returncode,1);self.assertIn('lint',result.stderr)
        self.assertFalse((self.root/'audits/candidate/candidate.json').exists());self.assertEqual(self.map.read_bytes(),self.before_map)

    def test_symlink_public_page_refused_before_cli(self):
        path=self.root/'wiki/actions/esc30.md';payload=path.read_text();path.unlink()
        outside=self.root/'symlink-target.md';outside.write_text(payload);path.symlink_to(outside)
        result=self.stage();self.assertEqual(result.returncode,1);self.assertIn('Symlink',result.stderr);self.assert_no_mutations()


if __name__ == '__main__':
    unittest.main()
