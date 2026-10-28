#!/usr/bin/env python3
"""Check plain-text application answers against localized form limits.

Counts include spaces and line breaks. Never trims or truncates an answer.
The online form remains authoritative about its counting convention.
"""
import argparse
import json
from pathlib import Path
import sys
from form_profile import validate_profile,normalize_context,instance_context,CONTEXT_ALIASES

ROOT=Path(__file__).resolve().parents[1]

def counts(text):
    raw_characters=len(text); raw_utf16_units=len(text.encode('utf-16-le'))//2
    text=text.replace('\r\n','\n').replace('\r','\n')
    return {'characters':len(text),'utf16_units':len(text.encode('utf-16-le'))//2,
            'raw_characters':raw_characters,'raw_utf16_units':raw_utf16_units,'words':len(text.split()),'line_breaks':text.count('\n')}

def identity_context(context):
    if not isinstance(context,dict):raise ValueError('Answer/applicability context must be an object')
    unknown=set(context)-set(CONTEXT_ALIASES)
    if unknown:raise ValueError('Unknown runtime context dimension: '+str(sorted(unknown,key=str)))
    return normalize_context(context)


def questions(profile):
    validation=validate_profile(profile)
    if not validation['passed']: raise ValueError('Ambiguous or invalid form profile: '+json.dumps(validation['issues']))
    return {q['id']:q for q in profile['questions']}

