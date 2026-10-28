from pathlib import Path
import copy
import json
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from application import check_answers,counts
from form_profile import validate_profile

class CharacterTests(unittest.TestCase):
    def profile(self,maximum): return {'questions':[{'id':'Q1','max_chars':maximum,'kind':'text','required':True}]}
    def test_limit_includes_spaces_and_newlines(self):
        r=check_answers([{'question_id':'Q1','text':'a b\nc'}],self.profile(5)); self.assertTrue(r['passed']); self.assertEqual(r['rows'][0]['remaining'],0)
        r=check_answers([{'question_id':'Q1','text':'a b\nc '}],self.profile(5)); self.assertFalse(r['passed'])
    def test_utf16_and_raw_linebreaks_are_conservative(self):
        self.assertEqual(counts('😀')['utf16_units'],2)
        self.assertFalse(check_answers([{'question_id':'Q1','text':'😀'}],self.profile(1))['passed'])
        r=check_answers([{'question_id':'Q1','text':'a\r\nb'}],self.profile(3)); self.assertFalse(r['passed'])
    def test_unknown_limit_does_not_become_pass(self):
        self.assertFalse(check_answers([{'question_id':'Q1','text':'text'}],self.profile(None))['passed'])
    def test_unverified_higher_override_does_not_bypass_limit(self):
        r=check_answers([{'question_id':'Q1','text':'long answer','max_chars':100}],self.profile(3))
        self.assertFalse(r['passed']); self.assertIn('unverified-limit-override',[i['code'] for i in r['issues']])
    def test_repeated_instances_and_missing_answers(self):
        a={'form_instance':{'program':'ERASMUS','year':2026,'action':'KA220-ADU','sector':'ADU','round':'March','current_call_verified':True,'verification_source':'Actual form 2026 field','all_limits_verified':True,'coverage_verified':True,
                          'required_instances':[{'question_id':'Q1','instance':'WP2'},{'question_id':'Q1','instance':'WP3'}],
                          'applicable_fields':[{'question_id':'Q1','instance':'WP2','required':True,'verification_source':'Synthetic current repeated field'},{'question_id':'Q1','instance':'WP3','required':True,'verification_source':'Synthetic current repeated field'}]},
           'answers':[{'question_id':'Q1','instance':'WP2','text':'OK'}]}
        self.assertFalse(check_answers(a,self.profile(5),True)['passed'])
        a['answers'].append({'question_id':'Q1','instance':'WP3','text':'OK'});p=self.profile(5);p['questions'][0]['repeatable']=True;self.assertTrue(check_answers(a,p,True)['passed'])
    def test_empty_answers_never_ready(self):
        self.assertFalse(check_answers({'form_instance':{},'answers':[]},self.profile(5),True)['passed'])
    def test_occurrence_specific_limit_is_applied(self):
        p=self.profile(None); p['questions'][0]['repeatable']=True; p['questions'][0]['occurrences']=[{'id':'WP2-Q1','max_chars':200,'context':{'work_package':2}},{'id':'WP3-Q1','max_chars':100,'context':{'work_package':3}}]
        r=check_answers([{'question_id':'Q1','instance':'WP3','text':'x'*120}],p)
        self.assertIn('over-limit',[i['code'] for i in r['issues']]); self.assertEqual(r['rows'][0]['maximum'],100)
        r=check_answers([{'question_id':'Q1','instance':'custom','text':'x'*120}],p)
        self.assertIn('ambiguous-occurrence-limit',[i['code'] for i in r['issues']])
    def test_alias_duplicate_and_wrong_context_are_rejected(self):
        p=self.profile(2000); p['questions'][0]['occurrences']=[{'id':'WP2-Q1','max_chars':1000,'context':{'work_package':2}},{'id':'WP3-Q1','max_chars':2000,'context':{'work_package':3}}]
        a=[{'question_id':'Q1','instance':'WP2','text':'OK'},{'question_id':'Q1','instance':'alias','occurrence_id':'WP2-Q1','text':'OK'}]
        self.assertIn('duplicate-physical-occurrence',[i['code'] for i in check_answers(a,p)['issues']])
        a=[{'question_id':'Q1','instance':'WP2','occurrence_id':'WP3-Q1','text':'x'*1500}]
        self.assertIn('instance-occurrence-context-mismatch',[i['code'] for i in check_answers(a,p)['issues']])
    def test_strict_form_identity_cannot_switch_program(self):
        p=self.profile(2000); p['programme']='ERASMUS'; p['action_family']='KA220'
        a={'form_instance':{'program':'ESC','year':2026,'action':'ESC30','sector':'ESC','round':'October','current_call_verified':True,'verification_source':'actual form','coverage_verified':True,'all_limits_verified':True},'answers':[{'question_id':'Q1','text':'OK'}]}
        self.assertIn('form-profile-program-mismatch',[i['code'] for i in check_answers(a,p,True)['issues']])

