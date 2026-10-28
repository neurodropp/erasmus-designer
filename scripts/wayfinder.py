#!/usr/bin/env python3
"""Local decision map for a dossier; not a task runner or an approval gate."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import sys
import tempfile

from project_paths import resolve_project, confined_path, preflight_dossier
from project_lock import project_lock
from project_memory import ProjectMemory

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'project-wayfinder-v1'

def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def atomic(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as out:
        temp = Path(out.name); out.write(encoded(value))
    try:
        temp.replace(path)
    finally:
        if temp.exists(): temp.unlink()

def nonempty(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(field + ' must be a nonempty string')
    return value

def graph(decisions):
    visiting, done = set(), set()
    def visit(ident):
        if ident in visiting: raise ValueError('Decision dependency cycle')
        if ident in done: return
        if ident not in decisions: raise ValueError('Unknown decision dependency: ' + ident)
        visiting.add(ident)
        for dependency in decisions[ident]['dependencies']: visit(dependency)
        visiting.remove(ident); done.add(ident)
    for ident in decisions: visit(ident)

def load(path):
    base = confined_path(path, 'wayfinder')
    if not base.is_dir(): raise ValueError('Initialize the dossier decision map first')
    head = json.loads(confined_path(base, 'head.json', True).read_text())
    pointer, revision, latest = head, head['revision'], None
    while pointer:
        artifact = confined_path(base, pointer['file'], True)
        if sha(artifact) != pointer['sha256']: raise ValueError('Decision history hash mismatch')
        event = json.loads(artifact.read_text())
        if event['schema'] != SCHEMA or event['revision'] != revision:
            raise ValueError('Decision history revision mismatch')
        state = event['state']
        if state['project_id'] != path.name: raise ValueError('Decision history belongs to another dossier')
        graph(state['decisions'])
        if latest is None: latest = state
        pointer = event['previous']; revision -= 1
    if revision != -1: raise ValueError('Incomplete decision history')
    return latest, head

def context(path, root=None):
    state, head = load(path); decisions = state['decisions']
    root = Path(root) if root else path.parents[1]
    route = json.loads((path / 'state.json').read_text())
    if any(state['route'][k] != route.get(k) for k in ('program', 'action', 'sector', 'year')):
        raise ValueError('Decision map route changed; explicit migration required')
    ready, human, blocked, claimed = [], [], [], []
    valid_resolved, invalid = set(), {}
    for row in decisions.values():
        if row['status'] != 'resolved': continue
        try:
            for item in row['evidence']:
                artifact = confined_path(path, item['path'], True)
                if sha(artifact) != item['sha256']: raise ValueError('Decision evidence changed')
            resolve_memory(root, path, row, row)
            valid_resolved.add(row['id'])
        except (ValueError, OSError, KeyError) as error:
            invalid[row['id']] = str(error)
    while True:
        stale = {i for i in valid_resolved if any(d not in valid_resolved for d in decisions[i]['dependencies'])}
        if not stale: break
        for ident in stale: invalid[ident] = 'Resolved decision depends on an invalid premise'
        valid_resolved.difference_update(stale)
    for row in decisions.values():
        if row['status'] == 'resolved':
            if row['id'] in invalid:
                blocked.append({'id': row['id'], 'dependencies': [], 'reason': invalid[row['id']]})
            continue
        if row['status'] == 'cancelled': continue
        unmet = [d for d in row['dependencies'] if d not in valid_resolved]
        if unmet or row['status'] == 'blocked':
            blocked.append({'id': row['id'], 'dependencies': unmet, 'reason': row.get('blocker')})
        elif row['status'] == 'claimed': claimed.append(row)
        elif row['kind'] == 'human-decision': human.append(row)
        else: ready.append(row)
    return {'schema': SCHEMA, 'project_id': state['project_id'], 'destination': state['destination'],
            'revision': head['revision'], 'head_sha256': head['sha256'],
            'research_frontier': ready, 'human_frontier': human, 'claimed': claimed,
            'blocked': blocked, 'invalid_resolutions': invalid,
            'authority': 'planning-only-not-model-or-gate-approval'}

def render(path, state=None):
    state = state or load(path)[0]
    lines = ['# Decision Map', '', 'Destination: ' + state['destination'], '',
             'This view can be rebuilt. The map does not change shared data or gates.', '',
             '| ID | Type | Status | Assignee | Dependencies | Question |',
             '|---|---|---|---|---|---|']
    def cell(x): return str(x or '').replace('|', '/').replace('\n', ' ')
    for row in state['decisions'].values():
        lines.append('| ' + ' | '.join(cell(x) for x in (row['id'], row['kind'], row['status'],
                     row['assignee'], ', '.join(row['dependencies']), row['question'])) + ' |')
    atomic(confined_path(path, 'wayfinder/map.json'), state)
    destination = confined_path(path, 'wayfinder/map.md')
    destination.write_text('\n'.join(lines) + '\n')

def commit(path, state, previous, author, reason):
    base = confined_path(path, 'wayfinder'); base.mkdir(exist_ok=True)
    revision = previous['revision'] + 1 if previous else 0
    event = {'schema': SCHEMA, 'revision': revision,
             'previous': {k: previous[k] for k in ('file', 'sha256')} if previous else None,
             'at': dt.datetime.now(dt.timezone.utc).isoformat(), 'author': nonempty(author, 'author'),
             'reason': nonempty(reason, 'reason'), 'state': state}
    content = encoded(event); digest = hashlib.sha256(content.encode()).hexdigest()
    relative = f'history/{revision:06d}-{digest[:16]}.json'
    target = confined_path(base, relative); target.parent.mkdir(exist_ok=True)
    with target.open('x') as out: out.write(content)
    atomic(confined_path(base, 'head.json'), {'revision': revision, 'file': relative, 'sha256': digest})
    render(path, state)

def initialize(path, state, root=None):
    path = Path(path); preflight_dossier(path)
    root = Path(root) if root else path.parents[1]
    with project_lock(path):
        if confined_path(path, 'wayfinder/head.json').exists():
            return context(path, root)
        if state.get('id') != path.name: raise ValueError('Dossier identity required for decision map')
        model = {'schema': SCHEMA, 'project_id': state['id'],
                 'route': {k: state.get(k) for k in ('program', 'action', 'sector', 'year')},
                 'destination': 'To be defined from the brief and actual decisions', 'decisions': {}}
        commit(path, model, None, 'workflow initialization', 'Empty planning map; no confirmed project decisions')
        return context(path, root)

def evidence(path, entries):
    if not isinstance(entries, list) or not entries: raise ValueError('Decision evidence is required')
    result = []
    for row in entries:
        item = confined_path(path, nonempty(row.get('path'), 'evidence.path'), True)
        if not item.is_file(): raise ValueError('Decision evidence must be a file')
        result.append({'path': str(item.relative_to(path)), 'locator': nonempty(row.get('locator'), 'locator'),
                       'sha256': sha(item)})
    return result

def resolve_memory(root, path, ticket, payload):
    ids = payload.get('memory_ids')
    if not isinstance(ids, list) or not ids or any(not isinstance(i, str) for i in ids):
        raise ValueError('Resolution requires real confirmed memory IDs from this dossier')
    memory = ProjectMemory(root, path.name)
    active = {r['id']: r for r in memory.context()['confirmed_active']}
    for ident in ids:
        if ident not in active: raise ValueError('Missing, superseded or unconfirmed decision memory')
        row = active[ident]
        if row['kind'] != 'decision': raise ValueError('Resolution memory must contain a decision')
        if 'wayfinder:' + ticket['id'] not in row['tags']:
            raise ValueError('Memory decision must explicitly reference this ticket ID in tags')
        choice = payload.get('resolution')
        if not isinstance(choice, str) or choice not in row['summary']:
            raise ValueError('Resolution text must match the confirmed memory decision summary')
        if ticket['kind'] == 'human-decision' and row['provenance']['type'] != 'user-instruction':
            raise ValueError('Human choice requires an observed user decision, not agent agreement')
    return ids

def change(root, path, operation, payload):
    with project_lock(path):
        state, head = load(path)
        author = nonempty(payload.get('author'), 'author')
        reason = nonempty(payload.get('reason'), 'reason')
        if operation == 'destination':
            state['destination'] = nonempty(payload.get('destination'), 'destination')
        elif operation == 'add':
            ident = f'D-{len(state["decisions"])+1:04d}'
            kind = payload.get('kind')
            if kind not in ('research', 'human-decision'): raise ValueError('Unknown decision kind')
            dependencies = payload.get('dependencies', [])
            if not isinstance(dependencies, list) or len(set(dependencies)) != len(dependencies):
                raise ValueError('Decision dependencies must be a unique list')
            state['decisions'][ident] = {'id': ident, 'title': nonempty(payload.get('title'), 'title'),
                'question': nonempty(payload.get('question'), 'question'), 'kind': kind, 'status': 'open',
                'assignee': None, 'dependencies': dependencies, 'evidence': [], 'memory_ids': [], 'resolution': None}
            graph(state['decisions'])
        else:
            ticket = state['decisions'].get(payload.get('id'))
            if not ticket: raise ValueError('Unknown decision ID')
            current = context(path, root)
            valid_resolved = {i for i, row in state['decisions'].items()
                              if row['status'] == 'resolved' and i not in current['invalid_resolutions']}
            if operation == 'claim':
                if ticket['status'] != 'open' or any(d not in valid_resolved for d in ticket['dependencies']):
                    raise ValueError('Only open research with satisfied dependencies can be claimed')
                if ticket['kind'] != 'research': raise ValueError('Human choices are not autonomous research assignments')
                ticket.update(status='claimed', assignee=nonempty(payload.get('assignee'), 'assignee'))
            elif operation == 'resolve':
                if ticket['status'] not in ('open', 'claimed', 'blocked'): raise ValueError('Decision is not active')
                if any(d not in valid_resolved for d in ticket['dependencies']):
                    raise ValueError('Unresolved dependency cannot be bypassed')
                memory_ids = resolve_memory(root, path, ticket, payload)
                proofs = evidence(path, payload.get('evidence'))
                if ticket['kind'] == 'research' and ticket['status'] == 'claimed' and ticket['assignee'] != author:
                    raise ValueError('Claimed research can only be resolved by its owner')
                ticket.update(status='resolved', memory_ids=memory_ids, evidence=proofs,
                              resolution=nonempty(payload.get('resolution'), 'resolution'), blocker=None)
            elif operation == 'block':
                if ticket['status'] in ('resolved', 'cancelled'): raise ValueError('Reopen terminal decision before blocking')
                ticket.update(status='blocked', blocker=nonempty(payload.get('blocker'), 'blocker'))
            elif operation == 'reopen':
                # Changing a premise reopens downstream decisions; history retains every prior choice.
                affected = {ticket['id']}
                while True:
                    more = {i for i, row in state['decisions'].items() if any(d in affected for d in row['dependencies'])}
                    if more.issubset(affected): break
                    affected.update(more)
                for ident in affected:
                    state['decisions'][ident].update(status='open', assignee=None, resolution=None, memory_ids=[], evidence=[], blocker=None)
            elif operation == 'cancel':
                ticket.update(status='cancelled', assignee=None)
            else: raise ValueError('Unknown decision operation')
        graph(state['decisions'])
        commit(path, state, head, author, reason)
        return context(path, root)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('command', choices=('init', 'context', 'check', 'render', 'destination', 'add', 'claim', 'resolve', 'block', 'reopen', 'cancel'))
    parser.add_argument('project'); parser.add_argument('--file')
    args = parser.parse_args(); root = args.root.resolve(); path = resolve_project(root, args.project)
    if args.command == 'init': result = initialize(path, json.loads((path / 'state.json').read_text()))
    elif args.command in ('context', 'check', 'render'):
        with project_lock(path):
            result = context(path, root)
            if args.command == 'check': result['passed'] = not result['invalid_resolutions']
            if args.command == 'render': render(path)
    else:
        if not args.file: parser.error('--file is required for a decision change')
        payload = json.loads(confined_path(path, args.file, True).read_text())
        result = change(root, path, args.command, payload)
    print(encoded(result), end='')

if __name__ == '__main__':
    try: main()
    except (ValueError, KeyError, OSError) as error:
        print(json.dumps({'passed': False, 'error': str(error)})); sys.exit(2)
