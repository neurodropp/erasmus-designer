"""Negative/positive regression fixtures; all reports and spawns are SYNTHETIC."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
import test_workflow as loop
import stage_gate as gate
import checklist
import workflow

class OrchestrationRepairTests(unittest.TestCase):
    setUp=loop.LoopTests.setUp
    tearDown=loop.LoopTests.tearDown
    state=loop.LoopTests.state
    record=loop.LoopTests.record
    _record_fixture=loop.LoopTests._record_fixture
    run_cli=loop.LoopTests.run_cli
    freeze_draft=loop.LoopTests.freeze_draft
    def hashes(self):
        return {str(p.relative_to(self.path)):gate.digest(p) for p in self.path.rglob('*') if p.is_file() and not p.is_symlink()}
    def change_report(self):
        f=self.path/'reports/change.json';f.write_text(json.dumps(dict(summary='SYNTHETIC mutation request',reason='SYNTHETIC verified change',evidence=[dict(source_id='programme-2026',locator='SYNTHETIC')])));return f
    def test_invalidate_cannot_skip_any_unreached_phase(self):
        r=self.change_report();before=self.hashes()
        for phase in ['eligibility','design','draft']:
            with self.subTest(phase=phase),self.assertRaisesRegex(ValueError,'already reached'):
                self.run_cli('invalidate',self.path.name,'--phase',phase,'--report',str(r))
            self.assertEqual(self.hashes(),before)
    def test_all_integrated_forward_targets_fail_without_mutations(self):
        self.run_cli('init','integrated-synthetic','--action','KA220','--sector','YOU')
        path=workflow.project('integrated-synthetic');report=path/'reports/change.json';report.write_text(json.dumps(dict(summary='SYNTHETIC',reason='SYNTHETIC forward jump',evidence=[dict(source_id='programme-2026',locator='SYNTHETIC')],critical_review=dict(weaknesses=['SYNTHETIC'],alternative='SYNTHETIC',decision_basis='SYNTHETIC'))))
        before={str(p.relative_to(path)):gate.digest(p) for p in path.rglob('*') if p.is_file()}
        for phase in workflow.INTEGRATED[:workflow.INTEGRATED.index('review')]:
            with self.subTest(phase=phase),self.assertRaisesRegex(ValueError,'already reached'):
                self.run_cli('invalidate',path.name,'--phase',phase,'--report',str(report))
            self.assertEqual(before,{str(p.relative_to(path)):gate.digest(p) for p in path.rglob('*') if p.is_file()})
    def test_production_revise_can_retry_with_new_product(self):
        self.record('eligibility','needs-revision')
        self.assertEqual(self.state()['next_phase'],'eligibility')
        self.assertEqual(self.state()['validator_sessions'][0]['verdict'],'revise')
        (self.path/'stages/eligibility/product.md').write_text('SYNTHETIC distinct revised eligibility result')
        self.record('eligibility',product_text='SYNTHETIC distinct accepted result');self.assertEqual(self.state()['next_phase'],'design')

    def test_legitimate_rewind_preserves_budget_and_receipt_bytes(self):
        self.record('eligibility');self.record('design')
        s=self.state();s['revisions']=1;(self.path/'state.json').write_text(json.dumps(s));r=self.change_report()
        archives={x['path']:x['sha256'] for x in s['receipts']};dispatches=list((self.path/'validation/dispatches').glob('*.json'))
        self.run_cli('invalidate',self.path.name,'--phase','design','--report',str(r))
        self.assertEqual(self.state()['revisions'],1);self.assertEqual(self.state()['next_phase'],'design')
        self.assertEqual(len(list((self.path/'validation/dispatches').glob('*.json'))),len(dispatches))
        for p,h in archives.items():self.assertEqual(gate.digest(self.root/p),h)
    def test_rejected_product_is_editable_and_not_a_dependency(self):
        self.record('eligibility','blocked',blockers=['SYNTHETIC missing datum'])
        old=self.state()['validator_sessions'][0];_,packet=gate.packet(self.path,old['packet_id']);snapshot=self.path/packet['files'][0]['snapshot'];expected=gate.digest(snapshot)
        product=self.path/'stages/eligibility/product.md';product.write_text('SYNTHETIC new participant evidence resolves blocked phase')
        report=self.path/'reports/new.json';report.write_text(json.dumps(dict(summary='SYNTHETIC new data',status='pass',evidence=[])))
        with patch.object(gate,'route_evidence',return_value=[product]):m=gate.prepare(self.root,self.path,self.state(),'eligibility',report,['test-producer'])
        self.assertFalse(any(x['role']=='dependency-product' for x in m['files']))
        self.assertEqual(gate.digest(snapshot),expected)
        self.record('eligibility',product_text='SYNTHETIC distinct accepted result');self.assertEqual(self.state()['next_phase'],'design')
        self.assertEqual(len(list((self.path/'validation/dispatches').glob('*.json'))),2)
    def test_review_changes_after_real_product_repair(self):
        self.freeze_draft();self.record('review','needs-revision',draft_sha256=self.state()['draft_sha256'])
        before=self.state();old=before['validator_sessions'][-1];_,m=gate.packet(self.path,old['packet_id']);old_snapshot=self.path/m['files'][0]['snapshot'];old_hash=gate.digest(old_snapshot)
        (self.path/'draft.md').write_text('SYNTHETIC genuinely different repaired draft')
        self.record('repair')
        product=self.path/'stages/review/product.md';product.write_text('SYNTHETIC review 2 on changed draft, with new findings')
        report=self.path/'reports/new-review.json';report.write_text(json.dumps(dict(status='pass',summary='SYNTHETIC review 2',evidence=[])))
        with patch.object(gate,'route_evidence',return_value=[product]):new=gate.prepare(self.root,self.path,self.state(),'review',report,['test-producer'])
        self.assertNotEqual(old_hash,gate.digest(product));self.assertEqual(old_hash,gate.digest(old_snapshot))
        self.assertEqual(self.state()['revisions'],1)
        self.assertFalse(any(f['role']=='dependency-product' and Path(f['original'])==old_snapshot.resolve() for f in new['files']))
    def test_changed_observation_has_preserved_copy_and_changed_copy_fails(self):
        self.record('eligibility');s=self.state();session=s['validator_sessions'][0];dispatch=gate.read(self.path/'validation/dispatches'/f'{session["packet_id"]}.json')
        original=Path(dispatch['observation']);original.unlink();archive=self.path/dispatch['observation_archive']
        self.assertEqual(gate.digest(archive),dispatch['observation_sha256']);self.run_cli('status',self.path.name)
        archive.write_text('SYNTHETIC historical evidence tampered')
        with self.assertRaisesRegex(ValueError,'Dispatch observation archive changed'):self.run_cli('status',self.path.name)
    def test_output_and_input_symlinks_fail_without_any_write(self):
        for label in ['validation/packets','receipts','brief.md']:
            with self.subTest(label=label):
                target=self.path/label;outside=self.root/('outside-'+label.replace('/','-'));is_dir=target.is_dir()
                if is_dir:target.rmdir();outside.mkdir()
                else:target.unlink();outside.write_text('SYNTHETIC unrelated dossier')
                target.symlink_to(outside,target_is_directory=is_dir)
                before=self.hashes();outside_before={str(p):gate.digest(p) for p in outside.rglob('*') if p.is_file()} if is_dir else gate.digest(outside)
                with self.assertRaisesRegex(ValueError,'Symbolic'):
                    self.run_cli('status',self.path.name)
                self.assertEqual(self.hashes(),before)
                self.assertEqual(outside_before,{str(p):gate.digest(p) for p in outside.rglob('*') if p.is_file()} if is_dir else gate.digest(outside))
                target.unlink()
                if is_dir:target.mkdir()
                else:target.write_text('SYNTHETIC restored brief')
    def test_report_nested_types_are_enforced(self):
        schema=json.loads((gate.CATALOG_ROOT/'config/stage-validation-report.schema.json').read_text())
        good=dict(packet_id='fixture',packet_sha256='fixture',phase='eligibility',reviewer_id='fixture',verdict='blocked',summary='SYNTHETIC',checks=[dict(id='fixture',status='pass',reason='fixture',verification='fixture',evidence=[dict(file_id='file-0',locator='fixture')])],discrepancies=[],verification_limits=['SYNTHETIC'],missing_information=[],critical_review=dict(weaknesses=['fixture'],alternative='fixture',decision_basis='fixture'),automatic_checks=[])
        gate.validate_schema(good,schema)
        for field,value in [('summary',{}),('missing_information',[5]),('verification_limits',[{}]),('checks',[None]),('critical_review',dict(weaknesses='text',alternative=42,decision_basis='fixture'))]:
            bad=dict(good);bad[field]=value
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'structural contract'):gate.validate_schema(bad,schema)
    def test_stale_dispatch_does_not_consume_budget(self):
        self.record('eligibility');s=self.state();s['next_phase']='eligibility';(self.path/'state.json').write_text(json.dumps(s))
        product=self.path/'stages/eligibility/product.md';report=self.path/'eligibility.json'
        with patch.object(gate,'route_evidence',return_value=[product]):m=gate.prepare(self.root,self.path,self.state(),'eligibility',report,['test-producer'])
        s['next_phase']='design';(self.path/'state.json').write_text(json.dumps(s));obs=self.path/'sessions/stale.json';obs.write_text(json.dumps(dict(tool='collaboration.spawn_agent',request={'fork_turns':'none'},result={'task_name':'SYNTHETIC-stale'},packet_id=m['packet_id'])))
        before=self.hashes();count=len(list((self.path/'validation/dispatches').glob('*.json')))
        with self.assertRaisesRegex(ValueError,'stale dispatch'):gate.dispatch(self.path,self.state(),m['packet_id'],'SYNTHETIC-stale','SYNTHETIC-stale','none',obs)
        self.assertEqual(self.hashes(),before);self.assertEqual(len(list((self.path/'validation/dispatches').glob('*.json'))),count)

if __name__=='__main__':unittest.main()
