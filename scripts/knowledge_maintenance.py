#!/usr/bin/env python3
"""Collect immutable, inactive annual source/form candidates; never publish them.

stdlib only. Capture is a bounded public GET without a browser session/cookies.
Content-addressed revisions include every original and evidence byte. Form
comparison preserves the complete schema, including unfamiliar metadata.
"""
import argparse
import datetime as dt
import difflib
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
import tarfile
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse, urldefrag
from urllib.request import Request, build_opener, HTTPRedirectHandler

from form_profile import validate_profile

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'knowledge-maintenance-v1'
KINDS = {'programme-guide', 'expert-guide', 'official-page', 'national-page',
         'form-export', 'form-profile', 'corrigendum'}
TEXT_KINDS = {'text', 'textarea', 'narrative', 'long-text', 'short-text'}
IDENTITY_KEYS = ('program', 'year', 'kind', 'action', 'sector', 'round',
                 'language', 'agency', 'jurisdiction')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def validator_fingerprints():
    import form_profile
    return {'maintenance_sha256': digest(Path(__file__).read_bytes()),
            'form_profile_sha256': digest(Path(form_profile.__file__).read_bytes())}


def configuration(engine=ROOT):
    return read_json(Path(engine) / 'config/knowledge-maintenance.json')


def confined(base, relative):
    raw = PurePosixPath(relative)
    if raw.is_absolute() or '..' in raw.parts or not raw.parts:
        raise ValueError('Artifact path must be relative and confined')
    result = Path(base) / Path(*raw.parts)
    if any(p.is_symlink() for p in [result, *result.parents]):
        raise ValueError('Symlink not allowed in maintenance artifacts')
    if not result.resolve().is_relative_to(Path(base).resolve()):
        raise ValueError('Artifact outside revision')
    return result


def workspace_path(workspace, engine=ROOT):
    path = Path(workspace)
    if not path.is_absolute():
        path = Path(engine).resolve() / path
    path = path.absolute()
    if any(p.is_symlink() for p in [path, *path.parents]) or '.lwc' in path.parts:
        raise ValueError('Workspace must not use symlinks or canonical LWC storage')
    engine = Path(engine).resolve()
    if path.resolve().is_relative_to(engine):
        parts = path.resolve().relative_to(engine).parts
        common = len(parts) >= 2 and parts[0] in ('audits', 'maintenance-candidates')
        private = (len(parts) >= 4 and parts[0] == 'projects' and parts[2] == 'inbox'
                   and (engine / 'projects' / parts[1] / 'project.json').is_file())
        if not common and not private:
            raise ValueError('Stage only in audits/, maintenance-candidates/ or an existing dossier inbox')
    return path


def write_once(path, data):
    path = Path(path)
    if path.exists():
        if path.is_symlink() or not path.is_file() or path.read_bytes() != data:
            raise ValueError('Immutable artifact exists with different bytes: ' + str(path))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as output:
        output.write(data)


def identity(metadata):
    if not isinstance(metadata, dict):
        raise ValueError('Metadata must be an object')
    for key in IDENTITY_KEYS:
        value = metadata.get(key)
        if key == 'year':
            if isinstance(value, bool) or not isinstance(value, int) or not 2021 <= value <= 2100:
                raise ValueError('Explicit valid year required')
        elif not isinstance(value, str) or not value.strip():
            raise ValueError('Explicit identity required: ' + key)
    if metadata['program'] not in ('ERASMUS', 'ESC') or metadata['kind'] not in KINDS:
        raise ValueError('Unsupported program or asset kind')
    if metadata['kind'] in ('form-export', 'form-profile') and any(metadata[k] == 'ALL' for k in ('action', 'sector', 'round')):
        raise ValueError('Form assets require exact action, sector and round')
    if metadata['program'] == 'ESC' and metadata['sector'] not in ('ESC', 'ALL'):
        raise ValueError('ESC sector mismatch')
    if metadata['program'] == 'ERASMUS' and metadata['sector'] == 'ESC':
        raise ValueError('Erasmus sector mismatch')
    if metadata['action'].startswith('ESC') != (metadata['program'] == 'ESC') and metadata['action'] != 'ALL':
        raise ValueError('Action and program mismatch')
    if metadata['jurisdiction'] not in ('NA', 'EACEA', 'general'):
        raise ValueError('Jurisdiction must be NA, EACEA or general')
    if metadata['kind'] == 'expert-guide' and metadata['jurisdiction'] not in ('NA', 'EACEA'):
        raise ValueError('Expert guide requires explicit NA/EACEA scope')
    if not isinstance(metadata.get('scope_note'), str) or not metadata['scope_note'].strip():
        raise ValueError('Explicit scope_note required')
    if metadata.get('data_classification') not in ('public', 'project-private'):
        raise ValueError('Explicit data classification required')
    if 'identity_verified' in metadata and not isinstance(metadata['identity_verified'], bool):
        raise ValueError('identity_verified must be boolean')
    if metadata.get('status') not in (None, 'staged'):
        raise ValueError('Maintenance cannot activate an asset')
    return {key: metadata[key] for key in IDENTITY_KEYS}


