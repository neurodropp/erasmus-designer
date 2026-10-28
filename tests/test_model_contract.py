"""Independent relationship and domain regressions for ED-07..ED-14."""
import copy
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from project_check import TABLES,MODEL_VERSION,check_model,check_manifest,annex_projections


def final_model():
    m={t:[] for t in TABLES}; m['schema_version']=MODEL_VERSION
    m['project']={'program':'ERASMUS','year':2026,'action':'KA220-YOU','sector':'YOU','duration_months':12,'requested_grant':120000,'currency':'EUR','financial_model':'lump-sum','financial_model_evidence':'Synthetic structural fixture; no actual call attestation','management_wp_id':'WP1'}
    m['partners']=[{'id':'P1'},{'id':'P2'}];m['priorities']=[{'id':'PR1'}]
    m['needs']=[{'id':'N1','problem':'Synthetic observed need','evidence':'Synthetic baseline','scale':'local'}]
    m['objectives']=[{'id':'O1','need_ids':['N1'],'priority_ids':['PR1']}]
    m['work_packages']=[{'id':'WP1','kind':'management','activity_ids':[]},{'id':'WP2','kind':'implementation','activity_ids':['A1'],'lead_partner_id':'P1','objective_ids':['O1'],'task_ids':['T1','T2'],'deliverable_ids':['D1'],'milestone_ids':['M1']}]
    m['activities']=[{'id':'A1','wp_id':'WP2','partner_id':'P1','objective_ids':['O1'],'assignment_evidence':'Synthetic capacity','start_month':1,'end_month':12,'task_ids':['T1','T2'],'deliverable_ids':['D1']}]
    m['tasks']=[{'id':'T1','title':'Prototype','activity_id':'A1','wp_id':'WP2','partner_id':'P1','start_month':1,'end_month':6,'deliverable_ids':['D1']},{'id':'T2','title':'Translate and test','activity_id':'A1','wp_id':'WP2','partner_id':'P2','start_month':7,'end_month':12,'dependency_ids':['T1'],'deliverable_ids':['D1']}]
    m['deliverables']=[{'id':'D1','title':'Tested toolkit','task_ids':['T1','T2'],'output_ids':['OUT1'],'wp_id':'WP2','partner_id':'P1','due_month':12,'acceptance_criteria':['Localized review before release'],'versions':[{'id':'D1-EN-v1','language':'en','version':'1.0','status':'planned'},{'id':'D1-IT-v1','language':'it','version':'1.0','status':'draft'}]}]
    m['milestones']=[{'id':'M1','title':'Toolkit gate','wp_id':'WP2','partner_id':'P1','task_ids':['T2'],'deliverable_ids':['D1'],'due_month':12,'acceptance_criteria':'Two languages reviewed'}]
    m['outputs']=[{'id':'OUT1','wp_id':'WP2','activity_ids':['A1'],'deliverable_ids':['D1']}]
    m['results']=[{'id':'R1','output_ids':['OUT1'],'objective_ids':['O1']}]
    m['impacts']=[{'id':'I1','result_ids':['R1'],'scale':'local'}]
    m['kpis']=[{'id':'K1','wp_id':'WP2','objective_ids':['O1'],'result_ids':['R1'],'baseline':0,'target':10,'unit':'people','measurement_source':'Synthetic measurement fixture','frequency':'monthly','partner_id':'P1'}]
    m['budget_lines']=[{'id':'B1','wp_id':'WP1','partner_id':'P1','grant_allocation':24000},{'id':'B2','wp_id':'WP2','activity_id':'A1','partner_id':'P1','grant_allocation':96000,'quantity':2,'unit_rate':500,'estimated_cost':1000}]
    return m


