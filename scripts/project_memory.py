#!/usr/bin/env python3
"""Append-only working memory scoped to one application dossier.

The log and its seal are canonical; search indexes and Markdown are disposable
projections. A confirmation is a recorded decision, never a project-model edit
or an independent validation receipt.
"""
import argparse
from contextlib import contextmanager
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unicodedata
from urllib.parse import urlparse

from project_paths import confined_path, preflight_dossier, project_input, resolve_project

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'project-working-memory-v1'
ENGINE_SCHEMA = 'engine-working-memory-v1'
KINDS = ('decision', 'fact', 'hypothesis', 'open-question', 'contradiction')
STATUSES = ('proposed', 'confirmed', 'rejected', 'superseded')
PROVENANCES = ('user-instruction', 'user-provided', 'agent-observed', 'agent-analysis', 'source-reading')
ZERO = '0' * 64
ROUTE_FIELDS = ('program', 'action', 'sector', 'year')
DERIVED = ('index.json', 'history.md', 'context.md')


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n').encode('utf-8')


def digest(value):
    return hashlib.sha256(value).hexdigest()


def tokens(value):
    return sorted(set(re.findall(r'[^\W_]+', unicodedata.normalize('NFKC', value).casefold())))


def nonempty(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(field + ' must be nonempty text')
    return value


def string_list(value, field):
    if not isinstance(value, list) or any(not isinstance(x, str) or not x.strip() for x in value) or len(value) != len(set(value)):
        raise ValueError(field + ' must be a list of distinct nonempty strings')
    return value


class ProjectMemory:
    def __init__(self, root, identifier):
        self.root = Path(root).absolute()
        self.schema = SCHEMA
        self.path = resolve_project(self.root, identifier)
        preflight_dossier(self.path)
        state = json.loads(confined_path(self.path, 'state.json', True).read_text(encoding='utf-8'))
        if state.get('id') != self.path.name:
            raise ValueError('Working memory requires state.id to match the full dossier folder ID')
        route = {key: state.get(key) for key in ROUTE_FIELDS}
        if any(not isinstance(route[k], str) or not route[k].strip() for k in ROUTE_FIELDS[:-1]) or type(route['year']) is not int or route['year'] < 1:
            raise ValueError('Working memory requires an explicit program, action, sector, and call year')
        self.binding = {'project_id': self.path.name, 'route': route}
        self.label = self.path.name
        self.id_prefix = self.path.name
        self.folder = confined_path(self.path, 'memory')

    def input(self, value, must_exist=True):
        return project_input(self.root, self.path, value, must_exist)

    def file(self, name, must_exist=False):
        return confined_path(self.path, self.folder / name, must_exist)

    def write(self, name, data):
        target = self.file(name)
        temp = None
        try:
            with tempfile.NamedTemporaryFile(dir=self.folder, prefix='.' + name + '-', suffix='.tmp', delete=False) as out:
                temp = Path(out.name)
                out.write(data)
                out.flush()
                os.fsync(out.fileno())
            temp.replace(target)
        finally:
            if temp and temp.exists():
                temp.unlink()

    @contextmanager
    def lock(self):
        target = self.file('.write.lock')
        try:
            fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise ValueError('A memory writer lock exists. Inspect the interrupted writer before removing memory/.write.lock') from exc
        try:
            with os.fdopen(fd, 'w') as out:
                out.write(str(os.getpid()) + '\n')
            yield
        finally:
            target.unlink()

    def initialize(self):
        if self.folder.exists() and (self.file('events.jsonl').exists() or self.file('seal.json').exists()):
            self.canonical()  # Never overwrite or silently reseal an existing log.
            return self.check()
        if self.folder.exists() and any(self.folder.iterdir()):
            raise ValueError('The memory folder is nonempty but has no complete canonical log. Preserve and inspect it.')
        self.folder.mkdir(exist_ok=True)
        with self.lock():
            with self.file('events.jsonl').open('xb') as out:
                out.flush()
                os.fsync(out.fileno())
            seal = {'schema_version': self.schema, **self.binding, 'count': 0, 'head': ZERO, 'log_sha256': digest(b'')}
            self.write('seal.json', encoded(seal))
            self.rebuild_derived([], seal)
        return self.check()

    def validate_evidence(self, value, capture=False):
        if not isinstance(value, list):
            raise ValueError('evidence must be a list')
        result = []
        for entry in value:
            if not isinstance(entry, dict) or set(entry) - {'source_id', 'locator', 'path', 'url', 'reference', 'sha256'}:
                raise ValueError('Evidence supports only source_id, locator, path, url, reference, and sha256')
            e = dict(entry)
            nonempty(e.get('locator'), 'evidence.locator')
            if not any(e.get(k) for k in ('source_id', 'path', 'url', 'reference')):
                raise ValueError('Evidence requires a source ID, dossier path, URL, or explicit reference')
            for key in ('source_id', 'url', 'reference', 'path', 'sha256'):
                if key in e:
                    nonempty(e[key], 'evidence.' + key)
            if 'url' in e:
                parsed = urlparse(e['url'])
                if parsed.scheme not in ('http', 'https') or not parsed.netloc:
                    raise ValueError('Evidence URL must use http or https')
            if 'path' in e:
                candidate = project_input(self.root, self.path, e['path'], must_exist=capture)
                relative = candidate.relative_to(self.path).as_posix()
                if self.schema == ENGINE_SCHEMA and Path(relative).parts[0] in ('projects', '.lwc'):
                    raise ValueError('Engine memory evidence cannot include application artifacts or LWC internals')
                if capture:
                    current = digest(candidate.read_bytes())
                    if e.get('sha256') and e['sha256'] != current:
                        raise ValueError('The supplied evidence hash does not match the dossier artifact')
                    e.update(path=relative, sha256=current)
                elif e['path'] != relative or not re.fullmatch(r'[0-9a-f]{64}', e.get('sha256', '')):
                    raise ValueError('A logged evidence path must be relative to the dossier and include its observed SHA256')
            elif 'sha256' in e:
                raise ValueError('sha256 is reserved for an observed dossier evidence file')
            result.append(e)
        return result

    def validate_payload(self, payload, previous, capture=False):
        allowed = {'kind', 'status', 'title', 'summary', 'author', 'provenance', 'evidence', 'supersedes', 'contradicts', 'tags'}
        if not isinstance(payload, dict) or set(payload) - allowed:
            raise ValueError('Unknown working-memory record field')
        item = dict(payload)
        if item.get('kind') not in KINDS or item.get('status') not in STATUSES:
            raise ValueError('Record kind or status is invalid')
        for key in ('title', 'summary', 'author'):
            nonempty(item.get(key), key)
        provenance = item.get('provenance')
        if not isinstance(provenance, dict) or set(provenance) != {'type', 'reference'} or provenance.get('type') not in PROVENANCES:
            raise ValueError('Provenance needs a supported type and explicit reference')
        nonempty(provenance.get('reference'), 'provenance.reference')
        item['evidence'] = self.validate_evidence(item.get('evidence', []), capture)
        if item['status'] == 'confirmed' and not item['evidence']:
            raise ValueError('A confirmed record requires located evidence; a proposal may state that evidence is missing')
        for key in ('supersedes', 'contradicts', 'tags'):
            item[key] = string_list(item.get(key, []), key)
        by_id = {r['id']: r for r in previous}
        retired = {target for r in previous for target in r['supersedes']}
        for target in item['supersedes']:
            if target not in by_id or target in retired or by_id[target]['status'] not in ('proposed', 'confirmed'):
                raise ValueError('supersedes must name an active previous record in this memory: ' + target)
        if item['supersedes'] and item['status'] == 'proposed':
            raise ValueError('A proposal cannot retire an active decision. Confirm or reject it explicitly.')
        if item['status'] == 'superseded' and not item['supersedes']:
            raise ValueError('A superseded record must explicitly retire a previous record')
        for target in item['contradicts']:
            if target not in by_id:
                raise ValueError('contradicts must name a previous record in this memory: ' + target)
        if set(item['supersedes']) & set(item['contradicts']):
            raise ValueError('A record cannot both supersede and contradict the same record')
        if item['kind'] == 'contradiction' and not item['contradicts']:
            raise ValueError('A contradiction must identify the previous claim it concerns')
        return item

    def canonical(self):
        raw = self.file('events.jsonl', True).read_bytes()
        seal = json.loads(self.file('seal.json', True).read_text(encoding='utf-8'))
        seal_keys = {'schema_version', 'count', 'head', 'log_sha256', *self.binding}
        if not isinstance(seal, dict) or set(seal) != seal_keys or seal.get('schema_version') != self.schema or any(seal.get(k) != v for k, v in self.binding.items()):
            raise ValueError('The memory seal belongs to another dossier or uses an unsupported schema')
        if type(seal['count']) is not int or seal['count'] < 0 or not all(isinstance(seal[k], str) and re.fullmatch(r'[0-9a-f]{64}', seal[k]) for k in ('head', 'log_sha256')):
            raise ValueError('Malformed memory seal')
        if digest(raw) != seal['log_sha256']:
            raise ValueError('The canonical memory log differs from its seal. Preserve the files and audit the change.')
        if raw and not raw.endswith(b'\n'):
            raise ValueError('The canonical memory log has an incomplete final record')
        records, head = [], ZERO
        metadata = {'schema_version', 'sequence', 'id', 'created_at', 'previous_sha256', 'sha256', *self.binding}
        for sequence, line in enumerate(raw.splitlines(), 1):
            event = json.loads(line)
            if not isinstance(event, dict) or not metadata.issubset(event):
                raise ValueError('Malformed canonical memory event')
            if event['schema_version'] != self.schema or any(event[k] != v for k, v in self.binding.items()):
                raise ValueError('The canonical event belongs to another dossier')
            if type(event['sequence']) is not int or event['sequence'] != sequence or event['id'] != f'{self.id_prefix}::MEM-{sequence:06d}' or event['previous_sha256'] != head:
                raise ValueError('Broken memory event sequence or hash chain')
            try:
                created = dt.datetime.fromisoformat(event['created_at'])
                if created.tzinfo is None or created.utcoffset() != dt.timedelta(0):
                    raise ValueError('Memory timestamp must have an explicit UTC timezone')
            except (TypeError, ValueError) as exc:
                raise ValueError('Malformed memory event timestamp') from exc
            body = {k: v for k, v in event.items() if k != 'sha256'}
            if digest(encoded(body)) != event['sha256'] or encoded(event).rstrip(b'\n') != line:
                raise ValueError('Canonical memory event changed or is not canonically encoded')
            payload = {k: v for k, v in event.items() if k not in metadata}
            validated = self.validate_payload(payload, records)
            if validated != payload:
                raise ValueError('Canonical memory event omitted normalized fields')
            records.append(event)
            head = event['sha256']
        if seal['count'] != len(records) or seal['head'] != head:
            raise ValueError('Memory seal count/head does not match its append-only log')
        return records, seal

    def index(self, records, seal):
        superseded_by = {target: r['id'] for r in records for target in r['supersedes']}
        postings = {}
        entries = []
        for r in records:
            status = 'superseded' if r['id'] in superseded_by else r['status']
            searchable = ' '.join([r['title'], r['summary'], r['kind'], r['author'], *r['tags'], json.dumps(r['provenance'], ensure_ascii=False), json.dumps(r['evidence'], ensure_ascii=False)])
            for token in tokens(searchable):
                postings.setdefault(token, []).append(r['id'])
            entries.append({'id': r['id'], 'effective_status': status, 'superseded_by': superseded_by.get(r['id'])})
        return {'schema_version': self.schema, **self.binding, 'log_sha256': seal['log_sha256'], 'head': seal['head'], 'count': len(records), 'entries': entries, 'tokens': postings}

    def context_value(self, records, seal, phase=None):
        retired = {target for r in records for target in r['supersedes']}
        active = [r for r in records if r['id'] not in retired and r['status'] in ('confirmed', 'proposed')]
        active_ids = {r['id'] for r in active}
        special = ('hypothesis', 'open-question', 'contradiction')
        return {'schema_version': self.schema, **self.binding, 'phase': phase, 'log_sha256': seal['log_sha256'],
                'authority': 'working-memory-only-no-model-or-gate-promotion',
                'confirmed_active': [r for r in active if r['status'] == 'confirmed' and r['kind'] not in special],
                'proposals': [r for r in active if r['status'] == 'proposed' and r['kind'] not in special],
                'hypotheses': [r for r in active if r['kind'] == 'hypothesis'],
                'open_questions': [r for r in active if r['kind'] == 'open-question'],
                'contradictions': [r for r in active if r['kind'] == 'contradiction'],
                'conflicting_pairs': [{'record_id': r['id'], 'contradicts': target} for r in active for target in r['contradicts'] if target in active_ids],
                'evidence_warnings': self.evidence_warnings(records)}

    def evidence_warnings(self, records):
        warnings = []
        for record in records:
            for e in record['evidence']:
                if 'path' not in e:
                    continue
                candidate = confined_path(self.path, e['path'])
                if not candidate.is_file():
                    warnings.append({'record_id': record['id'], 'path': e['path'], 'issue': 'evidence-missing'})
                elif digest(candidate.read_bytes()) != e['sha256']:
                    warnings.append({'record_id': record['id'], 'path': e['path'], 'issue': 'evidence-changed', 'observed_sha256': e['sha256'], 'current_sha256': digest(candidate.read_bytes())})
        return warnings

    def render_record(self, record, status=None, successor=None):
        # Text is data, not instructions; JSON remains the canonical representation.
        lines = [f'### {record["id"]}: {record["title"]}', '',
                 f'- Type: {record["kind"]}; status: {status or record["status"]}; stated author: {record["author"]}',
                 f'- Recorded: {record["created_at"]}',
                 f'- Provenance: {record["provenance"]["type"]} — {record["provenance"]["reference"]}',
                 '', record['summary'], '']
        if successor:
            lines.extend(['Superseded by: ' + successor, ''])
        if record['supersedes']:
            lines.extend(['Supersedes: ' + ', '.join(record['supersedes']), ''])
        if record['contradicts']:
            lines.extend(['Contradicts: ' + ', '.join(record['contradicts']), ''])
        lines.append('Evidence:')
        if not record['evidence']:
            lines.append('- Missing; this entry is not a verified fact.')
        for e in record['evidence']:
            # Relative file links resolve from memory/, while source IDs and user
            # references stay descriptive and do not become guessed hyperlinks.
            relative = os.path.relpath(self.path / e['path'], self.folder).replace(os.sep, '/') if 'path' in e else None
            ref = '[artifact](<' + relative + '>)' if relative else e.get('url') or e.get('reference') or e.get('source_id')
            lines.append('- ' + ref + ' — ' + e['locator'] + ('; SHA256 ' + e['sha256'] if 'sha256' in e else ''))
        lines.append('')
        return '\n'.join(lines)

    def projections(self, records, seal):
        index = self.index(records, seal)
        states = {r['id']: r for r in index['entries']}
        history = '# Working Memory History\n\nRebuildable view generated from events.jsonl and seal.json. Do not edit this view.\n\n'
        history += f'Context: {self.label}; head: {seal["head"]}\n\n'
        for record in records:
            state = states[record['id']]
            history += self.render_record(record, state['effective_status'], state['superseded_by']) + '\n'
        context = self.context_value(records, seal)
        current = '# Working Memory Context\n\nRecorded confirmations, hypotheses, and proposals do not update project.json or close gates. Evidence remains subject to review.\n\n'
        current += f'Context: {self.label}; head: {seal["head"]}\n\n'
        sections = [('confirmed_active', 'Active Confirmations'), ('proposals', 'Proposals'), ('hypotheses', 'Hypotheses'), ('open_questions', 'Open Questions'), ('contradictions', 'Contradictions')]
        for key, label in sections:
            current += '## ' + label + '\n\n'
            current += '\n'.join(self.render_record(r) for r in context[key]) if context[key] else 'No entries.\n'
            current += '\n'
        current += '## Active Contradiction Relationships\n\n'
        current += '\n'.join('- ' + p['record_id'] + ' contradicts ' + p['contradicts'] for p in context['conflicting_pairs']) or 'No relationships recorded.'
        # Evidence change warnings are computed at read time, not sealed into a
        # projection that would become stale whenever an input artifact changes.
        current += '\n\nLocal evidence is compared with the hashes observed by context/check; this view does not certify its current validity.\n'
        return {'index.json': encoded(index), 'history.md': history.encode('utf-8'), 'context.md': current.encode('utf-8')}

    def rebuild_derived(self, records, seal):
        for name, data in self.projections(records, seal).items():
            self.write(name, data)

    def derived_issues(self, records, seal):
        issues = []
        for name, expected in self.projections(records, seal).items():
            candidate = self.file(name)
            if not candidate.is_file() or candidate.read_bytes() != expected:
                issues.append({'issue': 'index-stale' if name == 'index.json' else 'projection-stale', 'path': 'memory/' + name})
        return issues

    def loaded(self):
        records, seal = self.canonical()
        issues = self.derived_issues(records, seal)
        if issues:
            raise ValueError('The working memory index/projection is stale. Run check ID --rebuild-index after inspecting canonical integrity: ' + json.dumps(issues))
        return records, seal

    def record(self, payload):
        if not self.folder.is_dir():
            raise ValueError('Initialize dossier memory first with project_memory.py init ID')
        with self.lock():
            records, seal = self.loaded()
            item = self.validate_payload(payload, records, capture=True)
            sequence = len(records) + 1
            body = {'schema_version': self.schema, **self.binding, 'sequence': sequence, 'id': f'{self.id_prefix}::MEM-{sequence:06d}',
                    'created_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'previous_sha256': seal['head'], **item}
            event = {**body, 'sha256': digest(encoded(body))}
            raw = encoded(event)
            with self.file('events.jsonl', True).open('ab') as out:
                out.write(raw)
                out.flush()
                os.fsync(out.fileno())
            records.append(event)
            seal = {**seal, 'count': sequence, 'head': event['sha256'], 'log_sha256': digest(self.file('events.jsonl', True).read_bytes())}
            self.write('seal.json', encoded(seal))
            self.rebuild_derived(records, seal)
        return event

    def search(self, query, limit=10, include_history=False):
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError('Search limit must be between 1 and 1000')
        query_tokens = tokens(nonempty(query, 'query'))
        if not query_tokens:
            raise ValueError('Search query must contain words or numbers')
        records, seal = self.loaded()
        index = json.loads(self.file('index.json', True).read_text(encoding='utf-8'))
        matches = set.intersection(*(set(index['tokens'].get(t, [])) for t in query_tokens))
        states = {r['id']: r for r in index['entries']}
        selected = []
        for record in reversed(records):
            state = states[record['id']]
            if record['id'] in matches and (include_history or state['effective_status'] in ('confirmed', 'proposed')):
                selected.append({**record, **state})
        return {**self.binding, 'log_sha256': seal['log_sha256'], 'query': query, 'total': len(selected), 'results': selected[:limit], 'evidence_warnings': self.evidence_warnings(records)}

    def context(self, phase=None):
        records, seal = self.loaded()
        return self.context_value(records, seal, phase)

    def check(self, rebuild_index=False):
        try:
            records, seal = self.canonical()
            if rebuild_index:
                with self.lock():
                    records, seal = self.canonical()
                    self.rebuild_derived(records, seal)
            issues = self.derived_issues(records, seal)
            return {**self.binding, 'passed': not issues, 'canonical_valid': True, 'count': len(records), 'head': seal['head'],
                    'index_stale': any(i['issue'] == 'index-stale' for i in issues), 'issues': issues,
                    'evidence_warnings': self.evidence_warnings(records), 'rebuilt_index': bool(rebuild_index)}
        except (ValueError, OSError, UnicodeError, KeyError, TypeError) as exc:
            return {**self.binding, 'passed': False, 'canonical_valid': False, 'index_stale': None,
                    'issues': [{'issue': 'memory-integrity-error', 'detail': str(exc)}], 'rebuilt_index': False}


class EngineMemory(ProjectMemory):
    """Same storage protocol, explicit namespace, no application dossier binding."""
    def __init__(self, root):
        self.root = Path(root).absolute()
        for marker in ('config/agent-registry.json', 'scripts/lwc'):
            confined_path(self.root, marker, True)
        self.schema = ENGINE_SCHEMA
        self.path = self.root
        self.binding = {'workspace_id': 'erasmus-designer-engine', 'scope': 'engine-maintenance'}
        self.label = 'erasmus-designer-engine'
        self.id_prefix = 'engine:erasmus-designer'
        self.folder = confined_path(self.root, 'work/engine-memory')

    def input(self, value, must_exist=True):
        raw = Path(value)
        if not raw.is_absolute() and raw.parts[:2] == ('work', 'engine-memory'):
            raw = self.root / raw
        return confined_path(self.folder, raw, must_exist)

    def initialize(self):
        confined_path(self.root, 'work').mkdir(exist_ok=True)
        return super().initialize()


def opening_context(root, identifier, phase=None):
    """Read-only context for workflow status; missing legacy memory stays explicit."""
    path = resolve_project(Path(root), identifier)
    if not confined_path(path, 'memory').exists():
        return {'project_id': path.name, 'available': False, 'instruction': f'Initialize working memory explicitly: python3 scripts/project_memory.py init {path.name}'}
    memory = ProjectMemory(root, identifier)
    return {'available': True, **memory.context(phase)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT, help='Engine root (defaults to this script location)')
    parser.add_argument('--engine-memory', action='store_true', help='Use work/engine-memory only, with an explicit engine namespace')
    commands = parser.add_subparsers(dest='command', required=True)
    for command in ('init', 'record', 'search', 'context', 'check'):
        child = commands.add_parser(command)
        child.add_argument('project', nargs='?', help='Full dossier ID; omit only with --engine-memory')
        if command == 'record':
            child.add_argument('--file', required=True, help='Record JSON file inside the assigned dossier')
        elif command == 'search':
            child.add_argument('query')
            child.add_argument('--limit', type=int, default=10)
            child.add_argument('--include-history', action='store_true')
        elif command == 'context':
            child.add_argument('--phase', help='Annotate the opening phase; all active memory remains visible')
        elif command == 'check':
            child.add_argument('--rebuild-index', action='store_true', help='Rebuild derived files only if the canonical log and seal are valid')
    args = parser.parse_args(argv)
    if args.engine_memory:
        if args.project is not None:
            parser.error('--engine-memory does not accept an application ID')
        memory = EngineMemory(args.root)
    else:
        if args.project is None:
            parser.error('A full application ID is required without --engine-memory')
        memory = ProjectMemory(args.root, args.project)
    if args.command == 'init':
        result = memory.initialize()
    elif args.command == 'record':
        source = memory.input(args.file)
        result = memory.record(json.loads(source.read_text(encoding='utf-8')))
    elif args.command == 'search':
        result = memory.search(args.query, args.limit, args.include_history)
    elif args.command == 'context':
        result = memory.context(args.phase)
    else:
        result = memory.check(args.rebuild_index)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result.get('passed') is False else 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, UnicodeError, KeyError, TypeError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
