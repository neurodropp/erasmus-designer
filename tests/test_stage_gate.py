import contextlib
import io
import json
import multiprocessing
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import stage_gate as gate
import workflow
import checklist


def concurrent_dispatch(path,packet_id,observation,agent,queue):
    """Synthetic process fixture; no real runtime spawn attestation."""
    try:
        path=Path(path);state=json.loads((path/'state.json').read_text())
        gate.dispatch(path,state,packet_id,agent,agent,'none',Path(observation));queue.put('dispatched')
    except ValueError as error:queue.put(str(error))

class StageGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.root_patch=patch.object(workflow,'ROOT',self.root);self.root_patch.start()
        self.cli('init','demo','--action','KA220','--sector','YOU')
        self.path=workflow.project('demo');self.product=self.path/'stages/idea-validation/product.md';self.product.parent.mkdir(parents=True,exist_ok=True);self.product.write_text('Synthetic product, not a real concept.')
        self.report=self.path/'reports/production.json';self.report.write_text(json.dumps({'status':'pass','summary':'Synthetic gate fixture','evidence':[{'source_id':'programme-2026','locator':'fixture','path':str(self.product)}],'critical_review':{'weaknesses':['Synthetic missing evidence'],'alternative':'narrow scope','decision_basis':'fixture'}}))
        checklist.initialize(self.root,self.path.name,'idea-validation')
        checklist.initialize(self.root,self.path.name,'needs-impact-research')
        checklist.initialize(self.root,self.path.name,'repair')
        with patch.object(gate,'route_evidence',return_value=[self.product]):self.m=gate.prepare(self.root,self.path,self.state(),'idea-validation',self.report,['producer'])
        self.ident=self.m['packet_id'];self.obs=self.path/'sessions/spawn.json';self.observation('fresh-reviewer');gate.dispatch(self.path,self.state(),self.ident,'fresh-reviewer','fresh-reviewer','none',self.obs)
        self.review=self.path/'validation/reports/review.json';self.r={'packet_id':self.ident,'packet_sha256':gate.digest(self.path/'validation/packets'/self.ident/'manifest.json'),'phase':'idea-validation','reviewer_id':'fresh-reviewer','verdict':'accept','summary':'Synthetic contract verification','discrepancies':[],'checks':[{'id':c['id'],'status':'pass','reason':'Synthetic acceptance','evidence':[{'file_id':'file-0','locator':'fixture'}]} for c in self.m['acceptance_checks']+self.m['compliance_checks']]};self.save_review()
        self.r.update(verification_limits=['Synthetic contract test'],missing_information=[],critical_review={'weaknesses':['Synthetic fixture'],'alternative':'fixture','decision_basis':'test'},automatic_checks=[])
        for c in self.r['checks']:c['verification']='Synthetic verification'
        self.save_review()
    def tearDown(self):self.root_patch.stop();self.tmp.cleanup()
    def cli(self,*args):
        with patch.object(sys,'argv',['workflow',*args]),contextlib.redirect_stdout(io.StringIO()):workflow.main()
    def state(self):return json.loads((self.path/'state.json').read_text())
    def observation(self,agent):self.obs.write_text(json.dumps({'tool':'collaboration.spawn_agent','request':{'fork_turns':'none'},'result':{'task_name':agent},'packet_id':self.ident}))
    def save_review(self):self.review.write_text(json.dumps(self.r))
    def verify(self):return gate.verify(self.root,self.path,self.state(),self.ident,self.review,self.report)


    def test_concurrent_dispatch_cannot_overspend_budget(self):
        state=self.state();state['max_validation_attempts']=2;(self.path/'state.json').write_text(json.dumps(state))
        with patch.object(gate,'route_evidence',return_value=[self.product]):
            packets=[gate.prepare(self.root,self.path,state,'idea-validation',self.report,['producer']) for _ in range(2)]
        context=multiprocessing.get_context('spawn');queue=context.Queue();processes=[]
        for number,m in enumerate(packets):
            agent=f'race-{number}';obs=self.path/f'sessions/race-{number}.json'
            obs.write_text(json.dumps({'tool':'collaboration.spawn_agent','request':{'fork_turns':'none'},'result':{'task_name':agent},'packet_id':m['packet_id']}))
            processes.append(context.Process(target=concurrent_dispatch,args=(str(self.path),m['packet_id'],str(obs),agent,queue)))
        for process in processes:process.start()
        for process in processes:process.join(10);self.assertFalse(process.is_alive())
        outcomes=[queue.get(timeout=2) for _ in processes]
        self.assertEqual(outcomes.count('dispatched'),1)
        self.assertEqual(len(list((self.path/'validation/dispatches').glob('*.json'))),2)
        self.assertTrue(any('attempt limit' in result or 'writer' in result for result in outcomes))

    def test_observed_interrupt_preserves_dispatch_identity_and_budget(self):
        before=(self.path/'validation/dispatches'/f'{self.ident}.json').read_bytes()
        observation=self.path/'sessions/interrupt.json'
        observation.write_text(json.dumps({'tool':'collaboration.interrupt_agent','request':{'target':'fresh-reviewer'},'result':{'previous_status':'running'}}))
        result=gate.recover_dispatch(self.path,self.state(),self.ident,'interrupted',observation,'Synthetic interrupt fixture')
        self.assertEqual(result['status'],'interrupted');self.assertTrue(result['budget_consumed']);self.assertTrue(result['identity_reserved'])
        self.assertEqual((self.path/'validation/dispatches'/f'{self.ident}.json').read_bytes(),before)
        with self.assertRaisesRegex(ValueError,'Terminal dispatch'):self.verify()
        with self.assertRaisesRegex(ValueError,'pending dispatch'):gate.recover_dispatch(self.path,self.state(),self.ident,'cancelled',observation,'again')
        with patch.object(gate,'route_evidence',return_value=[self.product]):m=gate.prepare(self.root,self.path,self.state(),'idea-validation',self.report,['producer'])
        obs=self.path/'sessions/reused.json';obs.write_text(json.dumps({'tool':'collaboration.spawn_agent','request':{'fork_turns':'none'},'result':{'task_name':'fresh-reviewer'},'packet_id':m['packet_id']}))
        with self.assertRaisesRegex(ValueError,'already dispatched'):gate.dispatch(self.path,self.state(),m['packet_id'],'fresh-reviewer','fresh-reviewer','none',obs)

    def test_terminal_lifecycle_deletion_is_detected_against_state_anchor(self):
        observation=self.path/'sessions/interruption.json'
        observation.write_text(json.dumps({'tool':'collaboration.interrupt_agent','request':{'target':'fresh-reviewer'},'result':{'previous_status':'running'}}))
        gate.recover_dispatch(self.path,self.state(),self.ident,'cancelled',observation,'Synthetic observed cancellation')
        (self.path/'validation/lifecycle'/self.ident/'0001.json').unlink()
        with self.assertRaisesRegex(ValueError,'terminal anchor'):gate.dispatch_lifecycle(self.path,self.ident)
    def test_recovery_never_resets_attempt_limit(self):
        state=self.state();state['max_validation_attempts']=1;(self.path/'state.json').write_text(json.dumps(state))
        observation=self.path/'sessions/interruption.json'
        observation.write_text(json.dumps({'tool':'collaboration.interrupt_agent','request':{'target':'fresh-reviewer'},'result':{'previous_status':'running'}}))
        gate.recover_dispatch(self.path,state,self.ident,'cancelled',observation,'Synthetic observed cancellation')
        with self.assertRaisesRegex(ValueError,'attempt limit'):gate.prepare(self.root,self.path,self.state(),'idea-validation',self.report,['producer'])

    def test_cancel_requires_matching_observed_tool_source(self):
        obs=self.path/'sessions/cancel.json';obs.write_text(json.dumps({'tool':'user-note','request':{'target':'fresh-reviewer'},'result':{'status':'cancelled'}}))
        with self.assertRaisesRegex(ValueError,'observed interrupt'):gate.recover_dispatch(self.path,self.state(),self.ident,'cancelled',obs,'Synthetic request is not observed action')
    def test_allowlisted_checker_reruns_and_never_executes_report_shell(self):
        manifest={'automatic_checks_expected':['answer-characters'],'phase':'application-draft'}
        result=gate.rerun_automatic_checks(self.root,self.path,self.state(),manifest)
        self.assertFalse(result[0]['result']['passed'])
        with self.assertRaisesRegex(ValueError,'Unsupported automatic'):gate.rerun_automatic_checks(self.root,self.path,self.state(),{'automatic_checks_expected':['shell-touch'],'phase':'qa'})
        manifest={'automatic_checks_expected':['project-model'],'phase':'qa'}
        actual=gate.rerun_automatic_checks(self.root,self.path,self.state(),manifest)
        self.assertFalse(actual[0]['result']['passed'])
        profile=self.root/'valid-profile.json';profile.write_text(json.dumps({'questions':[{'id':'Q1','kind':'text','max_chars':3}]}))
        (self.path/'answers.json').write_text(json.dumps({'form_instance':{},'answers':[{'question_id':'Q1','text':'abc'}]}))
        state={**self.state(),'form_profile':'valid-profile.json'}
        passed=gate.rerun_automatic_checks(self.root,self.path,state,{'automatic_checks_expected':['answer-characters'],'phase':'application-draft'})
        self.assertTrue(passed[0]['result']['passed'])
    def test_wrong_declared_pass_cannot_override_actual_checker(self):
        # Existing packet fixture has no automatic checks; switch expectation only
        # in memory to exercise verifier after immutable packet hashes are resolved.
        original=gate.packet
        def augmented(path,ident):
            mp,m=original(path,ident);m['automatic_checks_expected']=['answer-characters'];return mp,m
        marker=self.path/'untrusted-never-executed'
        self.r['automatic_checks']=[{'id':'answer-characters','status':'pass','reason':'Synthetic false pass','command':'touch '+str(marker),'result':{'passed':True},'evidence':[{'file_id':'file-0','locator':'fixture'}]}];self.save_review()
        with patch.object(gate,'packet',side_effect=augmented),self.assertRaisesRegex(ValueError,'Deterministic automatic checks failed'):self.verify()
        self.assertFalse(marker.exists())
    def test_gate_api_state_cas_refuses_stale_caller(self):
        s=self.state();s['state']='unpersisted'
        with self.assertRaisesRegex(ValueError,'CAS'):gate.dispatch(self.path,s,self.ident,'other','other','none',self.obs)

    def test_complete_fresh_review_advances_and_archives(self):
        self.cli('record','demo','--phase','idea-validation','--report',str(self.report),'--validation-packet',self.ident,'--validation-report',str(self.review))
        self.assertEqual(self.state()['next_phase'],'needs-impact-research');self.assertEqual(len(self.state()['validator_sessions']),1)
        self.review.write_text('Changed external original after archiving');workflow.verify_receipts(self.state(),self.path)
    def test_workflow_cannot_advance_without_independent_gate(self):
        with self.assertRaisesRegex(ValueError,'fresh independent'):self.cli('record','demo','--phase','idea-validation','--report',str(self.report))
    def test_project_extension_is_frozen_and_assessed_by_validator(self):
        f=self.path/'research/checklist-idea-validation.json'; data=json.loads(f.read_text())
        data['extensions']=[dict(check_id='project-fixture-extra',classification='requirement',check='Synthetic scoped rule',applicability='Fixture only',scope=data['scope'],sources=[{'source_id':'fixture','path':str(self.product),'locator':'paragraph 1'}],**checklist.outcome())]
        data['extensions'][0]['owner']='fixture-owner';f.write_text(json.dumps(data))
        with patch.object(gate,'route_evidence',return_value=[self.product]):m=gate.prepare(self.root,self.path,self.state(),'idea-validation',self.report,['producer'])
        self.assertIn('project-fixture-extra',{c['id'] for c in m['compliance_checks']})
        self.assertTrue(any(row['role']=='project-checklist' for row in m['files']))
        self.assertTrue(any(row['role']=='action-mode-controls' for row in m['files']))
    def test_new_project_requires_its_phase_checklist(self):
        (self.path/'research/checklist-idea-validation.json').unlink()
        with patch.object(gate,'route_evidence',return_value=[self.product]),self.assertRaisesRegex(ValueError,'Missing file'):
            gate.prepare(self.root,self.path,self.state(),'idea-validation',self.report,['producer'])
    def test_online_checklist_proof_must_have_local_snapshot(self):
        f=self.path/'research/checklist-idea-validation.json';data=json.loads(f.read_text())
        data['checks'][0].update(status='not-applicable',owner='fixture',reason='Scoped fixture',evidence=[dict(source_id='web-fixture',url='https://example.org/proof',locator='section',version='fixture',verified_at='2026-09-12')])
        f.write_text(json.dumps(data))
        with patch.object(gate,'route_evidence',return_value=[self.product]),self.assertRaisesRegex(ValueError,'local_snapshot'):
            gate.prepare(self.root,self.path,self.state(),'idea-validation',self.report,['producer'])
    def test_final_validator_cannot_skip_current_form_check(self):
        state=self.state();state['next_phase']='qa';(self.path/'state.json').write_text(json.dumps(state))
        checklist.initialize(self.root,self.path.name,'qa')
        product=self.path/'stages/qa/product.md';product.write_text('Synthetic QA product')
        with patch.object(gate,'route_evidence',return_value=[product]):m=gate.prepare(self.root,self.path,state,'qa',self.report,['producer'])
        self.ident=m['packet_id'];self.obs=self.path/'sessions/qa.json';self.observation('qa-fresh')
        gate.dispatch(self.path,state,self.ident,'qa-fresh','qa-fresh','none',self.obs)
        self.r.update(packet_id=self.ident,packet_sha256=gate.digest(self.path/'validation/packets'/self.ident/'manifest.json'),phase='qa',reviewer_id='qa-fresh',checks=[dict(id=c['id'],status='not-applicable' if c['id']=='shared-form' else 'pass',reason='Synthetic test',verification='Synthetic test',evidence=[dict(file_id='file-0',locator='fixture')]) for c in m['acceptance_checks']+m['compliance_checks']])
        self.save_review()
        with self.assertRaisesRegex(ValueError,'cannot be skipped'):gate.verify(self.root,self.path,state,self.ident,self.review,self.report)
    def test_changed_product_invalidates_review(self):
        self.product.write_text('Mutated after freeze')
        with self.assertRaisesRegex(ValueError,'changed'):self.verify()
    def test_working_memory_is_frozen_and_changes_require_a_new_review(self):
        from project_memory import ProjectMemory
        memory=ProjectMemory(self.root,self.path.name)
        memory.initialize()
        with patch.object(gate,'route_evidence',return_value=[self.product]):
            m=gate.prepare(self.root,self.path,self.state(),'idea-validation',self.report,['producer'])
        captured=[f for f in m['files'] if f['role']=='working-memory']
        self.assertEqual({Path(f['original']).name for f in captured},{'events.jsonl','seal.json','context.md'})
        for f in captured:self.assertEqual(gate.digest(self.path/f['snapshot']),f['sha256'])
        self.ident=m['packet_id'];self.obs=self.path/'sessions/memory-review.json';self.observation('memory-fresh')
        gate.dispatch(self.path,self.state(),self.ident,'memory-fresh','memory-fresh','none',self.obs)
        self.r.update(packet_id=self.ident,packet_sha256=gate.digest(self.path/'validation/packets'/self.ident/'manifest.json'),reviewer_id='memory-fresh')
        self.save_review()
        memory.record({'kind':'decision','status':'proposed','title':'New scope proposal','summary':'A new unapproved decision after freezing','author':'fixture','provenance':{'type':'agent-observed','reference':'synthetic test'},'evidence':[]})
        with self.assertRaisesRegex(ValueError,'changed'):self.verify()
    def test_incoherent_working_memory_prevents_packet_creation(self):
        from project_memory import ProjectMemory
        memory=ProjectMemory(self.root,self.path.name);memory.initialize()
        (self.path/'memory/context.md').write_text('Incorrect derived context')
        with patch.object(gate,'route_evidence',return_value=[self.product]),self.assertRaisesRegex(ValueError,'Working memory'):
            gate.prepare(self.root,self.path,self.state(),'idea-validation',self.report,['producer'])
    def test_missing_or_duplicate_check_is_rejected(self):
        self.r['checks'].pop();self.save_review()
        with self.assertRaisesRegex(ValueError,'exactly once'):self.verify()
    def test_author_cannot_be_validator(self):
        self.r['reviewer_id']='producer';self.save_review()
        with self.assertRaisesRegex(ValueError,'identity'):self.verify()
    def test_core_acceptance_cannot_be_declared_nonapplicable(self):
        self.r['checks'][0]['status']='not-applicable';self.save_review()
        with self.assertRaisesRegex(ValueError,'cannot be skipped'):self.verify()
    def test_session_cannot_be_reused_for_a_new_packet(self):
        with patch.object(gate,'route_evidence',return_value=[self.product]):m=gate.prepare(self.root,self.path,self.state(),'idea-validation',self.report,['producer'])
        self.ident=m['packet_id'];self.obs=self.path/'sessions/second.json';self.observation('fresh-reviewer')
        with self.assertRaisesRegex(ValueError,'already dispatched'):gate.dispatch(self.path,self.state(),self.ident,'fresh-reviewer','fresh-reviewer','none',self.obs)
    def test_unknown_check_needs_discrepancy_and_cannot_accept(self):
        self.r['checks'][0]['status']='unknown';self.save_review()
        with self.assertRaisesRegex(ValueError,'localized discrepancy'):self.verify()
        self.r['discrepancies']=[{'id':'D1','severity':'major','classification':'data-consistency','reopen_phase':'idea-validation','check_id':self.r['checks'][0]['id'],'file_id':'file-0','locator':'fixture','problem':'Missing real evidence','correction':'Acquire evidence'}];self.save_review()
        with self.assertRaisesRegex(ValueError,'Accept cannot'):self.verify()
    def test_snapshot_mutation_after_completed_step_is_detected(self):
        self.cli('record','demo','--phase','idea-validation','--report',str(self.report),'--validation-packet',self.ident,'--validation-report',str(self.review))
        (self.path/self.m['files'][0]['snapshot']).write_text('Mutated archived snapshot')
        with self.assertRaisesRegex(ValueError,'snapshot changed'):workflow.verify_receipts(self.state(),self.path)
    def test_attempt_budget_stops_an_infinite_revalidation_loop(self):
        s=self.state();s['max_validation_attempts']=1;(self.path/'state.json').write_text(json.dumps(s))
        with self.assertRaisesRegex(ValueError,'attempt limit'):gate.prepare(self.root,self.path,s,'idea-validation',self.report,['producer'])
    def test_prepared_packets_cannot_bypass_dispatch_attempt_budget(self):
        s=self.state();s['max_validation_attempts']=2;(self.path/'state.json').write_text(json.dumps(s))
        with patch.object(gate,'route_evidence',return_value=[self.product]):
            packets=[gate.prepare(self.root,self.path,s,'idea-validation',self.report,['producer']) for _ in range(2)]
        for number,m in enumerate(packets):
            self.ident=m['packet_id'];self.obs=self.path/f'sessions/pending-{number}.json';agent=f'pending-reviewer-{number}';self.observation(agent)
            if number==0:gate.dispatch(self.path,s,self.ident,agent,agent,'none',self.obs)
            else:
                with self.assertRaisesRegex(ValueError,'attempt limit'):gate.dispatch(self.path,s,self.ident,agent,agent,'none',self.obs)
        self.assertEqual(len(list((self.path/'validation/dispatches').glob('*.json'))),2)
    def test_historical_producer_cannot_validate_the_next_step(self):
        self.cli('record','demo','--phase','idea-validation','--report',str(self.report),'--validation-packet',self.ident,'--validation-report',str(self.review))
        product=self.path/'stages/needs-impact-research/product.md';product.parent.mkdir(parents=True,exist_ok=True);product.write_text('Next synthetic product')
        with patch.object(gate,'route_evidence',return_value=[product]):m=gate.prepare(self.root,self.path,self.state(),'needs-impact-research',self.report,['new-producer'])
        self.ident=m['packet_id'];self.obs=self.path/'sessions/historical-author.json';self.observation('producer')
        with self.assertRaisesRegex(ValueError,'all project producers'):gate.dispatch(self.path,self.state(),self.ident,'producer','new-session','none',self.obs)
    def test_accepted_product_changes_require_explicit_invalidation(self):
        self.cli('record','demo','--phase','idea-validation','--report',str(self.report),'--validation-packet',self.ident,'--validation-report',str(self.review))
        self.product.write_text('Changed accepted concept')
        with self.assertRaisesRegex(ValueError,'Accepted step product changed'):self.cli('status','demo')
        change=self.path/'reports/change.json';r=json.loads(self.report.read_text());r['reason']='New verified need changes the concept';change.write_text(json.dumps(r))
        self.cli('invalidate','demo','--phase','idea-validation','--report',str(change))
        self.assertTrue(self.state()['validator_sessions'][0]['superseded']);self.cli('status','demo')
    def test_repair_packet_contains_targets_and_frozen_baseline(self):
        self.r['discrepancies']=[{'id':'D1','severity':'minor','classification':'data-consistency','reopen_phase':'idea-validation','check_id':self.r['checks'][0]['id'],'file_id':'file-0','locator':'fixture','problem':'Example target','correction':'Clarify the evidence'}];self.save_review()
        self.cli('record','demo','--phase','idea-validation','--report',str(self.report),'--validation-packet',self.ident,'--validation-report',str(self.review))
        state=self.state();state['next_phase']='repair';(self.path/'state.json').write_text(json.dumps(state))
        product=self.path/'stages/repair/product.md';product.parent.mkdir(parents=True,exist_ok=True);product.write_text('Synthetic repair')
        (self.path/'findings.json').write_text(json.dumps([{'id':'D1','status':'corrected','problem':'Example target'}]))
        with patch.object(gate,'route_evidence',return_value=[product]):m=gate.prepare(self.root,self.path,state,'repair',self.report,['producer'])
        target=next(f for f in m['files'] if f['role']=='repair-targets' and Path(f['original']).name=='repair-targets.json')
        targets=json.loads((self.path/target['snapshot']).read_text())['targets'];self.assertEqual(targets[0]['discrepancy']['id'],'D1');self.assertEqual(targets[0]['origin_packet_id'],self.ident)
        old_snapshot=(self.path/self.m['files'][0]['snapshot']).resolve();self.assertTrue(any(Path(f['original'])==old_snapshot for f in m['files']))
    def test_independent_review_requires_limits_and_actual_check_method(self):
        del self.r['verification_limits'];self.save_review()
        with self.assertRaisesRegex(ValueError,'structural contract'):self.verify()
    def test_validation_root_type_fails_with_structural_error(self):
        self.review.write_text('[]')
        with self.assertRaisesRegex(ValueError,'structural contract.*expected object'):self.verify()
    def test_corpus_integrity_failure_refuses_prepare_before_any_write(self):
        import brain
        before={str(p.relative_to(self.path)):gate.digest(p) for p in self.path.rglob('*') if p.is_file()}
        with patch.object(brain,'integrity_for_root',return_value=[{'id':'fixture:p0001','state':'derived-page-altered'}]),self.assertRaisesRegex(ValueError,'Corpus integrity failed'):
            gate.prepare(self.root,self.path,self.state(),'idea-validation',self.report,['producer'])
        after={str(p.relative_to(self.path)):gate.digest(p) for p in self.path.rglob('*') if p.is_file()}
        self.assertEqual(before,after)
    def test_unbound_schema_example_cannot_weaken_frozen_contract(self):
        schema=self.path/'validation/packets'/self.ident/'report-schema.json';schema.write_text(json.dumps({'type':'object'}))
        self.r['summary']={'invalid':'object'};self.save_review()
        with self.assertRaisesRegex(ValueError,'expected string'):self.verify()
    def test_same_phase_changed_state_dispatch_refused_without_writes(self):
        with patch.object(gate,'route_evidence',return_value=[self.product]):m=gate.prepare(self.root,self.path,self.state(),'idea-validation',self.report,['producer'])
        self.ident=m['packet_id'];self.obs=self.path/'sessions/stale-state.json';self.observation('stale-state-reviewer')
        state=self.state();state['state']='synthetic-new-state';(self.path/'state.json').write_text(json.dumps(state))
        before={str(p.relative_to(self.path)):gate.digest(p) for p in self.path.rglob('*') if p.is_file()}
        with self.assertRaisesRegex(ValueError,'stale dispatch'):gate.dispatch(self.path,state,self.ident,'stale-state-reviewer','stale-state-reviewer','none',self.obs)
        after={str(p.relative_to(self.path)):gate.digest(p) for p in self.path.rglob('*') if p.is_file()}
        self.assertEqual(before,after)
    def test_prepare_cli_returns_a_bounded_handoff_not_the_corpus(self):
        out=io.StringIO()
        with patch.object(gate,'ROOT',self.root),patch.object(gate,'route_evidence',return_value=[self.product]),patch.object(sys,'argv',['stage_gate','prepare','demo','--phase','idea-validation','--report',str(self.report),'--producer-id','producer']),contextlib.redirect_stdout(out):gate.main()
        receipt=json.loads(out.getvalue());self.assertNotIn('files',receipt);self.assertLess(len(out.getvalue()),2000);self.assertTrue(Path(receipt['manifest']).exists())
    def test_gate_cli_uses_engine_relative_paths_for_all_three_commands(self):
        def cli(*args):
            out=io.StringIO()
            with patch.object(gate,'ROOT',self.root),patch.object(gate,'route_evidence',return_value=[self.product]),patch.object(sys,'argv',['stage_gate',*args]),contextlib.redirect_stdout(out):gate.main()
            return json.loads(out.getvalue())
        receipt=cli('prepare',self.path.name,'--phase','idea-validation','--report',str(self.report.relative_to(self.root)),'--producer-id','producer','--artifact',str(self.product.relative_to(self.root)))
        self.ident=receipt['packet_id'];self.obs=self.path/'sessions/cli-observation.json';self.observation('cli-fresh-reviewer')
        dispatched=cli('dispatch',self.path.name,'--packet',self.ident,'--agent-id','cli-fresh-reviewer','--session-id','cli-fresh-reviewer','--fork-turns','none','--observation',str(self.obs.relative_to(self.root)))
        self.assertEqual(dispatched['packet_id'],self.ident)
        self.r.update(packet_id=self.ident,packet_sha256=gate.digest(Path(receipt['manifest'])),reviewer_id='cli-fresh-reviewer');self.save_review()
        verified=cli('verify',self.path.name,'--packet',self.ident,'--report',str(self.review.relative_to(self.root)))
        self.assertEqual(verified['verdict'],'accept')

if __name__=='__main__':unittest.main()
