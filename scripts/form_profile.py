#!/usr/bin/env python3
"""Read a bounded question playbook window instead of loading the whole vault."""
import argparse
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]

CONTEXT_ALIASES = {'partner':'partner_id','partner_id':'partner_id','work_package':'wp_id','wp_id':'wp_id','activity':'activity_id','activity_id':'activity_id','contact_role':'role','role':'role'}

def normalize_context(context):
    """Normalize only identities, never workspace/example metadata into real facts."""
    if context is None: return {}
    if not isinstance(context,dict): raise ValueError('Context must be an object')
    result={}
    for key,target in CONTEXT_ALIASES.items():
        value=context.get(key)
        if value is None: continue
        if isinstance(value,bool) or not isinstance(value,(str,int)) or value=='': raise ValueError('Invalid context identity '+key)
        if target in ('wp_id','activity_id') and isinstance(value,int) and value<1: raise ValueError('Context number must be positive: '+key)
        if target=='wp_id' and isinstance(value,int): value='WP'+str(value)
        elif target=='activity_id' and isinstance(value,int): value='A'+str(value)
        elif not isinstance(value,str): raise ValueError('Context identity must be a string: '+key)
        if target in result and result[target]!=value: raise ValueError('Conflicting context aliases: '+target)
        result[target]=value
    return result

def instance_context(instance):
    """Conventional P/WP/A IDs are identities; other aliases need explicit context."""
    if not isinstance(instance,str) or not instance: raise ValueError('Instance must be a nonempty string')
    for prefix,key in [('WP','wp_id'),('P','partner_id'),('A','activity_id')]:
        if instance.startswith(prefix) and instance[len(prefix):].isdigit(): return {key:instance}
    return {}

