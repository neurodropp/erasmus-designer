#!/usr/bin/env python3
"""Freeze a step, record an observed fresh-agent dispatch, verify its review.

This is an integrity/contract gate, not an LLM runner or proof of provider
isolation. The orchestrator must actually spawn a new agent with fork none.
"""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import sys
import uuid
import tempfile
from project_lock import locked_gate, project_lock, state_cas
from project_paths import resolve_project, confined_path, preflight_dossier, project_input

ROOT=Path(__file__).resolve().parents[1]
CATALOG_ROOT=ROOT
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path): return json.loads(path.read_text())
def write_once(path,data):
    encoded=json.dumps(data,ensure_ascii=False,indent=2)+'\n'
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as f:f.write(encoded)
def inside(base,value):
    return confined_path(base,value,True)
def dossier(root,name):
    return resolve_project(root,name)
def idea_lab(root,name):
    base=confined_path(root,Path(root)/'work'/'idea-lab')
    direct=confined_path(base,base/name)
    if (direct/'state.json').is_file():
        return preflight_workspace(direct,read(direct/'state.json'))
    matches=[]
    if base.exists():
        for state_file in sorted(base.glob('*/state.json')):
            candidate=confined_path(base,state_file.parent)
            state=read(confined_path(candidate,'state.json',True))
            if state.get('name')==name:matches.append(candidate)
    if len(matches)>1:raise ValueError('Ambiguous idea name; use the complete idea-lab ID')
    if matches:return preflight_workspace(matches[0],read(matches[0]/'state.json'))
    raise ValueError('Missing idea-lab workspace')
def preflight_workspace(path,state=None):
    path=Path(path)
    state=state or read(path/'state.json')
    if state.get('workspace_type')!='idea-lab':return preflight_dossier(path)
    if path.parent.name!='idea-lab' or path.parent.parent.name!='work':
        raise ValueError('Idea lab must be a direct child of work/idea-lab')
    base=path.parent
    confined_path(base,path)
    if path.is_symlink() or not path.is_dir():raise ValueError('Missing or symbolic idea-lab workspace')
    import os
    for parent,dirs,files in os.walk(path,followlinks=False):
        for name in dirs+files:confined_path(path,Path(parent)/name)
    return path
def cli_input(root,path,value):
    return project_input(root,path,value)
def history_relax(state):
    return ('draft','application-draft','annexes','review','repair','qa') if state.get('next_phase')=='repair' else ()
def checklist_file(path,value):
    p=Path(value)
    if not p.is_absolute():p=(CATALOG_ROOT/p if p.parts and p.parts[0]=='sources' else path/p)
    return inside(path,p) if p.resolve().is_relative_to(path.resolve()) else inside(CATALOG_ROOT/'sources',p)
def route_evidence(state):
    import brain
    integrity=brain.integrity_for_root(CATALOG_ROOT)
    if integrity:raise ValueError('Corpus integrity failed before packet freeze: '+json.dumps(integrity[:8],ensure_ascii=False))
    route=next(r for r in read(CATALOG_ROOT/'config/actions.json') if r['code']==state['action'])
    programme=state['program']; psid='esc-programme-2026' if programme=='ESC' else 'programme-2026';esid='esc-expert-2026' if programme=='ESC' else 'expert-2026'
    ranges=[{'id':psid,'pages':route['programme_pages']}]
    if route.get('expert_pages'): ranges.append({'id':esid,'pages':route['expert_pages']})
    ranges+=route.get('general_sources',[])
    if not route.get('general_sources') and programme=='ERASMUS':
        ranges.extend([{'id':psid,'pages':[4,36]},{'id':psid,'pages':[413,442]}])
        if route.get('expert_pages'):ranges.append({'id':esid,'pages':[4,21]})
    paths=[]
    for section in ranges:
        sid=section['id'];metadata=CATALOG_ROOT/'sources'/sid/'metadata.json';meta=read(metadata);revision=CATALOG_ROOT/'sources'/sid/'revisions'/meta['original_sha256']/'pages'
        paths.append(metadata)
        for n in range(section['pages'][0],section['pages'][1]+1):
            candidates=list(revision.glob(f'*{n:04d}.md'))
            if len(candidates)!=1: raise ValueError('Missing immutable route evidence '+sid+':'+str(n))
            paths.append(candidates[0])
    for source in read(CATALOG_ROOT/'config/sources.json'):
        kind=source['kind']
        if kind not in ('national-priorities','national-guidance','national-provisions','quality-standards','funding-handbook'): continue
        if kind.startswith('national-') and route['agency']=='EACEA': continue
        meta={'source':source['id'],'program':source.get('program','ERASMUS'),'sectors':source['sectors'],'actions':source['actions']}
        if not brain.applicable(meta,state['action'],state['sector'],state['program']): continue
        p=CATALOG_ROOT/'sources'/source['id']/'metadata.json';m=read(p);full=p.parent/'revisions'/m['original_sha256']/'full.md'
        if not full.exists(): raise ValueError('Missing applicable immutable supporting source '+source['id'])
        paths.extend([full,p])
    return paths
def compliance(state,phase):
    checks=[]; coverage=[]
    for p in sorted((CATALOG_ROOT/'config/compliance').glob('*.json')):
        d=read(p)
        if d.get('program') not in ('SHARED',state['program']): continue
        if d.get('year') not in (None,state['year']): continue
        if not any(a in ('ALL',state['action']) for a in d.get('actions',[])): continue
        coverage.append({'file':str(p),'coverage':d.get('coverage',{})})
        for c in d.get('checks',[]):
            if any(s in ('ALL',phase) for s in c.get('stages',[])): checks.append(c)
    if len({c['id'] for c in checks})!=len(checks): raise ValueError('Duplicate compliance check ID')
    return checks,coverage

