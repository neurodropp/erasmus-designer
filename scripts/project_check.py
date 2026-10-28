#!/usr/bin/env python3
"""Cross-check project IDs, schedules, grant allocations and annex manifests.

This validates data relationships; it cannot establish substantive eligibility,
legal validity, needs evidence or impact causality without specialist review.
"""
import argparse
from datetime import date
from decimal import Decimal,InvalidOperation
import json
from pathlib import Path
import sys
from model_schema import validate_instance

ROOT=Path(__file__).resolve().parents[1]
MODEL_VERSION='project-model-v2'
LEGACY_TABLES=['partners','priorities','needs','objectives','work_packages','activities','outputs','results','impacts','kpis','budget_lines','dissemination','risks']
TABLES=LEGACY_TABLES+['tasks','deliverables','milestones']
LINKS={
 'objectives':{'need_ids':'needs','priority_ids':'priorities'},
 'work_packages':{'dependency_ids':'work_packages','objective_ids':'objectives','activity_ids':'activities','lead_partner_id':'partners','task_ids':'tasks','deliverable_ids':'deliverables','milestone_ids':'milestones'},
 'activities':{'objective_ids':'objectives','wp_id':'work_packages','partner_id':'partners','dependency_ids':'activities','task_ids':'tasks','deliverable_ids':'deliverables'},
 'tasks':{'activity_id':'activities','wp_id':'work_packages','partner_id':'partners','dependency_ids':'tasks','deliverable_ids':'deliverables'},
 'deliverables':{'task_ids':'tasks','output_ids':'outputs','wp_id':'work_packages','partner_id':'partners','dependency_ids':'deliverables'},
 'milestones':{'activity_ids':'activities','task_ids':'tasks','deliverable_ids':'deliverables','wp_id':'work_packages','partner_id':'partners','dependency_ids':'milestones'},
 'outputs':{'activity_ids':'activities','wp_id':'work_packages','deliverable_ids':'deliverables'},
 'results':{'output_ids':'outputs','objective_ids':'objectives'},
 'impacts':{'result_ids':'results'},
 'kpis':{'objective_ids':'objectives','output_ids':'outputs','deliverable_ids':'deliverables','result_ids':'results','impact_ids':'impacts','wp_id':'work_packages','partner_id':'partners'},
 'budget_lines':{'wp_id':'work_packages','activity_id':'activities','task_id':'tasks','deliverable_id':'deliverables','partner_id':'partners'},
 'dissemination':{'output_ids':'outputs','deliverable_ids':'deliverables','milestone_id':'milestones','kpi_ids':'kpis','partner_id':'partners','budget_line_id':'budget_lines'},
 'risks':{'activity_ids':'activities','task_ids':'tasks','deliverable_ids':'deliverables','wp_ids':'work_packages','partner_id':'partners'}
}


def action_mode(program, action, sector, year):
    """Resolve an exact indexed route; unknown annualities and scopes fail closed.

    Controls are a structural workflow method, not a full eligibility ruling.
    Read the matrix on each invocation so a changed/absent matrix cannot reuse
    previously cached controls during readiness checks.
    """
    matrix=json.loads((ROOT/'config/action-modes.json').read_text())
    actions=json.loads((ROOT/'config/actions.json').read_text())
    rows=matrix['routes']; catalog={r['code']:r for r in actions}
    if matrix.get('schema_version')!='action-modes-v1' or len(rows)!=len(catalog) or {r['action'] for r in rows}!=set(catalog):
        raise ValueError('Action-mode matrix does not cover the exact route catalog')
    for row in rows:
        route=catalog[row['action']]
        if row['program']!=route.get('program','ERASMUS') or row['sectors']!=route['sectors'] or row['year']!=route.get('year',2026):
            raise ValueError('Action-mode scope does not match the route catalog')
    row=next((r for r in rows if r['action']==action),None)
    if not row or row['program']!=program or sector not in row['sectors'] or isinstance(year,bool) or not isinstance(year,int) or year!=row['year']:
        raise ValueError('Unsupported programme/action/sector/year scope')
    controls=matrix['modes'][row['mode']]
    if any(not isinstance(controls.get(k),bool) for k in ('requested_grant_required','financial_model_required','activity_schedule_required','activity_assignment_required')):
        raise ValueError('Invalid action-mode controls')
    if not isinstance(controls.get('required_tables'),list) or any(t not in TABLES for t in controls['required_tables']):
        raise ValueError('Invalid action-mode required tables')
    return {**row,**controls}

def model_action_mode(project, strict):
    # Draft models may omit year/sector; supplied values are always checked.
    # Final readiness always requires the complete exact route.
    route=next((r for r in json.loads((ROOT/'config/actions.json').read_text()) if r['code']==project.get('action')),None)
    if not route: raise ValueError('Unknown action')
    sector=project.get('sector') if strict or 'sector' in project else route['sectors'][0]
    year=project.get('year') if strict or 'year' in project else route.get('year',2026)
    return action_mode(project.get('program'),project.get('action'),sector,year)

