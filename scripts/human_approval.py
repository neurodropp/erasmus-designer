"""Exact-bundle observed human decisions; no identity authentication or submission."""
import datetime as dt
import hashlib
import json
from pathlib import Path
from project_paths import confined_path
from project_lock import project_lock, state_cas

LIMIT = 'Localized coordinator observation; not host-authenticated human identity, consent signature or submission authorization'

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def canonical(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def read(path):return json.loads(Path(path).read_text())
def inside(path,value):return confined_path(path,value,True)

def bundle(root,path,state):
    import stage_gate
    if state.get('next_phase') not in ('ready-for-human-review','human-approved','human-rejected'):
        raise ValueError('Human decision requires completed QA')
    stage_gate.verify_history(path,state)
    sessions=[]
    for session in state.get('validator_sessions',[]):
        if session.get('verdict')!='accept' or session.get('superseded'):continue
        mp,m=stage_gate.packet(path,session['packet_id'])
        if m['phase']=='qa':sessions.append((session,mp,m))
    if len(sessions)!=1:raise ValueError('Exactly one active accepted QA bundle required')
    session,mp,m=sessions[0]
    if not state.get('form_profile'):raise ValueError('Current form profile required for human approval')
    roles={'project-input','annex','form-profile','form-source'}
    artifacts={}
    for entry in m['files']:
        if entry['role'] not in roles:continue
        original=stage_gate.original_file(root,path,entry)
        if digest(original)!=entry['sha256']:raise ValueError('QA bundle artifact changed; approval is stale')
        key=str(original.relative_to(Path(root).resolve()))
        artifacts[key]=entry['sha256']
    required={str((path/name).resolve().relative_to(Path(root).resolve())) for name in ('project.json','answers.json','draft.md','evidence.json','annex-manifest.json')}
    required.add(str(inside(root,state['form_profile']).relative_to(Path(root).resolve())))
    if not required.issubset(artifacts):raise ValueError('QA manifest misses required bundle artifacts')
    # Exact annex membership is taken from the bound manifest, never directory globs.
    manifest=read(path/'annex-manifest.json')
    for row in manifest.get('annexes',[]):
        if row.get('status')=='not-applicable':continue
        annex=inside(path,row.get('path',''))
        if str(annex.relative_to(Path(root).resolve())) not in artifacts:raise ValueError('Annex outside accepted QA artifact manifest')
    answers=read(path/'answers.json')
    form_source=answers.get('form_instance',{}).get('form_source',{})
    if not isinstance(form_source,dict) or not form_source.get('path') or not form_source.get('sha256'):
        raise ValueError('Original form artifact path/hash required for human approval')
    from project_paths import project_input
    original_form=project_input(root,path,form_source['path'])
    if digest(original_form)!=form_source['sha256'] or artifacts.get(str(original_form.relative_to(Path(root).resolve())))!=form_source['sha256']:
        raise ValueError('Original form artifact missing or changed outside accepted QA manifest')
    route={k:state.get(k) for k in ('program','year','action','sector')}
    project=read(path/'project.json').get('project',{})
    route.update({k:project.get(k,state.get(k)) for k in ('country','agency','role','round')})
    if any(m.get('route',{}).get(k)!=route.get(k) for k in route):
        raise ValueError('QA route and current dossier context do not match')
    value={'schema_version':'human-review-bundle-v1','project_id':state.get('id',path.name),
           'route':route,
           'qa_packet_id':session['packet_id'],'qa_packet_sha256':digest(mp),
           'qa_report_sha256':session['report_sha256'],'qa_dispatch_sha256':session['dispatch_sha256'],
           'artifacts':dict(sorted(artifacts.items())),
           'form_instance_sha256':canonical(answers.get('form_instance',{})),
           'scope':'approve-exact-bundle-for-handoff','rights':['handoff'],'submission_authorized':False,
           'verification_limit':LIMIT}
    value['bundle_sha256']=canonical(value)
    return value

def verify_history(path,state):
    for item in state.get('human_decisions',[]):
        archive=inside(path,item['path'])
        if digest(archive)!=item['sha256']:raise ValueError('Human decision archive changed')
        receipt=read(archive)
        evidence=inside(path,receipt['observation_archive'])
        if digest(evidence)!=receipt['observation_sha256']:raise ValueError('Human decision observation archive changed')
        if canonical({k:v for k,v in receipt['bundle'].items() if k!='bundle_sha256'})!=receipt['bundle']['bundle_sha256']:
            raise ValueError('Human decision bound bundle hash mismatch')

def status(root,path,state):
    verify_history(path,state)
    active=[d for d in state.get('human_decisions',[]) if not d.get('superseded')]
    if not active:return {'status':'none','verification_limit':LIMIT,'submission_authorized':False}
    if len(active)!=1:raise ValueError('Ambiguous active human decisions')
    receipt=read(inside(path,active[0]['path']))
    try:current=bundle(root,path,state)
    except (ValueError,OSError,KeyError):return {'status':'stale','verification_limit':LIMIT,'submission_authorized':False}
    return {'status':receipt['decision'] if current==receipt['bundle'] else 'stale',
            'bundle_sha256':receipt['bundle']['bundle_sha256'],'verification_limit':LIMIT,'submission_authorized':False}

def supersede(state,reason):
    state.pop('human_review_bundle',None)
    for item in state.get('human_decisions',[]):
        if not item.get('superseded'):item.update(superseded=True,superseded_reason=reason)
    if state.get('state') in ('human-approved','human-rejected'):
        state['state']='human-approval-stale'
        state['next_phase']='ready-for-human-review'

def decide(root,path,state,decision_path,decision):
    with project_lock(path):
        state_cas(path,state)
        verify_history(path,state)
        current=bundle(root,path,state)
        record=read(inside(path,decision_path))
        if record.get('schema_version')!='observed-human-decision-v1' or record.get('decision')!=decision:
            raise ValueError('Decision schema or command mismatch')
        if record.get('project_id')!=current['project_id'] or record.get('bundle_sha256')!=current['bundle_sha256']:
            raise ValueError('Decision belongs to a different project or bundle hash')
        if record.get('scope')!='approve-exact-bundle-for-handoff' or record.get('rights')!=['handoff']:
            raise ValueError('Decision scope/rights do not authorize this exact handoff bundle')
        if record.get('artifacts')!=current['artifacts']:raise ValueError('Decision artifact manifest must exactly match QA bundle')
        provenance=record.get('provenance',{})
        if provenance.get('type')!='user-instruction' or not all(isinstance(provenance.get(k),str) and provenance[k].strip() for k in ('reference','observed_by')):
            raise ValueError('Decision needs observed user-instruction provenance')
        if not isinstance(record.get('author'),str) or not record['author'].strip():raise ValueError('Observed decision author required')
        evidence=record.get('evidence',{})
        if not isinstance(evidence,dict) or not evidence.get('locator') or not isinstance(evidence.get('quote'),str) or not evidence['quote'].strip():
            raise ValueError('Decision requires authorized exact quote and localized source')
        source=inside(path,evidence.get('path',''))
        raw=source.read_bytes()
        if source==Path(decision_path).resolve() or evidence.get('sha256')!=hashlib.sha256(raw).hexdigest():raise ValueError('Decision evidence source hash mismatch or self-reference')
        if evidence['quote'] not in raw.decode('utf-8'):raise ValueError('Decision quote missing from observed source')
        if evidence.get('provenance')!='user-instruction' or evidence.get('quote_authorized') is not True:
            raise ValueError('Decision source must be an authorized observation of user instruction')
        number=len(state.get('human_decisions',[]))+1
        folder=confined_path(path,'approval');folder.mkdir(exist_ok=True)
        observation=folder/f'{number:04d}-observation.txt'
        receipt_path=folder/f'{number:04d}-{decision}.json'
        receipt={'schema_version':'human-decision-receipt-v1','decision':decision,'author':record['author'],
                 'provenance':provenance,'evidence':evidence,'bundle':current,
                 'observation_archive':str(observation.relative_to(path)),
                 'observation_sha256':hashlib.sha256(raw).hexdigest(),'decision_source_sha256':digest(decision_path),
                 'observed_at':dt.datetime.now(dt.timezone.utc).isoformat(),'verification_limit':LIMIT}
        with observation.open('xb') as output:output.write(raw)
        with receipt_path.open('x') as output:json.dump(receipt,output,ensure_ascii=False,indent=2);output.write('\n')
        supersede(state,'later-observed-human-decision')
        state.setdefault('human_decisions',[]).append({'path':str(receipt_path.relative_to(path)),'sha256':digest(receipt_path),'decision':decision})
        state['state']='human-approved' if decision=='approve' else 'human-rejected'
        state['next_phase']=state['state']
        return receipt