PHASE_ZERO_ACCEPTANCE = [
    {'id':'phase-zero-scope','check':'Idea, assumptions and unresolved choices are stated without presenting exploration as eligibility.','classification':'local-method'},
    {'id':'phase-zero-divergence','check':'Free brainstorming records one primary formulation and a pertinent alternative across problem, target, mechanism and scale, with provenance and explicit convergence reasons; a no-alternative exception is localized and evidence-backed.','classification':'local-method'},
    {'id':'route_call_fit','check':'Route discovery, comparisons and gaps are explicit; every route marked verified has dated, localized current-call evidence.','classification':'local-method'},
    {'id':'priority_contribution','check':'Priority contribution is assessed with applicable authority and contextual EU links kept distinct; nominal links are exposed.','classification':'local-method'},
    {'id':'primary_target_fit','check':'Primary target fit is assessed separately from participants, organisations and secondary audiences; mismatch is exposed.','classification':'local-method'},
    {'id':'secondary_target_fit','check':'Secondary target fit and reach assumptions are assessed without inflated beneficiary claims.','classification':'local-method'},
    {'id':'need_evidence','check':'Needs and problems are separated; support or a credible evidence gap/plan is recorded.','classification':'local-method'},
    {'id':'causal_chain','check':'Needs -> problems -> solutions -> activities -> outputs -> results -> impact is assessed, including broken links and assumptions.','classification':'local-method'},
    {'id':'scale_budget_fit','check':'Scale, duration, delivery capacity, financial model and any real budget tier are assessed; rescoping needs are explicit.','classification':'local-method'},
    {'id':'capability_partner_fit','check':'Capabilities and partner-role gaps are assessed without invented commitments.','classification':'local-method'},
    {'id':'european_added_value','check':'European added value is assessed and weak or nominal claims are exposed.','classification':'local-method'},
    {'id':'phase-zero-decision','check':'PROCEED/REFINE/PIVOT/STOP recommendation follows the evidence and contains no official score or funding prediction.','classification':'local-method'},
    {'id':'critical-review','check':'Weaknesses, a meaningful alternative and a traceable decision basis are present.','classification':'local-method'},
]
for _check in PHASE_ZERO_ACCEPTANCE:
    _check.update(authority='user-authorized process',artifacts=['step-product','idea-input','localized-evidence'],
                  verification_method='Open the frozen idea, checklist, sources and recommendation; compare the claim with localized evidence and declared gaps.',
                  expected_outcome='Evidence-backed exploratory assessment or an explicit gap; no official scoring and no final eligibility claim.',
                  evidence_needed='Frozen Phase zero outputs and exact source or input locators.')

def _idea_gate(function):
    def wrapped(root,path,state,*args,**kwargs):
        with project_lock(path):
            state_cas(path,state)
            return function(root,path,state,*args,**kwargs)
    return wrapped

@_idea_gate
def prepare_idea(root,path,state,production_report,producers,artifacts=None):
    """Freeze the route-neutral Phase zero package before a dossier exists."""
    preflight_workspace(path,state)
    if state.get('workspace_type')!='idea-lab' or state.get('next_phase')!='phase-zero':
        raise ValueError('Expected phase phase-zero in an idea-lab workspace')
    if state.get('revisions',0)>=state.get('max_revisions',3):
        raise ValueError('Phase zero revision limit reached; preserve unresolved issues and request a new explicit budget before continuing')
    attempts=sum(read(p).get('phase')=='phase-zero' for p in (path/'validation/dispatches').glob('*.json'))
    if attempts>=state.get('max_validation_attempts',4):
        raise ValueError('Validation attempt limit reached; report unresolved issues before another attempt')
    verify_history(path,state)
    report=inside(path,production_report)
    if not producers or any(not isinstance(value,str) or not value.strip() for value in producers):
        raise ValueError('Observed producer agent IDs required')
    requested=artifacts or [path/'stages/phase-zero/decision.md',path/'stages/phase-zero/decision.json']
    products=[inside(path,value) for value in requested]
    if not {'decision.md','decision.json'}.issubset({product.name for product in products}):
        raise ValueError('Phase zero packet requires versioned decision.md and decision.json products')
    if any(not product.read_bytes().strip() for product in products):raise ValueError('Phase zero needs nonempty decision MD and JSON products')
    if any(product==report for product in products):raise ValueError('Do not pass the producer report as a reviewed product')
    import checklist
    checklist_path=inside(path,'research/checklist-phase-zero.json')
    matrix=read(checklist_path);assessment=checklist.validate_phase_zero(matrix,state,path)
    if not assessment['valid']:raise ValueError('Phase zero checklist contract invalid: '+json.dumps(assessment['issues'][:8]))
    decision_path=next((product for product in products if product.name=='decision.json'),None)
    if decision_path is None:raise ValueError('Phase zero packet requires decision.json')
    decision=read(decision_path);decision_check=checklist.validate_phase_zero_decision(decision,matrix,state,path)
    if not decision_check['valid']:raise ValueError('Phase zero decision invalid: '+json.dumps(decision_check['issues'][:8]))
    brainstorm_md=inside(path,'brainstorm.md');free_lines=[line.strip() for line in brainstorm_md.read_text().splitlines() if line.strip() and not line.lstrip().startswith('#')]
    if not free_lines:raise ValueError('Phase zero requires a substantive free brainstorming record')
    brainstorm_json=inside(path,'brainstorm.json');brainstorm=read(brainstorm_json)
    brainstorm_check=checklist.validate_phase_zero_brainstorm(brainstorm,state,path)
    if not brainstorm_check['valid']:raise ValueError('Phase zero brainstorm invalid: '+json.dumps(brainstorm_check['issues'][:8]))
    if brainstorm.get('idea_version')!=decision.get('version'):
        raise ValueError('Brainstorm and Phase zero decision versions must match')
    if decision['version']<=state.get('last_decision_version',0):
        raise ValueError('Phase zero decision version must increase for every new reviewed iteration')
    packet_id='phase-zero-'+uuid.uuid4().hex[:16]
    folder=confined_path(path,'validation/packets/'+packet_id)
    entries=[];seen=set();pending=[]
    def snapshot(value,role,accepted=False,locator=None):
        value=Path(value)
        if value.resolve().is_relative_to(path.resolve()):source=inside(path,value)
        elif role in ('report-schema','phase-zero-policy','action-registry','source-registry'):source=inside(CATALOG_ROOT/'config',value)
        else:source=inside(CATALOG_ROOT/'sources',value)
        source=source.resolve();snapshot_key=(source,role,locator or '')
        if snapshot_key in seen:return
        seen.add(snapshot_key);data=source.read_bytes();dest=folder/'snapshots'/f'{len(entries):04d}-{source.name}'
        pending.append((dest,data));entry={'id':'file-'+str(len(entries)),'role':role,'original':str(source),'snapshot':str(dest.relative_to(path)),'sha256':hashlib.sha256(data).hexdigest()}
        if locator:entry['locator']=locator
        if accepted:entry['accepted_product']=True
        entries.append(entry)
    for product in products:snapshot(product,'step-product')
    for name in ('brief.md','brainstorm.md','brainstorm.json'):
        candidate=path/name
        if candidate.is_file():snapshot(candidate,'idea-input')
    snapshot(checklist_path,'project-checklist',True)
    snapshot(CATALOG_ROOT/'config/stage-validation-report.schema.json','report-schema')
    snapshot(CATALOG_ROOT/'config/actions.json','action-registry')
    snapshot(CATALOG_ROOT/'config/sources.json','source-registry')
    policy=CATALOG_ROOT/'config/phase-zero.json'
    if policy.is_file():snapshot(policy,'phase-zero-policy')
    def evidence(rows):
        for row in rows:
            for ref in row.get('evidence',[]):
                selectors=[key for key in ('local_snapshot','path','url','source_id') if ref.get(key)]
                if len(selectors)!=1:raise ValueError('Phase zero evidence requires exactly one selector')
                value=ref.get('local_snapshot') or ref.get('path')
                if value:
                    source=Path(value);source=source if source.is_absolute() else path/source
                    snapshot(source,'localized-evidence',locator=ref.get('locator'))
                elif ref.get('source_id'):
                    meta=CATALOG_ROOT/'sources'/ref['source_id']/'metadata.json'
                    if not meta.is_file():raise ValueError('Unknown Phase zero source ID '+str(ref['source_id']))
                    metadata=read(meta);full=meta.parent/'revisions'/metadata['original_sha256']/'full.md'
                    if not full.is_file():raise ValueError('Phase zero source requires a local immutable full document')
                    snapshot(meta,'normative-evidence',locator=ref.get('locator'));snapshot(full,'normative-evidence',locator=ref.get('locator'))
                elif ref.get('url'):
                    raise ValueError('Online Phase zero evidence requires a localized snapshot before freeze')
    evidence(matrix.get('axes',[]));evidence(matrix.get('route_candidates',[]))
    if isinstance(decision.get('route_handoff'),dict):evidence([decision['route_handoff']])
    alternative_exception=brainstorm.get('alternative_exception')
    if isinstance(alternative_exception,dict):evidence([alternative_exception])
    report_data=read(report)
    if not report_data.get('summary') or not isinstance(report_data.get('evidence'),list):
        raise ValueError('Phase zero producer report needs summary and evidence')
    report_evidence_check=checklist._phase_zero_reference_issues(report_data['evidence'],'production-report',path)
    if report_evidence_check:raise ValueError('Phase zero producer evidence invalid: '+json.dumps(report_evidence_check[:8]))
    evidence([report_data])
    route_identity=('program','year','action','sector','country','agency','role','round')
    identity={'program':None,'year':state['year'],'action':None,'sector':None,
              'candidate_routes':[{**{key:row.get(key) for key in route_identity},'status':row.get('status')} for row in matrix.get('route_candidates',[])]}
    manifest={'schema_version':1,'deterministic_checks_policy':'allowlisted-python-v1','packet_id':packet_id,'phase':'phase-zero','route':identity,
              'producer_ids':sorted(set(producers)),'production_report':str(report),'production_sha256':digest(report),'state_sha256':digest(path/'state.json'),
              'acceptance_checks':PHASE_ZERO_ACCEPTANCE,'automatic_checks_expected':[],'compliance_checks':[],
              'coverage':[{'file':str(checklist_path),'coverage':{'scope':'route-neutral-idea-lab','unresolved_items':assessment['unresolved_items']}}],
              'files':entries,'context_policy':'fresh-agent-fork-none-no-production-history','created_at':dt.datetime.now(dt.timezone.utc).isoformat()}
    folder.mkdir(parents=True)
    for destination,data in pending:
        destination.parent.mkdir(parents=True,exist_ok=True)
        with destination.open('xb') as output:output.write(data)
    write_once(folder/'manifest.json',manifest)
    (folder/'report-schema.json').write_bytes((CATALOG_ROOT/'config/stage-validation-report.schema.json').read_bytes())
    example={'packet_id':packet_id,'packet_sha256':digest(folder/'manifest.json'),'phase':'phase-zero','reviewer_id':'OBSERVED_NEW_AGENT_ID','verdict':'accept|revise|blocked','summary':'Evidence-based Phase zero assessment',
             'checks':[{'id':row['id'],'status':'pass|fail|unknown|not-applicable','verification':'Actual comparison performed','reason':'Assessment and applicability','evidence':[{'file_id':'file-0','locator':'precise section'}]} for row in PHASE_ZERO_ACCEPTANCE],
             'discrepancies':[],'verification_limits':['Observed tool context; no provider isolation attestation'],'missing_information':[],
             'critical_review':{'weaknesses':['Observed weakness'],'alternative':'Relevant alternative','decision_basis':'Frozen sources and criteria'},'automatic_checks':[]}
    write_once(folder/'review-schema.json',example)
    return manifest