def validate_profile(profile):
    """Validate the fields consumed by readers/checkers before making ID indexes.

    Rich editorial payload is retained verbatim and is not an official form.
    Repeated IDs in independent rich `fields` mirror the question registry once;
    they do not override it. Unknown descriptive metadata is not executed.
    """
    issues=[]
    def flag(code,**extra): issues.append({'code':code,**extra})
    if not isinstance(profile,dict): return {'passed':False,'issues':[{'code':'profile-not-object'}]}
    for key in ('current_call_verified','official','official_2026_form_verified'):
        if key in profile and not isinstance(profile[key],bool): flag('invalid-profile-type',field=key)
    for key in ('id','programme','program','action','action_family','sector'):
        if key in profile and (not isinstance(profile[key],str) or not profile[key]): flag('invalid-profile-type',field=key)
    for key in ('call_year','template_year'):
        if key in profile and profile[key] is not None and (isinstance(profile[key],bool) or not isinstance(profile[key],int)): flag('invalid-profile-type',field=key)
    if profile.get('program') and profile.get('programme') and profile['program']!=profile['programme']: flag('conflicting-profile-program-aliases')
    rows=profile.get('questions')
    if not isinstance(rows,list) or not rows: return {'passed':False,'issues':issues+[{'code':'profile-questions-not-nonempty-list'}]}
    qids=set(); occurrence_ids=set()
    kinds={'text','textarea','narrative','long-text','metadata','annex','choice','number','date','file','boolean','short-text'}
    for q in rows:
        if not isinstance(q,dict): flag('invalid-profile-question'); continue
        qid=q.get('id')
        if not isinstance(qid,str) or not qid: flag('invalid-profile-question-id'); continue
        if qid in qids: flag('duplicate-profile-question-id',question_id=qid)
        qids.add(qid)
        if 'kind' in q and (not isinstance(q['kind'],str) or q['kind'] not in kinds): flag('invalid-profile-kind',question_id=qid)
        for key in ('required','repeatable','current_call_verified'):
            if key in q and not isinstance(q[key],bool): flag('invalid-profile-question-type',question_id=qid,field=key)
        for key in ('prompt',):
            if key in q and not isinstance(q[key],str): flag('invalid-profile-question-type',question_id=qid,field=key)
        cap=q.get('max_chars')
        if cap is not None and (isinstance(cap,bool) or not isinstance(cap,int) or cap<=0): flag('invalid-profile-limit',question_id=qid)
        occurrences=q.get('occurrences',[])
        if not isinstance(occurrences,list): flag('invalid-profile-occurrences',question_id=qid); continue
        ids=[]
        for occurrence in occurrences:
            if not isinstance(occurrence,dict): flag('invalid-profile-occurrence',question_id=qid); continue
            oid=occurrence.get('id')
            if not isinstance(oid,str) or not oid: flag('invalid-profile-occurrence-id',question_id=qid); continue
            if oid in occurrence_ids: flag('duplicate-profile-occurrence-id',question_id=qid,occurrence_id=oid)
            occurrence_ids.add(oid); ids.append(oid)
            cap=occurrence.get('max_chars')
            if cap is not None and (isinstance(cap,bool) or not isinstance(cap,int) or cap<=0): flag('invalid-profile-occurrence-limit',question_id=qid,occurrence_id=oid)
            try: normalize_context(occurrence.get('context',{}))
            except ValueError as exc: flag('invalid-profile-occurrence-context',question_id=qid,occurrence_id=oid,message=str(exc))
        if 'occurrence_ids' in q and (not isinstance(q['occurrence_ids'],list) or q['occurrence_ids']!=ids): flag('profile-occurrence-registry-mismatch',question_id=qid)
    if issues: return {'passed':False,'issues':issues}
    if 'fields' in profile:
        fields=profile['fields']; seen=set()
        if not isinstance(fields,list): flag('invalid-profile-rich-fields')
        else:
            for field in fields:
                fid=field.get('id') if isinstance(field,dict) else None
                if not isinstance(fid,str) or fid not in qids or fid in seen: flag('invalid-or-duplicate-profile-rich-field',question_id=fid)
                if isinstance(fid,str): seen.add(fid)
                if not isinstance(field,dict) or not isinstance(fid,str) or fid not in qids: continue
                compact=next(q for q in rows if isinstance(q,dict) and q.get('id')==fid)
                if 'max_chars' in field and field['max_chars']!=compact.get('max_chars'): flag('profile-rich-limit-conflict',question_id=fid)
                if 'occurrences' in field:
                    rich=field['occurrences']; base=compact.get('occurrences',[])
                    if not isinstance(rich,list) or any(not isinstance(o,dict) for o in rich) or [o.get('id') for o in rich]!=[o.get('id') for o in base if isinstance(o,dict)]: flag('profile-rich-occurrence-conflict',question_id=fid); continue
                    for occurrence,original in zip(rich,base):
                        try:
                            if occurrence.get('max_chars')!=original.get('max_chars') or normalize_context(occurrence.get('context',{}))!=normalize_context(original.get('context',{})): flag('profile-rich-occurrence-conflict',question_id=fid,occurrence_id=occurrence.get('id'))
                        except ValueError: flag('profile-rich-occurrence-conflict',question_id=fid)
    return {'passed':not issues,'issues':issues}

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--profile',default='config/forms/ka220-user-template.json'); sub=p.add_subparsers(dest='cmd',required=True)
    q=sub.add_parser('list'); q.add_argument('--offset',type=int,default=0); q.add_argument('--limit',type=int,default=30)
    q=sub.add_parser('show'); q.add_argument('field'); q.add_argument('--offset',type=int,default=0); q.add_argument('--max-chars',type=int,default=8000)
    a=p.parse_args(); profile=json.loads((ROOT/a.profile).read_text())
    validation=validate_profile(profile)
    if not validation['passed']: raise ValueError(json.dumps(validation,ensure_ascii=False))
    if a.offset<0: raise ValueError('offset must be nonnegative')
    if a.cmd=='list':
        if not 1<=a.limit<=100: raise ValueError('limit must be 1..100')
        rows=profile['questions']; fields=[{k:q.get(k) for k in ('id','prompt','kind','max_chars','repeatable')} for q in rows[a.offset:a.offset+a.limit]]
        result={'fields':fields,'total':len(rows),'has_more':a.offset+a.limit<len(rows),'next_offset':a.offset+a.limit if a.offset+a.limit<len(rows) else None}
    else:
        if not 1<=a.max_chars<=50000: raise ValueError('max-chars must be 1..50000')
        field=next((q for q in profile['questions'] if q['id']==a.field),None)
        if not field: raise ValueError('Unknown question ID')
        if profile.get('id')=='ka220-user-template':
            body=(ROOT/'wiki/templates/ka220-question-playbook.md').read_text()
            start=re.search(r'^## '+re.escape(a.field)+r' · .+$',body,re.M)
            if not start: raise ValueError('Missing matching playbook section')
            end=re.search(r'^## ',body[start.end():],re.M); text=body[start.start():start.end()+end.start() if end else len(body)]
        else:
            rich=next((q for q in profile.get('fields',[]) if q['id']==a.field),field)
            text=json.dumps(rich,ensure_ascii=False,indent=2)
        content=text[a.offset:a.offset+a.max_chars]; next_offset=a.offset+len(content)
        result={'question_id':a.field,'max_chars':field.get('max_chars'),'current_call_verified':profile.get('current_call_verified',False),
                'window':{'offset':a.offset,'returned_chars':len(content),'total_chars':len(text),'has_more':next_offset<len(text),'next_offset':next_offset if next_offset<len(text) else None},'content':content}
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':
    try: main()
    except (ValueError,KeyError,OSError) as e: print(str(e),file=sys.stderr); sys.exit(1)