def number(value):
    if value is None or isinstance(value,bool): raise ValueError('Missing or invalid number')
    try: v=Decimal(str(value))
    except InvalidOperation: raise ValueError('Invalid number')
    if not v.is_finite(): raise ValueError('Non-finite number')
    return v

def localized_proof(value):
    if isinstance(value,str): return bool(value.strip())
    if not isinstance(value,dict): return False
    locator=value.get('locator')
    return isinstance(locator,str) and bool(locator.strip()) and any(isinstance(value.get(k),str) and bool(value[k].strip()) for k in ('source','path','url'))


def work_package_calendar(wp, activities):
    """Resolve a WP calendar without filling or changing the source model.

    Explicit production interval wins; otherwise use all declared activities
    when their intervals are known, then a due-only point, then unknown.
    Both dependency validation and Gantt use this same resolver.
    """
    def valid(value): return isinstance(value,int) and not isinstance(value,bool) and value>=1
    start,end=wp.get('start_month'),wp.get('end_month')
    if valid(start) and valid(end) and start<=end:
        return {'start_month':start,'end_month':end,'calendar_origin':'declared_interval','calendar_activity_ids':[]}
    identifiers=wp.get('activity_ids',[])
    identifiers=identifiers if isinstance(identifiers,list) else []
    rows=[activities.get(aid,{}) if isinstance(aid,str) else {} for aid in identifiers]
    if rows and all(valid(a.get('start_month')) and valid(a.get('end_month')) and a['start_month']<=a['end_month'] for a in rows):
        return {'start_month':min(a['start_month'] for a in rows),'end_month':max(a['end_month'] for a in rows),'calendar_origin':'activities','calendar_activity_ids':list(identifiers)}
    due=wp.get('due_month')
    return {'start_month':due if valid(due) else None,'end_month':due if valid(due) else None,'calendar_origin':'due_only' if valid(due) else 'unknown','calendar_activity_ids':[]}