@locked_gate
def prepare(root,path,state,phase,production_report,producers,artifacts=None):
    preflight_dossier(path)
    if phase!=state['next_phase']: raise ValueError('Expected phase '+state['next_phase'])
    attempts=sum(read(p).get('phase')==phase for p in (path/'validation/dispatches').glob('*.json'))
    if attempts>=state.get('max_validation_attempts',4): raise ValueError('Validation attempt limit reached; report unresolved issues before another attempt')
    verify_history(path,state,history_relax(state))
    spec=read(CATALOG_ROOT/'config/phase-validation.json')['phases'].get(phase)
    if not spec: raise ValueError('No integrated acceptance specification for this phase')
    report=inside(path,production_report)
    if not producers or any(not isinstance(p,str) or not p.strip() for p in producers): raise ValueError('Observed producer agent IDs required')
    reviewers={s['agent_id'] for s in state.get('validator_sessions',[])}
    reviewers.update(read(p)['agent_id'] for p in (path/'validation/dispatches').glob('*.json'))
    if reviewers.intersection(producers): raise ValueError('A project validator cannot become a producer of reviewed outputs')
    requested=artifacts or [str(path/'stages'/phase/'product.md')]
    products=[inside(path,p) for p in requested]
    if not products or any(not p.read_bytes().strip() for p in products): raise ValueError('A step needs its actual nonempty product')
    # The packet is the reviewer handoff, not the production conversation.
    if any(p==report or p.name in ('state.json','findings.json') or 'receipts' in p.parts for p in products): raise ValueError('Do not pass author conclusions or review history as a product')
    normative_paths=route_evidence(state)
    packet_id=phase+'-'+uuid.uuid4().hex[:16]
    folder=confined_path(path,'validation/packets/'+packet_id)
    entries=[]; seen=set(); pending=[]
    def snapshot(p,role):
        p=Path(p)
        if p.is_relative_to(path) or p.is_relative_to(path.resolve()):p=inside(path,p)
        elif role=='form-profile':p=inside(root,p)
        elif role in ('acceptance-specification','report-schema','action-mode-controls','compliance-profile','source-registry','design-methodology-controls','award-criteria-controls'):
            p=inside(CATALOG_ROOT/'config',p)
        elif role=='design-methodology-contract':
            p=inside(CATALOG_ROOT/'docs',p)
        else:p=inside(CATALOG_ROOT/'sources',p)
        p=p.resolve()
        if p in seen: return
        seen.add(p); dest=folder/'snapshots'/f'{len(entries):04d}-{p.name}';data=p.read_bytes();pending.append((dest,data))
        entries.append({'id':'file-'+str(len(entries)), 'role':role,'original':str(p),'snapshot':str(dest.relative_to(path)), 'sha256':hashlib.sha256(data).hexdigest()})
    for p in products: snapshot(p,'step-product')
    for session in state.get('validator_sessions',[]):
        if session.get('superseded') or session.get('verdict')!='accept': continue
        _,previous=packet(path,session['packet_id'])
        for f in previous['files']:
            if accepted_product(f): snapshot(inside(path,f['snapshot']),'dependency-product')
    for name in ('brief.md','project.json','answers.json','evidence.json','annex-manifest.json','draft.md'):
        p=confined_path(path,name)
        if p.exists(): snapshot(p,'project-input')
    phase_zero=state.get('phase_zero')
    if phase_zero:
        handoff=inside(path,phase_zero.get('handoff_manifest',''))
        if digest(handoff)!=phase_zero.get('handoff_manifest_sha256'):
            raise ValueError('Imported Phase zero handoff manifest changed')
        handoff_data=read(handoff)
        if handoff_data.get('human_decision')!='PROCEED' or handoff_data.get('recommendation')!='PROCEED':
            raise ValueError('Imported Phase zero handoff is not a confirmed PROCEED')
        snapshot(handoff,'dependency-product')
        entries[-1]['accepted_product']=True
        for item in handoff_data.get('files',[]):
            dependency=inside(path,item.get('path',''))
            if digest(dependency)!=item.get('sha256'):
                raise ValueError('Imported Phase zero dependency changed')
            snapshot(dependency,'dependency-product')
            entries[-1]['accepted_product']=True
    if (path/'memory').exists():
        from project_memory import ProjectMemory
        memory=ProjectMemory(root,path.name)
        assessment=memory.check()
        if not assessment['passed']:
            raise ValueError('Working memory is incoherent; verify canonical log/seal and rebuild derived files before freezing')
        for name in ('events.jsonl','seal.json','context.md'):
            snapshot(path/'memory'/name,'working-memory')
    for item in read(path/'annex-manifest.json').get('annexes',[]):
        if item.get('status')!='not-applicable': snapshot(inside(path,item.get('path','')),'annex')
    if state.get('form_profile'): snapshot(inside(root,state['form_profile']),'form-profile')
    form_source=read(path/'answers.json').get('form_instance',{}).get('form_source')
    if isinstance(form_source,dict) and form_source.get('path'):
        original_form=cli_input(root,path,form_source['path'])
        if digest(original_form)!=form_source.get('sha256'):raise ValueError('Original form source hash mismatch')
        snapshot(original_form,'form-source')
    if phase in ('repair','qa'):
        snapshot(path/'findings.json','repair-targets')
        targets=[]
        for receipt in state.get('receipts',[]):
            if not receipt['phase'].startswith('validator-'): continue
            p=inside(root,receipt['path']); old=read(p)
            for issue in old.get('discrepancies',[]):
                targets.append({'origin_packet_id':old['packet_id'],'origin_receipt_sha256':receipt['sha256'],'discrepancy':issue})
                _,baseline=packet(path,old['packet_id'])
                for f in baseline['files']:
                    if f['id']==issue['file_id']: snapshot(inside(path,f['snapshot']),'repair-baseline')
        # Only the outstanding issues and exact baseline files are handed over;
        # previous verdicts, ratings and producer conclusions remain excluded.
        target_file=folder/'repair-targets.json';target_data=(json.dumps({'targets':targets,'source':'archived independent discrepancies; recheck applicability to current repair'},ensure_ascii=False,indent=2)+'\n').encode()
        pending.append((target_file,target_data))
        dest=folder/'snapshots'/f'{len(entries):04d}-repair-targets.json';pending.append((dest,target_data))
        entries.append({'id':'file-'+str(len(entries)),'role':'repair-targets','original':str(target_file),'snapshot':str(dest.relative_to(path)),'sha256':hashlib.sha256(target_data).hexdigest()})
        for session in state.get('validator_sessions',[]):
            _,previous=packet(path,session['packet_id'])
            for f in previous['files']:
                if accepted_product(f): snapshot(inside(path,f['snapshot']),'repair-baseline')
    snapshot(CATALOG_ROOT/'config/phase-validation.json','acceptance-specification')
    snapshot(CATALOG_ROOT/'config/stage-validation-report.schema.json','report-schema')
    snapshot(CATALOG_ROOT/'config/action-modes.json','action-mode-controls')
    snapshot(CATALOG_ROOT/'config/sources.json','source-registry')
    checks,coverage=compliance(state,phase)
    # Freeze the actual method handed to this reviewer. Old packet histories
    # retain their original contracts; this adds no retroactive plan migration.
    if any(c['id'].startswith('method-') for c in checks):
        snapshot(CATALOG_ROOT/'config/design-methodology.json','design-methodology-controls')
        snapshot(CATALOG_ROOT/'docs/design-methodology.md','design-methodology-contract')
    if state.get('checklist_protocol')=='project-checklist-v1':
        import checklist
        checklist_path=inside(path,'research/checklist-'+phase+'.json')
        instance=read(checklist_path)
        if instance.get('phase')!=phase: raise ValueError('Checklist belongs to a different phase')
        assessment=checklist.validate(instance,state,path)
        if not assessment['valid']: raise ValueError('Project checklist contract invalid: '+json.dumps(assessment['issues'][:6]))
        snapshot(checklist_path,'project-checklist')
        if phase in checklist.IDEA_PHASES:
            # Pin early award decisions even when the caller omits --artifact.
            # Existing snapshots/receipts have no flag and retain their policy.
            next(f for f in entries if Path(f['original'])==checklist_path.resolve())['accepted_product']=True
            award=instance.get('award_coverage',{})
            if award.get('selection_status')!='selected':
                raise ValueError('Resolve award criteria profile/variant/context before the independent idea gate')
            for profile in award.get('catalog_files',[]):
                snapshot(CATALOG_ROOT/profile['path'],'award-criteria-controls')
            for ref in award.get('source_refs',[]):
                localized=checklist.source_ref(ref['source_id'],ref['pages'])
                for page in localized['references']:
                    snapshot(Path(page['path']),'normative-evidence')
            for row in award.get('entries',[]):
                for ref in row.get('evidence',[]):
                    value=ref.get('path') or ref.get('local_snapshot')
                    if not value:
                        raise ValueError('Award idea evidence requires a localized local snapshot before freeze')
                    snapshot(checklist_file(path,value),'checklist-localized-evidence')
        for extension in instance['extensions']:
            check={k:extension[k] for k in ('classification','check','applicability','sources','scope')}
            check['id']=extension['check_id'];check['stages']=[phase]
            checks.append(check)
        if len({c['id'] for c in checks})!=len(checks): raise ValueError('Duplicate project compliance check ID')
        for row in instance['checks']+instance['extensions']+instance['section_coverage']:
            references=[]
            for ref in row.get('evidence',[])+row.get('artifact_locators',[])+row.get('sources',[]):
                references.extend(ref.get('references',[]) or [ref])
            for ref in references:
                other=ref.get('source_path_or_url','')
                value=ref.get('path') or ref.get('local_snapshot') or (other if other and not str(other).startswith('https://') else None)
                if not value and str(ref.get('url') or ref.get('source_path_or_url') or '').startswith('https://'):
                    raise ValueError('Online checklist evidence requires a localized local_snapshot before freeze')
                if value:
                    snapshot(checklist_file(path,value),'checklist-localized-evidence')
        coverage.append({'file':str(checklist_path),'coverage':{'scope':'project-specific','baseline':assessment['baseline_coverage'],'unresolved_items':assessment['unresolved_items'],'gaps':assessment['coverage_gaps'],'ready_for_independent_review':assessment['ready_for_independent_review']}})
    for c in coverage: snapshot(Path(c['file']),'compliance-profile')
    for check in checks:
        for source in check.get('sources',[]):
            if source.get('path'): snapshot(checklist_file(path,source['path']),'checklist-evidence')
    # Read exact immutable route sections and general conditions, with complete
    # locators. The reviewer chooses passages; snippets do not replace sources.
    import brain
    for p in normative_paths: snapshot(p,'normative-evidence')
    # User evidence may add national/form-specific sources. Bind exact files,
    # never invent missing evidence or copy prior scoring into the prompt.
    for e in read(report).get('evidence',[]):
        sid=e.get('source_id'); original=e.get('path')
        if original:
            raw=Path(original)
            candidate=raw if raw.is_absolute() else (root/raw if raw.parts and raw.parts[0] in ('projects','sources') else path/raw)
            permitted=path if candidate.resolve().is_relative_to(path.resolve()) else root/'sources'
            snapshot(inside(permitted,candidate),'localized-evidence')
        elif sid:
            source=brain.ROOT/'sources'/sid/'metadata.json'
            if source.exists():
                meta=read(source); n=re.search(r':p(\d+)',e.get('locator',''))
                base=brain.ROOT/'sources'/sid/'revisions'/meta['original_sha256']
                if n:
                    matches=list((base/'pages').glob(f'*{int(n.group(1)):04d}.md'))
                    if len(matches)==1: snapshot(matches[0],'localized-evidence')
                else:
                    full=base/'full.md'
                    if full.exists(): snapshot(full,'localized-evidence')
    identity={k:state[k] for k in ('program','year','action','sector')}
    project=read(path/'project.json')['project']
    identity.update({k:project.get(k,state.get(k)) for k in ('country','agency','role','round')})
    manifest={'schema_version':1,'deterministic_checks_policy':'allowlisted-python-v1','packet_id':packet_id,'phase':phase,'route':identity,'producer_ids':sorted(set(producers)), 'production_report':str(report),'production_sha256':digest(report),'state_sha256':digest(path/'state.json'), 'acceptance_checks':spec['acceptance_checks'],'automatic_checks_expected':spec.get('automatic_checks_expected',[]),'compliance_checks':checks,'coverage':coverage,'files':entries,'context_policy':'fresh-agent-fork-none-no-production-history','created_at':dt.datetime.now(dt.timezone.utc).isoformat()}
    folder.mkdir(parents=True)
    for destination,data in pending:
        destination.parent.mkdir(parents=True,exist_ok=True)
        with destination.open('xb') as out:out.write(data)
    write_once(folder/'manifest.json',manifest)
    write_once(folder/'review-schema.json',{'packet_id':packet_id,'packet_sha256':digest(folder/'manifest.json'),'phase':phase,'reviewer_id':'OBSERVED_NEW_AGENT_ID','verdict':'accept|revise|blocked','summary':'Evidence-based assessment','checks':[{'id':c['id'],'status':'pass|fail|unknown|not-applicable','evidence':[{'file_id':'file-0','locator':'precise section'}],'reason':'assessment and applicability'} for c in manifest['acceptance_checks']+checks],'discrepancies':[{'id':'D1','severity':'blocking|major|minor|editorial','check_id':'check-id','file_id':'file-id','locator':'exact passage','problem':'observed discrepancy','correction':'actionable correction'}]})
    # review-schema.json remains a fillable example, while this is the actual
    # structural schema enforced together with packet-specific checks below.
    (folder/'report-schema.json').write_bytes((CATALOG_ROOT/'config/stage-validation-report.schema.json').read_bytes())
    example=read(folder/'review-schema.json');example.update(verification_limits=['Observed tool context; no provider isolation attestation'],missing_information=[],critical_review={'weaknesses':['Observed or precisely justified absence'],'alternative':'Relevant alternative','decision_basis':'Sources and criteria'},automatic_checks=[{'id':i,'status':'pass|fail|not-applicable|blocked','reason':'Outcome and applicability','command':'Executed command when applicable','result':{},'evidence':[{'file_id':'file-0','locator':'actual input/section'}]} for i in manifest['automatic_checks_expected']])
    for c in example['checks']:c['verification']='Actual comparison or calculation performed'
    for c in example['discrepancies']:c.update(classification='requirement|award-criterion|recommendation|good-practice|local-method|data-consistency|unknown',reopen_phase=phase)
    (folder/'review-schema.json').write_text(json.dumps(example,ensure_ascii=False,indent=2)+'\n')
    return manifest
