#!/usr/bin/env python3
"""Persistent receipts for the Codex-driven agentic loop, not an LLM runtime.

The agent supplies evidence-based phase reports. This helper checks sequencing,
frozen-draft hashes, blockers and revision limits, not substantive eligibility.
"""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
import shutil

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from brain import resolve_action, load, route_program
from application import check_answers
from project_check import check_model, check_manifest, TABLES, action_mode
import stage_gate
from project_lock import project_lock
import human_approval
from project_paths import resolve_project, new_identifier, bounded, initialize_directories, confined_path, preflight_dossier, project_input, validate_identifier
from project_memory import ProjectMemory, opening_context

COMPACT=['eligibility','design','draft','review','repair','qa']
INTEGRATED=['idea-validation','needs-impact-research','concept-note','intervention-design','work-packages','partner-concept','answer-outlines','application-draft','annexes','review','repair','qa']
PHASES=list(dict.fromkeys(COMPACT+INTEGRATED))
IDEA_DECISIONS=('PROCEED','REFINE','PIVOT','STOP')
IDEA_ROUTE_IDENTITY=tuple(json.loads((ROOT/'config/phase-zero.json').read_text()).get('route_identity_fields',()))
if IDEA_ROUTE_IDENTITY!=('program','year','action','sector','country','agency','role','round'):
    raise RuntimeError('Invalid Phase zero route identity policy')
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,data):
    path=confined_path(ROOT,path)
    temp=None
    try:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,prefix='.'+path.name+'-',suffix='.tmp',delete=False) as output:
            temp=Path(output.name);output.write(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
        temp.replace(path)
    finally:
        if temp and temp.exists():temp.unlink()
def project(name):
    return resolve_project(ROOT,name)

def idea_lab(name,must_exist=True):
    base=confined_path(ROOT,ROOT/'work'/'idea-lab')
    direct=confined_path(base,base/name)
    if (direct/'state.json').is_file():
        return stage_gate.preflight_workspace(direct,json.loads((direct/'state.json').read_text()))
    matches=[]
    if base.exists():
        for state_file in sorted(base.glob('*/state.json')):
            candidate=confined_path(base,state_file.parent)
            state=json.loads(confined_path(candidate,'state.json',True).read_text())
            if state.get('name')==name:matches.append(candidate)
    if len(matches)>1:raise ValueError('Ambiguous idea name; use the complete idea-lab ID')
    if matches:return stage_gate.preflight_workspace(matches[0],json.loads((matches[0]/'state.json').read_text()))
    if must_exist:raise ValueError('Missing idea-lab workspace')
    return direct

def idea_input(path,value,must_exist=True):
    raw=Path(value)
    if not raw.is_absolute():
        engine_candidate=ROOT/raw
        raw=engine_candidate if raw.parts[:2]==('work','idea-lab') else path/raw
    return confined_path(path,raw,must_exist)

def idea_archive(state,path,source,label,status):
    identity=digest(source);target=confined_path(path,path/'receipts'/f'{len(state["receipts"])+1:04d}-{label}-{identity[:12]}.json')
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as output:output.write(source.read_bytes())
    state['receipts'].append({'phase':label,'path':str(target.relative_to(path)),'sha256':identity,'status':status,'at':dt.datetime.now(dt.timezone.utc).isoformat()})

def verify_idea_history(state,path):
    stage_gate.verify_history(path,state)
    for receipt in state.get('receipts',[]):
        archived=confined_path(path,path/receipt['path'],True)
        if digest(archived)!=receipt['sha256']:raise ValueError('Archived idea-lab receipt missing or changed')

def initialize_idea(a):
    if a.year!=2026:raise ValueError('No indexed corpus for this annuality')
    if not 1<=a.max_revisions<=20:raise ValueError('max-revisions must be 1..20')
    validate_identifier(a.name)
    if '--' in a.name or len(a.name)>64:raise ValueError('Idea name must be a short slug without the reserved -- delimiter')
    ident=f'{a.name}--{a.year}';base=confined_path(ROOT,ROOT/'work'/'idea-lab');path=confined_path(base,base/ident)
    if path.exists():raise ValueError('Idea-lab workspace already exists; inspect its status instead')
    state={'schema_version':'idea-lab-state-v1','workspace_type':'idea-lab','id':ident,'name':a.name,'title':a.title or a.name,
           'year':a.year,'state':'brainstorming','next_phase':'phase-zero','revisions':0,'max_revisions':a.max_revisions,
           'validation_protocol':'fresh-step-v1','validator_sessions':[],'max_validation_attempts':a.max_revisions+1,
           'receipts':[],'blockers':[],'human_decisions':[]}
    import checklist
    matrix=checklist.phase_zero_template(state)
    for folder in ('research','reports','receipts','sessions','stages/phase-zero','validation/packets','validation/reports','validation/dispatches','validation/observations','validation/lifecycle','validation/lifecycle-observations','handoff'):
        confined_path(path,path/folder).mkdir(parents=True,exist_ok=True)
    save(path/'state.json',state)
    (path/'brief.md').write_text('# Idea lab\n\nRecord the core idea, real constraints, confirmed facts, and open questions. Creating this workspace does not select a call or establish eligibility.\n')
    (path/'brainstorm.md').write_text('# Open brainstorming\n\n')
    save(path/'brainstorm.json',{'schema_version':'phase-zero-brainstorm-v1','idea_version':1,
        'authority':'collaborative-exploration-not-human-approval','provenance':[],'options':[],
        'convergence':{'preferred_option_id':None,'compared_option_ids':[],'selection_reasons':[]},
        'alternative_exception':None})
    save(path/'research/checklist-phase-zero.json',matrix)
    (path/'README.md').write_text(f'# {state["title"]} — Phase zero\n\nID: `{ident}`. Exploratory workspace outside `projects/`: no route, sector, or application is created. The versioned phase product is `stages/phase-zero/decision.md` with `decision.json`; a fresh validation checks the exact package. The observed human decision remains separate from the recommendation. Only a recommended, validated, and confirmed PROCEED may be promoted to a dossier, which will still begin with `idea-validation`.\n')
    return path,state

def validate_human_idea_decision(data,state,path):
    if not isinstance(data,dict) or data.get('schema_version')!='phase-zero-human-decision-v1':raise ValueError('Invalid human Phase zero decision schema')
    if data.get('decision') not in IDEA_DECISIONS:raise ValueError('Human decision must be PROCEED, REFINE, PIVOT or STOP')
    if data.get('provenance')!='user-instruction' or not isinstance(data.get('observed_reference'),str) or not data['observed_reference'].strip():
        raise ValueError('Human decision requires an observed user-instruction reference')
    if not isinstance(data.get('rationale'),str) or not data['rationale'].strip():raise ValueError('Human decision requires rationale')
    if data.get('accepted_packet_id')!=state.get('pending_human_decision',{}).get('packet_id') or data.get('accepted_packet_sha256')!=state.get('pending_human_decision',{}).get('packet_sha256'):
        raise ValueError('Human decision does not bind the accepted Phase zero package')
    if data.get('accepted_decision_sha256')!=state.get('pending_human_decision',{}).get('decision_sha256'):
        raise ValueError('Human decision does not bind the accepted Phase zero decision version')
    if data['decision']=='PROCEED':
        recommendation=json.loads((path/'stages/phase-zero/decision.json').read_text());route=recommendation.get('route_handoff')
        selected=data.get('selected_route')
        if not isinstance(selected,dict) or not isinstance(route,dict) or any(key not in selected or selected.get(key)!=route.get(key) for key in IDEA_ROUTE_IDENTITY):
            raise ValueError('Human PROCEED must explicitly bind the accepted selected route')
    return data

def freeze_bundle(path):
    preflight_dossier(path)
    files=[path/name for name in ('draft.md','project.json','answers.json','evidence.json','annex-manifest.json')]
    manifest=json.loads((path/'annex-manifest.json').read_text())
    for item in manifest.get('annexes',[]):
        if item.get('status')=='not-applicable': continue
        candidate=(path/item.get('path','')).resolve()
        if not candidate.is_relative_to(path.resolve()) or not candidate.is_file(): raise ValueError('Annex missing or outside dossier')
        files.append(candidate)
    return {str(f.resolve().relative_to(path.resolve())):digest(f) for f in files}

def localized_evidence(report,path):
    if not report.get('summary') or not isinstance(report.get('evidence'),list) or not report['evidence']:
        raise ValueError('A report needs a summary and localized evidence entries')
    known={s['id'] for s in load('sources.json')}
    for e in report['evidence']:
        if not isinstance(e,dict) or not e.get('source_id') or not e.get('locator'): raise ValueError('Evidence entry requires source_id and locator')
        if e['source_id'] not in known:
            candidate=project_input(ROOT,path,e.get('path',''))
            if e.get('provenance') not in ('user-provided','agent-observed') or not candidate.is_relative_to(path.resolve()) or not candidate.is_file():
                raise ValueError('Unknown source ID without a localized project artifact and explicit provenance')

def archive_receipt(state,path,report_path,phase,status):
    ident=digest(report_path); archive=path/'receipts'/f'{len(state["receipts"])+1:04d}-{phase}-{ident[:12]}.json'
    archive=confined_path(path,archive)
    archive.parent.mkdir(exist_ok=True)
    with archive.open('xb') as output:output.write(report_path.read_bytes())
    state['receipts'].append(dict(phase=phase,path=str(archive.resolve().relative_to(ROOT.resolve())),sha256=ident,status=status,at=dt.datetime.now(dt.timezone.utc).isoformat()))

def verify_receipts(state,path,relax_phases=()):
    for receipt in state['receipts']:
        archive=(ROOT/receipt['path']).resolve()
        if not archive.is_relative_to(path.resolve()) or not archive.is_file() or digest(archive)!=receipt['sha256']:
            raise ValueError('Archived phase receipt missing or changed')
    stage_gate.verify_history(path,state,relax_phases)

def localized_profile(relative,state=None):
    path=confined_path(ROOT,relative,True)
    profile=json.loads(path.read_text())
    if not isinstance(profile.get('questions'),list): raise ValueError('Form profile needs questions')
    from form_profile import validate_profile
    profile_check=validate_profile(profile)
    if not profile_check['passed']:raise ValueError('Invalid form profile: '+json.dumps(profile_check['issues'][:8]))
    if state:
        relative_parts=path.resolve().relative_to(ROOT.resolve()).parts
        if relative_parts and relative_parts[0]=='projects' and (not state.get('id') or len(relative_parts)<2 or relative_parts[1]!=state['id']):
            raise ValueError('Form profile belongs to a different project dossier')
        programme=profile.get('program',profile.get('programme'))
        if programme and programme!=state['program']: raise ValueError('Form profile and programme do not match')
        if profile.get('action_family') and not state['action'].startswith(profile['action_family']): raise ValueError('Form profile and action do not match')
        if profile.get('action') and profile['action']!=state['action']: raise ValueError('Form profile and action do not match')
        if profile.get('sector') and state.get('sector') and profile['sector']!=state['sector']: raise ValueError('Form profile and sector do not match')
        if profile.get('call_year') and profile['call_year']!=state['year']: raise ValueError('Form profile and call year do not match')
    return str(path.resolve().relative_to(ROOT.resolve()))

def readiness(path,state):
    model=json.loads((path/'project.json').read_text()); result=check_model(model,True)
    if any(model.get('project',{}).get(k)!=state.get(k) for k in ('program','year','action','sector')):
        raise ValueError('Project model and dossier route do not match')
    if not result['passed']: raise ValueError('Project checks failed: '+json.dumps(result['issues'][:12]))
    manifest=json.loads((path/'annex-manifest.json').read_text()); annexes=check_manifest(manifest,path,True)
    if not annexes['passed']: raise ValueError('Annex checks failed: '+json.dumps(annexes['issues'][:12]))
    if not state.get('form_profile'): raise ValueError('No current form profile selected')
    localized_profile(state['form_profile'],state)
    profile=json.loads((ROOT/state['form_profile']).read_text()); answers=json.loads((path/'answers.json').read_text())
    instance=answers.get('form_instance',{})
    if any(instance.get(k)!=state.get(k) for k in ('program','year','action','sector')): raise ValueError('Verified form instance and dossier route do not match')
    limits=check_answers(answers,profile,True)
    if not limits['passed']: raise ValueError('Application checks failed: '+json.dumps(limits['issues'][:12]))


def initialize_dossier(a):
    if a.year!=2026: raise ValueError('No indexed corpus for this annuality')
    if not 1<=a.max_revisions<=20: raise ValueError('max-revisions must be 1..20')
    code=resolve_action(a.action,a.sector)
    route=next((r for r in load('actions.json') if r['code']==code),None)
    if not route: raise ValueError('Choose one exact action')
    controls=action_mode(route_program(route),code,a.sector.upper(),a.year)
    if any(x not in {row['id'] for row in load('annexes.json')} for x in a.annex):raise ValueError('Unknown annex workspace ID')
    ident=new_identifier(a.name,code,a.sector.upper(),a.year)
    path=bounded(ROOT,ident);state_path=path/'state.json'
    profile=None
    if a.form_profile:
        profile=localized_profile(a.form_profile,{'program':route_program(route),'action':code,'year':a.year,'sector':a.sector.upper(),'id':ident})
    if path.exists(): raise ValueError('Project folder already exists; preserve its contents and inspect status instead')
    phases=INTEGRATED if a.process=='integrated' else COMPACT
    initialize_directories(path,phases,code,a.annex,create=False)
    path.mkdir(parents=True,exist_ok=True)
    state=dict(name=a.name,action=code,sector=a.sector.upper(),year=a.year,program=route_program(route),process=a.process,form_profile=profile,state='collecting-data',next_phase='eligibility' if a.process=='compact' else 'idea-validation',revisions=0,max_revisions=a.max_revisions,receipts=[],blockers=[])
    state.update(id=ident,title=a.title or a.name,layout_version='project-layout-v1',
                 phase_zero_status=getattr(a,'phase_zero_status','bypassed-direct-init'))
    state.update(validation_protocol='fresh-step-v1',validator_sessions=[],max_validation_attempts=a.max_revisions+1)
    state['checklist_protocol']='project-checklist-v1'
    state.update({k:getattr(a,k) for k in ('country','agency','role','round')})
    save(state_path,state)
    (path/'brief.md').write_text('# Project dossier\n\nRecord the request and the coordinator/partner’s real data, needs and evidence, target groups, year/round, application form, assumptions, and decisions. Creating the dossier does not confirm any data.\n')
    (path/'evidence.json').write_text('[]\n'); (path/'findings.json').write_text('[]\n')
    model={'schema_version':'project-model-v2','project':{k:state[k] for k in ('program','year','action','sector')},**{t:[] for t in TABLES}}
    model['project'].update(duration_months=None,requested_grant=None,currency='EUR',financial_model='unverified',management_wp_id=None)
    state['action_mode']=controls['mode']
    model['project']['action_mode']=controls['mode']
    if not controls['financial_model_required']: model['project']['financial_model']='not-applicable'
    if controls['requirements_evidence_field']: model['project'][controls['requirements_evidence_field']]=[]
    save(state_path,state)
    model['project'].update({k:state[k] for k in ('country','agency','role','round')})
    model['project'].update(id=ident,title=state['title'])
    save(path/'project.json',model); save(path/'answers.json',{'form_instance':{},'answers':[]}); save(path/'annex-manifest.json',{'coverage_verified':False,'annexes':[]})
    phases=INTEGRATED if a.process=='integrated' else COMPACT
    workspaces=initialize_directories(path,phases,code,a.annex)
    memory=ProjectMemory(ROOT,ident).initialize()
    if not memory['passed']:raise ValueError('Working memory initialization failed: '+json.dumps(memory['issues']))
    (path/'draft.md').write_text('')
    import wayfinder
    wayfinder.initialize(path,state,ROOT)
    (path/'README.md').write_text(f'# {state["title"]}\n\nID: `{ident}`; route `{code}`, sector `{state["sector"]}`, call `{a.year}`. Open the shared engine as a Codex project and assign this dossier as context.\n\nShared data: project.json. Request and facts: brief.md/evidence.json. inbox contains inputs; research contains evidence about needs; design contains the intervention logic; partners contains verified contributions; application contains the outline and editorial versions; exports contains deliverables. draft.md and answers.json are the canonical application versions; do not duplicate their data.\n\nEach phase produces stages/PHASE/product.md or an explicit artifact. Production is not validation: stage_gate.py freezes the package; a new fork-none agent writes validation/reports; workflow record requires the relevant gate. Do not rename or move a validated dossier; preserve frozen references. Do not copy data into regulatory memory.\n\nShared instructions: [creating dossiers](../../docs/project-creation.md), [orchestrator](../../docs/orchestrator-protocol.md).\n')
    (path/'AGENTS.md').write_text(f'# Application context {ident}\n\nInherit the engine rules from ../../AGENTS.md and use ../../skills/erasmus-designer/SKILL.md. Keep all data and outputs for this application in this dossier. The name/route does not establish eligibility or the form version. Use its complete ID in workflow/stage_gate commands. An annex folder is only a workspace: required, optional, and NA status must be verified in the manifest against sources. A new fork-none validator is required for every gate. A producer’s mandate must not modify the corpus or other applications.\n')
    with (path/'AGENTS.md').open('a') as out:
        out.write(f'\nOn resumption and before each phase, read ../../skills/erasmus-project-memory/SKILL.md and open the memory from the engine root with `python3 scripts/project_memory.py context {ident} --phase PHASE`. Retrieve active confirmations, proposals, hypotheses, open questions, and contradictions. The lead records new facts, decisions, relevant options, and status changes with author, provenance, and real evidence; do not attribute confirmations to the user without an observed instruction. Do not edit events or generated views. Memory confirmations do not update project.json, modify state.json, or close gates; the coordinator separately integrates any required data and invalidations.\n')
    with (path/'README.md').open('a') as out:
        out.write('\nWorking memory: memory/events.jsonl and memory/seal.json are canonical; index.json, context.md, and history.md are rebuildable views. Before each phase, open the context via CLI, then record relevant decisions and evidence. [Working memory contract](../../docs/project-working-memory.md).\n')
    (path/'annexes/README.md').write_text('# Annex workspace\n\nPrepared folders: '+(', '.join(workspaces) or 'none specified; select after verifying the action')+'.\n\nThese folders do not establish mandatory uploads. Use the engine’s config/annexes.json, the specific owner, project.json data, and annex-manifest.json to record actual files, status, and applicable source.\n')
    return path,state

def promote_idea(a,path,state):
    verify_idea_history(state,path)
    if state.get('state')!='ready-for-dossier' or state.get('human_decision')!='PROCEED':
        raise ValueError('Only a human-confirmed PROCEED may create a dossier')
    pending=state.get('pending_human_decision',{})
    if pending.get('recommendation')!='PROCEED':raise ValueError('PROCEED requires an accepted PROCEED recommendation')
    if state.get('promoted_project_id'):raise ValueError('Idea lab already promoted to '+state['promoted_project_id'])
    recommendation=json.loads((path/'stages/phase-zero/decision.json').read_text())
    handoff=recommendation.get('route_handoff')
    if not isinstance(handoff,dict) or handoff.get('current_call_verified') is not True:
        raise ValueError('Accepted recommendation lacks a verified route handoff')
    namespace=argparse.Namespace(name=a.project_name,action=handoff['action'],sector=handoff['sector'],year=handoff['year'],
        max_revisions=a.max_revisions,process='integrated',form_profile=a.form_profile,title=a.title or state['title'],annex=a.annex,
        country=handoff.get('country'),agency=handoff.get('agency'),role=handoff.get('role'),round=handoff.get('round'),
        phase_zero_status='imported-accepted-human-confirmed')
    project_path,project_state=initialize_dossier(namespace)
    target=confined_path(project_path,project_path/'inbox'/'phase-zero-handoff');target.mkdir(parents=True,exist_ok=False)
    packet_manifest_path,packet_manifest=stage_gate.packet(path,pending['packet_id'])
    files=[]
    def copy(source,role):
        source=confined_path(path,source,True);destination=target/f'{len(files):04d}-{source.name}'
        shutil.copyfile(source,destination)
        files.append({'role':role,'path':str(destination.relative_to(project_path)),'sha256':digest(destination),'source_sha256':digest(source)})
    copy(packet_manifest_path,'source-packet-manifest')
    copy(Path(packet_manifest['production_report']),'production-report')
    dispatch_path=confined_path(path,path/'validation'/'dispatches'/f'{pending["packet_id"]}.json',True)
    copy(dispatch_path,'observed-dispatch')
    dispatch_data=json.loads(dispatch_path.read_text())
    copy(path/dispatch_data.get('observation_archive',dispatch_data['observation']),'observed-dispatch-source')
    for entry in packet_manifest['files']:
        copy(path/entry['snapshot'],entry['role'])
    copy(path/pending['validation_report'],'independent-validation-report')
    human=state['human_decisions'][-1]
    copy(path/human['receipt_path'],'human-decision')
    manifest={'schema_version':'phase-zero-handoff-v1','idea_lab_id':state['id'],'accepted_packet_id':pending['packet_id'],
              'accepted_packet_sha256':pending['packet_sha256'],'recommendation':'PROCEED','human_decision':'PROCEED',
              'route':{key:handoff.get(key) for key in ('program','year','action','sector','country','agency','role','round')},
              'files':files,'limitations':['Phase zero is exploratory and does not replace route-specific idea-validation, eligibility or award assessment.']}
    save(target/'manifest.json',manifest)
    project_state['phase_zero']={'idea_lab_id':state['id'],'handoff_manifest':str((target/'manifest.json').relative_to(project_path)),
                                 'handoff_manifest_sha256':digest(target/'manifest.json'),'accepted_packet_id':pending['packet_id'],
                                 'accepted_packet_sha256':pending['packet_sha256'],'human_decision':'PROCEED'}
    save(project_path/'state.json',project_state)
    state['state']='promoted';state['next_phase']='closed';state['promoted_project_id']=project_state['id'];state['promoted_at']=dt.datetime.now(dt.timezone.utc).isoformat()
    save(path/'state.json',state)
    return project_path,project_state

def _main():
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='cmd',required=True)
    q=sub.add_parser('idea-init');q.add_argument('name');q.add_argument('--title');q.add_argument('--year',type=int,default=2026);q.add_argument('--max-revisions',type=int,default=3)
    q=sub.add_parser('idea-status');q.add_argument('name')
    q=sub.add_parser('idea-record');q.add_argument('name');q.add_argument('--report',required=True);q.add_argument('--validation-packet',required=True);q.add_argument('--validation-report',required=True)
    q=sub.add_parser('idea-decide');q.add_argument('name');q.add_argument('--decision-file',required=True)
    q=sub.add_parser('promote-idea');q.add_argument('name');q.add_argument('--project-name',required=True);q.add_argument('--title');q.add_argument('--max-revisions',type=int,default=3);q.add_argument('--form-profile');q.add_argument('--annex',action='append',default=[])
    q=sub.add_parser('init'); q.add_argument('name'); q.add_argument('--action',required=True); q.add_argument('--sector',required=True); q.add_argument('--year',type=int,default=2026); q.add_argument('--max-revisions',type=int,default=3); q.add_argument('--process',choices=['integrated','compact'],default='integrated'); q.add_argument('--form-profile')
    q.add_argument('--title'); q.add_argument('--annex',action='append',default=[])
    for flag in ('country','agency','role','round'):q.add_argument('--'+flag)
    q=sub.add_parser('status'); q.add_argument('name')
    q=sub.add_parser('record'); q.add_argument('name'); q.add_argument('--phase',choices=PHASES,required=True); q.add_argument('--report',required=True); q.add_argument('--validation-packet'); q.add_argument('--validation-report')
    q=sub.add_parser('invalidate'); q.add_argument('name'); q.add_argument('--phase',choices=PHASES,required=True); q.add_argument('--report',required=True)
    q=sub.add_parser('bind-form'); q.add_argument('name'); q.add_argument('--profile',required=True); q.add_argument('--report',required=True)
    q=sub.add_parser('approve'); q.add_argument('name'); q.add_argument('--decision',required=True)
    q=sub.add_parser('reject'); q.add_argument('name'); q.add_argument('--decision',required=True)
    q=sub.add_parser('approval-status'); q.add_argument('name')
    q=sub.add_parser('approval-bundle'); q.add_argument('name')
    a=p.parse_args()
    if a.cmd=='idea-init':
        path,state=initialize_idea(a)
    elif a.cmd.startswith('idea-') or a.cmd=='promote-idea':
        path=idea_lab(a.name);state_path=path/'state.json';state=json.loads(state_path.read_text())
        verify_idea_history(state,path)
        if a.cmd=='idea-status':
            pass
        elif a.cmd=='idea-record':
            if state.get('next_phase')!='phase-zero':raise ValueError('Expected phase '+str(state.get('next_phase')))
            report_path=idea_input(path,a.report);report=json.loads(report_path.read_text())
            if report.get('status') not in ('pass','blocked','needs-revision') or not report.get('summary') or not isinstance(report.get('evidence'),list):
                raise ValueError('Phase zero report requires status, summary and evidence')
            critique=report.get('critical_review')
            if not isinstance(critique,dict) or not all(critique.get(key) for key in ('weaknesses','alternative','decision_basis')):
                raise ValueError('Phase zero report requires a critical review')
            validation=stage_gate.verify(ROOT,path,state,a.validation_packet,idea_input(path,a.validation_report),report_path)
            if report['status']=='pass' and validation['verdict']!='accept':raise ValueError('Independent validator did not accept Phase zero')
            if report['status']!='pass' and validation['verdict'] not in ('revise','blocked'):raise ValueError('Phase zero outcome does not match independent validation')
            decision_path=confined_path(path,path/'stages/phase-zero/decision.json',True);matrix_path=confined_path(path,path/'research/checklist-phase-zero.json',True)
            import checklist
            decision=json.loads(decision_path.read_text());matrix=json.loads(matrix_path.read_text())
            result=checklist.validate_phase_zero_decision(decision,matrix,state,path)
            if not result['valid']:raise ValueError('Phase zero decision invalid: '+json.dumps(result['issues'][:8]))
            if decision['version']<=state.get('last_decision_version',0):raise ValueError('Phase zero decision version must increase')
            state['last_decision_version']=decision['version']
            session={**validation,'phase':'phase-zero'};state['validator_sessions'].append(session)
            idea_archive(state,path,Path(validation['report_path']),'validator-phase-zero',validation['verdict'])
            idea_archive(state,path,report_path,'phase-zero',report['status'])
            if report['status']=='pass':
                state['pending_human_decision']={'packet_id':validation['packet_id'],'packet_sha256':validation['packet_sha256'],
                    'validation_report':str(Path(validation['report_path']).relative_to(path)),'recommendation':decision['recommendation'],'decision_sha256':digest(decision_path)}
                state['state']='awaiting-human-decision';state['next_phase']='human-decision';state['blockers']=[]
            else:
                state['revisions']+=1;state['state']='revision-limit-reached' if state['revisions']>=state['max_revisions'] else 'revision-needed'
                state['next_phase']='phase-zero';state['blockers']=report.get('blockers',[])
            save(state_path,state)
        elif a.cmd=='idea-decide':
            if state.get('state')!='awaiting-human-decision':raise ValueError('No accepted Phase zero package awaits human decision')
            source=idea_input(path,a.decision_file);decision=validate_human_idea_decision(json.loads(source.read_text()),state,path)
            pending=state['pending_human_decision'];choice=decision['decision']
            if choice=='PROCEED' and pending['recommendation']!='PROCEED':
                raise ValueError('Human PROCEED requires a fresh accepted PROCEED recommendation; refine or pivot first')
            idea_archive(state,path,source,'human-phase-zero',choice.lower())
            receipt=state['receipts'][-1];state['human_decisions'].append({'decision':choice,'receipt_path':receipt['path'],'sha256':receipt['sha256'],'at':receipt['at']})
            state['human_decision']=choice
            if choice=='PROCEED':state['state']='ready-for-dossier';state['next_phase']='ready-for-dossier'
            elif choice=='STOP':state['state']='stopped';state['next_phase']='closed'
            else:
                state['revisions']+=1
                for session in state['validator_sessions']:
                    if session['packet_id']==pending['packet_id']:
                        session['superseded']=True;session['superseded_reason']='human-'+choice.lower()+'-iteration'
                state.pop('pending_human_decision',None);state['next_phase']='phase-zero'
                state['state']='revision-limit-reached' if state['revisions']>=state['max_revisions'] else choice.lower()
            save(state_path,state)
        else:
            path,state=promote_idea(a,path,state)
    elif a.cmd=='init':
        path,state=initialize_dossier(a)
    else:
        path=project(a.name);state_path=path/'state.json'
        state=json.loads(state_path.read_text())
        phases=INTEGRATED if state.get('process')=='integrated' else COMPACT
        target=a.phase if a.cmd=='invalidate' else 'answer-outlines' if state.get('process')=='integrated' else 'draft'
        relax=phases[phases.index(target):] if a.cmd in ('invalidate','bind-form') and target in phases else []
        if a.cmd in ('approve','reject','approval-status','approval-bundle'):
            verify_receipts(state,path,tuple(relax)+stage_gate.history_relax(state))
            if a.cmd=='approval-bundle': result=human_approval.bundle(ROOT,path,state)
            elif a.cmd=='approval-status': result=human_approval.status(ROOT,path,state)
            else:
                result=human_approval.decide(ROOT,path,state,project_input(ROOT,path,a.decision),a.cmd)
                save(state_path,state)
            print(json.dumps(result,ensure_ascii=False,indent=2)); return
        if a.cmd=='status':
            approval=human_approval.status(ROOT,path,state)
            if approval['status']=='stale':
                human_approval.supersede(state,'bound-bundle-changed')
                save(state_path,state)
        verify_receipts(state,path,tuple(relax)+stage_gate.history_relax(state))
        if a.cmd in ('record','invalidate','bind-form'):
            report_path=project_input(ROOT,path,a.report)
            r=json.loads(report_path.read_text())
            localized_evidence(r,path)
            integrated=state.get('process')=='integrated'
            phases=INTEGRATED if integrated else COMPACT
            if a.cmd!='bind-form' and a.phase not in phases: raise ValueError('Phase does not belong to this process')
            if integrated:
                critique=r.get('critical_review')
                if not isinstance(critique,dict) or not all(critique.get(k) for k in ('weaknesses','alternative','decision_basis')):
                    raise ValueError('Each integrated phase needs critical_review: weaknesses, alternative, decision_basis')
            human_approval.supersede(state,'workflow-'+a.cmd)
            if a.cmd=='bind-form':
                state['form_profile']=localized_profile(a.profile,state)
                production=phases[:phases.index('review')]
                target='answer-outlines' if integrated else 'draft'
                if state['next_phase'] not in production or production.index(state['next_phase'])>=production.index(target):
                    state['next_phase']=target; state['state']='form-changed'; state.pop('bundle_snapshot',None); state.pop('draft_sha256',None); state.pop('form_profile_sha256',None)
                    for s in state.get('validator_sessions',[]):
                        _,m=stage_gate.packet(path,s['packet_id'])
                        if m['phase'] in relax:s['superseded']=True
                archive_receipt(state,path,report_path,'bind-form','bound'); save(state_path,state)
                print(json.dumps(state,ensure_ascii=False,indent=2)); return
            if a.cmd=='invalidate':
                if a.phase in ('repair','qa','review'): raise ValueError('Invalidate to the earliest affected production phase')
                if not r.get('reason'): raise ValueError('Invalidation report needs a reason')
                production=phases[:phases.index('review')]
                accepted={receipt['phase'] for receipt in state.get('receipts',[]) if receipt.get('status')=='pass'}
                active={stage_gate.packet(path,s['packet_id'])[1]['phase'] for s in state.get('validator_sessions',[]) if s.get('verdict')=='accept' and not s.get('superseded')} if state.get('validation_protocol')=='fresh-step-v1' else accepted
                target_index=production.index(a.phase)
                if a.phase not in accepted or any(prerequisite not in active for prerequisite in production[:target_index]):
                    raise ValueError('Invalidation requires an already reached phase and all accepted active prerequisites')
                state['next_phase']=a.phase; state['state']='invalidated'; state['blockers']=r.get('blockers',[])
                state.pop('bundle_snapshot',None); state.pop('draft_sha256',None)
                state.pop('form_profile_sha256',None)
                for s in state.get('validator_sessions',[]):
                    _,m=stage_gate.packet(path,s['packet_id'])
                    if m['phase'] in relax:s['superseded']=True
                archive_receipt(state,path,report_path,'invalidate-'+a.phase,'invalidated'); save(state_path,state)
                print(json.dumps(state,ensure_ascii=False,indent=2)); return
            if r.get('status') not in ('pass','blocked','needs-revision'): raise ValueError('Report status: pass, blocked or needs-revision')
            if a.phase!=state['next_phase']: raise ValueError('Expected phase '+state['next_phase'])
            blockers=r.get('blockers',[])
            if blockers and r['status']=='pass': raise ValueError('A phase cannot pass with blockers')
            validation=None
            if state.get('validation_protocol')=='fresh-step-v1':
                if not a.validation_packet or not a.validation_report: raise ValueError('Each completed step requires a fresh independent validation packet and report')
                validation=stage_gate.verify(ROOT,path,state,a.validation_packet,a.validation_report,report_path)
                if r['status']=='pass' and validation['verdict']!='accept': raise ValueError('Independent validator did not accept this step')
                if r['status']=='needs-revision' and validation['verdict'] not in ('revise','blocked'): raise ValueError('Revision outcome does not match independent validation')
                if r['status']=='blocked' and validation['verdict'] not in ('revise','blocked'): raise ValueError('Blocked outcome does not match independent validation')
            if integrated and a.phase in ('answer-outlines','application-draft') and r['status']=='pass':
                if not state.get('form_profile'): raise ValueError('Select a form profile before preparing field answers')
                if a.phase=='application-draft':
                    answers=json.loads((path/'answers.json').read_text())
                    if not answers.get('answers'): raise ValueError('Missing plain-text field answers')
                    check=check_answers(answers,json.loads((ROOT/state['form_profile']).read_text()))
                    if not check['passed']: raise ValueError('Draft character checks failed: '+json.dumps(check['issues'][:12]))
            if a.phase in ('draft','application-draft','repair','annexes') and r['status']=='pass':
                if not (path/'draft.md').exists(): raise ValueError('Missing draft.md')
                if a.phase=='annexes' and digest(path/'draft.md')!=state.get('draft_sha256'): raise ValueError('Draft changed while generating annexes; integrate through repair or invalidate')
                if a.phase=='annexes' and state.get('form_profile') and digest(ROOT/state['form_profile'])!=state.get('form_profile_sha256'): raise ValueError('Form profile changed while generating annexes')
                state['draft_sha256']=digest(path/'draft.md')
                if integrated and state.get('form_profile'): state['form_profile_sha256']=digest(ROOT/state['form_profile'])
                if integrated and a.phase in ('annexes','repair'): state['bundle_snapshot']=freeze_bundle(path)
            if a.phase in ('review','qa'):
                if not (path/'draft.md').exists(): raise ValueError('Missing draft.md')
                if r.get('draft_sha256')!=digest(path/'draft.md'): raise ValueError('Report does not match the current frozen draft')
                if r.get('draft_sha256')!=state.get('draft_sha256'): raise ValueError('Draft changed since the prior phase freeze')
                if integrated and freeze_bundle(path)!=state.get('bundle_snapshot'): raise ValueError('Project data or annex changed since the bundle freeze')
                if integrated and state.get('form_profile') and digest(ROOT/state['form_profile'])!=state.get('form_profile_sha256'): raise ValueError('Form profile changed since the freeze')
            if a.phase=='qa' and r['status']=='pass':
                findings=json.loads((path/'findings.json').read_text())
                if not isinstance(findings,list) or any(not isinstance(f,dict) or f.get('severity') not in ('blocking','major','minor','editorial') or f.get('status') not in ('open','corrected','verified','unresolved') for f in findings): raise ValueError('Invalid finding severity or status')
                if any(f.get('severity') in ('blocking','major') and f.get('status')!='verified' for f in findings): raise ValueError('Unverified blocking/major findings remain')
                if integrated: readiness(path,state)
            if a.phase=='repair' and state['revisions']>=state['max_revisions']: raise ValueError('Revision limit reached; deliver draft and unresolved issues')
            production=phases[:phases.index('review')]+['review']
            next_phase=({'review':'qa','repair':'review','qa':'ready-for-human-review'}[a.phase] if a.phase in ('review','repair','qa') else production[production.index(a.phase)+1])
            if r['status']=='blocked': next_phase=a.phase; state['state']='blocked'
            elif r['status']=='needs-revision':
                next_phase='repair' if a.phase in ('review','qa') else a.phase; state['state']='revision-needed'
            else: state['state']=next_phase
            if a.phase=='repair' and r['status']=='pass':
                state['revisions']+=1
                for previous in state.get('validator_sessions',[]):
                    _,previous_packet=stage_gate.packet(path,previous['packet_id'])
                    if previous_packet['phase'] in stage_gate.history_relax({'next_phase':'repair'}):
                        previous['superseded']=True
                        previous['superseded_reason']='accepted-repair'
                        if validation:previous['superseded_by_packet']=validation['packet_id']
            if next_phase=='repair' and state['revisions']>=state['max_revisions']: state['state']='revision-limit-reached'
            state['next_phase']=next_phase; state['blockers']=blockers
            if validation:
                state['validator_sessions'].append(validation)
                archive_receipt(state,path,Path(validation['report_path']),'validator-'+a.phase,validation['verdict'])
            archive_receipt(state,path,report_path,a.phase,r['status'])
            if integrated and a.phase=='qa' and r['status']=='pass':
                state['human_review_bundle']=human_approval.bundle(ROOT,path,state)
            save(state_path,state)
    output={**state,'working_memory_context':opening_context(ROOT,path.name,state.get('next_phase'))} if a.cmd in ('status','init') else state
    print(json.dumps(output,ensure_ascii=False,indent=2))

def main():
    # Lock before loading state and retain it through packet verification and save.
    if any(flag in sys.argv[1:] for flag in ('-h','--help')):return _main()
    idea_commands=('idea-init','idea-status','idea-record','idea-decide','promote-idea')
    if len(sys.argv)>2 and sys.argv[1] in ('init','status','record','invalidate','bind-form','approve','reject','approval-status','approval-bundle')+idea_commands:
        # Creation uses an existing engine directory: invalid init must not create projects.
        if sys.argv[1] in ('init','idea-init'):lock_path=ROOT
        elif sys.argv[1] in idea_commands:lock_path=idea_lab(sys.argv[2])
        else:lock_path=project(sys.argv[2])
        with project_lock(lock_path):return _main()
    return _main()

if __name__=='__main__':
    try: main()
    except (ValueError,OSError,KeyError) as e: print(str(e),file=sys.stderr); sys.exit(1)