def runtime_support(meta, engine=ROOT):
    """Fail closed: this adapter understands the existing explicit 2026 guards.

    A future guard refactor needs an audited adapter, not a JSON year toggle.
    Source inventory alone cannot claim that the application runtime works.
    """
    engine = Path(engine)
    actions = read_json(engine / 'config/actions.json')
    sources = read_json(engine / 'config/sources.json')
    brain = (engine / 'scripts/brain.py').read_text()
    workflow = (engine / 'scripts/workflow.py').read_text()
    brain_years = {int(v) for v in re.findall(r'if args\.year\s*!=\s*(\d+)\s*:', brain)}
    workflow_years = {int(v) for v in re.findall(r'if a\.year\s*!=\s*(\d+)\s*:', workflow)}
    audited_guards = brain_years == {2026} and workflow_years == {2026}
    common = meta['action'] == 'ALL'
    routes = [a for a in actions if a.get('program', 'ERASMUS') == meta['program']
              and (common or a['code'] == meta['action'])
              and (meta['sector'] == 'ALL' or meta['sector'] in a['sectors'])]
    guide_present = any(s.get('program', 'ERASMUS') == meta['program']
                        and s.get('year') == meta['year'] and s.get('kind') == 'programme-guide'
                        for s in sources)
    supported = audited_guards and meta['year'] == 2026 and bool(routes) and guide_present
    return {'supported': supported, 'guard_adapter_verified': audited_guards,
            'indexed_years': [2026] if audited_guards else [],
            'route_registered': bool(routes), 'programme_guide_registered': guide_present,
            'active': False,
            'reason': 'Candidate remains staged; catalogue/runtime support is not publication' if supported
            else 'Extend and test catalogue, routing, page scopes, runtime year guards and retrieval before promotion'}


def profile_check(profile, meta):
    result = validate_profile(profile)
    issues = list(result['issues'])
    if not isinstance(profile, dict):
        return {'passed': False, 'issues': issues}
    comparisons = {'program': profile.get('program', profile.get('programme')),
                   'year': profile.get('call_year') if profile.get('call_year') is not None else profile.get('template_year'),
                   'action': profile.get('action'), 'sector': profile.get('sector'),
                   'round': profile.get('round'), 'language': profile.get('language'),
                   'agency': profile.get('agency')}
    for key, actual in comparisons.items():
        if actual is None:
            issues.append({'code': 'profile-identity-missing', 'field': key})
        if actual is not None and actual != meta[key]:
            raise ValueError('Form profile and metadata identity mismatch: ' + key)
    if profile.get('action_family') and not meta['action'].startswith(profile['action_family']):
        raise ValueError('Form profile and metadata action family mismatch')
    if not profile.get('stable_id_namespace') or not profile.get('stable_id_evidence'):
        issues.append({'code': 'stable-id-registry-unverified'})
    for q in profile.get('questions', []) if isinstance(profile.get('questions'), list) else []:
        if not isinstance(q, dict):
            continue
        if not isinstance(q.get('prompt'), str) or not q.get('prompt', '').strip():
            issues.append({'code': 'missing-exact-prompt', 'question_id': q.get('id')})
        if q.get('kind', 'text') in TEXT_KINDS:
            cap = q.get('max_chars')
            occurrences = q.get('occurrences', [])
            targets = occurrences if isinstance(occurrences, list) and occurrences else [q]
            for target in targets:
                if not isinstance(target, dict):
                    continue
                effective = target.get('max_chars', cap)
                if isinstance(effective, bool) or not isinstance(effective, int) or effective <= 0:
                    issues.append({'code': 'missing-or-invalid-limit', 'question_id': q.get('id'),
                                   'occurrence_id': target.get('id') if target is not q else None})
                if not (target.get('limit_source') or target.get('verification_source')
                        or target.get('source_locator') or q.get('limit_source') or q.get('verification_source')):
                    issues.append({'code': 'limit-evidence-missing', 'question_id': q.get('id')})
    return {'passed': not issues, 'issues': issues, 'base_validator_passed': result['passed']}