def packet(path,ident):
    if not re.fullmatch(r'[a-z0-9-]+',ident): raise ValueError('Invalid packet ID')
    p=inside(path,'validation/packets/'+ident+'/manifest.json');return p,read(p)
@locked_gate
def dispatch(path,state,ident,agent_id,session_id,fork_turns,observation):
    preflight_workspace(path,state)
    verify_history(path,state,history_relax(state))
    mp,m=packet(path,ident)
    if m['phase']!=state['next_phase'] or digest(inside(path,'state.json'))!=m['state_sha256']:
        raise ValueError('Workflow changed since validation packet preparation; stale dispatch refused')
    obs=inside(path,observation);o=read(obs)
    if fork_turns!='none' or o.get('tool')!='collaboration.spawn_agent' or o.get('request',{}).get('fork_turns')!='none' or o.get('result',{}).get('task_name')!=agent_id or o.get('packet_id')!=ident: raise ValueError('Dispatch requires the localized observed spawn result and fork none')
    used=state.get('validator_sessions',[])
    authors=set(m['producer_ids'])
    for p in (path/'validation/packets').glob('*/manifest.json'): authors.update(read(p)['producer_ids'])
    if not agent_id or not session_id or agent_id in authors or any(x['agent_id']==agent_id or x['session_id']==session_id for x in used): raise ValueError('Validator must be a fresh agent/session independent of all project producers and prior validators')
    # Also reserve IDs in pending dispatches, so parallel or rejected reviews
    # cannot reuse the same session under a different packet.
    for p in (path/'validation/dispatches').glob('*.json'):
        d=read(p)
        if d['agent_id']==agent_id or d['session_id']==session_id: raise ValueError('Validator session already dispatched')
    attempts=sum(read(p).get('phase')==m['phase'] for p in (path/'validation/dispatches').glob('*.json'))
    if attempts>=state.get('max_validation_attempts',4): raise ValueError('Validation attempt limit reached; report unresolved issues before another attempt')
    archived=confined_path(path,'validation/observations/'+ident+'.json')
    destination=confined_path(path,'validation/dispatches/'+ident+'.json')
    if archived.exists() or destination.exists():raise ValueError('Dispatch already recorded')
    data=obs.read_bytes();archived.parent.mkdir(parents=True,exist_ok=True)
    with archived.open('xb') as out:out.write(data)
    d={'packet_id':ident,'phase':m['phase'],'packet_sha256':digest(mp),'agent_id':agent_id,'session_id':session_id,'fork_turns':'none','observation':str(obs),'observation_sha256':hashlib.sha256(data).hexdigest(),'observation_archive':str(archived.relative_to(path)),'identity_verification':'coordinator-observed-not-host-authenticated','session_id_provenance':'caller-declared-not-provider-authenticated','lifecycle':'dispatched'}
    write_once(path/'validation/dispatches'/f'{ident}.json',d);return d