def check_answers(answers,profile,strict=False):
    rows=[]; issues=[]
    validation=validate_profile(profile)
    if not validation['passed']: return {'passed':False,'strict_current_form':strict,'rows':[],'issues':validation['issues']}
    registry=questions(profile)
    rows_in=answers.get('answers',[]) if isinstance(answers,dict) else answers
    if not isinstance(rows_in,list): return {'passed':False,'rows':[],'issues':[{'code':'answers-not-list'}]}
    seen=set(); seen_occurrences=set(); matrix={}
    form_instance=answers.get('form_instance',{}) if isinstance(answers,dict) else {}
    if not isinstance(form_instance,dict): return {'passed':False,'rows':[],'issues':[{'code':'form-instance-not-object'}]}
    for proof_field in ('verification_source',):
        if proof_field in form_instance and not isinstance(form_instance[proof_field],(str,dict)): issues.append({'code':'invalid-form-instance-type','field':proof_field})
    for field in ('current_call_verified','coverage_verified','all_limits_verified'):
        if field in form_instance and not isinstance(form_instance[field],bool): issues.append({'code':'invalid-form-instance-type','field':field})
    if strict:
        for key in ('program','year','action','sector','round'):
            if not form_instance.get(key) or (key=='year' and (isinstance(form_instance[key],bool) or not isinstance(form_instance[key],int))) or (key!='year' and not isinstance(form_instance[key],str)): issues.append({'code':'form-identity-incomplete','field':key})
        profile_program=profile.get('program',profile.get('programme'))
        if profile_program and profile_program!=form_instance.get('program'): issues.append({'code':'form-profile-program-mismatch'})
        family=profile.get('action_family')
        if family and not (form_instance.get('action')==family or str(form_instance.get('action','')).startswith(family+'-')): issues.append({'code':'form-profile-action-mismatch'})
        if profile.get('action') and profile['action']!=form_instance.get('action'): issues.append({'code':'form-profile-exact-action-mismatch'})
        if profile.get('sector') and profile['sector']!=form_instance.get('sector'): issues.append({'code':'form-profile-sector-mismatch'})
        if profile.get('call_year') and profile['call_year']!=form_instance.get('year'): issues.append({'code':'form-profile-year-mismatch'})
    if strict and (not form_instance.get('current_call_verified') or not form_instance.get('verification_source')):
        issues.append({'code':'current-form-unverified','message':'Verify the actual year/round form and localize its evidence.'})
    if strict and not form_instance.get('coverage_verified'):
        issues.append({'code':'current-form-question-coverage-unverified'})
    applicability=form_instance.get('applicable_fields',[])
    if not isinstance(applicability,list): issues.append({'code':'applicability-matrix-not-list'}); applicability=[]
    if strict:
        if not applicability: issues.append({'code':'applicability-matrix-missing'})
        covered=set()
        for field in applicability:
            if not isinstance(field,dict): issues.append({'code':'invalid-field-applicability-entry'}); continue
            qid=field.get('question_id'); instance=field.get('instance','default')
            if not isinstance(qid,str) or not isinstance(instance,str) or not instance:
                issues.append({'code':'invalid-field-applicability-entry'}); continue
            covered.add(qid); key=(qid,instance)
            if key in matrix: issues.append({'code':'duplicate-applicability-pair','question_id':qid,'instance':instance})
            matrix[key]=field
            if 'max_chars' in field and field['max_chars'] is not None and (isinstance(field['max_chars'],bool) or not isinstance(field['max_chars'],int) or field['max_chars']<=0): issues.append({'code':'invalid-applicability-limit','question_id':qid,'instance':instance})
            if 'current_repeatable' in field and not isinstance(field['current_repeatable'],bool): issues.append({'code':'invalid-field-applicability-entry','question_id':qid})
            if 'verification_source' in field and not isinstance(field['verification_source'],(str,dict)): issues.append({'code':'invalid-field-applicability-entry','question_id':qid})
            if 'not_applicable' in field and not isinstance(field['not_applicable'],bool): issues.append({'code':'invalid-field-applicability-entry','question_id':qid})
            try:
                inferred=instance_context(instance); context=identity_context(field.get('context',{}))
                if any(k in context and context[k]!=v for k,v in inferred.items()): raise ValueError('Instance and matrix context differ')
                context={**inferred,**context}
                oid=field.get('occurrence_id')
                if oid is not None:
                    if not isinstance(oid,str): raise ValueError('Occurrence ID must be a string')
                    occurrence=next((o for o in registry.get(qid,{}).get('occurrences',[]) if o['id']==oid),None)
                    if occurrence is None: raise ValueError('Unknown matrix occurrence')
                    physical=normalize_context(occurrence.get('context',{}))
                    if any(k not in physical or physical[k]!=v for k,v in context.items()): raise ValueError('Matrix and occurrence contexts differ')
            except ValueError as exc: issues.append({'code':'invalid-applicability-context','question_id':qid,'instance':instance,'message':str(exc)})
            if qid not in registry or not isinstance(field.get('required'),bool) or not (field.get('verification_source') or form_instance.get('verification_source')):
                issues.append({'code':'invalid-field-applicability-entry','question_id':qid})
            if field.get('not_applicable') and (field.get('required') or not field.get('reason')):
                issues.append({'code':'invalid-not-applicable-field','question_id':qid})
        for qid in registry:
            if qid not in covered: issues.append({'code':'question-applicability-not-resolved','question_id':qid})
    if strict and not rows_in: issues.append({'code':'no-application-answers'})
    for answer in rows_in:
        if not isinstance(answer,dict): issues.append({'code':'answer-not-object'}); continue
        qid=answer.get('question_id',answer.get('id')); instance=answer.get('instance','default')
        if not isinstance(qid,str) or not isinstance(instance,str) or not instance:
            issues.append({'code':'invalid-answer-identity'}); continue
        for proof_field in ('verification_source',):
            if proof_field in answer and not isinstance(answer[proof_field],(str,dict)): issues.append({'code':'invalid-answer-type','question_id':qid,'field':proof_field})
        for field in ('limit_verified',):
            if field in answer and not isinstance(answer[field],bool): issues.append({'code':'invalid-answer-type','question_id':qid,'field':field})
        if qid not in registry:
            issues.append({'code':'unknown-question','question_id':qid}); continue
        key=(qid,instance)
        if key in seen:
            issues.append({'code':'duplicate-answer','question_id':qid,'instance':instance}); continue
        seen.add(key); q=registry[qid]
        matrix_entry=matrix.get(key)
        if strict and not matrix_entry: issues.append({'code':'answer-instance-not-in-applicability-matrix','question_id':qid,'instance':instance})
        if strict and instance!='default' and not (q.get('repeatable') or len(q.get('occurrences',[]))>1 or (matrix_entry and matrix_entry.get('current_repeatable') is True and matrix_entry.get('verification_source'))):
            issues.append({'code':'nonrepeatable-question-instance','question_id':qid,'instance':instance})
        text=answer.get('text','')
        if not isinstance(text,str):
            issues.append({'code':'answer-not-text','question_id':qid}); continue
        occurrence_id=answer.get('occurrence_id'); occurrences=q.get('occurrences',[])
        matched=[o for o in occurrences if o['id']==(occurrence_id or instance)]
        try:
            context=instance_context(instance)
            for extra in (answer.get('context',{}),matrix_entry.get('context',{}) if matrix_entry else {}):
                for identity,value in identity_context(extra).items():
                    if identity in context and context[identity]!=value: raise ValueError('Instance contexts disagree: '+identity)
                    context[identity]=value
        except ValueError as exc:
            context={}; issues.append({'code':'instance-occurrence-context-mismatch','question_id':qid,'instance':instance,'message':str(exc)})
        if not matched and not occurrence_id and context:
            matched=[o for o in occurrences if all(normalize_context(o.get('context',{})).get(k)==v for k,v in context.items())]
        if occurrence_id is not None and (not isinstance(occurrence_id,str) or not matched): issues.append({'code':'unknown-occurrence','question_id':qid,'occurrence_id':occurrence_id})
        if len(matched)>1: issues.append({'code':'ambiguous-physical-occurrence','question_id':qid,'instance':instance})
        occurrence=matched[0] if len(matched)==1 else None
        if occurrence:
            physical_context=normalize_context(occurrence.get('context',{}))
            if any(k not in physical_context or physical_context[k]!=v for k,v in context.items()):
                issues.append({'code':'instance-occurrence-context-mismatch','question_id':qid,'instance':instance,'occurrence_id':occurrence['id']})
            if matrix_entry and matrix_entry.get('occurrence_id') and matrix_entry['occurrence_id']!=occurrence['id']:
                issues.append({'code':'matrix-occurrence-mismatch','question_id':qid,'instance':instance})
            occurrence_key=(qid,occurrence['id'])
            if occurrence_key in seen_occurrences: issues.append({'code':'duplicate-physical-occurrence','question_id':qid,'occurrence_id':occurrence['id']})
            seen_occurrences.add(occurrence_key)
        elif strict and matrix_entry and matrix_entry.get('occurrence_id'):
            issues.append({'code':'unknown-matrix-occurrence','question_id':qid,'instance':instance})
        # An actual newly repeated field can be declared by the current matrix.
        # Its context and override must come from localized current-form proof.
        context_patterns=[set(normalize_context(o.get('context',{}))) for o in occurrences]
        if strict and instance!='default' and not occurrence and context and any(context_patterns) and not any(set(context).issubset(pattern) for pattern in context_patterns):
            issues.append({'code':'new-field-instance-context-dimensions-unverified','question_id':qid,'instance':instance})
        if strict and instance!='default' and not occurrence and not (matrix_entry and context and matrix_entry.get('verification_source')):
            issues.append({'code':'new-field-instance-context-unverified','question_id':qid,'instance':instance})
        if occurrences and len({o.get('max_chars') for o in occurrences})>1 and not occurrence and 'max_chars' not in answer:
            issues.append({'code':'ambiguous-occurrence-limit','question_id':qid,'instance':instance})
        provisional_limit=occurrence.get('max_chars') if occurrence else q.get('max_chars')
        limit=answer.get('max_chars',provisional_limit)
        override='max_chars' in answer
        if strict and matrix_entry and 'max_chars' in matrix_entry and matrix_entry['max_chars']!=limit:
            issues.append({'code':'current-field-limit-mismatch','question_id':qid,'instance':instance})
        if override and (not answer.get('limit_verified') or not answer.get('verification_source')):
            issues.append({'code':'unverified-limit-override','question_id':qid})
        if limit is not None and (isinstance(limit,bool) or not isinstance(limit,int) or limit<=0):
            issues.append({'code':'invalid-limit','question_id':qid}); continue
        c=counts(text); conservative=max(c['raw_characters'],c['raw_utf16_units'],c['characters'],c['utf16_units'])
        text_kind=q.get('kind','text') in ('text','textarea','narrative','long-text','short-text')
        status='within-limit' if limit is not None and conservative<=limit else ('over-limit' if limit else 'limit-unknown')
        if text_kind and limit is None: issues.append({'code':'limit-unknown','question_id':qid})
        if limit and conservative>limit: issues.append({'code':'over-limit','question_id':qid,'excess':conservative-limit})
        if strict and (not text.strip() or any(marker in text for marker in ('[TODO]','[DA CONFERMARE]','[INSERT]'))):
            issues.append({'code':'unfinished-answer','question_id':qid})
        if strict and text_kind and not (answer.get('limit_verified') and answer.get('verification_source')) and not form_instance.get('all_limits_verified'):
            issues.append({'code':'field-limit-not-verified-for-current-form','question_id':qid})
        rows.append({'question_id':qid,'instance':instance,**c,'maximum':limit,'remaining':limit-conservative if limit else None,
                     'planning_target':int(limit*.95) if limit else None,'status':status,
                     'occurrence_id':occurrence['id'] if occurrence else None,
                     'limit_source':'project-verified-override' if override else 'supplied-template-occurrence-provisional' if occurrence else 'supplied-template-provisional'})
    if strict:
        for item in matrix.values():
            key=(item.get('question_id'),item.get('instance','default'))
            if item.get('required') and key not in seen: issues.append({'code':'missing-applicable-answer','question_id':key[0],'instance':key[1]})
            if item.get('not_applicable') and key in seen: issues.append({'code':'answer-for-nonapplicable-field','question_id':key[0],'instance':key[1]})
        required_instances=form_instance.get('required_instances',[])
        if not isinstance(required_instances,list): issues.append({'code':'required-instances-not-list'}); required_instances=[]
        for item in required_instances:
            if not isinstance(item,dict) or not isinstance(item.get('question_id'),str) or not isinstance(item.get('instance'),str): issues.append({'code':'invalid-required-instance'}); continue
            if (item['question_id'],item['instance']) not in matrix: issues.append({'code':'required-instance-not-in-matrix',**item})
            if (item['question_id'],item['instance']) not in seen:
                issues.append({'code':'missing-required-instance',**item})
    return {'passed':not issues,'strict_current_form':strict,'rows':rows,'issues':issues,
            'counting':'Spaces and line breaks included; normalized-LF and raw counts shown, maximum of code points and UTF-16 units used conservatively. Confirm online counter.'}

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('answers'); p.add_argument('--profile',required=True); p.add_argument('--strict',action='store_true'); p.add_argument('--output')
    a=p.parse_args(); result=check_answers(json.loads(Path(a.answers).read_text()),json.loads(Path(a.profile).read_text()),a.strict)
    if a.output: Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2)); return 0 if result['passed'] else 1

if __name__=='__main__': sys.exit(main())