class IdentityRegressions(unittest.TestCase):
    def profile(self):
        return {'questions':[{'id':'Q1','kind':'text','repeatable':True,'max_chars':100,'occurrences':[{'id':'Q1-P1','max_chars':100,'context':{'partner':'P1'}},{'id':'Q1-P2','max_chars':100,'context':{'partner':'P2'}}]}]}
    def answers(self,instance='P1'):
        return {'form_instance':{'program':'ERASMUS','year':2026,'action':'KA220-YOU','sector':'YOU','round':'Synthetic','current_call_verified':True,'coverage_verified':True,'all_limits_verified':True,'verification_source':'Synthetic form locator; not a real call','applicable_fields':[{'question_id':'Q1','instance':instance,'required':True,'verification_source':'Synthetic repeated field locator'}]},'answers':[{'question_id':'Q1','instance':instance,'text':'Structural fixture'}]}
    def codes(self,a,p=None):return [i['code'] for i in check_answers(a,p or self.profile(),True)['issues']]
    def test_partner_cannot_borrow_other_partner_occurrence(self):
        a=self.answers('P2');a['answers'][0]['occurrence_id']='Q1-P1'
        self.assertIn('instance-occurrence-context-mismatch',self.codes(a))
    def test_wp_activity_and_role_contexts_are_checked(self):
        for key,value,wrong,instance in [('work_package',2,3,'WP3'),('activity_id','A1','A2','A2'),('contact_role','representative','contact','custom')]:
            with self.subTest(key=key):
                p={'questions':[{'id':'Q1','max_chars':100,'repeatable':True,'occurrences':[{'id':'physical','max_chars':100,'context':{key:value}}]}]}
                a=self.answers(instance);a['answers'][0].update(occurrence_id='physical',context={key:wrong})
                self.assertIn('instance-occurrence-context-mismatch',self.codes(a,p))
    def test_unknown_answer_instance_cannot_hide_behind_other_na_pair(self):
        a=self.answers();a['form_instance']['applicable_fields'][0].update(required=False,not_applicable=True,reason='Synthetic P1 not applicable');a['answers'][0]['instance']='P7'
        self.assertIn('answer-instance-not-in-applicability-matrix',self.codes(a))
    def test_nonrepeatable_unlisted_instance_is_rejected(self):
        p={'questions':[{'id':'Q1','max_chars':100,'repeatable':False}]};a=self.answers('default');a['answers'][0]['instance']='unlisted'
        codes=self.codes(a,p);self.assertIn('answer-instance-not-in-applicability-matrix',codes);self.assertIn('nonrepeatable-question-instance',codes)
    def test_true_new_current_instance_requires_declaration_and_localized_context(self):
        a=self.answers('P3');a['form_instance']['applicable_fields'][0]['context']={'partner_id':'P3'}
        a['answers'][0].update(max_chars=80,limit_verified=True,verification_source='Synthetic P3 field counter')
        self.assertTrue(check_answers(a,self.profile(),True)['passed'])
        a['form_instance']['applicable_fields'][0].pop('verification_source')
        self.assertIn('new-field-instance-context-unverified',self.codes(a))
    def test_verified_matrix_cap_cannot_disagree_with_answer_override(self):
        a=self.answers();a['form_instance']['applicable_fields'][0]['max_chars']=5;a['answers'][0].update(max_chars=100,limit_verified=True,verification_source='Synthetic conflicting counter proof')
        self.assertIn('current-field-limit-mismatch',self.codes(a))
    def test_duplicate_profile_limits_are_rejected_before_counting_both_orders(self):
        for caps in ((5,100),(100,5)):
            with self.subTest(caps=caps):
                p={'questions':[{'id':'Q1','max_chars':c} for c in caps]};result=check_answers([{'question_id':'Q1','text':'x'*20}],p)
                self.assertFalse(result['passed']);self.assertEqual(result['rows'],[]);self.assertIn('duplicate-profile-question-id',[i['code'] for i in result['issues']])
    def test_duplicate_occurrence_ids_and_rich_registry_fail_closed(self):
        p=self.profile();p['questions'][0]['occurrences'][1]['id']='Q1-P1'
        self.assertIn('duplicate-profile-occurrence-id',[i['code'] for i in validate_profile(p)['issues']])
        p=self.profile();p['fields']=[{'id':'Q1'},{'id':'Q1'}]
        self.assertFalse(validate_profile(p)['passed'])
        for rich in ([{'id':[]}],[{'id':'Q1','occurrences':{}}],[{'id':'Q1','max_chars':5}],[{'id':'Q1','occurrences':[{'id':'Q1-P1','max_chars':100,'context':{'partner':'P2'}},{'id':'Q1-P2','max_chars':100,'context':{'partner':'P2'}}]}]):
            p=self.profile();p['fields']=rich;self.assertFalse(validate_profile(p)['passed'])
    def test_profile_structured_types_fail_without_runtime_exceptions(self):
        for update in ({'questions':{}},{'questions':[None]},{'questions':[{'id':[]} ]},{'questions':[{'id':'Q1','occurrences':{}}]},{'questions':[{'id':'Q1','kind':[]}]},{'questions':[{'id':'Q1','repeatable':'false'}]},{'questions':[{'id':'Q1','max_chars':True}]},{'questions':[{'id':'Q1','occurrences':[{'id':'physical','context':[]}]}]}):
            with self.subTest(update=update):self.assertFalse(check_answers([],update)['passed'])
    def test_answer_and_matrix_structured_types_fail_closed(self):
        for mutation in ('answers-dict','answer-null','instance-list','form-list','matrix-list','matrix-duplicate','matrix-context-conflict','verified-string'):
            with self.subTest(mutation=mutation):
                a=self.answers()
                if mutation=='answers-dict':a['answers']={}
                elif mutation=='answer-null':a['answers']=[None]
                elif mutation=='instance-list':a['answers'][0]['instance']=[]
                elif mutation=='form-list':a['form_instance']=[]
                elif mutation=='matrix-list':a['form_instance']['applicable_fields']=[[]]
                elif mutation=='matrix-duplicate':a['form_instance']['applicable_fields']*=2
                elif mutation=='matrix-context-conflict':a['form_instance']['applicable_fields'][0]['context']={'partner_id':'P2'}
                elif mutation=='verified-string':a['form_instance']['current_call_verified']='true'
                self.assertFalse(check_answers(a,self.profile(),True)['passed'])
    def test_unused_matrix_occurrence_conflict_is_rejected(self):
        a=self.answers('P2');a['form_instance']['applicable_fields'][0].update(required=False,occurrence_id='Q1-P1');a['answers']=[]
        self.assertIn('invalid-applicability-context',self.codes(a))
    def test_distributed_98_questions_346_occurrences_preserved_and_still_unverified(self):
        path=Path(__file__).resolve().parents[1]/'config/forms/ka220-user-template.json';p=json.loads(path.read_text());self.assertTrue(validate_profile(p)['passed']);self.assertEqual(len(p['questions']),98);self.assertEqual(sum(len(q.get('occurrences',[])) for q in p['questions']),346);self.assertFalse(p['current_call_verified']);self.assertIsNone(p['call_year'])