def rerun_automatic_checks(root,path,state,manifest):
    """Execute only imported, owned Python checkers; report command text is data."""
    from application import check_answers
    from project_check import check_model
    results=[]
    for ident in manifest['automatic_checks_expected']:
        if ident=='project-model':result=check_model(read(path/'project.json'),manifest['phase']=='qa')
        elif ident=='answer-characters':
            if not state.get('form_profile'):
                result={'passed':False,'issues':[{'code':'missing-form-profile'}]}
            else:result=check_answers(read(path/'answers.json'),read(inside(root,state['form_profile'])),manifest['phase']=='qa')
        else:raise ValueError('Unsupported automatic checker ID; no report command execution: '+ident)
        results.append({'id':ident,'result':result,'checker':'owned-python-api','phase':manifest['phase']})
    return results

def dispatch_lifecycle(path,ident):
    _,m=packet(path,ident)
    dp=inside(path,'validation/dispatches/'+ident+'.json');d=read(dp)
    if d['packet_sha256']!=digest(inside(path,'validation/packets/'+ident+'/manifest.json')):raise ValueError('Dispatch packet changed')
    if digest(inside(path,d.get('observation_archive',d['observation'])))!=d['observation_sha256']:raise ValueError('Dispatch observation archive changed')
    previous=digest(dp);status='dispatched';events=[]
    for ep in sorted((path/'validation/lifecycle'/ident).glob('*.json')):
        e=read(ep)
        if status in ('interrupted','cancelled') or e.get('previous_sha256')!=previous or e.get('packet_id')!=ident or e.get('agent_id')!=d['agent_id'] or e.get('status') not in ('interrupted','cancelled'):
            raise ValueError('Dispatch lifecycle chain invalid')
        if digest(inside(path,e['observation_archive']))!=e['observation_sha256']:raise ValueError('Lifecycle observation archive changed')
        previous=digest(ep);status=e['status'];events.append(e)
    anchor=read(path/'state.json').get('dispatch_lifecycle',{}).get(ident)
    if anchor and (not events or status!=anchor['status'] or previous!=anchor['event_sha256']):
        raise ValueError('Dispatch lifecycle terminal anchor missing or changed')
    return {'packet_id':ident,'phase':m['phase'],'status':status,'events':events,'dispatch_sha256':digest(dp),'budget_consumed':True,'identity_reserved':True,'verification_limit':'Coordinator-observed lifecycle, not host authentication'}

