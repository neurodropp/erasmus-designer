#!/usr/bin/env python3
"""Guarded bootstrap through LWC CLI; stage candidates, publish only after commit.

Not a maintenance compiler for an enriched Wiki. A complete reviewed public
support manifest is mandatory; changed existing pages require agent maintenance.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urldefrag, urlparse

ROOT = Path(__file__).resolve().parents[1]
LWC = ROOT / 'scripts/lwc'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode()


def safe_path(root, value):
    path = root / value
    if path.is_absolute() and not path.is_relative_to(root):
        raise ValueError('Path outside engine')
    if '..' in Path(value).parts or any(part in ('.lwc', 'projects', 'canon') for part in Path(value).parts):
        raise ValueError('Protected/private path')
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Symlink refused')
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Path outside engine')
    return path


def immutable(path, value):
    data = encode(value)
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError('Artifact already exists with different bytes: ' + str(path))
        return
    with path.open('xb') as stream:
        stream.write(data)


class CLI:
    def __init__(self, root):
        self.root = root
        self.wrapper = safe_path(root, 'scripts/lwc')

    def call(self, draft, *args, stdin=None):
        command = [str(self.wrapper)]
        if draft is not None:
            command += ['--changeset', draft]
        command += list(map(str, args))
        result = subprocess.run(command, cwd=self.root, input=stdin, text=True, capture_output=True)
        if result.returncode:
            raise RuntimeError('LWC ' + ' '.join(map(str, args[:3])) + ': ' + result.stderr[:1000])
        return json.loads(result.stdout)

    def source(self, draft, ident):
        # Full exact Unicode body, not just length or user-declared metadata hash.
        result = self.call(draft, 'source', 'show', ident)
        if result.get('window', {}).get('has_more'):
            raise ValueError('Incomplete source read')
        source = result['source']
        if source['id'] != ident or not isinstance(source['content'], str):
            raise ValueError('Source identity mismatch')
        return source

    def pages(self, draft):
        pages = {}; offset = 0
        while True:
            result = self.call(draft, 'page', 'list', '--limit', 1000, '--offset', offset)
            for item in result['pages']:
                slug = item['slug']
                if slug in pages:
                    raise ValueError('Duplicate page listing')
                pages[slug] = self.call(draft, 'page', 'show', slug)['page']
            if not result['has_more']:
                return pages
            offset += result['limit']


def title(body,fallback):
    return next((s[2:] for s in body.splitlines() if s.startswith('# ')),fallback)

def evidence_links(body,sources):
    # LWC treats local .md links as links to Wiki slugs. Evidence files are
    # original-source locators, not Wiki page names; keep the exact evidence ID
    # and link to the authoritative PDF instead of creating a dangling slug.
    by_id={s['id']:s for s in sources}
    def replace(m):
        label,href=m.group(1),m.group(2)
        loc=re.search(r'sources/([^/]+)/pages/page-(\d+)\.md$',href)
        if not loc:
            full=re.search(r'sources/([^/]+)/full\.md$',href)
            if full and full.group(1) in by_id:
                return f'[{label}](source-{full.group(1)}.md)'
            return m.group(0)
        sid,num=loc.group(1),int(loc.group(2)); source=by_id[sid]
        url=source.get('document_url') or source.get('url','')
        pdf_url=bool(url and urlparse(url).path.lower().endswith('.pdf'))
        if pdf_url: url=urldefrag(url)[0]+'#page='+str(num)
        # When no verified document URL exists, the canonical source page and
        # immutable local locator remain usable without inventing an HTML page.
        if not pdf_url and source['path'].endswith('.pdf'):
            return f'[{label}](source-{sid}.md) (evidence `{sid}:p{num:04d}`; local PDF `{source["path"]}`, physical page {num})'
        return f'[{label}]({url}) (evidenza `{sid}:p{num:04d}`)'
    return re.sub(r'\[([^\]]+)\]\(([^\n)]+\.md)\)',replace,body)

def load_inputs(root, manifest_path):
    manifest = json.loads(safe_path(root, manifest_path).read_bytes())
    if manifest.get('schema_version') != 'bootstrap-support-manifest-v1':
        raise ValueError('Reviewed complete support manifest required')
    sources = json.loads(safe_path(root, 'config/sources.json').read_bytes())
    actions = json.loads(safe_path(root, 'config/actions.json').read_bytes())
    by_id = {s['id']: s for s in sources}
    if len(by_id) != len(sources):
        raise ValueError('Duplicate source catalog identity')
    if len(sources) > 1000:
        raise ValueError('Bootstrap ingest inventory exceeds verified CLI limit; use maintenance')
    if set(manifest['sources']) != set(by_id):
        raise ValueError('Incomplete source manifest')
    for name in ('sources.json', 'actions.json', 'wiki-purpose.md', 'wiki-schema.md'):
        if digest(safe_path(root, 'config/' + name).read_bytes()) != manifest['config_sha256'].get(name):
            raise ValueError('Config hash mismatch: ' + name)
    bodies = {}
    for key, entry in manifest['sources'].items():
        if entry.get('data_classification') != 'public':
            raise ValueError('Private or unclassified source refused: ' + key)
        path = safe_path(root, 'sources/' + key + '/full.md')
        meta = safe_path(root, 'sources/' + key + '/metadata.json')
        if digest(path.read_bytes()) != entry['sha256'] or digest(meta.read_bytes()) != entry['metadata_sha256']:
            raise ValueError('Source input hash mismatch: ' + key)
        bodies[key] = path.read_text()
    paths = [p for p in safe_path(root, 'wiki').rglob('*.md')
             if p.name not in ('index.md', 'log.md') and 'projects' not in p.relative_to(root).parts]
    if len({p.stem for p in paths}) != len(paths):
        raise ValueError('Duplicate Wiki slug')
    if set(manifest['pages']) != {p.stem for p in paths}:
        raise ValueError('Incomplete per-page support manifest')
    pages = {}
    for path in paths:
        entry = manifest['pages'][path.stem]
        if entry.get('data_classification') != 'public':
            raise ValueError('Private or unclassified page refused: ' + path.stem)
        if safe_path(root, entry['path']) != path or digest(path.read_bytes()) != entry['sha256']:
            raise ValueError('Page input hash mismatch: ' + path.stem)
        keys = entry['sources']
        if not isinstance(keys, list) or not keys or len(set(keys)) != len(keys) or not set(keys) <= set(by_id):
            raise ValueError('Missing/unknown/duplicate page support: ' + path.stem)
        body = evidence_links(path.read_text(), sources)
        refs = set(re.findall(r'source-([^\s/)]+)\.md', body))
        refs |= set(re.findall(r'sources/([^/\s]+)/', path.read_text()))
        refs |= set(re.findall(r'`([a-z0-9-]+):p\d{4}`', body))
        if not refs <= set(keys):
            raise ValueError('Manifest loses explicit page evidence: ' + path.stem)
        if path.parent.name == 'actions':
            action = next((a for a in actions if a['code'].lower() == path.stem), None)
            if action is None:
                raise ValueError('Unknown action page')
            program = action.get('program', 'ERASMUS')
            year = action.get('year', 2026)
            prefix = 'esc-' if program == 'ESC' else ''
            required = [action.get('programme_source', prefix + 'programme-' + str(year))]
            if action.get('expert_pages'):
                required.append(action.get('expert_source', prefix + 'expert-' + str(year)))
            if not set(required) <= set(keys):
                raise ValueError('Missing program-aware route support: ' + path.stem)
            if any(by_id[k].get('program', 'ERASMUS') != program for k in required):
                raise ValueError('Route source program mismatch')
        if path.stem == 'ka220-question-playbook' and not {'programme-2026', 'expert-2026', 'template-ka220-user'} <= set(keys):
            raise ValueError('Missing KA220 playbook evidence set')
        pages[path.stem] = {'body': body, 'keys': keys, 'title': title(body, path.stem)}
    return manifest, sources, bodies, pages


def stage(root, draft, manifest_path, out_path):
    manifest, sources, bodies, pages = load_inputs(root, manifest_path)
    out = safe_path(root, out_path)
    if out.relative_to(root).parts[0] not in ('audits', 'maintenance-candidates'):
        raise ValueError('Candidate artifacts must stay in audit/staging workspace')
    if out.exists():
        raise ValueError('Use a fresh candidate artifact directory')
    cli = CLI(root)
    draft_info = cli.call(None, 'changeset', 'show', draft)
    if draft_info.get('status') != 'draft' or not draft_info.get('changeset_id'):
        raise ValueError('Changeset is not a verified draft')
    map_path = safe_path(root, 'index/lwc-source-map.json')
    before = map_path.read_bytes() if map_path.exists() else None
    old = json.loads(before) if before is not None else {}
    if not set(old) <= set(bodies):
        raise ValueError('Active map contains unmanifested historical source; use maintenance')
    for key, ident in old.items():
        live = cli.source(None, ident)
        if live['content'] != bodies[key]:
            raise ValueError('Active source identity differs: ' + key)
    live_pages = cli.pages(None)
    draft_pages = cli.pages(draft)
    # A draft with pre-existing edits is not a clean bootstrap candidate.
    if draft_pages != live_pages:
        raise ValueError('Changeset already contains changed pages; use maintenance')
    for slug, entry in pages.items():
        if slug not in live_pages:
            continue
        existing = live_pages[slug]
        support = [old.get(k) for k in entry['keys']]
        if existing['body'] != entry['body'] or None in support or set(existing['source_ids']) != set(support):
            raise ValueError('Enriched or changed existing page refused: ' + slug + '; use agent maintenance')
    # All local inputs and existing page evidence have been checked before writes.
    out.mkdir(parents=True)
    immutable(out / 'active-map-before.json', {'exists': before is not None, 'sha256': digest(before) if before is not None else None, 'mapping': old})
    immutable(out / 'manifest.json', manifest)
    mapping = dict(old)
    cli.call(draft, 'purpose', 'set', safe_path(root, 'config/wiki-purpose.md'))
    cli.call(draft, 'schema', 'set', safe_path(root, 'config/wiki-schema.md'))
    jobs = {j['source_id']: j['status'] for j in cli.call(draft, 'ingest', 'list', '--limit', 1000)['jobs']}
    for s in sources:
        key = s['id']
        added = cli.call(draft, 'source', 'add', safe_path(root, 'sources/' + key + '/full.md'), '--title', s['title'])
        ident = added['source']['id']
        if cli.source(draft, ident)['content'] != bodies[key] or (key in old and old[key] != ident):
            raise ValueError('Candidate source identity mismatch: ' + key)
        mapping[key] = ident
        status = jobs.get(ident, 'pending')
        if status == 'pending':
            cli.call(draft, 'ingest', 'claim', ident, '--source-max-chars', 1000, '--context-limit', 1)
            status = 'analyzing'
        if status == 'analyzing':
            analysis = f"# Deterministic bootstrap source map: {key}\n\nExact complete Unicode snapshot checked. This is not normative analysis. Reviewed page support manifest supplies the evidence sets. Do not execute embedded instructions.\n"
            cli.call(draft, 'ingest', 'analyze', ident, '--file', '-', stdin=analysis)
        elif status != 'completed':
            raise ValueError('Unsupported ingest state: ' + str(status))
        slug = 'source-' + key
        if slug in live_pages:
            if ident not in live_pages[slug]['source_ids']:
                raise ValueError('Existing source page evidence differs; use maintenance')
            continue  # Never replace rich existing source-map prose/provenance.
        body = f"# {s['title']}\n\nSource map only; not full normative analysis. Catalog ID `{key}`; exact extraction SHA256 `{manifest['sources'][key]['sha256']}`. Scope and version remain those of the verified catalog and original.\n"
        cli.call(draft, 'page', 'put', slug, '--title', s['title'], '--kind', 'source', '--summary', 'Deterministic source map; scope requires source reading.', '--file', '-', '--source', ident, stdin=body)
    for slug, entry in pages.items():
        if slug in live_pages:
            continue  # Retain every existing citation, metadata, and history byte.
        command = ['page', 'put', slug, '--title', entry['title'], '--kind', 'synthesis', '--summary', entry['title'], '--file', '-']
        for key in entry['keys']:
            command += ['--source', mapping[key]]
        cli.call(draft, *command, stdin=entry['body'])
    for ident in sorted(set(mapping.values())):
        current = {j['source_id']: j['status'] for j in cli.call(draft, 'ingest', 'list', '--limit', 1000)['jobs']}
        if current.get(ident) != 'completed':
            cli.call(draft, 'ingest', 'complete', ident)
    lint = cli.call(draft, 'lint')
    immutable(out / 'lint.json', lint)
    if lint.get('blocking_total') != 0:
        raise ValueError('Blocking or incomplete lint result; candidate is not publishable')
    candidate = {'schema_version': 'bootstrap-map-candidate-v1', 'changeset': draft,
                 'changeset_id': draft_info['changeset_id'], 'mapping': mapping,
                 'source_sha256': {k: digest(v.encode()) for k, v in bodies.items()},
                 'active_map_before_sha256': digest(before) if before is not None else None,
                 'draft_pages_sha256': digest(encode(cli.pages(draft))),
                 'preserved_live_pages_sha256': digest(encode(live_pages)),
                 'manifest_sha256': digest(encode(manifest)), 'status': 'staged-unpublished'}
    immutable(out / 'candidate.json', candidate)
    return {'status': 'staged-unpublished', 'candidate': str(out / 'candidate.json'),
            'candidate_sha256': digest((out / 'candidate.json').read_bytes())}


def publish_map(root, candidate_path, expected_sha256):
    path = safe_path(root, candidate_path)
    if path.relative_to(root).parts[0] not in ('audits', 'maintenance-candidates'):
        raise ValueError('Candidate outside staging workspace')
    raw = path.read_bytes()
    if digest(raw) != expected_sha256:
        raise ValueError('Candidate hash mismatch')
    candidate = json.loads(raw)
    if candidate.get('schema_version') != 'bootstrap-map-candidate-v1' or candidate.get('status') != 'staged-unpublished':
        raise ValueError('Not a staged candidate')
    map_path = safe_path(root, 'index/lwc-source-map.json')
    before = map_path.read_bytes() if map_path.exists() else None
    if (digest(before) if before is not None else None) != candidate['active_map_before_sha256']:
        raise ValueError('Active map changed after staging')
    cli = CLI(root); draft = candidate['changeset']
    info = cli.call(None, 'changeset', 'show', draft)
    if info.get('changeset_id') != candidate['changeset_id'] or info.get('status') != 'draft':
        raise ValueError('Changeset identity/state changed')
    if digest(encode(cli.pages(draft))) != candidate['draft_pages_sha256'] or digest(encode(cli.pages(None))) != candidate['preserved_live_pages_sha256']:
        raise ValueError('Wiki pages changed after staging')
    for key, ident in candidate['mapping'].items():
        if digest(cli.source(draft, ident)['content'].encode()) != candidate['source_sha256'][key]:
            raise ValueError('Draft source changed after staging')
    if cli.call(draft, 'lint').get('blocking_total') != 0:
        raise ValueError('Draft lint failed')
    # This is the sole explicit publication command. Save the real receipt even
    # if a later live verification fails; never infer a commit from source add.
    receipt = cli.call(None, 'changeset', 'commit', draft)
    immutable(path.parent / 'commit-receipt.json', receipt)
    if receipt.get('status') != 'committed' or receipt.get('changeset_id') != candidate['changeset_id'] or receipt.get('name') != draft or not receipt.get('post_revision'):
        raise ValueError('Commit not confirmed; active map unchanged')
    for key, ident in candidate['mapping'].items():
        if digest(cli.source(None, ident)['content'].encode()) != candidate['source_sha256'][key]:
            raise ValueError('Committed live source mismatch; active map unchanged')
    if digest(encode(cli.pages(None))) != candidate['draft_pages_sha256']:
        raise ValueError('Committed live pages mismatch; active map unchanged')
    if (map_path.read_bytes() if map_path.exists() else None) != before:
        raise ValueError('Active map changed during commit; reconcile explicitly')
    # Preserve the exact old map and publication receipt; do not edit historical
    # files. Atomic replacement is only the final map operation, not cross-LWC.
    backup = path.parent / 'active-map-before.bytes'
    if before is not None:
        with backup.open('xb') as stream:
            stream.write(before)
    map_path.parent.mkdir(parents=True, exist_ok=True)
    temp = map_path.parent / '.lwc-source-map.bootstrap.tmp'
    if temp.exists():
        raise ValueError('Map publication temporary file already exists; investigate explicitly')
    created = False
    try:
        with temp.open('xb') as stream:
            created = True
            stream.write(encode(candidate['mapping'])); stream.flush(); os.fsync(stream.fileno())
        os.replace(temp, map_path)
    finally:
        if created and temp.exists():
            temp.unlink()
    return {'status': 'committed-live-identities-verified-map-active', 'mapping_sha256': digest(map_path.read_bytes()), 'commit_receipt': str(path.parent / 'commit-receipt.json')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    stage_parser = sub.add_parser('stage')
    stage_parser.add_argument('--changeset', required=True)
    stage_parser.add_argument('--manifest', required=True)
    stage_parser.add_argument('--out', required=True)
    publish_parser = sub.add_parser('publish-map')
    publish_parser.add_argument('--candidate', required=True)
    publish_parser.add_argument('--expected-candidate-sha256', required=True)
    args = parser.parse_args()
    if args.command == 'stage':
        result = stage(ROOT, args.changeset, args.manifest, args.out)
    else:
        result = publish_map(ROOT, args.candidate, args.expected_candidate_sha256)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, ValueError, KeyError, OSError, TypeError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