def check_model(model,strict=False):
    issues=[]; tables={}; indexes={}
    if not isinstance(model,dict): return {'passed':False,'issues':[{'code':'model-not-object'}]}
    project=model.get('project',{})
    if not isinstance(project,dict): return {'passed':False,'issues':[{'code':'project-not-object'}]}
    def flag(code,table=None,id=None,**extra): issues.append({'code':code,**({'table':table} if table else {}),**({'id':id} if id else {}),**extra})
    for key in model:
        if key not in {*TABLES,'project','schema_version','metadata'}: flag('unknown-model-root-field',field=key)
    if 'metadata' in model and not isinstance(model['metadata'],dict): flag('invalid-model-metadata')
    try: mode=model_action_mode(project,strict)
    except (ValueError,KeyError,TypeError,OSError) as exc:
        mode={}; flag('action-mode-scope-unverified',message=str(exc))
    ka220=mode.get('ka220_management_cap',False)
    version=model.get('schema_version')
    if version is not None and version not in (MODEL_VERSION,'project-model-v1'): flag('unsupported-model-version')
    missing_new=[t for t in TABLES if t not in LEGACY_TABLES and t not in model]
    legacy=bool(missing_new) or version=='project-model-v1'
    migration_required=legacy or version!=MODEL_VERSION
    if strict and migration_required: flag('project-model-migration-required',missing_tables=missing_new,target_version=MODEL_VERSION)
    if strict:
        try:
            schema=json.loads((ROOT/'config/project-model.schema.json').read_text())
            schema_result=validate_instance(model,schema)
            issues.extend(schema_result['issues'])
        except (OSError,ValueError,TypeError) as exc: flag('model-schema-unavailable',message=str(exc))
    for table in TABLES:
        records=model.get(table)
        if not isinstance(records,list):
            if table in model or table in LEGACY_TABLES or version==MODEL_VERSION: flag('missing-record-table',table)
            records=[]
        tables[table]=records; ids=[r.get('id') for r in records if isinstance(r,dict)]
        indexes[table]={r['id']:r for r in records if isinstance(r,dict) and isinstance(r.get('id'),str) and r['id']}
        if len(ids)!=len(records) or any(not isinstance(x,str) or not x for x in ids): flag('invalid-record-id',table)
        string_ids=[x for x in ids if isinstance(x,str)]
        if len(string_ids)!=len(set(string_ids)): flag('duplicate-record-id',table)
    for table in TABLES:
        for row in indexes[table].values():
            for field in ('title','description'):
                if field in row and not isinstance(row[field],str): flag('invalid-record-field-type',table,row['id'],field=field)
            for alias,canonical in {'owner_partner_id':'partner_id','depends_on_task_ids':'dependency_ids','outcome_ids':'result_ids','deliverable':'deliverable_ids'}.items():
                if alias in row and strict: flag('noncanonical-record-alias',table,row['id'],field=alias,canonical_field=canonical)
    for table,fields in LINKS.items():
        for row in indexes[table].values():
            for field,target in fields.items():
                value=row.get(field)
                plural=field.endswith('_ids')
                supplied=value is not None or (table=='work_packages' and field=='dependency_ids' and field in row)
                if supplied and (not isinstance(value,list) if plural else not isinstance(value,str)):
                    flag('invalid-reference-type',table,row['id'],field=field); continue
                values=value if plural and isinstance(value,list) else [value] if value is not None else []
                if plural and len([x for x in values if isinstance(x,str)])!=len(set(x for x in values if isinstance(x,str))): flag('duplicate-reference',table,row['id'],field=field)
                for ident in values:
                    if not isinstance(ident,str) or ident not in indexes[target]: flag('broken-reference',table,row['id'],field=field,target=ident)
    duration=project.get('duration_months')
    calendar_present=any(row.get(k) is not None for t in ('work_packages','activities','tasks','deliverables','milestones') for row in indexes[t].values() for k in ('start_month','end_month','due_month'))
    duration_required=calendar_present or (strict and mode.get('activity_schedule_required',True) and bool(tables['activities']))
    duration_valid=isinstance(duration,int) and not isinstance(duration,bool) and duration>=1
    if ('duration_months' in project and duration is not None and not duration_valid) or (duration_required and not duration_valid): flag('invalid-project-duration',field='duration_months')
    graph={}
    for a in indexes['activities'].values():
        ident=a['id']; graph[ident]=a.get('dependency_ids',[]) if isinstance(a.get('dependency_ids',[]),list) else []
        start,end=a.get('start_month'),a.get('end_month')
        if start is not None or end is not None:
            if any(isinstance(v,bool) or not isinstance(v,int) for v in (start,end)) or start<1 or end<start or (duration_valid and end>duration):
                flag('invalid-activity-schedule','activities',ident)
        elif strict and mode.get('activity_schedule_required',True): flag('missing-activity-schedule','activities',ident)
        if strict and mode.get('activity_assignment_required',True):
            if (not a.get('wp_id') and (ka220 or tables['work_packages'])) or not a.get('partner_id') or not a.get('objective_ids'): flag('unassigned-activity','activities',ident)
            if not a.get('assignment_evidence'): flag('partner-expertise-assignment-unverified','activities',ident)
        for dep in graph[ident]:
            if not isinstance(dep,str): continue
            prior=indexes['activities'].get(dep,{})
            if isinstance(prior.get('end_month'),int) and not isinstance(prior['end_month'],bool) and isinstance(start,int) and not isinstance(start,bool) and prior['end_month']>start:
                flag('dependency-schedule-overlap','activities',ident,dependency=dep)
        wp=indexes['work_packages'].get(a.get('wp_id') if isinstance(a.get('wp_id'),str) else None)
        if wp and ident not in (wp.get('activity_ids',[]) if isinstance(wp.get('activity_ids',[]),list) else []): flag('wp-activity-membership-mismatch','activities',ident)
    visited=set(); active=set()
    def visit(node):
        if node in active: flag('cyclic-dependency','activities',node); return
        if node in visited: return
        active.add(node)
        for dep in graph.get(node,[]):
            if isinstance(dep,str): visit(dep)
        active.remove(node); visited.add(node)
    for node in graph: visit(node)
    for wp in indexes['work_packages'].values():
        for aid in wp.get('activity_ids',[]) if isinstance(wp.get('activity_ids',[]),list) else []:
            if not isinstance(aid,str): continue
            if aid in indexes['activities'] and indexes['activities'][aid].get('wp_id')!=wp['id']: flag('activity-wp-mismatch','work_packages',wp['id'],activity=aid)
    _check_delivery_graph(indexes,mode,strict,duration,duration_valid,flag)
    management_ids={wp['id'] for wp in indexes['work_packages'].values() if wp.get('kind')=='management'}
    if ka220 and len(management_ids)>1: flag('multiple-ka220-management-work-packages',ids=sorted(management_ids))
    total=Decimal(0); management=Decimal(0); complete=True
    for row in indexes['budget_lines'].values():
        a=indexes['activities'].get(row.get('activity_id') if isinstance(row.get('activity_id'),str) else None)
        if a and a.get('wp_id')!=row.get('wp_id'): flag('budget-activity-wp-mismatch','budget_lines',row['id'])
        if ka220 and not row.get('wp_id'): flag('budget-wp-unassigned','budget_lines',row['id'])
        try:
            amount=number(row.get('grant_allocation'))
            if amount<0: raise ValueError('Negative amount')
            total+=amount
            if isinstance(row.get('wp_id'),str) and row['wp_id'] in management_ids: management+=amount
            if row.get('currency',project.get('currency'))!=project.get('currency'): flag('currency-mismatch','budget_lines',row['id'])
            for field in ('quantity','unit_rate','estimated_cost'):
                if row.get(field) is not None and number(row[field])<0: flag('negative-budget-factor','budget_lines',row['id'],field=field)
            if row.get('quantity') is not None and row.get('unit_rate') is not None and row.get('estimated_cost') is not None:
                if abs(number(row['quantity'])*number(row['unit_rate'])-number(row['estimated_cost']))>Decimal('.01'): flag('quantity-rate-cost-mismatch','budget_lines',row['id'])
        except ValueError: complete=False; flag('invalid-budget-number','budget_lines',row['id'])
    grant=project.get('requested_grant')
    if grant is not None:
        try:
            grant=number(grant)
            if grant<0: raise ValueError('Negative grant')
            if complete and (mode.get('requested_grant_required',True) or tables['budget_lines']) and abs(total-grant)>Decimal('.01'): flag('grant-allocation-total-mismatch',expected=str(grant),actual=str(total))
            if mode.get('mode') in ('accreditation','quality-label') and grant>0: flag('nonfinancial-action-has-requested-grant')
            if ka220:
                if not project.get('management_wp_id'): flag('management-wp-not-identified')
                else:
                    wp=indexes['work_packages'].get(project['management_wp_id'] if isinstance(project['management_wp_id'],str) else None)
                    if not wp or wp.get('kind')!='management': flag('management-wp-kind-unverified')
                    if management>grant*Decimal('.20'): flag('ka220-management-over-20-percent-total',actual=str(management),maximum=str(grant*Decimal('.20')))
        except ValueError: flag('invalid-requested-grant')
    elif strict and mode.get('requested_grant_required',True): flag('requested-grant-unconfirmed')
    if strict:
        required_tables=mode.get('required_tables',('partners','needs','objectives','activities','outputs','results','impacts','kpis'))
        for table in required_tables:
            if not tables[table]: flag('empty-required-project-data',table)
        for table,fields in {'needs':['problem','evidence','scale'], 'objectives':['need_ids','priority_ids'],
                             'results':['output_ids'], 'impacts':['result_ids','scale'],
                             'kpis':['baseline','target','unit','measurement_source','frequency','partner_id'],
                             'risks':['partner_id','mitigation','trigger','contingency']}.items():
            for row in indexes[table].values():
                for f in fields:
                    if row.get(f) is None or row.get(f)=='' or row.get(f)==[]: flag('missing-final-data',table,row['id'],field=f)
        if mode.get('financial_model_required',True) and (project.get('financial_model') not in mode.get('allowed_financial_models',()) or not project.get('financial_model_evidence')): flag('financial-model-unverified')
        evidence_field=mode.get('requirements_evidence_field')
        if evidence_field and not project.get(evidence_field): flag(mode['mode']+'-requirements-unverified',field=evidence_field)
    return {'passed':not issues,'model_version':MODEL_VERSION if not legacy else 'project-model-v1','strict':strict,'action_mode':mode.get('mode'),'issues':issues,'grant_allocation_total':str(total),'management_grant_allocation':str(management),'counts':{t:len(v) for t,v in tables.items()}}