def stage(workspace, file, metadata, evidence=(), engine=ROOT, capture=None):
    workspace = workspace_path(workspace, engine)
    ident = identity(metadata)
    if metadata['data_classification'] == 'project-private':
        resolved = workspace.resolve()
        base = Path(engine).resolve()
        if resolved.is_relative_to(base) and resolved.relative_to(base).parts[0] != 'projects':
            raise ValueError('Private forms/evidence must remain in selected dossier inbox or external workspace')
    original = Path(file)
    if original.is_symlink() or not original.is_file():
        raise ValueError('Original must be a regular file')
    payload = original.read_bytes()
    if not payload or len(payload) > configuration(engine)['max_capture_bytes']:
        raise ValueError('Original empty or exceeds capture limit')
    suffix = original.suffix.lower()
    if suffix not in ('.pdf', '.html', '.htm', '.json', '.txt', '.md', '.docx'):
        raise ValueError('Unsupported original format; retain export without inventing an extractor')
    if suffix == '.pdf' and not payload.startswith(b'%PDF-'):
        raise ValueError('Original is not a PDF')
    if suffix == '.docx' and not payload.startswith(b'PK'):
        raise ValueError('Original is not a DOCX archive')
    artifacts = {'payload' + suffix: payload, 'metadata.json': encoded(metadata)}
    for i, item in enumerate(evidence):
        candidate = Path(item)
        if candidate.is_symlink() or not candidate.is_file():
            raise ValueError('Evidence must be a regular file')
        data = candidate.read_bytes()
        if not data or len(data) > configuration(engine)['max_capture_bytes']:
            raise ValueError('Evidence empty or too large')
        artifacts[f'evidence/{i + 1:04d}{candidate.suffix.lower()}'] = data
    validation = None
    if metadata['kind'] == 'form-profile':
        profile = json.loads(payload.decode('utf-8'))
        validation = profile_check(profile, ident)
    manifest = {'schema_version': SCHEMA, 'status': 'staged', 'active': False,
                'identity': ident, 'payload_path': 'payload' + suffix,
                'payload_sha256': digest(payload), 'data_classification': metadata['data_classification'],
                'artifacts': [{'path': name, 'sha256': digest(data), 'bytes': len(data)}
                              for name, data in sorted(artifacts.items())],
                'profile_validation': validation,
                'validator_fingerprints': validator_fingerprints() if validation is not None else None,
                'capture': capture,
                'runtime_support': runtime_support(ident, engine)}
    manifest_bytes = encoded(manifest)
    key = digest(encoded(ident))
    revision = workspace / 'revisions' / key / digest(payload) / digest(manifest_bytes)
    for name, data in artifacts.items():
        write_once(confined(revision, name), data)
    write_once(confined(revision, 'manifest.json'), manifest_bytes)
    return {'revision': str(revision.relative_to(workspace)), 'manifest_sha256': digest(manifest_bytes),
            'payload_sha256': digest(payload), 'status': 'staged', 'active': False,
            'profile_validation': validation}


