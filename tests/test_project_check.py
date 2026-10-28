import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from project_check import check_model,check_manifest,action_mode,TABLES,ROOT,MODEL_VERSION

def model():
    m={t:[] for t in TABLES}; m['schema_version']=MODEL_VERSION; m['project']={'program':'ERASMUS','action':'KA220-ADU','year':2026,'sector':'ADU','duration_months':24,'currency':'EUR','requested_grant':120000,'management_wp_id':'WP1'}
    m['partners']=[{'id':'P1'}]; m['objectives']=[{'id':'O1'}]
    m['work_packages']=[{'id':'WP1','kind':'management','activity_ids':['A1']},{'id':'WP2','kind':'implementation','activity_ids':['A2']}]
    m['activities']=[{'id':'A1','wp_id':'WP1','partner_id':'P1','objective_ids':['O1'],'start_month':1,'end_month':3},
                     {'id':'A2','wp_id':'WP2','partner_id':'P1','objective_ids':['O1'],'start_month':4,'end_month':24,'dependency_ids':['A1']}]
    m['budget_lines']=[{'id':'B1','wp_id':'WP1','partner_id':'P1','grant_allocation':24000},
                       {'id':'B2','wp_id':'WP2','partner_id':'P1','grant_allocation':96000}]
    return m