def _check_delivery_graph(indexes,mode,strict,duration,duration_valid,flag):
    """Canonical IDs, membership, schedules and output measurement relationships."""
    def refs(row,key):
        value=row.get(key,[])
        return [v for v in value if isinstance(v,str)] if isinstance(value,list) else []
    def lookup(table,key): return indexes[table].get(key,{}) if isinstance(key,str) else {}
    def require(table,row,fields):
        for field in fields:
            if row.get(field) is None or row.get(field)=='' or row.get(field)==[]: flag('missing-final-data',table,row['id'],field=field)
    def schedule(table,row,single=False):
        fields=('due_month',) if single else ('start_month','end_month')
        values=[row.get(k) for k in fields]
        if any(v is not None for v in values) or strict:
            if any(isinstance(v,bool) or not isinstance(v,int) or v<1 or (duration_valid and v>duration) for v in values) or (not single and all(isinstance(v,int) and not isinstance(v,bool) for v in values) and values[1]<values[0]):
                flag('invalid-'+table.rstrip('s')+'-schedule',table,row['id'])
    production=bool(indexes['tasks'] or indexes['deliverables'])
    grant=mode.get('mode')=='grant'
    full_delivery=strict and grant and (mode.get('ka220_management_cap') or production)
    for table in ('work_packages','activities','tasks','deliverables','milestones'):
        for row in indexes[table].values():
            for field in ('start_month','end_month','due_month'):
                value=row.get(field)
                if value is not None and (isinstance(value,bool) or not isinstance(value,int) or value<1 or (duration_valid and value>duration)):
                    flag('invalid-entity-calendar',table,row['id'],field=field)
            start,end,due=row.get('start_month'),row.get('end_month'),row.get('due_month')
            if all(isinstance(v,int) and not isinstance(v,bool) for v in (start,end,due)):
                if table in ('deliverables','milestones') and not start<=due<=end: flag('deadline-outside-delivery-window',table,row['id'])
                elif table not in ('deliverables','milestones') and due<end: flag('deadline-before-production-end',table,row['id'])
    for table in ('deliverables','milestones'):
        for row in indexes[table].values():
            if row.get('start_month') is not None or row.get('end_month') is not None:
                schedule(table,row)
    for wp in indexes['work_packages'].values():
        if wp.get('start_month') is not None or wp.get('end_month') is not None:
            schedule('work_packages',wp)
            lo,hi=wp.get('start_month'),wp.get('end_month')
            if all(isinstance(v,int) and not isinstance(v,bool) for v in (lo,hi)):
                for aid in refs(wp,'activity_ids'):
                    activity=lookup('activities',aid);start,end=activity.get('start_month'),activity.get('end_month')
                    if all(isinstance(v,int) and not isinstance(v,bool) for v in (start,end)) and (start<lo or end>hi): flag('activity-outside-wp-schedule','work_packages',wp['id'],activity_id=aid)
        due=wp.get('due_month')
        if isinstance(due,int) and not isinstance(due,bool):
            for aid in refs(wp,'activity_ids'):
                end=lookup('activities',aid).get('end_month')
                if isinstance(end,int) and not isinstance(end,bool) and end>due: flag('wp-deadline-before-activity-completion','work_packages',wp['id'],activity_id=aid)
        if wp.get('kind') is not None and wp.get('kind') not in ('management','implementation'): flag('invalid-wp-kind','work_packages',wp['id'])
        for field,target in [('task_ids','tasks'),('deliverable_ids','deliverables'),('milestone_ids','milestones')]:
            for ident in refs(wp,field):
                row=lookup(target,ident)
                if row and row.get('wp_id')!=wp['id']: flag('wp-entity-membership-mismatch','work_packages',wp['id'],field=field,target=ident)
    for activity in indexes['activities'].values():
        for field,target,back in [('task_ids','tasks','activity_id'),('deliverable_ids','deliverables',None)]:
            for ident in refs(activity,field):
                row=lookup(target,ident)
                if row and ((back and row.get(back)!=activity['id']) or (not back and not any(lookup('tasks',tid).get('activity_id')==activity['id'] for tid in refs(row,'task_ids')))):
                    flag('activity-entity-membership-mismatch','activities',activity['id'],field=field,target=ident)
        wp=lookup('work_packages',activity.get('wp_id'))
        if full_delivery and wp.get('kind')!='management' and not any(t.get('activity_id')==activity['id'] for t in indexes['tasks'].values()):
            flag('activity-tasks-missing','activities',activity['id'])
    for task in indexes['tasks'].values():
        activity=lookup('activities',task.get('activity_id')); wp=lookup('work_packages',task.get('wp_id'))
        if strict: require('tasks',task,('activity_id','partner_id','title'))
        if activity and activity.get('wp_id')!=task.get('wp_id'): flag('task-activity-wp-mismatch','tasks',task['id'])
        if 'task_ids' in activity and task['id'] not in refs(activity,'task_ids'): flag('task-activity-membership-mismatch','tasks',task['id'])
        if 'task_ids' in wp and task['id'] not in refs(wp,'task_ids'): flag('task-wp-membership-mismatch','tasks',task['id'])
        schedule('tasks',task)
        for field in ('start_month','end_month'):
            value=task.get(field); lo=activity.get('start_month'); hi=activity.get('end_month')
            if all(isinstance(v,int) and not isinstance(v,bool) for v in (value,lo,hi)) and not lo<=value<=hi: flag('task-outside-activity-schedule','tasks',task['id'],field=field)
        for did in refs(task,'deliverable_ids'):
            deliverable=lookup('deliverables',did)
            if deliverable and task['id'] not in refs(deliverable,'task_ids'): flag('task-deliverable-membership-mismatch','tasks',task['id'],deliverable_id=did)
        if full_delivery and wp.get('kind')!='management' and not any(task['id'] in refs(d,'task_ids') for d in indexes['deliverables'].values()): flag('task-deliverable-missing','tasks',task['id'])
    versions_seen=set()
    for deliverable in indexes['deliverables'].values():
        if strict: require('deliverables',deliverable,('title','task_ids','output_ids','partner_id','acceptance_criteria','versions'))
        criteria=deliverable.get('acceptance_criteria')
        if criteria is not None and (not isinstance(criteria,(str,list)) or isinstance(criteria,list) and any(not isinstance(v,str) or not v for v in criteria)): flag('invalid-deliverable-acceptance-criteria','deliverables',deliverable['id'])
        schedule('deliverables',deliverable,True)
        task_ids=refs(deliverable,'task_ids'); activity_ids={lookup('tasks',tid).get('activity_id') for tid in task_ids if isinstance(lookup('tasks',tid).get('activity_id'),str)}
        for tid in task_ids:
            task=lookup('tasks',tid)
            if task and task.get('wp_id')!=deliverable.get('wp_id'): flag('deliverable-task-wp-mismatch','deliverables',deliverable['id'],task_id=tid)
            if task and 'deliverable_ids' in task and deliverable['id'] not in refs(task,'deliverable_ids'): flag('deliverable-task-membership-mismatch','deliverables',deliverable['id'],task_id=tid)
            end=task.get('end_month'); due=deliverable.get('due_month')
            if isinstance(end,int) and not isinstance(end,bool) and isinstance(due,int) and not isinstance(due,bool) and due<end: flag('deliverable-before-task-completion','deliverables',deliverable['id'],task_id=tid)
        for aid in activity_ids:
            activity=lookup('activities',aid)
            if 'deliverable_ids' in activity and deliverable['id'] not in refs(activity,'deliverable_ids'): flag('deliverable-activity-membership-mismatch','deliverables',deliverable['id'],activity_id=aid)
        wp=lookup('work_packages',deliverable.get('wp_id'))
        if 'deliverable_ids' in wp and deliverable['id'] not in refs(wp,'deliverable_ids'): flag('deliverable-wp-membership-mismatch','deliverables',deliverable['id'])
        for oid in refs(deliverable,'output_ids'):
            output=lookup('outputs',oid)
            if output and (output.get('wp_id')!=deliverable.get('wp_id') or not activity_ids.issubset(set(refs(output,'activity_ids')))):
                flag('deliverable-output-chain-mismatch','deliverables',deliverable['id'],output_id=oid)
            if output and deliverable['id'] not in refs(output,'deliverable_ids'): flag('deliverable-output-membership-mismatch','deliverables',deliverable['id'],output_id=oid)
        versions=deliverable.get('versions',[])
        if not isinstance(versions,list): flag('invalid-deliverable-versions','deliverables',deliverable['id']); continue
        language_versions=set()
        for version in versions:
            if not isinstance(version,dict): flag('invalid-deliverable-version','deliverables',deliverable['id']); continue
            vid=version.get('id'); language=version.get('language'); label=version.get('version')
            if any(not isinstance(v,str) or not v for v in (vid,language,label)): flag('invalid-deliverable-version-identity','deliverables',deliverable['id']); continue
            if vid in versions_seen or (language,label) in language_versions: flag('duplicate-deliverable-version','deliverables',deliverable['id'],version_id=vid)
            versions_seen.add(vid); language_versions.add((language,label))
            status=version.get('status','planned')
            if status not in ('planned','draft','submitted','accepted','superseded'): flag('invalid-deliverable-version-status','deliverables',deliverable['id'],version_id=vid)
            for field in ('path','published_url','acceptance_partner_id','acceptance_date'):
                if field in version and (not isinstance(version[field],str) or not version[field]): flag('invalid-deliverable-version-field','deliverables',deliverable['id'],version_id=vid,field=field)
            if status=='accepted':
                try:
                    value=version.get('acceptance_date')
                    if not isinstance(value,str) or date.fromisoformat(value).isoformat()!=value: raise ValueError('Invalid date')
                except ValueError: flag('invalid-deliverable-acceptance-date','deliverables',deliverable['id'],version_id=vid)
                if not localized_proof(version.get('approval_evidence')) or not (version.get('path') or version.get('published_url')) or not version.get('acceptance_date') or not isinstance(version.get('acceptance_partner_id'),str) or version.get('acceptance_partner_id') not in indexes['partners']:
                    flag('deliverable-acceptance-unverified','deliverables',deliverable['id'],version_id=vid)
    for output in indexes['outputs'].values():
        if strict and grant and not refs(output,'activity_ids'): flag('output-activities-missing','outputs',output['id'])
        activity_wps=[lookup('activities',aid).get('wp_id') for aid in refs(output,'activity_ids')]
        if any(wp!=output.get('wp_id') for wp in activity_wps): flag('output-activity-wp-mismatch','outputs',output['id'])
        if full_delivery and not refs(output,'deliverable_ids'): flag('output-deliverables-missing','outputs',output['id'])
        for did in refs(output,'deliverable_ids'):
            d=lookup('deliverables',did)
            if d and output['id'] not in refs(d,'output_ids'): flag('output-deliverable-membership-mismatch','outputs',output['id'],deliverable_id=did)
    for result in indexes['results'].values():
        if result.get('wp_id') is not None and any(lookup('outputs',oid).get('wp_id')!=result['wp_id'] for oid in refs(result,'output_ids')): flag('result-output-wp-mismatch','results',result['id'])
    for kpi in indexes['kpis'].values():
        links={field:refs(kpi,field) for field in ('objective_ids','output_ids','deliverable_ids','result_ids','impact_ids')}
        if strict and not any(links.values()): flag('kpi-measured-entity-missing','kpis',kpi['id'])
        if kpi.get('wp_id') is not None:
            output_ids=set(links['output_ids'])
            for rid in links['result_ids']: output_ids.update(refs(lookup('results',rid),'output_ids'))
            for iid in links['impact_ids']:
                for rid in refs(lookup('impacts',iid),'result_ids'): output_ids.update(refs(lookup('results',rid),'output_ids'))
            for did in links['deliverable_ids']: output_ids.update(refs(lookup('deliverables',did),'output_ids'))
            if any(lookup('outputs',oid).get('wp_id')!=kpi['wp_id'] for oid in output_ids): flag('kpi-measured-entity-wp-mismatch','kpis',kpi['id'])
    for milestone in indexes['milestones'].values():
        wp=lookup('work_packages',milestone.get('wp_id'))
        if 'milestone_ids' in wp and milestone['id'] not in refs(wp,'milestone_ids'): flag('milestone-wp-membership-mismatch','milestones',milestone['id'])
        if strict: require('milestones',milestone,('title','partner_id','acceptance_criteria'))
        criteria=milestone.get('acceptance_criteria')
        if criteria is not None and (not isinstance(criteria,(str,list)) or isinstance(criteria,list) and any(not isinstance(v,str) or not v for v in criteria)): flag('invalid-milestone-acceptance-criteria','milestones',milestone['id'])
        if strict and not any(refs(milestone,k) for k in ('activity_ids','task_ids','deliverable_ids')): flag('milestone-entity-missing','milestones',milestone['id'])
        schedule('milestones',milestone,True)
        for field,target in [('activity_ids','activities'),('task_ids','tasks'),('deliverable_ids','deliverables')]:
            for ident in refs(milestone,field):
                row=lookup(target,ident)
                if row and milestone.get('wp_id')!=row.get('wp_id'): flag('milestone-entity-wp-mismatch','milestones',milestone['id'],target=ident)
    for table in ('work_packages','tasks','deliverables','milestones'):
        visited=set(); active=set()
        def visit(node):
            if node in active: flag('cyclic-dependency',table,node); return
            if node in visited: return
            active.add(node); row=lookup(table,node)
            for dep in refs(row,'dependency_ids'):
                prior=lookup(table,dep); visit(dep)
                if table=='work_packages':
                    start=work_package_calendar(row,indexes['activities'])['start_month'];end=work_package_calendar(prior,indexes['activities'])['end_month']
                    if strict and prior and (start is None or end is None): flag('wp-dependency-calendar-unverified',table,node,dependency=dep)
                else:
                    end=prior.get('end_month') if table=='tasks' else prior.get('due_month')
                    start=row.get('start_month') if table=='tasks' else row.get('due_month')
                if isinstance(end,int) and not isinstance(end,bool) and isinstance(start,int) and not isinstance(start,bool) and end>start: flag('dependency-schedule-overlap',table,node,dependency=dep)
            active.remove(node); visited.add(node)
        for ident in indexes[table]: visit(ident)
    for budget in indexes['budget_lines'].values():
        task=lookup('tasks',budget.get('task_id'));delivery=lookup('deliverables',budget.get('deliverable_id'))
        if task and delivery and task['id'] not in refs(delivery,'task_ids'): flag('budget-task-deliverable-mismatch','budget_lines',budget['id'],task_id=task['id'],deliverable_id=delivery['id'])
        if delivery and budget.get('activity_id') is not None and not any(lookup('tasks',tid).get('activity_id')==budget['activity_id'] for tid in refs(delivery,'task_ids')): flag('budget-deliverable-activity-mismatch','budget_lines',budget['id'],deliverable_id=delivery['id'])
        for field,target in [('task_id','tasks'),('deliverable_id','deliverables')]:
            row=lookup(target,budget.get(field))
            if row and row.get('wp_id')!=budget.get('wp_id'): flag('budget-entity-wp-mismatch','budget_lines',budget['id'],field=field)
            if target=='tasks' and row and budget.get('activity_id') is not None and row.get('activity_id')!=budget['activity_id']: flag('budget-task-activity-mismatch','budget_lines',budget['id'])