def check_revision(revision, expected_manifest=None):
    revision = Path(revision)
    if any(p.is_symlink() for p in [revision, *revision.parents]):
        raise ValueError('Symlink revision rejected')
    raw = (revision / 'manifest.json').read_bytes()
    if digest(raw) != revision.name or (expected_manifest and digest(raw) != expected_manifest):
        raise ValueError('Manifest digest changed')
    manifest = json.loads(raw)
    if manifest.get('schema_version') != SCHEMA or manifest.get('status') != 'staged' or manifest.get('active') is not False:
        raise ValueError('Revision is not an inactive maintenance candidate')
    identity(manifest['identity'] | {'scope_note': 'manifest identity',
             'data_classification': manifest.get('data_classification')})
    if revision.parent.name != manifest['payload_sha256'] or revision.parent.parent.name != digest(encoded(manifest['identity'])):
        raise ValueError('Revision content/identity address changed')
    seen = set()
    for entry in manifest['artifacts']:
        name = entry['path']
        if name in seen:
            raise ValueError('Duplicate artifact path')
        seen.add(name)
        artifact = confined(revision, name)
        if not artifact.is_file():
            raise ValueError('Missing revision artifact: ' + name)
        data = artifact.read_bytes()
        if len(data) != entry['bytes'] or digest(data) != entry['sha256']:
            raise ValueError('Artifact digest changed: ' + name)
    actual = {str(p.relative_to(revision)) for p in revision.rglob('*') if p.is_file() or p.is_symlink()}
    if actual != seen | {'manifest.json'}:
        raise ValueError('Unmanifested revision artifacts')
    payload = confined(revision, manifest['payload_path'])
    if manifest['payload_path'] not in seen or digest(payload.read_bytes()) != manifest['payload_sha256']:
        raise ValueError('Payload digest mismatch')
    metadata = read_json(revision / 'metadata.json')
    if identity(metadata) != manifest['identity'] or metadata['data_classification'] != manifest['data_classification']:
        raise ValueError('Metadata and manifest identity mismatch')
    validation = profile_check(read_json(payload), manifest['identity']) if manifest['identity']['kind'] == 'form-profile' else None
    snapshot_current = validation is None or manifest.get('validator_fingerprints') == validator_fingerprints()
    if snapshot_current and validation != manifest.get('profile_validation'):
        raise ValueError('Profile validation snapshot differs; freeze a new revision under changed validator')
    return {'passed': True, 'manifest_sha256': digest(raw), 'manifest': manifest,
            'ready_for_review': (validation is None or (validation['passed'] and snapshot_current)), 'active': False,
            'validation_snapshot_current': snapshot_current, 'current_profile_validation': validation,
            'new_snapshot_required': not snapshot_current}


def validate_url(url, settings):
    parts = urlparse(url)
    if parts.scheme != 'https' or parts.hostname not in settings['allowed_hosts'] or parts.username or parts.password:
        raise ValueError('Public HTTPS URL on an explicitly allowed official host required')
    if parts.port not in (None, 443) or re.search(r'/(login|authenticate|oauth|sso)(/|$)', parts.path, re.I):
        raise ValueError('Capture does not authorize authentication')


class PublicRedirect(HTTPRedirectHandler):
    def __init__(self, settings):
        super().__init__()
        self.settings = settings

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl, self.settings)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def capture(workspace, url, metadata, engine=ROOT):
    """Bounded unauthenticated GET; redirects are checked before being followed."""
    import tempfile
    settings = configuration(engine)
    identity(metadata)
    workspace_path(workspace, engine)
    if metadata['data_classification'] != 'public':
        raise ValueError('Network capture only supports public assets')
    validate_url(url, settings)
    opener = build_opener(PublicRedirect(settings))
    request = Request(url, headers={'User-Agent': 'ErasmusDesigner/knowledge-maintenance (public research)'})
    with opener.open(request, timeout=settings['timeout_seconds']) as response:
        validate_url(response.url, settings)
        data = response.read(settings['max_capture_bytes'] + 1)
        content_type = response.headers.get_content_type()
        if len(data) > settings['max_capture_bytes']:
            raise ValueError('Capture exceeds configured limit; nothing staged')
        if content_type == 'application/pdf' and data.startswith(b'%PDF-'):
            suffix = '.pdf'
        elif content_type in ('text/html', 'application/xhtml+xml'):
            suffix = '.html'
        elif content_type == 'application/json':
            suffix = '.json'
        elif content_type == 'text/plain':
            suffix = '.txt'
        else:
            raise ValueError('Unexpected capture content type: ' + content_type)
        observation = {'url': url, 'resolved_url': response.url, 'content_type': content_type,
                       'captured_at': dt.datetime.now(dt.timezone.utc).isoformat(),
                       'remote_byte_sha256': digest(data), 'complete_response': True,
                       'etag': response.headers.get('ETag'), 'last_modified': response.headers.get('Last-Modified'),
                       'identity_verified': False, 'authentication_used': False}
    with tempfile.TemporaryDirectory(prefix='erasmus-maintenance-capture-') as temp:
        original = Path(temp) / ('capture' + suffix)
        original.write_bytes(data)
        return stage(workspace, original, metadata, engine=engine, capture=observation)


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            href = dict(attrs).get('href')
            self.current = {'href': href, 'label': ''} if href else None

    def handle_data(self, data):
        if self.current is not None:
            self.current['label'] += data

    def handle_endtag(self, tag):
        if tag == 'a' and self.current is not None:
            self.links.append(self.current)
            self.current = None


