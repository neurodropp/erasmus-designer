import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import checklist
import stage_gate
import workflow


class PhaseZeroTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.workflow_root=patch.object(workflow,'ROOT',self.root);self.workflow_root.start()
        self.run_workflow('idea-init','seed','--title','Seed idea','--max-revisions','2')
        self.path=workflow.idea_lab('seed');self.state=lambda:json.loads((self.path/'state.json').read_text())
        self.evidence=self.path/'research/observed.md';self.evidence.write_text('Synthetic current-call and design evidence.')
    def tearDown(self):
        self.workflow_root.stop();self.tmp.cleanup()
    def run_workflow(self,*args):
        out=io.StringIO()
        with patch.object(sys,'argv',['workflow',*args]),contextlib.redirect_stdout(out):workflow.main()
        return json.loads(out.getvalue())
    def complete_outputs(self,recommendation='PROCEED'):
        (self.path/'brainstorm.md').write_text('# Brainstorming libero\n\nAbbiamo confrontato un percorso cooperativo con un pilot locale più piccolo, distinguendo problema, target, meccanismo e scala.\n')
        (self.path/'brainstorm.json').write_text(json.dumps({
            'schema_version':'phase-zero-brainstorm-v1','idea_version':1,
            'authority':'collaborative-exploration-not-human-approval',
            'provenance':[{'id':'P-1','actor':'user','type':'user-input','reference':'synthetic user idea'},
                          {'id':'P-2','actor':'agent','type':'agent-proposal','reference':'synthetic alternative'}],
            'options':[{'id':'OPT-1','kind':'primary','problem':'Observed participation gap','primary_target':'Adult learners',
                        'mechanism':'Transnational co-design and testing','scale':'Three-country partnership','assumptions':['Partners can recruit learners'],'provenance_refs':['P-1']},
                       {'id':'OPT-2','kind':'alternative','problem':'Observed participation gap','primary_target':'Adult learners',
                        'mechanism':'Local pilot before transnational scaling','scale':'One-territory pilot','assumptions':['Local pilot can test the mechanism'],'provenance_refs':['P-2']}],
            'convergence':{'preferred_option_id':'OPT-1','compared_option_ids':['OPT-2'],
                           'selection_reasons':['The verified route supports the transnational mechanism and target.']},
            'alternative_exception':None}))
        matrix=json.loads((self.path/'research/checklist-phase-zero.json').read_text())
        ref={'path':str(self.evidence),'locator':'synthetic evidence','sha256':workflow.digest(self.evidence)}
        policy=json.loads((Path(__file__).resolve().parents[1]/'config/phase-zero.json').read_text())
        for row in matrix['axes']:
            wanted=policy['proceed_requires'][row['id']];row['outcome']=wanted[0] if isinstance(wanted,list) else wanted
            row.update(reason='Synthetic evidence supports this axis.',evidence=[ref],owner='fixture-owner',design_implication='Keep scope bounded.')
        candidate={'id':'ka220-adu','program':'ERASMUS','year':2026,'action':'KA220-ADU','sector':'ADU','status':'verified',
                   'country':'IT','agency':'INDIRE','role':'applicant','round':'2026-03',
                   'rationale':'Synthetic route comparison','current_call_verified':True,'evidence':[ref]}
        matrix['route_candidates']=[candidate]
        (self.path/'research/checklist-phase-zero.json').write_text(json.dumps(matrix))
        handoff=None
        if recommendation=='PROCEED':
            handoff={**candidate,'candidate_id':candidate['id']};handoff.pop('id');handoff.pop('status')
        decision={'schema_version':'phase-zero-decision-v1','version':1,'authority':'assistant-recommendation-pending-human-decision',
                  'recommendation':recommendation,'summary':'Synthetic Phase zero recommendation','strengths':['Bounded scope'],
                  'reasons':['Evidence and route fit reviewed'],'changes_required':[] if recommendation=='PROCEED' else ['Clarify route'],
                  'unknowns':[] if recommendation=='PROCEED' else ['Current route choice'],'route_handoff':handoff}
        stage=self.path/'stages/phase-zero';(stage/'decision.json').write_text(json.dumps(decision));(stage/'decision.md').write_text('# Version 1\n\nSynthetic recommendation.')
        report=self.path/'reports/phase-zero.json';report.write_text(json.dumps({'status':'pass','summary':'Synthetic Phase zero production',
            'evidence':[ref],'critical_review':{'weaknesses':['Synthetic fixture'],'alternative':'Narrower pilot','decision_basis':'Frozen inputs'}}))
        return report
    def gate(self,report):
        state=self.state()
        manifest=stage_gate.prepare_idea(self.root,self.path,state,report,['producer'])
        packet=manifest['packet_id'];reviewer='fresh-'+packet
        obs=self.path/'sessions/spawn.json';obs.write_text(json.dumps({'tool':'collaboration.spawn_agent','request':{'fork_turns':'none'},'result':{'task_name':reviewer},'packet_id':packet}))
        stage_gate.dispatch(self.path,state,packet,reviewer,reviewer,'none',obs)
        review=self.path/'validation/reports/review.json';review.write_text(json.dumps({
            'packet_id':packet,'packet_sha256':stage_gate.digest(self.path/'validation/packets'/packet/'manifest.json'),'phase':'phase-zero',
            'reviewer_id':reviewer,'verdict':'accept','summary':'Synthetic independent acceptance','discrepancies':[],
            'verification_limits':['Synthetic protocol fixture'],'missing_information':[],
            'critical_review':{'weaknesses':['Fixture limitation'],'alternative':'Refine','decision_basis':'Frozen package'},'automatic_checks':[],
            'checks':[{'id':row['id'],'status':'pass','reason':'Synthetic pass','verification':'Compared frozen fixture',
                       'evidence':[{'file_id':'file-0','locator':'fixture'}]} for row in manifest['acceptance_checks']]}))
        return packet,review
    def human(self,packet,decision='PROCEED'):
        manifest=self.path/'validation/packets'/packet/'manifest.json'
        accepted=self.path/'stages/phase-zero/decision.json';route=json.loads(accepted.read_text()).get('route_handoff')
        source=self.path/'handoff/human-decision.json';source.write_text(json.dumps({'schema_version':'phase-zero-human-decision-v1','decision':decision,
            'rationale':'Observed synthetic human choice','provenance':'user-instruction','observed_reference':'synthetic test instruction',
            'accepted_packet_id':packet,'accepted_packet_sha256':stage_gate.digest(manifest),'accepted_decision_sha256':workflow.digest(accepted),
            'selected_route':{key:route.get(key) for key in workflow.IDEA_ROUTE_IDENTITY} if decision=='PROCEED' else None}))
        self.run_workflow('idea-decide',self.path.name,'--decision-file',str(source));return source

    def test_route_neutral_workspace_is_not_a_project(self):
        self.assertTrue(self.path.is_relative_to(self.root/'work/idea-lab'))
        self.assertFalse((self.root/'projects').exists())
        state=self.state();self.assertNotIn('action',state);self.assertEqual(state['next_phase'],'phase-zero')
        self.assertEqual(json.loads((self.path/'research/checklist-phase-zero.json').read_text())['phase'],'phase-zero')

    def test_proceed_requires_fresh_gate_human_choice_and_preserves_dependency(self):
        report=self.complete_outputs();packet,review=self.gate(report)
        self.run_workflow('idea-record',self.path.name,'--report',str(report),'--validation-packet',packet,'--validation-report',str(review))
        self.assertEqual(self.state()['state'],'awaiting-human-decision')
        with self.assertRaisesRegex(ValueError,'human-confirmed'):
            args=type('A',(),{'project_name':'project','title':None,'max_revisions':2,'process':'integrated','form_profile':None,'annex':[]})
            workflow.promote_idea(args,self.path,self.state())
        self.human(packet)
        promoted=self.run_workflow('promote-idea',self.path.name,'--project-name','project','--max-revisions','2')
        project=self.root/'projects'/promoted['id']
        project_state=json.loads((project/'state.json').read_text())
        self.assertEqual(project_state['next_phase'],'idea-validation')
        self.assertEqual(project_state['phase_zero_status'],'imported-accepted-human-confirmed')
        for key,value in {'country':'IT','agency':'INDIRE','role':'applicant','round':'2026-03'}.items():
            self.assertEqual(project_state[key],value)
        handoff=project/project_state['phase_zero']['handoff_manifest'];self.assertEqual(workflow.digest(handoff),project_state['phase_zero']['handoff_manifest_sha256'])
        for row in json.loads(handoff.read_text())['files']:
            self.assertEqual(workflow.digest(project/row['path']),row['sha256'])
        checklist.initialize(self.root,project.name,'idea-validation')
        product=project/'stages/idea-validation/product.md';product.write_text('Synthetic route-specific idea validation product')
        production=project/'reports/idea-validation.json';production.write_text(json.dumps({'status':'pass','summary':'Synthetic production',
            'evidence':[{'source_id':'fixture','locator':'product','path':str(product)}],
            'critical_review':{'weaknesses':['Fixture'],'alternative':'Narrower design','decision_basis':'Imported Phase zero and route evidence'}}))
        with patch.object(stage_gate,'route_evidence',return_value=[product]):
            next_packet=stage_gate.prepare(self.root,project,project_state,'idea-validation',production,['next-producer'])
        imported=[row for row in next_packet['files'] if row['role']=='dependency-product' and row.get('accepted_product')]
        self.assertGreaterEqual(len(imported),2)

    def test_refine_returns_to_phase_zero_and_supersedes_accepted_product(self):
        report=self.complete_outputs();packet,review=self.gate(report)
        self.run_workflow('idea-record',self.path.name,'--report',str(report),'--validation-packet',packet,'--validation-report',str(review))
        self.human(packet,'REFINE')
        state=self.state();self.assertEqual(state['next_phase'],'phase-zero');self.assertEqual(state['revisions'],1)
        self.assertTrue(state['validator_sessions'][0]['superseded'])
        with self.assertRaisesRegex(ValueError,'version must increase'):
            stage_gate.prepare_idea(self.root,self.path,state,report,['producer-2'])
        (self.path/'stages/phase-zero/decision.md').write_text('New version may now be produced')
        self.run_workflow('idea-status',self.path.name)

    def test_phase_zero_revision_limit_blocks_another_packet(self):
        report=self.complete_outputs();packet,review=self.gate(report)
        self.run_workflow('idea-record',self.path.name,'--report',str(report),'--validation-packet',packet,'--validation-report',str(review))
        state=self.state();state['max_revisions']=1;(self.path/'state.json').write_text(json.dumps(state))
        self.human(packet,'PIVOT')
        self.assertEqual(self.state()['state'],'revision-limit-reached')
        with self.assertRaisesRegex(ValueError,'revision limit'):
            stage_gate.prepare_idea(self.root,self.path,self.state(),report,['producer-2'])

    def test_stop_closes_without_creating_a_project(self):
        report=self.complete_outputs();packet,review=self.gate(report)
        self.run_workflow('idea-record',self.path.name,'--report',str(report),'--validation-packet',packet,'--validation-report',str(review))
        self.human(packet,'STOP')
        self.assertEqual(self.state()['state'],'stopped');self.assertEqual(self.state()['next_phase'],'closed')
        with self.assertRaisesRegex(ValueError,'human-confirmed PROCEED'):
            args=type('A',(),{'project_name':'stopped','title':None,'max_revisions':2,'form_profile':None,'annex':[]})
            workflow.promote_idea(args,self.path,self.state())
        self.assertFalse((self.root/'projects').exists())

    def test_direct_init_is_compatible_and_marks_phase_zero_bypass(self):
        result=self.run_workflow('init','legacy','--action','KA220','--sector','ADU')
        self.assertEqual(result['phase_zero_status'],'bypassed-direct-init')
        self.assertEqual(result['next_phase'],'idea-validation')

    def test_no_official_score_is_accepted_in_phase_zero_decision(self):
        self.complete_outputs();decision=self.path/'stages/phase-zero/decision.json';data=json.loads(decision.read_text());data['official_score']=90
        matrix=json.loads((self.path/'research/checklist-phase-zero.json').read_text())
        result=checklist.validate_phase_zero_decision(data,matrix,self.state(),self.path)
        self.assertFalse(result['valid']);self.assertTrue(any('official scores' in row['issue'] for row in result['issues']))

    def test_route_handoff_rejects_mixed_or_unknown_evidence_and_requires_candidate_binding(self):
        self.complete_outputs();decision=json.loads((self.path/'stages/phase-zero/decision.json').read_text())
        matrix=json.loads((self.path/'research/checklist-phase-zero.json').read_text())
        valid_ref=matrix['route_candidates'][0]['evidence'][0]
        probes=(
            {**valid_ref,'source_id':'nonexistent-phase-zero-source'},
            {'source_id':'nonexistent-phase-zero-source','locator':'claimed handoff source'},
            {'path':str(self.path/'brainstorm.md'),'locator':'different but valid local proof'},
        )
        expected=('exactly one','does not resolve','exactly match')
        for ref,needle in zip(probes,expected):
            mutated=json.loads(json.dumps(decision));mutated['route_handoff']['evidence']=[ref]
            result=checklist.validate_phase_zero_decision(mutated,matrix,self.state(),self.path)
            self.assertFalse(result['valid'])
            self.assertTrue(any(needle in row['issue'] for row in result['issues']),result['issues'])
        self.assertTrue(checklist.validate_phase_zero_decision(decision,matrix,self.state(),self.path)['valid'])

    def test_route_handoff_and_human_choice_bind_full_canonical_identity(self):
        self.complete_outputs();decision=json.loads((self.path/'stages/phase-zero/decision.json').read_text())
        matrix=json.loads((self.path/'research/checklist-phase-zero.json').read_text())
        for key,replacement in {'country':'FR','agency':'AIG','role':'partner','round':'2026-10'}.items():
            mutated=json.loads(json.dumps(decision));mutated['route_handoff'][key]=replacement
            result=checklist.validate_phase_zero_decision(mutated,matrix,self.state(),self.path)
            self.assertFalse(result['valid']);self.assertTrue(any(row['item_id']=='route_handoff' for row in result['issues']))
        missing=json.loads(json.dumps(decision));missing['route_handoff'].pop('agency')
        self.assertFalse(checklist.validate_phase_zero_decision(missing,matrix,self.state(),self.path)['valid'])
        state=self.state();state['pending_human_decision']={'packet_id':'packet','packet_sha256':'packet-sha',
            'decision_sha256':workflow.digest(self.path/'stages/phase-zero/decision.json')}
        human={'schema_version':'phase-zero-human-decision-v1','decision':'PROCEED','rationale':'Observed choice',
            'provenance':'user-instruction','observed_reference':'synthetic observed instruction',
            'accepted_packet_id':'packet','accepted_packet_sha256':'packet-sha','accepted_decision_sha256':state['pending_human_decision']['decision_sha256'],
            'selected_route':{key:decision['route_handoff'].get(key) for key in workflow.IDEA_ROUTE_IDENTITY}}
        self.assertEqual(workflow.validate_human_idea_decision(human,state,self.path)['decision'],'PROCEED')
        for key,replacement in {'country':'FR','agency':'AIG','role':'partner','round':'2026-10'}.items():
            mutated=json.loads(json.dumps(human));mutated['selected_route'][key]=replacement
            with self.assertRaisesRegex(ValueError,'selected route'):
                workflow.validate_human_idea_decision(mutated,state,self.path)
        omitted=json.loads(json.dumps(human));omitted['selected_route'].pop('country')
        with self.assertRaisesRegex(ValueError,'selected route'):
            workflow.validate_human_idea_decision(omitted,state,self.path)

    def test_subcommand_help_does_not_resolve_a_workspace(self):
        for module,command in ((workflow,'idea-status'),(stage_gate,'prepare-idea')):
            output=io.StringIO()
            with patch.object(sys,'argv',['command',command,'--help']),contextlib.redirect_stdout(output),self.assertRaises(SystemExit) as ended:
                module.main()
            self.assertEqual(ended.exception.code,0);self.assertIn('usage:',output.getvalue())

    def test_prepare_rejects_empty_free_brainstorm(self):
        report=self.complete_outputs();(self.path/'brainstorm.md').write_text('# Brainstorming libero\n\n')
        with self.assertRaisesRegex(ValueError,'substantive free brainstorming'):
            stage_gate.prepare_idea(self.root,self.path,self.state(),report,['producer'])

    def test_prepare_rejects_missing_structured_alternative(self):
        report=self.complete_outputs();path=self.path/'brainstorm.json';data=json.loads(path.read_text())
        data['options']=data['options'][:1];data['convergence']['compared_option_ids']=[];path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'brainstorm invalid'):
            stage_gate.prepare_idea(self.root,self.path,self.state(),report,['producer'])

    def test_alternative_exception_cannot_bypass_a_recorded_alternative(self):
        self.complete_outputs();path=self.path/'brainstorm.json';data=json.loads(path.read_text())
        data['convergence']['compared_option_ids']=[]
        data['alternative_exception']={'reason':'Synthetic exception','owner':'fixture-owner','evidence':[
            {'path':str(self.evidence),'locator':'synthetic exception evidence','sha256':workflow.digest(self.evidence)}]}
        result=checklist.validate_phase_zero_brainstorm(data,self.state(),self.path)
        self.assertFalse(result['valid'])
        self.assertTrue(any('primary and an alternative' in row['issue'] for row in result['issues']))
        self.assertTrue(any(row['item_id']=='alternative_exception' for row in result['issues']))

    def test_alternative_exception_rejects_unknown_catalog_source(self):
        self.complete_outputs();path=self.path/'brainstorm.json';data=json.loads(path.read_text())
        data['options']=data['options'][:1];data['convergence']['compared_option_ids']=[]
        data['alternative_exception']={'reason':'No pertinent alternative found','owner':'fixture-owner','evidence':[
            {'source_id':'nonexistent-phase-zero-source','locator':'claimed source section'}]}
        result=checklist.validate_phase_zero_brainstorm(data,self.state(),self.path)
        self.assertFalse(result['valid'])
        self.assertTrue(any('does not resolve' in row['issue'] for row in result['issues']))

    def test_phase_zero_evidence_rejects_mixed_local_and_catalog_selectors(self):
        self.complete_outputs();path=self.path/'brainstorm.json';data=json.loads(path.read_text())
        data['options']=data['options'][:1];data['convergence']['compared_option_ids']=[]
        data['alternative_exception']={'reason':'No pertinent alternative found','owner':'fixture-owner','evidence':[
            {'path':str(self.evidence),'source_id':'nonexistent-phase-zero-source','locator':'ambiguous evidence'}]}
        result=checklist.validate_phase_zero_brainstorm(data,self.state(),self.path)
        self.assertFalse(result['valid'])
        self.assertTrue(any('exactly one' in row['issue'] for row in result['issues']))

    def test_localized_alternative_exception_is_frozen_with_locator_and_hash(self):
        report=self.complete_outputs();exception_evidence=self.path/'research/alternative-search.md'
        exception_evidence.write_text('Synthetic record of the alternative search and its bounded result.')
        path=self.path/'brainstorm.json';data=json.loads(path.read_text())
        data['options']=data['options'][:1];data['convergence']['compared_option_ids']=[]
        data['alternative_exception']={'reason':'No pertinent alternative remained after bounded search','owner':'fixture-owner','evidence':[
            {'path':str(exception_evidence),'locator':'bounded alternative search result','sha256':workflow.digest(exception_evidence)}]}
        path.write_text(json.dumps(data))
        manifest=stage_gate.prepare_idea(self.root,self.path,self.state(),report,['producer'])
        frozen=[row for row in manifest['files'] if row['role']=='localized-evidence' and Path(row['original'])==exception_evidence.resolve()]
        self.assertEqual(len(frozen),1)
        self.assertEqual(frozen[0]['locator'],'bounded alternative search result')
        self.assertEqual(frozen[0]['sha256'],workflow.digest(exception_evidence))

    def test_convergence_accepts_an_alternative_as_preferred_after_comparing_primary(self):
        self.complete_outputs();data=json.loads((self.path/'brainstorm.json').read_text())
        data['convergence']['preferred_option_id']='OPT-2';data['convergence']['compared_option_ids']=['OPT-1']
        result=checklist.validate_phase_zero_brainstorm(data,self.state(),self.path)
        self.assertTrue(result['valid'],result['issues'])

    def test_convergence_cannot_exclude_primary_when_comparing_only_alternatives(self):
        self.complete_outputs();data=json.loads((self.path/'brainstorm.json').read_text())
        data['options'].append({'id':'OPT-3','kind':'alternative','problem':'Observed participation gap',
            'primary_target':'Adult learners','mechanism':'Transnational staff-only toolkit',
            'scale':'Three-country partnership','assumptions':['Staff adoption can change access'],'provenance_refs':['P-2']})
        data['convergence']['preferred_option_id']='OPT-2';data['convergence']['compared_option_ids']=['OPT-3']
        result=checklist.validate_phase_zero_brainstorm(data,self.state(),self.path)
        self.assertFalse(result['valid'])
        self.assertTrue(any('primary and an alternative' in row['issue'] for row in result['issues']))

if __name__=='__main__':unittest.main()