class ContractRegressions(unittest.TestCase):
    def codes(self,m,strict=True): return [i['code'] for i in check_model(m,strict)['issues']]
    def test_positive_two_tasks_two_language_versions_reconcile_all_views(self):
        m=final_model(); self.assertTrue(check_model(m,True)['passed'],check_model(m,True)['issues'])
        v=annex_projections(m)
        self.assertEqual({r['task_id'] for r in v['ka2-task-file']},{'T1','T2'})
        self.assertTrue(all(r['deliverable_ids']==['D1'] for r in v['ka2-task-file']))
        self.assertEqual({r['artifact_id'] for r in v['results-register']},{'D1-EN-v1','D1-IT-v1'})
        self.assertEqual({r['deliverable_id'] for r in v['results-register']},{'D1'})
        self.assertIn('D1',{r['schedule_id'] for r in v['gantt-table']})
        self.assertIn('D1',{r['entity_id'] for r in v['work-packages-table']})
        self.assertEqual(len(v['budget-table']),2)
        self.assertEqual(v['budget-table'][1]['task_ids'],['T1','T2'])
        self.assertEqual(v['budget-table'][1]['deliverable_ids'],['D1'])
        self.assertEqual(sum(r['grant_allocation'] for r in v['budget-table']),120000)
        self.assertEqual(v['calendar_unit'],'project_month')
    def test_cli_projects_only_a_passing_requested_check(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'model.json';output=root/'views.json';source.write_text(json.dumps(final_model()))
            command=[sys.executable,str(Path(__file__).resolve().parents[1]/'scripts/project_check.py'),str(source),'--strict','--projections-output',str(output)]
            positive=subprocess.run(command,capture_output=True,text=True);self.assertEqual(positive.returncode,0,positive.stdout);self.assertEqual(json.loads(output.read_text())['results-register'][0]['deliverable_id'],'D1')
            output.unlink();m=final_model();m['tasks'][0]['activity_id']='missing';source.write_text(json.dumps(m))
            negative=subprocess.run(command,capture_output=True,text=True);self.assertNotEqual(negative.returncode,0);self.assertFalse(output.exists())
    def test_disconnected_output_and_unmeasured_kpi(self):
        m=final_model();m['outputs'][0].update(activity_ids=[],wp_id=None); m['kpis'][0].update(objective_ids=[],result_ids=[])
        self.assertIn('output-activities-missing',self.codes(m));self.assertIn('kpi-measured-entity-missing',self.codes(m))
    def test_output_wp_conflicts_with_activity(self):
        m=final_model();m['outputs'][0]['wp_id']='WP1'
        self.assertIn('output-activity-wp-mismatch',self.codes(m))
    def test_transitive_kpi_wp_conflict(self):
        m=final_model();m['kpis'][0]['wp_id']='WP1'
        self.assertIn('kpi-measured-entity-wp-mismatch',self.codes(m))
    def test_all_new_registries_validate_references(self):
        for table,field,bad in [('tasks','activity_id','A-missing'),('deliverables','task_ids',['T-missing']),('milestones','deliverable_ids',['D-missing']),('work_packages','deliverable_ids',['D-missing'])]:
            with self.subTest(table=table):
                m=final_model(); row=m[table][-1];row[field]=bad
                self.assertIn('broken-reference',self.codes(m))
    def test_no_untyped_shadow_registry_or_structured_reference(self):
        m=final_model();m['outcomes']=[{'id':'R1'}]
        self.assertIn('unknown-model-root-field',self.codes(m))
        m=final_model();m['tasks'][0]['dependency_ids']='T2'
        self.assertIn('invalid-reference-type',self.codes(m))
        m=final_model();m['tasks'][0]['wp_id']=['WP2']
        self.assertIn('invalid-reference-type',self.codes(m))
    def test_legacy_migration_is_explicit_and_does_not_mutate(self):
        m=final_model()
        for key in ('schema_version','tasks','deliverables','milestones'):m.pop(key)
        for table in ('work_packages','activities','outputs'):
            for row in m[table]:
                for key in ('task_ids','deliverable_ids','milestone_ids'):row.pop(key,None)
        before=copy.deepcopy(m);self.assertTrue(check_model(m,False)['passed'])
        self.assertIn('project-model-migration-required',self.codes(m));self.assertEqual(m,before)
        m=final_model();m.pop('schema_version');self.assertIn('project-model-migration-required',self.codes(m));self.assertNotIn('schema_version',m)
    def test_task_calendar_wp_and_cycles(self):
        m=final_model();m['tasks'][0].update(wp_id='WP1',end_month=13,dependency_ids=['T2'])
        codes=self.codes(m);self.assertIn('task-activity-wp-mismatch',codes);self.assertIn('invalid-task-schedule',codes);self.assertIn('cyclic-dependency',codes)
    def test_deliverable_links_and_version_identity(self):
        m=final_model();m['deliverables'][0]['task_ids']=['T1'];m['deliverables'][0]['versions'][1]['id']='D1-EN-v1'
        codes=self.codes(m);self.assertIn('task-deliverable-membership-mismatch',codes);self.assertIn('duplicate-deliverable-version',codes)
        m=final_model();m['deliverables'][0]['due_month']=5
        self.assertIn('deliverable-before-task-completion',self.codes(m))
    def test_accepted_version_requires_localized_review_not_just_status(self):
        m=final_model();v=m['deliverables'][0]['versions'][0];v['status']='accepted'
        self.assertIn('deliverable-acceptance-unverified',self.codes(m))
        v.update(path='annexes/toolkit-en.md',acceptance_partner_id='P1',acceptance_date='2026-09-12',approval_evidence='Synthetic review locator; not actual acceptance')
        self.assertNotIn('deliverable-acceptance-unverified',self.codes(m))
        v['approval_evidence']=True;self.assertIn('deliverable-acceptance-unverified',self.codes(m));v['approval_evidence']='Synthetic localized review'
        v['acceptance_date']='September';self.assertIn('invalid-deliverable-acceptance-date',self.codes(m))
    def test_duration_domain_cannot_disable_scheduled_model(self):
        for value in (None,0,-1,True,'12',12.0):
            with self.subTest(value=value):
                m=final_model();m['project']['duration_months']=value
                self.assertIn('invalid-project-duration',self.codes(m))
        m=final_model();del m['project']['duration_months'];self.assertIn('invalid-project-duration',self.codes(m))
        m=final_model();self.assertNotIn('invalid-project-duration',self.codes(m))
    def test_two_negative_factors_do_not_become_valid_positive_cost(self):
        m=final_model();m['budget_lines'][1].update(quantity=-5,unit_rate=-100,estimated_cost=500)
        self.assertEqual(self.codes(m).count('negative-budget-factor'),2)
        m['budget_lines'][1].update(quantity=5,unit_rate=100,estimated_cost=500);self.assertTrue(check_model(m,True)['passed'])
        m['budget_lines'][1]['estimated_cost']=600;self.assertIn('quantity-rate-cost-mismatch',self.codes(m))
    def test_negative_single_factor_is_checked_even_without_complete_product(self):
        m=final_model();m['budget_lines'][0]['unit_rate']=-1
        self.assertIn('negative-budget-factor',self.codes(m))
    def test_all_management_classifications_are_counted_and_unique(self):
        m=final_model();m['work_packages'][1]['kind']='management'
        result=check_model(m,True);self.assertEqual(result['management_grant_allocation'],'120000')
        codes=[i['code'] for i in result['issues']]
        self.assertIn('multiple-ka220-management-work-packages',codes);self.assertIn('ka220-management-over-20-percent-total',codes)
        m=final_model();m['budget_lines'][0]['grant_allocation']=24001;m['budget_lines'][1]['grant_allocation']=95999
        self.assertIn('ka220-management-over-20-percent-total',self.codes(m))
    def test_no_ka220_cap_or_mandatory_full_delivery_transferred_to_ka210_or_esc(self):
        for program,action,sector,financial in [('ERASMUS','KA210-YOU','YOU','lump-sum'),('ESC','ESC30','ESC','mixed')]:
            with self.subTest(action=action):
                m=final_model();m['project'].update(program=program,action=action,sector=sector,financial_model=financial)
                m['budget_lines'][0]['grant_allocation']=60000;m['budget_lines'][1]['grant_allocation']=60000
                for table in ('tasks','deliverables','milestones'):m[table]=[]
                for table in ('work_packages','activities','outputs'):
                    for row in m[table]:
                        for key in ('task_ids','deliverable_ids','milestone_ids'):row.pop(key,None)
                self.assertTrue(check_model(m,True)['passed'],check_model(m,True)['issues'])
    def test_contract_id_type_conflict_cannot_bypass_legal_gate(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'contract.md').write_text('Synthetic draft')
            for ident,typ in [('partner-contract','other'),('generic-contract','partner-contract')]:
                item={'id':ident,'type':typ,'path':'contract.md','status':'verified','delivery_status':'ready-to-sign','classification':'internal'}
                result=check_manifest({'coverage_verified':True,'annexes':[item]},root,True)
                self.assertFalse(result['passed']);self.assertIn('contract-legal-review-not-localized',[i['code'] for i in result['issues']])
            item.update(id='partner-contract',type='partner-contract',legal_review_evidence='Synthetic counsel review locator')
            self.assertTrue(check_manifest({'coverage_verified':True,'annexes':[item]},root,True)['passed'])
            item.update(type='other',delivery_status='draft-for-review');self.assertFalse(check_manifest({'coverage_verified':True,'annexes':[item]},root,True)['passed'])
            item.update(type='partner-contract');self.assertTrue(check_manifest({'coverage_verified':True,'annexes':[item]},root,True)['passed'])


def second_delivery_model():
    m=final_model();wp=m['work_packages'][1]
    wp['activity_ids'].append('A2');wp['task_ids'].append('T3');wp['deliverable_ids'].append('D2')
    m['activities'].append({'id':'A2','wp_id':'WP2','partner_id':'P1','objective_ids':['O1'],'assignment_evidence':'Synthetic second capacity fixture','start_month':7,'end_month':12,'task_ids':['T3'],'deliverable_ids':['D2']})
    m['tasks'].append({'id':'T3','title':'Second delivery task','activity_id':'A2','wp_id':'WP2','partner_id':'P1','start_month':7,'end_month':12,'deliverable_ids':['D2']})
    m['outputs'].append({'id':'OUT2','wp_id':'WP2','activity_ids':['A2'],'deliverable_ids':['D2']})
    m['deliverables'].append({'id':'D2','title':'Second output','task_ids':['T3'],'output_ids':['OUT2'],'wp_id':'WP2','partner_id':'P1','due_month':12,'acceptance_criteria':'Synthetic independent output gate','versions':[{'id':'D2-EN-v1','language':'en','version':'1.0','status':'planned'}]})
    return m


class ModelRound2Regressions(unittest.TestCase):
    def codes(self,m,strict=True):return [i['code'] for i in check_model(m,strict)['issues']]
    def test_present_inverse_lists_cannot_omit_milestone_or_activity_delivery(self):
        m=final_model();m['work_packages'][1]['milestone_ids']=[]
        result=check_model(m,True);self.assertFalse(result['passed']);self.assertTrue(any(i['code']=='milestone-wp-membership-mismatch' and i['id']=='M1' for i in result['issues']))
        m=final_model();m['activities'][0]['deliverable_ids']=[]
        result=check_model(m,True);self.assertFalse(result['passed']);self.assertTrue(any(i['code']=='deliverable-activity-membership-mismatch' and i['id']=='D1' for i in result['issues']))
    def test_absent_optional_inverse_lists_do_not_invent_membership(self):
        m=final_model();m['work_packages'][1].pop('milestone_ids');m['activities'][0].pop('deliverable_ids')
        self.assertTrue(check_model(m,True)['passed'],check_model(m,True)['issues'])
        self.assertNotIn('milestone_ids',m['work_packages'][1]);self.assertNotIn('deliverable_ids',m['activities'][0])
    def test_budget_cannot_pair_unrelated_task_and_delivery_in_same_wp(self):
        m=second_delivery_model();self.assertTrue(check_model(m,True)['passed'],check_model(m,True)['issues'])
        m['budget_lines'][1].update(task_id='T1',deliverable_id='D2')
        self.assertIn('budget-task-deliverable-mismatch',self.codes(m))
        with self.assertRaises(ValueError):annex_projections(m)
        m['budget_lines'][1].update(task_id='T3',activity_id='A2')
        self.assertTrue(check_model(m,True)['passed'],check_model(m,True)['issues'])
        row=annex_projections(m)['budget-table'][1];self.assertEqual(row['task_ids'],['T3']);self.assertEqual(row['deliverable_ids'],['D2'])
    def test_budget_delivery_cannot_borrow_an_unrelated_activity(self):
        m=second_delivery_model();m['budget_lines'][1]['deliverable_id']='D2'
        self.assertIn('budget-deliverable-activity-mismatch',self.codes(m))
        m['budget_lines'][1]['activity_id']='A2';self.assertTrue(check_model(m,True)['passed'])
        row=annex_projections(m)['budget-table'][1];self.assertEqual(row['task_ids'],['T3']);self.assertEqual(row['deliverable_ids'],['D2'])
    def test_budget_view_derives_only_actual_delivery_activity_links_and_keeps_one_allocation(self):
        for scope in ('activity','wp','delivery'):
            with self.subTest(scope=scope):
                m=second_delivery_model();line=m['budget_lines'][1]
                if scope=='activity':line['activity_id']='A2'
                elif scope=='wp':line.pop('activity_id')
                else:line.pop('activity_id');line['deliverable_id']='D2'
                self.assertTrue(check_model(m,True)['passed']);v=annex_projections(m);row=v['budget-table'][1]
                self.assertEqual(len(v['budget-table']),2);self.assertEqual(sum(r['grant_allocation'] for r in v['budget-table']),120000)
                self.assertEqual(row['task_ids'],[] if scope=='wp' else ['T3']);self.assertEqual(row['deliverable_ids'],[] if scope=='wp' else ['D2'])
    def test_strict_applies_actual_schema_for_requested_grant_and_plural_null(self):
        for field in ('requested_grant','dependency_ids'):
            with self.subTest(field=field):
                m=final_model()
                if field=='requested_grant':m['project'][field]='120000'
                else:m['tasks'][0][field]=None
                self.assertTrue(check_model(m,False)['passed'])
                result=check_model(m,True);self.assertFalse(result['passed']);self.assertTrue(any(i['code']=='model-schema-violation' and i['keyword']=='type' and i['path'].endswith('/'+field) for i in result['issues']))
    def test_wp_calendar_domain_and_boundaries_block_even_preview_views(self):
        for start,end in ((-10,-1),(1,13),(0,12),(True,12),(1,None),(5,4)):
            with self.subTest(start=start,end=end):
                m=final_model();m['work_packages'][1].update(start_month=start,end_month=end)
                self.assertFalse(check_model(m,False)['passed']);self.assertFalse(check_model(m,True)['passed'])
                with self.assertRaises(ValueError):annex_projections(m)
        m=final_model();m['work_packages'][1]['due_month']=13
        with self.assertRaises(ValueError):annex_projections(m)
    def test_wp_explicit_calendar_contains_its_included_activities(self):
        m=final_model();m['work_packages'][1].update(start_month=2,end_month=12)
        self.assertIn('activity-outside-wp-schedule',self.codes(m))
        m['work_packages'][1]['start_month']=1;self.assertTrue(check_model(m,True)['passed'])
        wp=next(r for r in annex_projections(m)['gantt-table'] if r['entity_id']=='WP2');self.assertEqual((wp['start_month'],wp['end_month']),(1,12))
    def test_cli_does_not_export_a_new_invalid_wp_preview(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'model.json';output=root/'views.json';m=final_model();m['work_packages'][1].update(start_month=-10,end_month=-1);source.write_text(json.dumps(m))
            result=subprocess.run([sys.executable,str(Path(__file__).resolve().parents[1]/'scripts/project_check.py'),str(source),'--projections-output',str(output)],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0);self.assertFalse(output.exists())


def wp_dependency_model(explicit=True):
    m=final_model();m['activities'][0]['start_month']=4;m['tasks'][0]['start_month']=4
    m['work_packages'][1]['dependency_ids']=['WP1']
    if explicit:
        m['work_packages'][0].update(start_month=1,end_month=3)
        m['work_packages'][1].update(start_month=4,end_month=12)
    else:
        m['work_packages'][0]['activity_ids']=['A0']
        m['activities'].append({'id':'A0','wp_id':'WP1','partner_id':'P1','objective_ids':['O1'],'assignment_evidence':'Synthetic management activity evidence','start_month':1,'end_month':3})
    return m


class ModelRound3Regressions(unittest.TestCase):
    def test_optional_delivery_and_milestone_intervals_never_export_reversed_or_partial_ranges(self):
        for table in ('deliverables','milestones'):
            for start,end in ((12,1),(0,12),(1,13),(True,12),(1,None)):
                with self.subTest(table=table,start=start,end=end):
                    m=final_model();m[table][0].update(start_month=start,end_month=end)
                    self.assertFalse(check_model(m,False)['passed']);self.assertFalse(check_model(m,True)['passed'])
                    with self.assertRaises(ValueError):annex_projections(m)
    def test_due_only_and_null_optional_interval_are_valid_delivery_points(self):
        for table in ('deliverables','milestones'):
            for null_range in (False,True):
                with self.subTest(table=table,null_range=null_range):
                    m=final_model()
                    if null_range:m[table][0].update(start_month=None,end_month=None)
                    self.assertTrue(check_model(m,True)['passed'])
                    row=next(r for r in annex_projections(m)['gantt-table'] if r['row_kind']==table)
                    self.assertEqual((row['start_month'],row['end_month'],row['due_month']),(12,12,12))
    def test_declared_delivery_gate_window_contains_its_due_point(self):
        for table in ('deliverables','milestones'):
            with self.subTest(table=table):
                m=final_model();m[table][0].update(start_month=9,end_month=12,due_month=12)
                self.assertTrue(check_model(m,True)['passed'])
                for due in (8,13):
                    m[table][0]['due_month']=due
                    codes=[i['code'] for i in check_model(m,False)['issues']];self.assertIn('deadline-outside-delivery-window',codes)
                    with self.assertRaises(ValueError):annex_projections(m)
                m[table][0].update(start_month=9,end_month=11,due_month=12)
                self.assertIn('deadline-outside-delivery-window',[i['code'] for i in check_model(m,False)['issues']])
    def test_wp_activity_task_supplementary_deadline_is_not_before_end_but_may_follow_it(self):
        for table in ('work_packages','activities','tasks'):
            with self.subTest(table=table):
                m=final_model();row=m[table][1] if table=='work_packages' else m[table][0]
                if table=='work_packages':row.update(start_month=1,end_month=12)
                end=row['end_month'];row['due_month']=end-1
                self.assertIn('deadline-before-production-end',[i['code'] for i in check_model(m,False)['issues']])
                with self.assertRaises(ValueError):annex_projections(m)
                row['due_month']=end;self.assertTrue(check_model(m,True)['passed'])
        m=final_model();m['tasks'][0]['due_month']=9
        self.assertTrue(check_model(m,True)['passed'])
        row=next(r for r in annex_projections(m)['gantt-table'] if r['entity_id']=='T1')
        self.assertEqual((row['start_month'],row['end_month'],row['due_month']),(1,6,9))
        task=next(r for r in annex_projections(m)['ka2-task-file'] if r['task_id']=='T1')
        self.assertEqual((task['end_month'],task['due_month']),(6,9))
    def test_wp_deadline_with_only_activity_period_still_cannot_precede_completion(self):
        m=final_model();m['work_packages'][1]['due_month']=9
        self.assertIn('wp-deadline-before-activity-completion',[i['code'] for i in check_model(m,False)['issues']])
        m['work_packages'][1]['due_month']=12;self.assertTrue(check_model(m,True)['passed'])
    def test_deadline_after_productive_task_activity_end_is_a_valid_due_only_delivery(self):
        m=final_model();m['activities'][0]['end_month']=9;m['tasks'][1]['end_month']=9
        m['deliverables'][0]['due_month']=12
        self.assertTrue(check_model(m,True)['passed']);d=next(r for r in annex_projections(m)['gantt-table'] if r['entity_id']=='D1')
        self.assertEqual((d['start_month'],d['end_month'],d['due_month']),(12,12,12))
    def test_wp_predecessors_are_resolved_unambiguous_and_acyclic(self):
        for dependency in (['WP404'],['WP1'],['WP1','WP1']):
            with self.subTest(dependency=dependency):
                m=final_model();m['work_packages'][0]['dependency_ids']=dependency
                self.assertFalse(check_model(m,True)['passed']);self.assertFalse(check_model(m,False)['passed'])
                with self.assertRaises(ValueError):annex_projections(m)
        m=wp_dependency_model();m['work_packages'][0]['dependency_ids']=['WP2']
        self.assertIn('cyclic-dependency',[i['code'] for i in check_model(m,True)['issues']])
    def test_wp_predecessor_schema_rejects_wrong_types(self):
        for value in (None,'WP1',[True]):
            with self.subTest(value=value):
                m=final_model();m['work_packages'][0]['dependency_ids']=value
                self.assertFalse(check_model(m,True)['passed'])
                self.assertFalse(check_model(m,False)['passed'])
                with self.assertRaises(ValueError):annex_projections(m)
    def test_valid_wp_dependencies_use_explicit_or_complete_included_activity_calendar(self):
        for explicit in (True,False):
            with self.subTest(explicit=explicit):
                m=wp_dependency_model(explicit);before=copy.deepcopy(m)
                self.assertTrue(check_model(m,True)['passed'],check_model(m,True)['issues']);self.assertEqual(m,before)
                wp=next(r for r in annex_projections(m)['gantt-table'] if r['entity_id']=='WP2');self.assertEqual(wp['predecessor_ids'],['WP1'])
                prior=next(r for r in annex_projections(m)['gantt-table'] if r['entity_id']=='WP1')
                self.assertEqual((prior['start_month'],prior['end_month'],wp['start_month'],wp['end_month']),(1,3,4,12))
                self.assertEqual(wp['calendar_origin'],'declared_interval' if explicit else 'activities')
                if not explicit:
                    self.assertEqual((prior['calendar_activity_ids'],wp['calendar_activity_ids']),(['A0'],['A1']))
                    self.assertNotIn('start_month',m['work_packages'][0]);self.assertNotIn('start_month',m['work_packages'][1])
    def test_wp_due_with_activities_preserves_same_known_production_period_and_separate_deadline(self):
        m=wp_dependency_model(False);m['activities'][0]['end_month']=9;m['tasks'][1]['end_month']=9;m['work_packages'][1]['due_month']=12;before=copy.deepcopy(m)
        self.assertTrue(check_model(m,True)['passed'])
        wp=next(r for r in annex_projections(m)['gantt-table'] if r['entity_id']=='WP2')
        self.assertEqual((wp['start_month'],wp['end_month'],wp['due_month'],wp['calendar_origin'],wp['calendar_activity_ids']),(4,9,12,'activities',['A1']))
        self.assertEqual(m,before)
    def test_wp_declared_temporal_dependency_cannot_overlap_its_predecessor(self):
        m=wp_dependency_model();m['work_packages'][0]['end_month']=5
        self.assertIn('dependency-schedule-overlap',[i['code'] for i in check_model(m,False)['issues']])
        with self.assertRaises(ValueError):annex_projections(m)
        m['work_packages'][0]['end_month']=3;self.assertTrue(check_model(m,True)['passed'])
    def test_unknown_calendar_on_voluntary_wp_dependency_stays_open_without_fabrication(self):
        m=final_model();m['work_packages'][1]['dependency_ids']=['WP1'];before=copy.deepcopy(m)
        self.assertTrue(check_model(m,False)['passed'])
        self.assertIn('wp-dependency-calendar-unverified',[i['code'] for i in check_model(m,True)['issues']]);self.assertEqual(m,before)
    def test_routes_without_wp_receive_no_fictitious_dependencies_or_periods(self):
        m={table:[] for table in TABLES};m['schema_version']=MODEL_VERSION;m['project']={'program':'ESC','year':2026,'action':'ESC50-HOST-SUPPORT','sector':'ESC','quality_label_requirements_evidence':'Synthetic label scope only'};m['partners']=[{'id':'P1'}]
        self.assertTrue(check_model(m,True)['passed']);self.assertEqual(annex_projections(m)['gantt-table'],[])

if __name__=='__main__':unittest.main()