def discover(revision, engine=ROOT):
    manifest = check_revision(revision)['manifest']
    payload = confined(revision, manifest['payload_path'])
    if payload.suffix not in ('.html', '.htm'):
        raise ValueError('Discovery requires a captured/staged HTML access point')
    metadata = read_json(Path(revision) / 'metadata.json')
    origin = (manifest.get('capture') or {}).get('resolved_url') or metadata.get('url')
    if not origin:
        raise ValueError('Discovery requires the observed page URL')
    parser = Links()
    parser.feed(payload.read_text(encoding='utf-8'))
    rows = []
    seen = set()
    for link in parser.links:
        url = urldefrag(urljoin(origin, link['href']))[0]
        label = ' '.join(link['label'].split())
        if url in seen:
            continue
        seen.add(url)
        text = label + ' ' + url
        if not re.search(r'guide|expert|form|corrig|call|proposal|application|202\d', text, re.I):
            continue
        try:
            validate_url(url, configuration(engine))
            allowed = True
        except ValueError:
            allowed = False
        hint = ('corrigendum' if re.search(r'corrig', text, re.I) else
                'expert-guide' if re.search(r'expert', text, re.I) else
                'form-export' if re.search(r'form|sample', text, re.I) else 'official-page')
        rows.append({'url': url, 'label': label, 'kind_hint': hint,
                     'possible_years': sorted({int(v) for v in re.findall(r'\b20\d{2}\b', text)}),
                     'capture_allowed': allowed, 'identity_verified': False})
    return {'schema_version': SCHEMA, 'source_manifest_sha256': Path(revision).name,
            'links': rows, 'complete_discovery': False,
            'caveat': 'Hints only; inspect pagination, dynamic library filters, current versions and adjacent call pages. No automatic year substitution.'}


def leaf_changes(old, new, path=''):
    """Compare JSON types and content; arrays retain order and complete values."""
    # Python equality conflates false/0 and true/1, including nested values.
    # Canonical JSON distinguishes those types and 1/1.0 at every depth while
    # ignoring object insertion order. Inputs here are JSON payloads only.
    if encoded(old) == encoded(new):
        return []
    if isinstance(old, dict) and isinstance(new, dict):
        rows = []
        for key in sorted(set(old) | set(new)):
            child = path + '/' + key.replace('~', '~0').replace('/', '~1')
            if key not in old:
                rows.append({'path': child, 'change': 'added', 'new': new[key]})
            elif key not in new:
                rows.append({'path': child, 'change': 'removed', 'old': old[key]})
            else:
                rows.extend(leaf_changes(old[key], new[key], child))
        return rows
    return [{'path': path or '/', 'change': 'changed', 'old': old, 'new': new}]


