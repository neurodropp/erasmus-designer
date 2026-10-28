#!/usr/bin/env python3
"""Read-only consistency check of engine, layout, discovery and local contracts.

Not an exhaustive normative audit, provider certification or relocation tool.
"""
import argparse
import json
from pathlib import Path
import re
import tomllib
from project_paths import resolve_project

ROOT=Path(__file__).resolve().parents[1]

def check(root=ROOT):
    issues=[];counts={}
    def flag(code,path,detail):issues.append({'code':code,'file':str(path.relative_to(root)),'detail':detail})
    for relative in ['projects/README.md','docs/project-creation.md','docs/architecture.md','docs/phase-zero-idea-lab.md','docs/replication.md','docs/form-intake.md','docs/checklist-workflow.md','docs/action-modes.md','docs/release-bundles.md','docs/relocation.md','docs/repairs-0.2.1.md','docs/orchestration-repairs-0.2.1.md','docs/knowledge-repairs-0.2.1.md','docs/model-form-repairs-0.2.1.md','docs/portability-repairs-0.2.1.md','wiki/templates/phase-zero-decision-contract.md','config/phase-zero.json','config/project-layout.json','config/project-model.schema.json','config/replication-requirements.json','config/action-modes.json','config/engine-version.json','requirements-import.txt','requirements-import.lock.txt']:
        if not (root/relative).is_file():flag('missing-contract',root/relative,'Required engine/layout contract absent')
    phase_zero=json.loads((root/'config/phase-zero.json').read_text())
    expected_axes={'route_call_fit','priority_contribution','primary_target_fit','secondary_target_fit','need_evidence','causal_chain','scale_budget_fit','capability_partner_fit','european_added_value'}
    if phase_zero.get('schema_version')!='phase-zero-policy-v1' or set(phase_zero.get('mandatory_axes',{}))!=expected_axes:
        flag('phase-zero-contract',root/'config/phase-zero.json','Expected Phase zero v1 and all nine mandatory axes')
    if phase_zero.get('workspace')!='work/idea-lab/<slug>--<year>/' or phase_zero.get('next_project_phase')!='idea-validation':
        flag('phase-zero-routing',root/'config/phase-zero.json','Idea Lab must remain outside projects and promote to idea-validation')
    if phase_zero.get('route_identity_fields')!=['program','year','action','sector','country','agency','role','round']:
        flag('phase-zero-route-identity',root/'config/phase-zero.json','Expected one canonical route identity from candidate through human choice and promotion')
    routes=json.loads((root/'config/actions.json').read_text());route_ids={r['code'] for r in routes}
    matrix=json.loads((root/'config/action-modes.json').read_text())
    if len(matrix['routes'])!=len(routes) or {r['action'] for r in matrix['routes']}!=route_ids:flag('action-mode-coverage',root/'config/action-modes.json','Expected one mode per exact route')
    registry=json.loads((root/'config/agent-registry.json').read_text());annexes=json.loads((root/'config/annexes.json').read_text())
    annex_ids={r['id'] for r in annexes};layout=json.loads((root/'config/project-layout.json').read_text())
    if layout['root']!='projects':flag('layout-root',root/'config/project-layout.json','Resolver supports projects root')
    for action in set(layout['action_tags'])|set(layout['annex_workspaces']):
        if action not in route_ids:flag('layout-unknown-route',root/'config/project-layout.json',action)
    for key,values in {**layout['annex_workspaces'],**layout.get('annex_family_workspaces',{})}.items():
        for ident in values:
            if ident not in annex_ids:flag('layout-unknown-annex',root/'config/project-layout.json',key+': '+ident)
    for folder in layout['base_directories']:
        if Path(folder).is_absolute() or '..' in Path(folder).parts:flag('layout-path-escape',root/'config/project-layout.json',folder)
    counts.update(routes=len(routes),annex_owners=len(annexes),skills=len(list((root/'skills').glob('*/SKILL.md'))),native_definitions=len(list((root/'.codex/agents').glob('*.toml'))))
    roles={r['name']:r for r in registry}
    native={}
    for path in (root/'.codex/agents').glob('*.toml'):
        data=tomllib.loads(path.read_text());native[data.get('name')]=data
    if set(native)!=set(roles):flag('agent-registry-mismatch',root/'config/agent-registry.json','Native names differ from maintained registry')
    for role in registry:
        if not (root/'skills'/role['skill']/'SKILL.md').is_file():flag('agent-skill-missing',root/'config/agent-registry.json',role['name'])
    for annex in annexes:
        if annex['agent_name'] not in roles or roles[annex['agent_name']]['skill']!=annex['skill']:flag('annex-owner-mismatch',root/'config/annexes.json',annex['id'])
    config=tomllib.loads((root/'.codex/config.toml').read_text())
    if config.get('agents',{}).get('max_concurrent_threads_per_session')!=3:flag('concurrency-count',root/'.codex/config.toml','Expected 3 children plus primary')
    if config['mcp_servers']['erasmus_wiki']['command']!=str(root/'scripts/lwc'):flag('mcp-root-mismatch',root/'.codex/config.toml','Regenerate native surfaces for this root')
    discovery=root/'.agents/skills'
    if not discovery.exists() or discovery.resolve()!=(root/'skills').resolve():flag('skill-discovery',discovery,'Expected project-local skills discovery')
    docs=[root/'AGENTS.md',root/'README.md',root/'projects/README.md']
    docs += [root/'docs'/name for name in ['architecture.md','project-creation.md','phase-zero-idea-lab.md','replication.md','orchestrator-protocol.md','multiagent-loop.md','action-modes.md','form-intake.md','checklist-workflow.md','release-bundles.md','relocation.md']]
    docs += list((root/'skills').rglob('*.md'))
    docs += [root/'wiki/templates/project-memory-contract.md',root/'wiki/templates/phase-zero-decision-contract.md',root/'wiki/templates/response-contract.md',root/'wiki/topics/orchestrator-architecture.md']
    for path in docs:
        body=re.sub(r'```.*?```','',path.read_text(),flags=re.S)
        for href in re.findall(r'\[[^\]\n]+\]\(([^\n)]+)\)',body):
            href=href.strip().strip('<>');href=href.split('#')[0]
            if not href or re.match(r'[a-zA-Z][a-zA-Z0-9+.-]*:',href):continue
            href=re.sub(r':\d+$','',href)
            if Path(href).suffix not in ('.md','.json','.py','.toml','.txt'):continue
            target=Path(href) if Path(href).is_absolute() else path.parent/href
            if not target.is_file():flag('broken-local-contract-link',path,href)
    dossiers=list((root/'projects').glob('*/state.json'));counts['project_dossiers']=len(dossiers)
    for p in dossiers:
        state=json.loads(p.read_text())
        if state.get('id') and state['id']!=p.parent.name:flag('project-folder-id-mismatch',p,'Folder renamed or identity changed')
        try:resolve_project(root,p.parent.name)
        except ValueError as e:flag('project-path',p,str(e))
    counts['legacy_dossiers']=len(list((root/'wiki/projects').glob('*/state.json')))
    counts['idea_labs']=len(list((root/'work/idea-lab').glob('*/state.json')))
    return {'scope':'local-structure-and-contracts','passed':not issues,'counts':counts,'issues':issues,'limits':['Not a normative completeness audit','No destination-PC transfer test','No automatic relocation of frozen receipts','Fresh validator still required for completed phases']}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output');args=parser.parse_args()
    result=check()
    if args.output:
        path=(ROOT/args.output).resolve()
        if not path.is_relative_to(ROOT):raise ValueError('Output outside engine')
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
