"""Structural schema regressions: the dependency-free subset is fail closed."""
import copy
import json
from pathlib import Path
import sys
import unittest
import tempfile
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from model_schema import validate_instance,validate_schema,KEYWORDS
from test_model_contract import final_model
import project_check


class SchemaRegressions(unittest.TestCase):
    def setUp(self):self.schema=json.loads((Path(__file__).resolve().parents[1]/'config/project-model.schema.json').read_text())
    def keywords(self,schema):
        keys=set()
        def walk(node):
            if not isinstance(node,dict):return
            keys.update(node)
            for key in ('properties','$defs'):
                for child in node.get(key,{}).values():walk(child)
            for key in ('items','additionalProperties'):
                if key in node:walk(node[key])
            for child in node.get('oneOf',[]):walk(child)
        walk(schema);return keys
    def test_every_keyword_in_the_actual_schema_is_supported_and_positive_matches(self):
        self.assertLessEqual(self.keywords(self.schema),KEYWORDS)
        self.assertTrue(validate_schema(self.schema)['passed'])
        m=final_model();before=copy.deepcopy(m);self.assertTrue(validate_instance(m,self.schema)['passed']);self.assertEqual(m,before)
    def test_check_model_strict_does_not_ignore_an_unsupported_schema_keyword(self):
        original=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'config').mkdir()
            for name in ('actions.json','action-modes.json'):(root/'config'/name).write_bytes((original/'config'/name).read_bytes())
            schema=copy.deepcopy(self.schema);schema['$defs']['unused']={'maxLength':4};(root/'config/project-model.schema.json').write_text(json.dumps(schema))
            with patch.object(project_check,'ROOT',root):result=project_check.check_model(final_model(),True)
            self.assertFalse(result['passed']);self.assertTrue(any(i['code']=='unsupported-or-invalid-model-schema' and i['keyword']=='maxLength' for i in result['issues']))
    def test_unknown_keyword_even_in_unused_definition_fails_closed(self):
        s=copy.deepcopy(self.schema);s['$defs']['unused']={'maxLength':4}
        result=validate_instance(final_model(),s)
        self.assertFalse(result['passed']);self.assertEqual(result['issues'][0]['keyword'],'maxLength')
    def test_refs_are_local_resolved_and_nonrecursive_and_siblings_apply(self):
        for ref in ('https://invalid.example/schema.json','#/missing'):
            self.assertFalse(validate_instance({}, {'$ref':ref})['passed'])
        s={'$defs':{'self':{'$ref':'#/$defs/self'}},'$ref':'#/$defs/self'}
        self.assertFalse(validate_schema(s)['passed'])
        s={'$defs':{'plain':{'type':'string'}},'$ref':'#/$defs/plain','minLength':2}
        self.assertTrue(validate_instance('ok',s)['passed']);self.assertFalse(validate_instance('x',s)['passed'])
    def test_types_unions_and_json_numeric_boolean_identity(self):
        self.assertTrue(validate_instance(None,{'type':['number','null']})['passed'])
        self.assertFalse(validate_instance('5',{'type':['number','null']})['passed'])
        self.assertFalse(validate_instance(True,{'type':'integer'})['passed'])
        self.assertTrue(validate_instance(1.0,{'type':'integer'})['passed'])
        self.assertFalse(validate_instance(1.5,{'type':'integer'})['passed'])
        self.assertFalse(validate_instance(True,{'const':1})['passed'])
        self.assertFalse(validate_instance(False,{'enum':[0]})['passed'])
        self.assertTrue(validate_instance(1.0,{'const':1})['passed'])
    def test_oneof_requires_exactly_one_successful_branch(self):
        s={'oneOf':[{'type':'number'},{'type':'integer'}]}
        self.assertFalse(validate_instance(1,s)['passed']);self.assertTrue(validate_instance(1.5,s)['passed']);self.assertFalse(validate_instance(True,s)['passed'])
    def test_array_unique_items_use_deep_json_value_equality(self):
        s={'type':'array','uniqueItems':True,'items':True}
        for value in ([1,1.0],[{'x':1,'y':2},{'y':2,'x':1}],[[1],[1]]):self.assertFalse(validate_instance(value,s)['passed'])
        self.assertTrue(validate_instance([True,1],s)['passed'])
        self.assertFalse(validate_instance([],{**s,'minItems':1})['passed'])
    def test_required_properties_additionalproperties_and_object_size(self):
        s={'type':'object','required':['x'],'properties':{'x':{'type':'string'}},'additionalProperties':False,'minProperties':1}
        self.assertTrue(validate_instance({'x':'ok'},s)['passed'])
        for value in ({},{'x':2},{'x':'ok','extra':True}):self.assertFalse(validate_instance(value,s)['passed'])
    def test_numeric_string_length_pattern_and_dates_are_asserted(self):
        self.assertFalse(validate_instance(-1,{'type':'number','minimum':0})['passed'])
        self.assertFalse(validate_instance('',{'type':'string','minLength':1})['passed'])
        pattern={'type':'string','pattern':r'^\d+(\.\d+)?$'}
        self.assertTrue(validate_instance('123.45',pattern)['passed']);self.assertFalse(validate_instance('-5',pattern)['passed']);self.assertFalse(validate_instance('١٢',pattern)['passed'])
        dates={'type':'string','format':'date'}
        self.assertTrue(validate_instance('2024-02-29',dates)['passed'])
        for value in ('2025-02-29','2026-9-12','20260912','2026-09-12T12:00:00Z'):self.assertFalse(validate_instance(value,dates)['passed'])
    def test_malformed_supported_schema_keywords_do_not_raise_or_get_ignored(self):
        for s in ({'type':[]},{'type':{}},{'required':True},{'items':[]},{'properties':[]},{'oneOf':[]},{'oneOf':[[]]},{'uniqueItems':'true'},{'minimum':True},{'minItems':-1},{'minProperties':None},{'pattern':'['},{'format':'uri'},{'$schema':'unknown'}):
            with self.subTest(schema=s):self.assertFalse(validate_instance({},s)['passed'])
    def test_nonjson_python_values_and_nonfinite_numbers_fail_even_in_open_properties(self):
        for value in ({'untyped':float('nan')},{'untyped':float('inf')},{'untyped':set()},{1:'not a JSON key'}):self.assertFalse(validate_instance(value,{'type':'object'})['passed'])
    def test_actual_requested_grant_null_and_string_plural_reference_are_distinct(self):
        m=final_model();m['project']['requested_grant']='120000'
        result=validate_instance(m,self.schema);self.assertFalse(result['passed']);self.assertTrue(any(i['path']=='/project/requested_grant' and i['keyword']=='type' for i in result['issues']))
        m=final_model();m['tasks'][0]['dependency_ids']=None;result=validate_instance(m,self.schema)
        self.assertFalse(result['passed']);self.assertTrue(any(i['path']=='/tasks/0/dependency_ids' and i['keyword']=='type' for i in result['issues']))

if __name__=='__main__':unittest.main()