def annex_projections(model):
    """Return reproducible semantic views, using canonical IDs and month units.

    No file is emitted or content certified. Render/upload/financial evidence
    checks remain necessary when a specialist materializes an actual annex.
    """
    check=check_model(model,False)
    if not check['passed']: raise ValueError('Cannot project an inconsistent model: '+json.dumps(check['issues']))
    indexes={table:{r['id']:r for r in model.get(table,[])} for table in TABLES}
    def ids(value): return list(value) if isinstance(value,list) else []
    gantt=[]; wp=[]; task_file=[]; results=[]; budget=[]
    for table in ('work_packages','activities','tasks','deliverables','milestones'):
        for row in indexes[table].values():
            common={'row_kind':table,'entity_id':row['id'],'wp_id':row['id'] if table=='work_packages' else row.get('wp_id'),'owner_partner_id':row.get('partner_id',row.get('lead_partner_id'))}
            wp.append({**common,'activity_id':row.get('activity_id'),'task_ids':ids(row.get('task_ids')),'deliverable_ids':ids(row.get('deliverable_ids')),'output_ids':ids(row.get('output_ids'))})
            calendar=work_package_calendar(row,indexes['activities']) if table=='work_packages' else {'start_month':row.get('start_month') if row.get('start_month') is not None else row.get('due_month'),'end_month':row.get('end_month') if row.get('end_month') is not None else row.get('due_month')}
            gantt.append({**common,'schedule_id':row['id'],**calendar,'predecessor_ids':ids(row.get('dependency_ids')),'due_month':row.get('due_month')})
    for task in indexes['tasks'].values():
        dids=[d['id'] for d in indexes['deliverables'].values() if task['id'] in ids(d.get('task_ids'))]
        task_file.append({'task_id':task['id'],'wp_id':task.get('wp_id'),'activity_id':task.get('activity_id'),'deliverable_ids':dids,'owner_partner_id':task.get('partner_id'),'start_month':task.get('start_month'),'end_month':task.get('end_month'),'due_month':task.get('due_month') if task.get('due_month') is not None else task.get('end_month'),'depends_on_task_ids':ids(task.get('dependency_ids'))})
    for deliverable in indexes['deliverables'].values():
        for version in deliverable.get('versions',[]):
            results.append({'artifact_id':version['id'],'deliverable_id':deliverable['id'],'output_ids':ids(deliverable.get('output_ids')),'wp_id':deliverable.get('wp_id'),'owner_partner_id':deliverable.get('partner_id'),'task_ids':ids(deliverable.get('task_ids')),'language':version['language'],'version':version['version'],'status':version.get('status','planned'),'path':version.get('path')})
    for line in indexes['budget_lines'].values():
        if line.get('task_id'): tids=[line['task_id']]
        elif line.get('deliverable_id'):
            tids=[tid for tid in ids(indexes['deliverables'][line['deliverable_id']].get('task_ids')) if not line.get('activity_id') or indexes['tasks'][tid].get('activity_id')==line['activity_id']]
        else: tids=[t['id'] for t in indexes['tasks'].values() if line.get('activity_id') and t.get('activity_id')==line['activity_id']]
        dids=[line['deliverable_id']] if line.get('deliverable_id') else [d['id'] for d in indexes['deliverables'].values() if set(tids)&set(ids(d.get('task_ids')))]
        budget.append({**line,'budget_line_id':line['id'],'task_ids':tids,'deliverable_ids':dids})
    return {'schema_version':'canonical-annex-projections-v1','project_model_version':MODEL_VERSION,'calendar_unit':'project_month','semantic_only':True,'work-packages-table':wp,'gantt-table':gantt,'ka2-task-file':task_file,'results-register':results,'budget-table':budget}