class ProjectTests(unittest.TestCase):
    def test_allocations_balance_and_management_uses_total(self):
        m=model(); self.assertTrue(check_model(m)['passed'])
        m['budget_lines'][0]['grant_allocation']=24001; m['budget_lines'][1]['grant_allocation']=95999
        self.assertIn('ka220-management-over-20-percent-total',[i['code'] for i in check_model(m)['issues']])
    def test_esc_does_not_inherit_ka220_management_cap(self):
        m=model(); m['project'].update(program='ESC',action='ESC30',sector='ESC'); m['budget_lines'][0]['grant_allocation']=60000; m['budget_lines'][1]['grant_allocation']=60000
        self.assertNotIn('ka220-management-over-20-percent-total',[i['code'] for i in check_model(m)['issues']])
    def test_quality_label_requires_its_evidence_without_a_grant(self):
        m={t:[] for t in TABLES}; m['schema_version']=MODEL_VERSION
        m['project']={'program':'ESC','action':'ESC50-HOST-SUPPORT','year':2026,'sector':'ESC','quality_label_requirements_evidence':'esc-programme-2026:p0030'}
        m['partners']=[{'id':'P1'}]
        self.assertTrue(check_model(m,True)['passed'])
        del m['project']['quality_label_requirements_evidence']
        self.assertIn('quality-label-requirements-unverified',[i['code'] for i in check_model(m,True)['issues']])
    def test_exact_matrix_covers_all_catalog_routes_and_original_evidence(self):
        routes=json.loads((ROOT/'config/actions.json').read_text())
        matrix=json.loads((ROOT/'config/action-modes.json').read_text())
        self.assertEqual(len(matrix['routes']),50)
        self.assertEqual({r['action'] for r in matrix['routes']},{r['code'] for r in routes})
        for route in routes:
            for sector in route['sectors']:
                with self.subTest(action=route['code'],sector=sector):
                    resolved=action_mode(route.get('program','ERASMUS'),route['code'],sector,2026)
                    self.assertIn(resolved['mode'],('grant','allocation','accreditation','quality-label'))
                    source=resolved['evidence']
                    self.assertEqual(Path(source['immutable_path']).name,source['revision_sha256'])
                    for page in source['physical_pages']:
                        self.assertTrue((ROOT/source['immutable_path']/'pages'/f'page-{page:04d}.md').is_file())
    def test_accreditation_keeps_plan_data_without_fabricated_project_grant(self):
        for action,sector in [('KA120-VET','VET'),('KA120-SCH','SCH'),('KA120-ADU','ADU'),('KA150','YOU')]:
            with self.subTest(action=action):
                m={t:[] for t in TABLES}; m['schema_version']=MODEL_VERSION
                m['project']={'program':'ERASMUS','action':action,'sector':sector,'year':2026,'duration_months':36,'accreditation_requirements_evidence':'Original accreditation section'}
                m['partners']=[{'id':'P1'}]; m['priorities']=[{'id':'PR1'}]
                m['needs']=[{'id':'N1','problem':'Observed need','evidence':'Local evidence','scale':'Organisation'}]
                m['objectives']=[{'id':'O1','need_ids':['N1'],'priority_ids':['PR1']}]
                m['activities']=[{'id':'A1','partner_id':'P1','objective_ids':['O1'],'start_month':1,'end_month':36,'assignment_evidence':'Capacity evidence'}]
                m['kpis']=[{'id':'K1','objective_ids':['O1'],'baseline':0,'target':5,'unit':'participants','measurement_source':'Register','frequency':'Annual','partner_id':'P1'}]
                self.assertTrue(check_model(m,True)['passed'],check_model(m,True)['issues'])
                m['objectives']=[]
                self.assertFalse(check_model(m,True)['passed'])
                self.assertIn('empty-required-project-data',[i['code'] for i in check_model(m,True)['issues']])
    def test_every_quality_label_is_nonfinancial_and_keeps_requirement_evidence(self):
        for action in ('ESC50-HOST-SUPPORT','ESC50-LEAD','ESC-HUMAID-QL'):
            with self.subTest(action=action):
                m={t:[] for t in TABLES}; m['schema_version']=MODEL_VERSION; m['partners']=[{'id':'P1'}]
                m['project']={'program':'ESC','action':action,'sector':'ESC','year':2026,'quality_label_requirements_evidence':'Role-specific original evidence'}
                self.assertTrue(check_model(m,True)['passed'])
                m['project']['requested_grant']='NaN'
                self.assertIn('invalid-requested-grant',[i['code'] for i in check_model(m,True)['issues']])
                m['project']['requested_grant']=10
                self.assertIn('nonfinancial-action-has-requested-grant',[i['code'] for i in check_model(m,True)['issues']])
    def test_allocation_keeps_funding_and_prerequisite_controls_without_detailed_plan(self):
        for action,sector,program in [('KA131','HED','ERASMUS'),('KA121-VET','VET','ERASMUS'),('KA121-SCH','SCH','ERASMUS'),('KA121-ADU','ADU','ERASMUS'),('KA151','YOU','ERASMUS'),('ESC51','ESC','ESC')]:
            with self.subTest(action=action):
                m={t:[] for t in TABLES}; m['schema_version']=MODEL_VERSION; m['partners']=[{'id':'P1'}]
                m['project']={'program':program,'action':action,'sector':sector,'year':2026,'financial_model':'mixed','financial_model_evidence':'Original funding rules','allocation_requirements_evidence':'Accreditation/label and allocation rules'}
                m['activities']=[{'id':'A1','estimated_participants':10}]
                self.assertTrue(check_model(m,True)['passed'],check_model(m,True)['issues'])
                del m['project']['financial_model_evidence']
                self.assertIn('financial-model-unverified',[i['code'] for i in check_model(m,True)['issues']])
                m['project']['requested_grant']=100; m['budget_lines']=[{'id':'B1','grant_allocation':99}]
                self.assertIn('grant-allocation-total-mismatch',[i['code'] for i in check_model(m,True)['issues']])
    def test_financial_grants_keep_request_balance_and_real_model_checks(self):
        for action,sector,program,financial in [('KA220-ADU','ADU','ERASMUS','lump-sum'),('KA210-YOU','YOU','ERASMUS','lump-sum'),('KA152','YOU','ERASMUS','mixed'),('ESC30','ESC','ESC','mixed')]:
            with self.subTest(action=action):
                m=model(); m['project'].update(action=action,sector=sector,program=program,financial_model=financial,financial_model_evidence='Original action rules')
                del m['project']['requested_grant']
                self.assertIn('requested-grant-unconfirmed',[i['code'] for i in check_model(m,True)['issues']])
                m['project']['requested_grant']=120001
                self.assertIn('grant-allocation-total-mismatch',[i['code'] for i in check_model(m,True)['issues']])
                m['project']['financial_model']='arbitrary-confirmation'
                self.assertIn('financial-model-unverified',[i['code'] for i in check_model(m,True)['issues']])
        m=model(); m['project'].update(financial_model='unit-cost',financial_model_evidence='Wrong model despite evidence')
        self.assertIn('financial-model-unverified',[i['code'] for i in check_model(m,True)['issues']])
    def test_unknown_or_mismatched_scope_cannot_select_looser_controls(self):
        for update in ({'action':'ESC50-UNKNOWN'},{'action':'KA120-UNKNOWN'},{'program':'ESC'},{'sector':'HED'},{'year':2025},{'year':2026.0},{'year':True}):
            with self.subTest(update=update):
                m=model(); m['project'].update(update)
                for strict in (False,True):
                    result=check_model(m,strict)
                    self.assertFalse(result['passed'])
                    self.assertIn('action-mode-scope-unverified',[i['code'] for i in result['issues']])
        for field in ('year','sector','program','action'):
            m=model(); del m['project'][field]
            self.assertIn('action-mode-scope-unverified',[i['code'] for i in check_model(m,True)['issues']])
    def test_broken_assignment_and_cycles_are_detected(self):
        m=model(); m['activities'][0]['partner_id']='P99'; m['activities'][0]['dependency_ids']=['A2']
        codes=[i['code'] for i in check_model(m)['issues']]; self.assertIn('broken-reference',codes); self.assertIn('cyclic-dependency',codes)
    def test_schedule_must_fit_project_duration(self):
        m=model(); m['activities'][1]['end_month']=25
        self.assertIn('invalid-activity-schedule',[i['code'] for i in check_model(m)['issues']])
    def test_quantity_rate_is_cost_not_grant_allocation(self):
        m=model(); m['budget_lines'][0].update(quantity=10,unit_rate=500,estimated_cost=5000)
        self.assertTrue(check_model(m)['passed'])
    def test_budget_cannot_assign_activity_to_a_different_wp(self):
        m=model(); m['budget_lines'][0]['activity_id']='A2'
        self.assertIn('budget-activity-wp-mismatch',[i['code'] for i in check_model(m)['issues']])
    def test_management_id_must_identify_management_wp(self):
        m=model(); m['project']['management_wp_id']='WP2'
        self.assertIn('management-wp-kind-unverified',[i['code'] for i in check_model(m)['issues']])
    def test_legal_gate_cannot_be_bypassed_by_omitting_type(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); (root/'contract.md').write_text('Draft')
            m={'coverage_verified':True,'annexes':[{'id':'partner-contract','classification':'optional','path':'contract.md','status':'verified','delivery_status':'ready-to-sign'}]}
            self.assertFalse(check_manifest(m,root,True)['passed'])
    def test_required_annex_requires_call_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); (root/'budget.md').write_text('Test content')
            manifest={'annexes':[{'id':'budget','classification':'required','path':'budget.md'}]}
            self.assertFalse(check_manifest(manifest,root)['passed'])
            manifest['annexes'][0]['requirement_source']='Actual call field'; self.assertTrue(check_manifest(manifest,root)['passed'])
    def test_contract_draft_is_distinct_from_ready_to_sign(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); (root/'contract.md').write_text('Draft clauses')
            m={'coverage_verified':True,'annexes':[{'id':'contract','type':'partner-contract','classification':'internal','path':'contract.md','status':'verified','delivery_status':'draft-for-review'}]}
            self.assertTrue(check_manifest(m,root,True)['passed']); m['annexes'][0]['delivery_status']='ready-to-sign'
            self.assertFalse(check_manifest(m,root,True)['passed'])
    def test_non_applicable_annex_needs_reason_but_no_file(self):
        with tempfile.TemporaryDirectory() as d:
            m={'coverage_verified':True,'annexes':[{'id':'gantt-table','classification':'internal','status':'not-applicable','reason':'Quality label application with no project activity schedule.'}]}
            self.assertTrue(check_manifest(m,d,True)['passed'])
            del m['annexes'][0]['reason']
            self.assertFalse(check_manifest(m,d,True)['passed'])

if __name__=='__main__': unittest.main()