def diff_profiles(old, new, old_meta, new_meta, id_map=None):
    """Match only a shared evidenced registry or explicit one-to-one ID map.

    Equal labels are reported as possible ambiguities, never accepted matches.
    Differences across annualities are allowed; programs/actions cannot mix.
    """
    for key in ('program', 'action', 'sector', 'language', 'agency', 'jurisdiction'):
        if old_meta[key] != new_meta[key]:
            raise ValueError('Cannot compare unrelated form identities: ' + key)
    for profile, meta in ((old, old_meta), (new, new_meta)):
        profile_check(profile, meta)  # identity mismatches raise even for incomplete schemas
        validation = validate_profile(profile)
        if not validation['passed']:
            # Invalid limits remain diffable; malformed identity registries do not.
            structural = [i for i in validation['issues'] if i['code'] not in
                          ('invalid-profile-limit', 'invalid-profile-occurrence-limit', 'profile-rich-limit-conflict')]
            if structural:
                raise ValueError('Malformed profile registry: ' + json.dumps(structural))
    left = {q['id']: q for q in old['questions']}
    right = {q['id']: q for q in new['questions']}
    shared = (isinstance(old.get('stable_id_namespace'), str)
              and bool(old['stable_id_namespace']) and old['stable_id_namespace'] == new.get('stable_id_namespace')
              and bool(old.get('stable_id_evidence')) and bool(new.get('stable_id_evidence')))
    pairs = {qid: qid for qid in left.keys() & right.keys()} if shared else {}
    if id_map is not None:
        if not isinstance(id_map, list):
            raise ValueError('ID map must be a list of evidence-backed pairs')
        map_from, map_to = set(), set()
        for row in id_map:
            if not isinstance(row, dict) or row.get('from') not in left or row.get('to') not in right or not row.get('evidence'):
                raise ValueError('ID map requires known IDs and localized evidence')
            if row['from'] in map_from or row['to'] in map_to or (row['from'] in pairs and pairs[row['from']] != row['to']):
                raise ValueError('Ambiguous ID map')
            map_from.add(row['from']); map_to.add(row['to'])
            pairs[row['from']] = row['to']
        if len(set(pairs.values())) != len(pairs):
            raise ValueError('Ambiguous ID map target')
    removed = sorted(left.keys() - pairs.keys())
    added = sorted(right.keys() - set(pairs.values()))
    ambiguous = []
    for qid in removed:
        label = ' '.join(left[qid].get('prompt', '').split()).casefold()
        candidates = [nid for nid in added if nid == qid or (label and
                      ' '.join(right[nid].get('prompt', '').split()).casefold() == label)]
        if candidates:
            ambiguous.append({'old_id': qid, 'candidate_new_ids': candidates,
                              'reason': 'Identity lacks a shared evidenced registry or explicit mapping; label is not identity'})
    old_rich = {q['id']: q for q in old.get('fields', [])}
    new_rich = {q['id']: q for q in new.get('fields', [])}
    changed = []
    reduced = []
    for old_id, new_id in sorted(pairs.items()):
        changes = leaf_changes(left[old_id], right[new_id])
        changes += leaf_changes(old_rich.get(old_id), new_rich.get(new_id), '/rich_field')
        if changes:
            changed.append({'old_id': old_id, 'new_id': new_id, 'changes': changes})
        old_caps = {'field': left[old_id].get('max_chars')}
        new_caps = {'field': right[new_id].get('max_chars')}
        old_caps.update({o['id']: o.get('max_chars', old_caps['field']) for o in left[old_id].get('occurrences', [])})
        new_caps.update({o['id']: o.get('max_chars', new_caps['field']) for o in right[new_id].get('occurrences', [])})
        for key in old_caps.keys() & new_caps.keys():
            before, after = old_caps[key], new_caps[key]
            if isinstance(before, int) and not isinstance(before, bool) and isinstance(after, int) and not isinstance(after, bool) and 0 < after < before:
                reduced.append({'question_id': new_id, 'occurrence': key, 'old': before, 'new': after})
    # Retain the complete rich registry as well as the per-question ID view:
    # indexing fields alone loses array order and absence versus an empty list.
    old_extra = {k: v for k, v in old.items() if k != 'questions'}
    new_extra = {k: v for k, v in new.items() if k != 'questions'}
    top = leaf_changes(old_extra, new_extra, '/profile')
    order = {'old': list(left), 'new': list(right)} if list(left) != list(right) else None
    validation = profile_check(new, new_meta)
    blockers = list(validation['issues'])
    if ambiguous:
        blockers.append({'code': 'ambiguous-field-match'})
    if reduced:
        blockers.append({'code': 'limit-reduced-response-review-required'})
    if added or removed:
        blockers.append({'code': 'field-coverage-review-required'})
    return {'added': added, 'removed': removed,
            'added_fields': [{'question': right[qid], 'rich_field': new_rich.get(qid)} for qid in added],
            'removed_fields': [{'question': left[qid], 'rich_field': old_rich.get(qid)} for qid in removed],
            'changed': changed, 'ambiguous': ambiguous,
            'profile_changes': top, 'question_order_changes': order, 'reduced_limits': reduced,
            'candidate_validation': validation, 'migration_allowed': False,
            'requires_fresh_review': True, 'blockers': blockers,
            'ready_for_response_reuse': not blockers and not changed and not top and not order}