class ContextRound2Regressions(unittest.TestCase):
    def profile(self):return {'program':'ERASMUS','action':'KA220-YOU','sector':'YOU','questions':[{'id':'Q','max_chars':100,'repeatable':True,'occurrences':[{'id':'Q1','max_chars':100,'context':{'partner_id':'P1','role':'legal'}},{'id':'Q2','max_chars':100,'context':{'partner_id':'P2','role':'legal'}}]}]}
    def answers(self,instance='P1'):
        return {'form_instance':{'program':'ERASMUS','year':2026,'action':'KA220-YOU','sector':'YOU','round':'R1','current_call_verified':True,'verification_source':'Synthetic field fixture; not a current form attestation','coverage_verified':True,'all_limits_verified':True,'applicable_fields':[{'question_id':'Q','instance':instance,'required':True,'occurrence_id':'Q1'}]},'answers':[{'question_id':'Q','instance':instance,'occurrence_id':'Q1','text':'Synthetic answer'}]}
    def test_unrelated_context_dimension_cannot_borrow_partner_occurrence(self):
        for dimension,instance in [('wp_id','WP9'),('activity_id','A9')]:
            with self.subTest(dimension=dimension):
                a=self.answers(instance);r=check_answers(a,self.profile(),True);self.assertFalse(r['passed']);self.assertIn('instance-occurrence-context-mismatch',[i['code'] for i in r['issues']]);self.assertIn('invalid-applicability-context',[i['code'] for i in r['issues']])
    def test_explicit_dimension_not_in_physical_context_fails_without_a_conventional_id(self):
        a=self.answers();a['answers'][0]['context']={'wp_id':'WP9'}
        self.assertIn('instance-occurrence-context-mismatch',[i['code'] for i in check_answers(a,self.profile(),True)['issues']])
        a=self.answers();a['form_instance']['applicable_fields'][0]['context']={'activity_id':'A9'}
        self.assertIn('invalid-applicability-context',[i['code'] for i in check_answers(a,self.profile(),True)['issues']])
    def test_compatible_aliases_retain_occurrence_identity_without_inventing_another_context(self):
        a=self.answers('representative-alias');a['answers'][0]['context']={'partner':'P1','contact_role':'legal'};a['form_instance']['applicable_fields'][0]['context']={'partner_id':'P1','role':'legal'}
        self.assertTrue(check_answers(a,self.profile(),True)['passed'])
        self.assertTrue(check_answers(self.answers(),self.profile(),True)['passed'])
    def test_new_current_partner_instance_is_declared_with_supported_dimensions(self):
        a=self.answers('P3');a['answers'][0].pop('occurrence_id');item=a['form_instance']['applicable_fields'][0];item.pop('occurrence_id');item.update(context={'partner_id':'P3','role':'legal'},verification_source='Synthetic additional partner field')
        a['answers'][0].update(max_chars=80,limit_verified=True,verification_source='Synthetic additional field counter');self.assertTrue(check_answers(a,self.profile(),True)['passed'])
        a['answers'][0]['instance']='WP9';item.update(instance='WP9',context={'wp_id':'WP9'})
        self.assertIn('new-field-instance-context-dimensions-unverified',[i['code'] for i in check_answers(a,self.profile(),True)['issues']])
    def test_unknown_runtime_context_keys_cannot_disappear_in_normalization(self):
        a=self.answers();a['answers'][0]['context']={'work_package_id':'WP9'}
        self.assertFalse(check_answers(a,self.profile(),True)['passed'])

if __name__=='__main__': unittest.main()