def check_manifest(manifest,project_root,strict=False):
    issues=[]; root=Path(project_root).resolve(); seen=set()
    registry={entry['id'] for entry in json.loads((ROOT/'config/annexes.json').read_text())}
    entries=manifest.get('annexes',[]) if isinstance(manifest,dict) else manifest
    if not isinstance(entries,list): return {'passed':False,'issues':[{'code':'annex-manifest-not-list'}],'count':0}
    for item in entries:
        if not isinstance(item,dict): issues.append({'code':'annex-entry-not-object'}); continue
        ident=item.get('id')
        if not isinstance(ident,str) or not ident or ident in seen: issues.append({'code':'duplicate-or-missing-annex-id','id':ident})
        if isinstance(ident,str): seen.add(ident)
        classification=item.get('classification','internal'); doc_type=item.get('type',ident)
        if 'type' in item and (not isinstance(item['type'],str) or item['type'] not in registry|{'other'}): issues.append({'code':'invalid-annex-type','id':ident})
        if isinstance(ident,str) and ident in registry and 'type' in item and item['type']!=ident: issues.append({'code':'annex-id-type-conflict','id':ident,'type':item['type']})
        not_applicable=item.get('status')=='not-applicable'
        if not_applicable and (not item.get('reason') or classification=='required'): issues.append({'code':'invalid-not-applicable-annex','id':ident})
        if classification not in ('internal','required','optional'): issues.append({'code':'invalid-annex-classification','id':ident})
        if classification=='required' and not item.get('requirement_source'): issues.append({'code':'unverified-required-annex','id':ident})
        item_path=item.get('path','')
        if not isinstance(item_path,str): issues.append({'code':'invalid-annex-path','id':ident}); item_path=''
        path=(root/item_path).resolve()
        if not not_applicable and (not item_path or not path.is_relative_to(root) or not path.is_file()): issues.append({'code':'annex-file-missing-or-outside-project','id':ident})
        if strict and item.get('status') not in ('verified','not-applicable'): issues.append({'code':'annex-not-verified','id':ident})
        if item.get('delivery_status')=='ready-to-sign':
            contract=ident in ('partner-contract','participant-rules-code') or doc_type in ('partner-contract','participant-rules-code')
            proof=item.get('legal_review_evidence')
            localized=localized_proof(proof)
            if contract and not localized: issues.append({'code':'contract-legal-review-not-localized','id':ident})
            elif not contract and (not isinstance(doc_type,str) or doc_type not in registry): issues.append({'code':'signing-document-type-unverified','id':ident})
        if strict and classification=='required' and item.get('upload_constraints_verified') is not True: issues.append({'code':'annex-upload-constraints-unverified','id':ident})
    if strict and isinstance(manifest,dict) and manifest.get('coverage_verified') is not True:
        issues.append({'code':'annex-coverage-unverified','message':'Check actual call-required and internally agreed annexes; empty manifest is not proof of no annexes.'})
    return {'passed':not issues,'issues':issues,'count':len(entries)}

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('model'); p.add_argument('--strict',action='store_true'); p.add_argument('--manifest'); p.add_argument('--project-root'); p.add_argument('--output'); p.add_argument('--projections-output',help='Write canonical annex views only when model and any requested manifest checks pass')
    a=p.parse_args(); model=json.loads(Path(a.model).read_text()); result=check_model(model,a.strict)
    if a.manifest:
        annexes=check_manifest(json.loads(Path(a.manifest).read_text()),a.project_root or Path(a.model).parent,a.strict); result['annexes']=annexes; result['passed']=result['passed'] and annexes['passed']
    if a.projections_output and result['passed']: Path(a.projections_output).write_text(json.dumps(annex_projections(model),ensure_ascii=False,indent=2)+'\n')
    if a.output: Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2)); return 0 if result['passed'] else 1

if __name__=='__main__': sys.exit(main())