def diff_revisions(old_revision, new_revision, id_map=None):
    before_check = check_revision(old_revision)
    after_check = check_revision(new_revision)
    before = before_check['manifest']
    after = after_check['manifest']
    for key in ('program', 'kind', 'action', 'sector', 'language', 'agency', 'jurisdiction'):
        if before['identity'][key] != after['identity'][key]:
            raise ValueError('Cannot diff unrelated assets: ' + key)
    if after['identity']['year'] < before['identity']['year']:
        raise ValueError('Diff candidate year precedes baseline; choose rollback explicitly')
    left = confined(old_revision, before['payload_path']).read_bytes()
    right = confined(new_revision, after['payload_path']).read_bytes()
    result = {'schema_version': SCHEMA, 'baseline_manifest_sha256': Path(old_revision).name,
              'candidate_manifest_sha256': Path(new_revision).name, 'active': False,
              'identity_changes': leaf_changes(before['identity'], after['identity']),
              'content_changed': left != right, 'requires_fresh_review': True}
    result['candidate_validation_snapshot_current'] = after_check['validation_snapshot_current']
    result['current_validator_fingerprints'] = validator_fingerprints()
    if after['identity']['kind'] == 'form-profile':
        result['form'] = diff_profiles(json.loads(left), json.loads(right), before['identity'], after['identity'], id_map)
        if after_check['new_snapshot_required']:
            result['form']['blockers'].append({'code': 'validator-snapshot-stale'})
            result['form']['ready_for_response_reuse'] = False
    elif Path(after['payload_path']).suffix in ('.html', '.htm', '.txt', '.md', '.json'):
        result['text_diff'] = ''.join(difflib.unified_diff(left.decode('utf-8').splitlines(True),
                                  right.decode('utf-8').splitlines(True), fromfile='baseline', tofile='candidate'))
    else:
        result['semantic_diff_pending'] = True
        result['next_step'] = 'Extract from verified originals in candidate engine; compare full sections/tables, page numbering, rules and award grids. Byte change is not a normative conclusion.'
    return result


def inventory(workspace, engine=ROOT):
    settings = configuration(engine)
    registered = read_json(Path(engine) / 'config/sources.json')
    rows = [{'id': s['id'], 'program': s.get('program', 'ERASMUS'), 'year': s.get('year'),
             'kind': s.get('kind'), 'path': s['path'], 'sha256': s.get('sha256'),
             'url': s.get('document_url') or s.get('url'), 'status': 'registered-existing',
             'integrity_verified_here': False} for s in registered]
    candidates = []
    path = workspace_path(workspace, engine)
    for manifest in sorted(path.glob('revisions/*/*/*/manifest.json')) if path.exists() else []:
        checked = check_revision(manifest.parent)
        candidates.append({'revision': str(manifest.parent.relative_to(path)),
                           'manifest_sha256': checked['manifest_sha256'],
                           'identity': checked['manifest']['identity'], 'status': 'staged', 'active': False,
                           'ready_for_review': checked['ready_for_review'],
                           'new_snapshot_required': checked['new_snapshot_required']})
    method_paths = [Path(engine) / name for name in (
        'config/design-methodology.json', 'config/phase-zero.json',
        'config/compliance/design-methodology-2026.json',
        'docs/design-methodology.md', 'docs/phase-zero-idea-lab.md',
        'docs/award-idea-checklists.md', 'wiki/templates/phase-zero-decision-contract.md',
        'scripts/award_criteria.py', 'scripts/checklist.py', 'scripts/stage_gate.py',
        'scripts/workflow.py', 'skills/erasmus-designer/SKILL.md',
        'skills/erasmus-project-design/SKILL.md',
        'skills/erasmus-stage-validator/SKILL.md')]
    method_paths += sorted((Path(engine) / 'config/award-criteria').glob('*.json'))
    method_paths += sorted((Path(engine) / 'wiki/checklists/award-criteria').glob('*.md'))
    method_assets = [{'path': str(p.relative_to(engine)), 'sha256': digest(p.read_bytes()),
                      'kind': 'derived-operational-contract', 'active_year': 2026,
                      'integrity_verified_here': False,
                      'update_policy': 'Full guide revision, profile/selectors and effective checker review; no automatic dossier migration'}
                     for p in method_paths if p.is_file()]
    return {'schema_version': SCHEMA, 'registered': rows, 'staged': candidates,
            'methodology_assets': method_assets,
            'access_points': settings['access_points'],
            'caveat': 'Registered inventory is not a fresh online/integrity check; run brain.py check separately.'}


