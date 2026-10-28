"""Synthetic protocol fixtures, never approval of a real dossier or user."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import human_approval as approval
import stage_gate

class HumanApprovalTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name).resolve();self.path=self.root/'projects/fixture--ka220-youth--2026';self.path.mkdir(parents=True)
        self.state={'id':self.path.name,'program':'ERASMUS','year':2026,'action':'KA220-YOU','sector':'YOU','next_phase':'ready-for-human-review','state':'ready-for-human-review','form_profile':'form.json','validator_sessions':[]}
        self.files=['project.json','answers.json','draft.md','evidence.json','annex-manifest.json']
        for name in self.files:(self.path/name).write_text('{}')
        (self.path/'original-form.pdf').write_text('Synthetic original form bytes')
        (self.path/'answers.json').write_text(json.dumps({'form_instance':{'verification_source':'fixture','form_source':{'path':'original-form.pdf','sha256':approval.digest(self.path/'original-form.pdf')}},'answers':[]}))
        (self.path/'annex-manifest.json').write_text(json.dumps({'annexes':[{'id':'budget','path':'budget.md'}]}));(self.path/'budget.md').write_text('Synthetic annex')
        (self.root/'form.json').write_text('{}')
        folder=self.path/'validation/packets/qa-fixture';folder.mkdir(parents=True)
        entries=[]
        for name in self.files+['budget.md']:
            original=self.path/name;entries.append({'role':'annex' if name=='budget.md' else 'project-input','original':str(original),'sha256':approval.digest(original)})
        entries.append({'role':'form-source','original':str(self.path/'original-form.pdf'),'sha256':approval.digest(self.path/'original-form.pdf')})
        entries.append({'role':'form-profile','original':str(self.root/'form.json'),'sha256':approval.digest(self.root/'form.json')})
        manifest={'phase':'qa','files':entries,'route':{k:self.state.get(k) for k in ('program','year','action','sector','country','agency','role','round')}};(folder/'manifest.json').write_text(json.dumps(manifest))
        self.state['validator_sessions']=[{'packet_id':'qa-fixture','verdict':'accept','report_sha256':'a'*64,'dispatch_sha256':'b'*64}]
        # Deliberately isolated from real gate attestations: this fixture tests binding.
        self.history=patch.object(stage_gate,'verify_history');self.history.start()
        self.save_state();self.source=self.path/'instruction.txt';self.source.write_text('SYNTHETIC USER: approvo questo bundle per handoff')
        current=approval.bundle(self.root,self.path,self.state)
        self.record={'schema_version':'observed-human-decision-v1','decision':'approve','project_id':self.path.name,'bundle_sha256':current['bundle_sha256'],'artifacts':current['artifacts'],'scope':current['scope'],'rights':['handoff'],'author':'synthetic-user','provenance':{'type':'user-instruction','reference':'synthetic-test','observed_by':'synthetic-coordinator'},'evidence':{'path':'instruction.txt','sha256':approval.digest(self.source),'locator':'line 1','quote':'approvo questo bundle per handoff','quote_authorized':True,'provenance':'user-instruction'}}
        self.input=self.path/'decision.json';self.write_record()
    def tearDown(self):self.history.stop();self.tmp.cleanup()
    def save_state(self):(self.path/'state.json').write_text(json.dumps(self.state))
    def write_record(self):self.input.write_text(json.dumps(self.record))
    def decide(self,kind='approve'):
        result=approval.decide(self.root,self.path,self.state,self.input,kind);self.save_state();return result
    def test_exact_approval_and_reject_are_history_preserving(self):
        receipt=self.decide();original=copy.deepcopy(receipt)
        self.assertEqual(self.state['state'],'human-approved');self.assertEqual(approval.status(self.root,self.path,self.state)['status'],'approve')
        self.record['decision']='reject';self.write_record();self.decide('reject')
        self.assertEqual(self.state['state'],'human-rejected');self.assertTrue(self.state['human_decisions'][0]['superseded'])
        self.assertEqual(approval.read(self.path/self.state['human_decisions'][0]['path']),original)
    def test_hash_scope_project_and_extra_artifacts_rejected(self):
        for field,value in [('bundle_sha256','c'*64),('scope','submit'),('rights',['submit']),('project_id','other'),('artifacts',{})]:
            with self.subTest(field=field):
                original=self.record[field];self.record[field]=value;self.write_record()
                with self.assertRaises(ValueError):self.decide()
                self.record[field]=original
        self.assertFalse((self.path/'approval').exists())
    def test_missing_or_superseded_qa_refuses_approval(self):
        for sessions in ([],[{**self.state['validator_sessions'][0],'superseded':True}]):
            with self.subTest(sessions=sessions):
                state={**self.state,'validator_sessions':sessions}
                with self.assertRaisesRegex(ValueError,'QA'):approval.bundle(self.root,self.path,state)
    def test_fake_source_missing_quote_and_unauthorized_quote_refused(self):
        for field,value in [('sha256','0'*64),('quote','missing'),('quote_authorized',False),('provenance','agent-analysis')]:
            original=self.record['evidence'][field];self.record['evidence'][field]=value;self.write_record()
            with self.subTest(field=field),self.assertRaises(ValueError):self.decide()
            self.record['evidence'][field]=original
        self.record['provenance']['type']='agent-analysis';self.write_record()
        with self.assertRaisesRegex(ValueError,'user-instruction'):self.decide()
    def test_bound_artifact_mutation_stales_without_rewriting_receipt(self):
        self.decide();item=self.state['human_decisions'][0];old=(self.path/item['path']).read_bytes()
        (self.path/'budget.md').write_text('changed')
        self.assertEqual(approval.status(self.root,self.path,self.state)['status'],'stale')
        approval.supersede(self.state,'changed')
        self.assertTrue(item['superseded']);self.assertEqual((self.path/item['path']).read_bytes(),old)
    def test_unlisted_extra_file_is_not_approved_and_does_not_expand_scope(self):
        self.decide();(self.path/'extra.pdf').write_text('not in QA')
        status=approval.status(self.root,self.path,self.state);self.assertEqual(status['status'],'approve')
        self.assertFalse(status['submission_authorized']);self.assertNotIn('extra.pdf',str(approval.read(self.path/self.state['human_decisions'][0]['path'])['bundle']['artifacts']))
    def test_archive_and_observation_tampering_are_detected(self):
        receipt=self.decide();(self.path/receipt['observation_archive']).write_text('tampered')
        with self.assertRaisesRegex(ValueError,'observation archive changed'):approval.status(self.root,self.path,self.state)
    def test_stale_state_cas_blocks_decision(self):
        (self.path/'state.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'CAS'):self.decide()
