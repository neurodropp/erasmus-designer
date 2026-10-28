import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import workflow
import stage_gate
import checklist

class LoopTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.root_patch=patch.object(workflow,'ROOT',self.root); self.root_patch.start()
        self.run_cli('init','demo','--action','KA220','--sector','ADU','--max-revisions','1','--process','compact')
        self.path=workflow.project('demo')
    def tearDown(self):
        self.root_patch.stop(); self.temp.cleanup()
    def run_cli(self,*args):
        with patch.object(sys,'argv',['workflow',*args]),contextlib.redirect_stdout(io.StringIO()):
            workflow.main()
    def state(self): return json.loads((self.path/'state.json').read_text())
    def record(self,phase,status='pass',**extra):
        # This helper exercises sequencing with incomplete synthetic models.
        # Real deterministic checker execution is covered separately.
        with patch.object(stage_gate,'rerun_automatic_checks',return_value=[]):
            return self._record_fixture(phase,status,**extra)
    def _record_fixture(self,phase,status='pass',**extra):
        product_text=extra.pop('product_text','Synthetic step product.')
        report={'status':status,'summary':'Test localized evidence contract',
                'evidence':[{'source_id':'programme-2026','locator':'PDF p. 242'}],**extra}
        f=self.path/f'{phase}.json'; f.write_text(json.dumps(report))
        # Synthetic protocol fixtures, not a claim of an actual LLM review.
        evidence=self.path/'test-evidence.md';evidence.write_text('Synthetic observed input for integrity tests.')
        product=self.path/'stages'/phase/'product.md';product.parent.mkdir(parents=True,exist_ok=True);product.write_text(product_text)
        report['evidence'][0]['path']=str(evidence);f.write_text(json.dumps(report))
        if not (self.path/f'research/checklist-{phase}.json').exists():checklist.initialize(self.root,self.path.name,phase)
        with patch.object(stage_gate,'route_evidence',return_value=[evidence]):
            m=stage_gate.prepare(self.root,self.path,self.state(),phase,f,['test-producer'])
        ident=m['packet_id']; reviewer='test-reviewer-'+ident
        observation=self.path/'sessions'/f'{ident}.json'; observation.write_text(json.dumps({'tool':'collaboration.spawn_agent','request':{'fork_turns':'none'},'result':{'task_name':reviewer},'packet_id':ident}))
        stage_gate.dispatch(self.path,self.state(),ident,reviewer,reviewer,'none',observation)
        mp=self.path/'validation/packets'/ident/'manifest.json'
        validation=self.path/'validation/reports'/f'{ident}.json';validation.write_text(json.dumps({'packet_id':ident,'packet_sha256':stage_gate.digest(mp),'phase':phase,'reviewer_id':reviewer,'verdict':'accept' if status=='pass' else 'blocked' if status=='blocked' else 'revise','summary':'Synthetic complete contract review','discrepancies':[],
            'verification_limits':['Synthetic protocol test, not actual LLM validation'],'missing_information':[],'critical_review':{'weaknesses':['Synthetic fixture limitation'],'alternative':'fixture','decision_basis':'contract test'},
            'automatic_checks':[{'id':i,'status':'pass','reason':'Synthetic test result','command':'synthetic test fixture','result':{'synthetic':True},'evidence':[{'file_id':'file-0','locator':'fixture'}]} for i in m['automatic_checks_expected']],
            'checks':[{'id':c['id'],'status':'pass','verification':'Synthetic contract test','reason':'Synthetic protocol acceptance','evidence':[{'file_id':m['files'][0]['id'],'locator':'test fixture'}]} for c in m['acceptance_checks']+m['compliance_checks']]}))
        self.run_cli('record','demo','--phase',phase,'--report',str(f),'--validation-packet',ident,'--validation-report',str(validation))
    def freeze_draft(self):
        self.record('eligibility'); self.record('design')
        (self.path/'draft.md').write_text('Draft version one')
        self.record('draft')
        return self.state()['draft_sha256']
    def test_blocked_phase_does_not_advance(self):
        self.record('eligibility','blocked',blockers=['Missing confirmed partner'])
        self.assertEqual(self.state()['next_phase'],'eligibility')
        with self.assertRaises(ValueError): self.record('eligibility',blockers=['Missing partner'])
    def test_review_rejects_changed_draft_even_with_new_hash(self):
        self.freeze_draft()
        (self.path/'draft.md').write_text('Changed without the repair phase')
        with self.assertRaisesRegex(ValueError,'prior phase freeze'):
            self.record('review',draft_sha256=workflow.digest(self.path/'draft.md'))
        self.assertEqual(self.state()['next_phase'],'review')
    def test_qa_cannot_close_unverified_major_finding(self):
        frozen=self.freeze_draft(); self.record('review',draft_sha256=frozen)
        (self.path/'findings.json').write_text(json.dumps([{'severity':'major','status':'open'}]))
        with self.assertRaisesRegex(ValueError,'Unverified'):
            self.record('qa',draft_sha256=frozen)
        (self.path/'findings.json').write_text(json.dumps([{'severity':'major','status':'verified'}]))
        self.record('qa',draft_sha256=frozen)
        self.assertEqual(self.state()['state'],'ready-for-human-review')
    def test_revision_limit_stops_an_endless_loop(self):
        frozen=self.freeze_draft(); self.record('review','needs-revision',draft_sha256=frozen)
        (self.path/'draft.md').write_text('Repaired draft'); self.record('repair')
        self.record('review','needs-revision',draft_sha256=self.state()['draft_sha256'])
        self.assertEqual(self.state()['state'],'revision-limit-reached')
        with self.assertRaisesRegex(ValueError,'Revision limit'):
            self.record('repair')
    def test_unknown_evidence_cannot_be_used_without_provenance(self):
        with self.assertRaisesRegex(ValueError,'Unknown source'):
            self.record('eligibility',evidence=[{'source_id':'invented','locator':'somewhere'}])
    def test_invalid_phase_sequence_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'Expected phase'):
            self.record('design')
    def test_receipts_preserve_old_report_after_source_file_changes(self):
        self.record('eligibility','blocked',blockers=['Missing partner'])
        receipt=self.state()['receipts'][0]; archived=self.root/receipt['path']
        self.record('eligibility')
        self.assertEqual(workflow.digest(archived),receipt['sha256'])