def export_revision(revision, destination):
    checked = check_revision(revision)
    if checked['manifest']['data_classification'] != 'public':
        raise ValueError('Default export excludes private forms and evidence')
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise ValueError('Export destination must be new')
    # All operational addresses in the archive are relative. Original bytes,
    # including historical provenance text, are deliberately not rewritten.
    names = ['manifest.json'] + [a['path'] for a in checked['manifest']['artifacts']]
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(destination, 'x:gz') as output:
        for name in sorted(names):
            artifact = confined(revision, name)
            info = output.gettarinfo(str(artifact), arcname='revision/' + name)
            info.uid = info.gid = 0; info.uname = info.gname = ''; info.mtime = 0
            with artifact.open('rb') as data:
                output.addfile(info, data)
    return {'path': destination.name, 'sha256': digest(destination.read_bytes()),
            'manifest_sha256': checked['manifest_sha256'], 'active': False}


def report(workspace, engine=ROOT):
    collected = inventory(workspace, engine)
    return {'schema_version': SCHEMA, 'inventory': collected, 'active': False,
            'publication_performed': False, 'review_status': 'pending-fresh-independent-review',
            'required_checks': ['official-version-and-corrigenda', 'program-year-action-sector-round-language-agency',
                                'expert-scope-NA-or-EACEA', 'complete-rules-and-award-grids',
                                'all-form-fields-conditional-repeated-limits-and-evidence',
                                'candidate-engine-brain-check-retrieval-runtime-and-workflow-tests',
                                'fresh-review-frozen-packet', 'explicit-LWC-changeset-publication',
                                'selected-dossiers-invalidate-earliest-dependent-phase-and-bind-form']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine', type=Path, default=ROOT)
    parser.add_argument('--workspace', type=Path, default=ROOT / 'audits/knowledge-maintenance/staging')
    commands = parser.add_subparsers(dest='cmd', required=True)
    for name in ('inventory', 'report'):
        commands.add_parser(name)
    for name in ('stage', 'capture'):
        cmd = commands.add_parser(name)
        cmd.add_argument('--metadata', type=Path, required=True)
        cmd.add_argument('--file' if name == 'stage' else '--url', required=True)
        if name == 'stage':
            cmd.add_argument('--evidence', type=Path, action='append', default=[])
    for name in ('check', 'discover', 'export'):
        cmd = commands.add_parser(name)
        cmd.add_argument('--revision', required=True)
        if name == 'check':
            cmd.add_argument('--expected-manifest')
            cmd.add_argument('--strict', action='store_true', help='Fail if profile is incomplete or invalid')
        if name == 'export':
            cmd.add_argument('--destination', required=True)
    cmd = commands.add_parser('diff')
    cmd.add_argument('--baseline', required=True)
    cmd.add_argument('--candidate', required=True)
    cmd.add_argument('--id-map', type=Path)
    cmd.add_argument('--fail-on-blockers', action='store_true')
    for cmd in commands.choices.values():
        cmd.add_argument('--out', help='New JSON report relative to workspace; existing bytes never overwritten')
    args = parser.parse_args(argv)
    args.engine = args.engine.resolve()
    workspace = workspace_path(args.workspace, args.engine)
    def input_path(value):
        value = Path(value)
        return value if value.is_absolute() else args.engine / value
    def revision(value):
        return confined(workspace, value)
    if args.cmd == 'inventory':
        result = inventory(workspace, args.engine)
    elif args.cmd == 'report':
        result = report(workspace, args.engine)
    elif args.cmd == 'stage':
        result = stage(workspace, input_path(args.file), read_json(input_path(args.metadata)),
                       [input_path(p) for p in args.evidence], args.engine)
    elif args.cmd == 'capture':
        result = capture(workspace, args.url, read_json(input_path(args.metadata)), args.engine)
    elif args.cmd == 'check':
        result = check_revision(revision(args.revision), args.expected_manifest)
    elif args.cmd == 'discover':
        result = discover(revision(args.revision), args.engine)
    elif args.cmd == 'diff':
        result = diff_revisions(revision(args.baseline), revision(args.candidate),
                                read_json(input_path(args.id_map)) if args.id_map else None)
    else:
        result = export_revision(revision(args.revision), confined(workspace, args.destination))
    if args.out:
        write_once(confined(workspace, args.out), encoded(result))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.cmd == 'check' and args.strict and not result['ready_for_review']:
        return 1
    if args.cmd == 'diff' and args.fail_on_blockers and result.get('form', {}).get('blockers'):
        return 1
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, KeyError, OSError, TypeError) as error:
        print(json.dumps({'error': str(error), 'publication_performed': False}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