@locked_gate
def recover_dispatch(path,state,ident,status,observation,reason):
    if status not in ('interrupted','cancelled') or not reason.strip():raise ValueError('Recovery requires terminal status and reason')
    current=dispatch_lifecycle(path,ident)
    if current['status']!='dispatched' or any(s['packet_id']==ident for s in state.get('validator_sessions',[])):
        raise ValueError('Only a pending dispatch can be interrupted/cancelled; recorded gates remain historical')
    dp=inside(path,'validation/dispatches/'+ident+'.json');d=read(dp)
    source=inside(path,observation);obs=read(source)
    if obs.get('tool')!='collaboration.interrupt_agent' or obs.get('request',{}).get('target')!=d['agent_id'] or not isinstance(obs.get('result'),dict) or not obs['result']:
        raise ValueError('Recovery requires localized observed interrupt tool request/result for the dispatched agent')
    archive=confined_path(path,'validation/lifecycle-observations/'+ident+'.json')
    archive.parent.mkdir(parents=True,exist_ok=True)
    with archive.open('xb') as out:out.write(source.read_bytes())
    event={'schema_version':'dispatch-lifecycle-v1','packet_id':ident,'agent_id':d['agent_id'],'status':status,'reason':reason,'previous_sha256':digest(dp),'observation_archive':str(archive.relative_to(path)),'observation_sha256':digest(archive),'observed_at':dt.datetime.now(dt.timezone.utc).isoformat(),'verification_limit':'Observed tool export supplied by coordinator; not independently host-authenticated'}
    event_path=confined_path(path,'validation/lifecycle/'+ident+'/0001.json')
    write_once(event_path,event)
    state.setdefault('dispatch_lifecycle',{})[ident]={'status':status,'event_sha256':digest(event_path)}
    # Per-file atomic publication under the cooperative lock, not a transaction.
    with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path,prefix='.state-recovery-',delete=False) as output:
        temp=Path(output.name);output.write(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
    try:temp.replace(confined_path(path,'state.json'))
    finally:
        if temp.exists():temp.unlink()
    return dispatch_lifecycle(path,ident)

def validate_schema(value,schema,location='$'):
    """Enforce the schema subset used by the frozen report contract, stdlib only."""
    allowed={'$schema','title','type','required','properties','items','enum','minLength','minItems','additionalProperties'}
    unknown=set(schema)-allowed
    if unknown:raise ValueError('Unsupported report schema keyword: '+','.join(sorted(unknown)))
    types={'object':lambda v:isinstance(v,dict),'array':lambda v:isinstance(v,list),'string':lambda v:isinstance(v,str),'integer':lambda v:isinstance(v,int) and not isinstance(v,bool),'number':lambda v:isinstance(v,(int,float)) and not isinstance(v,bool),'boolean':lambda v:isinstance(v,bool),'null':lambda v:v is None}
    wanted=schema.get('type')
    if wanted and (wanted not in types or not types[wanted](value)):raise ValueError('Validation structural contract '+location+': expected '+str(wanted))
    if 'enum' in schema and value not in schema['enum']:raise ValueError('Validation structural contract '+location+': unsupported value')
    if isinstance(value,str) and len(value)<schema.get('minLength',0):raise ValueError('Validation structural contract '+location+': text too short')
    if isinstance(value,list):
        if len(value)<schema.get('minItems',0):raise ValueError('Validation structural contract '+location+': too few items')
        for i,item in enumerate(value):validate_schema(item,schema.get('items',{}),location+'['+str(i)+']')
    if isinstance(value,dict):
        for key in schema.get('required',[]):
            if key not in value:raise ValueError('Validation structural contract '+location+': missing '+key)
        for key,child in schema.get('properties',{}).items():
            if key in value:validate_schema(value[key],child,location+'.'+key)
        if schema.get('additionalProperties') is False and set(value)-set(schema.get('properties',{})):raise ValueError('Validation structural contract '+location+': unknown field')

def original_file(root,path,entry):
    original=Path(entry['original'])
    if original.is_relative_to(path) or original.is_relative_to(path.resolve()):return inside(path,original)
    if entry['role']=='form-profile':return inside(root,original)
    if entry['role'] in ('acceptance-specification','report-schema','action-mode-controls','compliance-profile','source-registry','design-methodology-controls','award-criteria-controls','phase-zero-policy','action-registry'):
        return inside(CATALOG_ROOT/'config',original)
    if entry['role']=='design-methodology-contract':
        return inside(CATALOG_ROOT/'docs',original)
    return inside(CATALOG_ROOT/'sources',original)

@locked_gate
def verify(root,path,state,ident,validation_report,production_report=None):
    verify_history(path,state,history_relax(state))
    mp,m=packet(path,ident);report=inside(path,validation_report);r=read(report);dp=inside(path,'validation/dispatches/'+ident+'.json');d=read(dp)
    if dispatch_lifecycle(path,ident)['status'] in ('interrupted','cancelled'):
        raise ValueError('Terminal dispatch cannot accept a report; prepare a fresh packet and validator within remaining budget')
    if not isinstance(r,dict):raise ValueError('Validation structural contract $: expected object')
    if m['phase']!=state['next_phase'] or digest(path/'state.json')!=m['state_sha256']: raise ValueError('Workflow changed since validation packet preparation')
    production=inside(path,m['production_report'])
    if production_report and inside(path,production_report).resolve()!=production.resolve(): raise ValueError('Review belongs to a different production report')
    if digest(production)!=m['production_sha256']: raise ValueError('Production report changed since packet freeze')
    if d['packet_sha256']!=digest(mp) or r.get('packet_sha256')!=digest(mp) or r.get('packet_id')!=ident or r.get('phase')!=m['phase']: raise ValueError('Review or dispatch does not match the immutable packet')
    if r.get('reviewer_id')!=d['agent_id'] or d['fork_turns']!='none' or d['agent_id'] in m['producer_ids']: raise ValueError('Reviewer identity/independence mismatch')
    schema_entries=[f for f in m['files'] if f['role']=='report-schema']
    if len(schema_entries)!=1:raise ValueError('Packet needs exactly one frozen report schema')
    schema=read(inside(path,schema_entries[0]['snapshot']))
    validate_schema(r,schema)
    critique=r.get('critical_review',{})
    if not isinstance(r.get('verification_limits'),list) or not r['verification_limits'] or not isinstance(r.get('missing_information'),list) or not isinstance(critique,dict) or not all(critique.get(k) for k in ('weaknesses','alternative','decision_basis')): raise ValueError('Validation needs limits, missing information and independent critical review')
    if digest(inside(path,d.get('observation_archive',d['observation'])))!=d['observation_sha256']: raise ValueError('Observed dispatch record changed')
    for f in m['files']:
        if digest(inside(path,f['snapshot']))!=f['sha256'] or digest(original_file(root,path,f))!=f['sha256']: raise ValueError('A packet input/product/source changed; prepare and review a fresh packet')
    expected={c['id'] for c in m['acceptance_checks']+m['compliance_checks']}; rows=r.get('checks',[]); identifiers=[c.get('id') for c in rows]
    if len(identifiers)!=len(set(identifiers)) or set(identifiers)!=expected: raise ValueError('Validator must assess every acceptance and compliance check exactly once')
    files={f['id'] for f in m['files']}; failing=False
    always_applicable={c['id'] for c in m['acceptance_checks']}
    import checklist
    if m['phase'] in checklist.FORM_REQUIRED_PHASES:always_applicable.add('shared-form')
    for c in rows:
        if c.get('status') not in ('pass','fail','unknown','not-applicable') or not c.get('reason') or not c.get('verification') or not c.get('evidence'): raise ValueError('Each validation check needs status, actual verification, reason and localized evidence')
        if any(e.get('file_id') not in files or not e.get('locator') for e in c['evidence']): raise ValueError('Validation evidence must locate a frozen packet file')
        if c['id'] in always_applicable and c['status']=='not-applicable': raise ValueError('Step acceptance checks cannot be skipped as not applicable')
        failing|=c['status'] in ('fail','unknown')
    discrepancies=r.get('discrepancies')
    if not isinstance(discrepancies,list): raise ValueError('Validation report needs a discrepancies list')
    for f in discrepancies:
        allowed_phases=set(read(CATALOG_ROOT/'config/phase-validation.json')['phases'])|{'phase-zero'}
        if f.get('severity') not in ('blocking','major','minor','editorial') or f.get('check_id') not in expected or f.get('file_id') not in files or not all(f.get(k) for k in ('id','locator','problem','correction')) or f.get('classification') not in ('requirement','award-criterion','recommendation','good-practice','local-method','data-consistency','unknown') or f.get('reopen_phase') not in allowed_phases: raise ValueError('Discrepancy needs valid severity, classification, check, passage, correction and dependent phase')
    for c in rows:
        if c['status'] in ('fail','unknown') and not any(f['check_id']==c['id'] for f in discrepancies): raise ValueError('Failed/unknown check requires a localized discrepancy')
    verdict=r.get('verdict')
    automatic=r.get('automatic_checks',[])
    if not isinstance(automatic,list) or {c.get('id') for c in automatic}!=set(m['automatic_checks_expected']) or len(automatic)!=len(m['automatic_checks_expected']): raise ValueError('All phase-specific automatic checks must be reported exactly once')
    deterministic=[]
    if m.get('deterministic_checks_policy')=='allowlisted-python-v1':
        deterministic=rerun_automatic_checks(root,path,state,m)
        if verdict=='accept' and any(not row['result']['passed'] for row in deterministic):
            raise ValueError('Deterministic automatic checks failed; declarations cannot override actual checker result')
    for c in automatic:
        if c.get('status') not in ('pass','fail','not-applicable','blocked') or not c.get('reason') or not c.get('evidence') or any(e.get('file_id') not in files or not e.get('locator') for e in c['evidence']): raise ValueError('Automatic check needs status and localized result/input evidence')
        if c['status'] in ('pass','fail') and (not c.get('command') or not isinstance(c.get('result'),dict)):raise ValueError('Executed automatic check needs its command and result')
        if verdict=='accept' and c['status']!='pass':raise ValueError('An expected automatic check must pass before acceptance')
    if verdict not in ('accept','revise','blocked') or not r.get('summary'): raise ValueError('Invalid independent validation verdict')
    if verdict=='accept' and (failing or any(f['severity'] in ('blocking','major') for f in discrepancies)): raise ValueError('Accept cannot coexist with failed/unknown checks or major/blocking discrepancies')
    return {'packet_id':ident,'packet_sha256':digest(mp),'dispatch_sha256':digest(dp),'agent_id':d['agent_id'],'session_id':d['session_id'],'report_path':str(report),'report_sha256':digest(report),'verdict':verdict,'checks':len(rows),'isolation_attestation':'observed tool dispatch, not provider-certified sandbox isolation','identity_verification':'coordinator-observed-not-host-authenticated','automatic_verification':'allowlisted-python-v1' if deterministic else 'declared-report-only-no-command-execution','deterministic_checks':deterministic}
def accepted_product(entry):
    return entry['role']=='step-product' or entry.get('accepted_product') is True

def verify_history(path,state,relax_phases=()):
    preflight_workspace(path,state)
    for dp in (path/'validation/dispatches').glob('*.json'):
        dispatch_lifecycle(path,dp.stem)
    for s in state.get('validator_sessions',[]):
        mp,m=packet(path,s['packet_id']);dp=inside(path,'validation/dispatches/'+s['packet_id']+'.json')
        if digest(mp)!=s['packet_sha256'] or digest(dp)!=s['dispatch_sha256']: raise ValueError('Archived validation packet/dispatch changed')
        d=read(dp)
        if digest(inside(path,d.get('observation_archive',d['observation'])))!=d['observation_sha256']:
            raise ValueError('Archived observed dispatch record changed')
        for f in m['files']:
            if digest(inside(path,f['snapshot']))!=f['sha256']: raise ValueError('Archived validation snapshot changed')
            if accepted_product(f) and s.get('verdict')=='accept' and not s.get('superseded') and m['phase'] not in relax_phases:
                if digest(inside(path,f['original']))!=f['sha256']: raise ValueError('Accepted step product changed; invalidate its earliest affected phase')
def _main():
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='cmd',required=True)
    q=sub.add_parser('prepare');q.add_argument('name');q.add_argument('--phase',required=True);q.add_argument('--report',required=True);q.add_argument('--producer-id',action='append',required=True);q.add_argument('--artifact',action='append')
    q=sub.add_parser('dispatch');q.add_argument('name');q.add_argument('--packet',required=True);q.add_argument('--agent-id',required=True);q.add_argument('--session-id',required=True);q.add_argument('--fork-turns',choices=['none'],required=True);q.add_argument('--observation',required=True)
    q=sub.add_parser('recover-dispatch');q.add_argument('name');q.add_argument('--packet',required=True);q.add_argument('--status',choices=['interrupted','cancelled'],required=True);q.add_argument('--observation',required=True);q.add_argument('--reason',required=True)
    q=sub.add_parser('dispatch-status');q.add_argument('name');q.add_argument('--packet',required=True)
    q=sub.add_parser('verify');q.add_argument('name');q.add_argument('--packet',required=True);q.add_argument('--report',required=True)
    q=sub.add_parser('prepare-idea');q.add_argument('name');q.add_argument('--report',required=True);q.add_argument('--producer-id',action='append',required=True);q.add_argument('--artifact',action='append')
    q=sub.add_parser('dispatch-idea');q.add_argument('name');q.add_argument('--packet',required=True);q.add_argument('--agent-id',required=True);q.add_argument('--session-id',required=True);q.add_argument('--fork-turns',choices=['none'],required=True);q.add_argument('--observation',required=True)
    q=sub.add_parser('recover-idea-dispatch');q.add_argument('name');q.add_argument('--packet',required=True);q.add_argument('--status',choices=['interrupted','cancelled'],required=True);q.add_argument('--observation',required=True);q.add_argument('--reason',required=True)
    q=sub.add_parser('idea-dispatch-status');q.add_argument('name');q.add_argument('--packet',required=True)
    q=sub.add_parser('verify-idea');q.add_argument('name');q.add_argument('--packet',required=True);q.add_argument('--report',required=True)
    a=p.parse_args();is_idea=a.cmd in ('prepare-idea','dispatch-idea','recover-idea-dispatch','idea-dispatch-status','verify-idea')
    path=idea_lab(ROOT,a.name) if is_idea else dossier(ROOT,a.name);state=read(path/'state.json')
    if a.cmd=='prepare':
        artifacts=[cli_input(ROOT,path,x) for x in a.artifact] if a.artifact else None
        m=prepare(ROOT,path,state,a.phase,cli_input(ROOT,path,a.report),a.producer_id,artifacts)
        r={'packet_id':m['packet_id'],'phase':m['phase'],'route':m['route'],'manifest':str(path/'validation/packets'/m['packet_id']/'manifest.json'),'input_files':len(m['files']),'acceptance_checks':len(m['acceptance_checks']),'compliance_checks':len(m['compliance_checks'])}
    elif a.cmd=='prepare-idea':
        artifacts=[cli_input(ROOT,path,x) for x in a.artifact] if a.artifact else None
        m=prepare_idea(ROOT,path,state,cli_input(ROOT,path,a.report),a.producer_id,artifacts)
        r={'packet_id':m['packet_id'],'phase':m['phase'],'route':m['route'],'manifest':str(path/'validation/packets'/m['packet_id']/'manifest.json'),'input_files':len(m['files']),'acceptance_checks':len(m['acceptance_checks']),'compliance_checks':0}
    elif a.cmd in ('dispatch','dispatch-idea'):r=dispatch(path,state,a.packet,a.agent_id,a.session_id,a.fork_turns,cli_input(ROOT,path,a.observation))
    elif a.cmd in ('recover-dispatch','recover-idea-dispatch'):r=recover_dispatch(path,state,a.packet,a.status,cli_input(ROOT,path,a.observation),a.reason)
    elif a.cmd in ('dispatch-status','idea-dispatch-status'):r=dispatch_lifecycle(path,a.packet)
    else:r=verify(ROOT,path,state,a.packet,cli_input(ROOT,path,a.report))
    print(json.dumps(r,ensure_ascii=False,indent=2))
def main():
    if any(flag in sys.argv[1:] for flag in ('-h','--help')):return _main()
    if len(sys.argv)>2 and sys.argv[1] in ('prepare','dispatch','verify','recover-dispatch','dispatch-status','prepare-idea','dispatch-idea','verify-idea','recover-idea-dispatch','idea-dispatch-status'):
        resolver=idea_lab if 'idea' in sys.argv[1] else dossier
        with project_lock(resolver(ROOT,sys.argv[2])):return _main()
    return _main()

if __name__=='__main__':
    try:main()
    except (ValueError,OSError,KeyError,TypeError) as e: print(str(e),file=sys.stderr);sys.exit(1)