class IntegratedLoopTests(LoopTests):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
        self.root_patch=patch.object(workflow,'ROOT',self.root); self.root_patch.start()
        profile=self.root/'form.json'; profile.write_text(json.dumps({'questions':[{'id':'Q1','kind':'text','max_chars':100}]}))
        self.run_cli('init','demo','--action','KA220','--sector','ADU','--max-revisions','1','--form-profile','form.json')
        self.path=workflow.project('demo')
        (self.path/'answers.json').write_text(json.dumps({'form_instance':{},'answers':[{'question_id':'Q1','text':'Frozen text'}]}))
    def record(self,phase,status='pass',**extra):
        return super().record(phase,status,critical_review={'weaknesses':['Missing local evidence'],
                           'alternative':'Narrow the scope','decision_basis':'Actual evidence review'},**extra)
    # Integrated phases have their own sequence; do not inherit compact tests.
    test_blocked_phase_does_not_advance=None
    test_review_rejects_changed_draft_even_with_new_hash=None
    test_qa_cannot_close_unverified_major_finding=None
    test_revision_limit_stops_an_endless_loop=None
    test_unknown_evidence_cannot_be_used_without_provenance=None
    test_invalid_phase_sequence_is_rejected=None
    test_receipts_preserve_old_report_after_source_file_changes=None
    def test_critical_review_is_required_in_every_phase(self):
        with self.assertRaisesRegex(ValueError,'critical_review'):
            LoopTests.record(self,'idea-validation')
        self.record('idea-validation')
        self.assertEqual(self.state()['next_phase'],'needs-impact-research')
    def test_bundle_detects_changed_annex(self):
        for phase in workflow.INTEGRATED[:workflow.INTEGRATED.index('application-draft')]: self.record(phase)
        (self.path/'draft.md').write_text('Frozen text'); self.record('application-draft')
        annex=self.path/'annexes/budget.md'; annex.write_text('Budget version one')
        (self.path/'annex-manifest.json').write_text(json.dumps({'annexes':[{'id':'budget','path':'annexes/budget.md'}]}))
        self.record('annexes'); annex.write_text('Budget version two')
        with self.assertRaisesRegex(ValueError,'bundle freeze'):
            self.record('review',draft_sha256=self.state()['draft_sha256'])
    def test_invalidation_reopens_affected_phase_without_resetting_limit(self):
        self.record('idea-validation'); s=self.state(); s['revisions']=1; (self.path/'state.json').write_text(json.dumps(s))
        report=self.path/'change.json'; report.write_text(json.dumps({'summary':'New evidence changes initial choice','reason':'Changed needs evidence',
                'evidence':[{'source_id':'programme-2026','locator':'PDF p. 236'}],
                'critical_review':{'weaknesses':['Original design no longer justified'],'alternative':'Narrow the idea','decision_basis':'Updated evidence'}}))
        self.run_cli('invalidate','demo','--phase','idea-validation','--report',str(report))
        self.assertEqual(self.state()['next_phase'],'idea-validation'); self.assertEqual(self.state()['revisions'],1)
    def test_frozen_profile_changes_are_detected(self):
        for phase in workflow.INTEGRATED[:workflow.INTEGRATED.index('application-draft')]: self.record(phase)
        (self.path/'draft.md').write_text('Frozen text'); self.record('application-draft'); self.record('annexes')
        (self.root/'form.json').write_text(json.dumps({'questions':[{'id':'Q1','kind':'text','max_chars':200}]}))
        with self.assertRaisesRegex(ValueError,'profile changed'):
            self.record('review',draft_sha256=self.state()['draft_sha256'])
    def test_archived_receipt_tampering_is_detected(self):
        self.record('idea-validation'); archive=self.root/self.state()['receipts'][0]['path']; archive.write_text('{}')
        with self.assertRaisesRegex(ValueError,'receipt'):
            self.run_cli('status','demo')
    def test_erasmus_form_cannot_be_bound_to_esc(self):
        profile=self.root/'erasmus-form.json'; profile.write_text(json.dumps({'programme':'ERASMUS','action_family':'KA220','questions':[{'id':'Q1','kind':'text','max_chars':100}]}))
        with self.assertRaisesRegex(ValueError,'programme'):
            self.run_cli('init','esc-demo','--action','ESC30','--sector','ESC','--form-profile','erasmus-form.json')

if __name__=='__main__': unittest.main()
