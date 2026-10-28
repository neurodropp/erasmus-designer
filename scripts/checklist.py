#!/usr/bin/env python3
"""Project-specific, evidence-bearing checklist. This checks contracts, not eligibility."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import sys

import brain
import stage_gate
from project_paths import resolve_project

ROOT = Path(__file__).resolve().parents[1]
CATALOG_ROOT = ROOT
STATUSES = {'satisfied', 'not-satisfied', 'to-verify', 'not-applicable'}
FORM_REQUIRED_PHASES = {'answer-outlines', 'application-draft', 'annexes', 'review', 'repair', 'qa', 'draft'}
IDENTITY = ('program', 'year', 'action', 'sector', 'country', 'agency', 'role', 'round')
IDEA_PHASES = {'idea-validation', 'eligibility'}
PHASE_ZERO = 'phase-zero'
PHASE_ZERO_AXES = (
    ('route_call_fit', 'Which call or route genuinely supports the core idea, and which alternatives have been ruled out?'),
    ('priority_contribution', 'Which European and programme priorities does the idea address through an observable mechanism?'),
    ('primary_target_fit', 'Is the primary target group specific, reachable, and consistent with the beneficiaries and participants of the candidate route?'),
    ('secondary_target_fit', 'Are secondary target groups distinct from the primary target group, with a credible role in the change pathway?'),
    ('need_evidence', 'Are needs and problems distinguished and supported by localized evidence or a credible research plan?'),
    ('causal_chain', 'Are needs, problems, solutions, activities, outputs, results, and impact linked without causal gaps?'),
    ('scale_budget_fit', 'Are ambition, duration, activities, capacity, and budget tier proportionate?'),
    ('capability_partner_fit', 'Are the required capabilities and potential partner roles identified without inventing commitments?'),
    ('european_added_value', 'Does the European dimension create demonstrable value beyond parallel local activities?'),
)


def read(path):
    return json.loads(path.read_text())


def outcome():
    return dict(status='to-verify', evidence=[], artifact_locators=[], reason='',
                discrepancy='', severity='', required_fix='', owner='')


def phase_zero_template(state):
    """Route-neutral checklist for the pre-dossier idea lab.

    This is a local design contract.  It deliberately contains no official
    score and does not select an award-criteria profile before a route exists.
    """
    if state.get('workspace_type') != 'idea-lab' or state.get('next_phase') not in (PHASE_ZERO, 'human-decision', 'ready-for-dossier', 'closed'):
        raise ValueError('Phase zero checklist requires an idea-lab workspace')
    policy = read(CATALOG_ROOT / 'config/phase-zero.json')
    if policy.get('schema_version') != 'phase-zero-policy-v1' or policy.get('active_year') != state['year']:
        raise ValueError('Phase zero policy does not cover this annuality')
    mandatory = policy.get('mandatory_axes', {})
    if list(mandatory) != [ident for ident, _ in PHASE_ZERO_AXES]:
        raise ValueError('Phase zero policy axes differ from the owned checklist contract')
    return {
        'schema_version': 'phase-zero-checklist-v1',
        'phase': PHASE_ZERO,
        'scope': {'idea_id': state['id'], 'year': state['year']},
        'authority': 'user-authorized-local-method-not-programme-requirement',
        'limitations': [
            'This exploratory checklist is not an eligibility verdict, official assessment or funding prediction.',
            'Award criteria may be previewed only for an identified candidate route and remain subject to the later route-specific idea-validation.',
        ],
        'route_candidates': [],
        'axes': [
            {
                'id': ident, 'question': question, 'allowed_outcomes': mandatory[ident], 'outcome': 'unassessed',
                'reason': '', 'evidence': [], 'evidence_plan': '', 'owner': '',
                'design_implication': ''
            }
            for ident, question in PHASE_ZERO_AXES
        ],
    }


def validate_phase_zero_brainstorm(data, state, path):
    """Validate observable divergence without storing private reasoning."""
    issues = []
    if not isinstance(data, dict) or data.get('schema_version') != 'phase-zero-brainstorm-v1':
        return {'valid': False, 'issues': [{'item_id': 'brainstorm', 'issue': 'Invalid Phase zero brainstorm schema'}]}
    if not isinstance(data.get('idea_version'), int) or data['idea_version'] < 1:
        issues.append({'item_id': 'idea_version', 'issue': 'Brainstorm idea_version must be a positive integer'})
    if data.get('authority') != 'collaborative-exploration-not-human-approval':
        issues.append({'item_id': 'authority', 'issue': 'Brainstorm authority must remain exploratory'})
    provenance = data.get('provenance')
    if not isinstance(provenance, list) or not provenance:
        issues.append({'item_id': 'provenance', 'issue': 'Brainstorm requires observed provenance'})
        provenance = []
    provenance_ids = []
    for row in provenance:
        if not isinstance(row, dict) or any(not isinstance(row.get(k), str) or not row[k].strip() for k in ('id', 'actor', 'type', 'reference')):
            issues.append({'item_id': 'provenance', 'issue': 'Each provenance entry needs id, actor, type and reference'})
            continue
        if row['type'] not in ('user-input', 'agent-proposal', 'source-reading'):
            issues.append({'item_id': row['id'], 'issue': 'Unsupported brainstorm provenance type'})
        provenance_ids.append(row['id'])
    if len(provenance_ids) != len(set(provenance_ids)):
        issues.append({'item_id': 'provenance', 'issue': 'Brainstorm provenance IDs must be unique'})
    options = data.get('options')
    if not isinstance(options, list) or not options:
        issues.append({'item_id': 'options', 'issue': 'Brainstorm requires at least one option'})
        options = []
    ids, kinds = [], []
    for option in options:
        if not isinstance(option, dict):
            issues.append({'item_id': 'options', 'issue': 'Each brainstorm option must be an object'}); continue
        ident = option.get('id', 'unknown');ids.append(ident);kinds.append(option.get('kind'))
        if not isinstance(ident, str) or not ident.strip() or option.get('kind') not in ('primary', 'alternative'):
            issues.append({'item_id': ident, 'issue': 'Option needs a unique id and primary|alternative kind'})
        for key in ('problem', 'primary_target', 'mechanism', 'scale'):
            if not isinstance(option.get(key), str) or not option[key].strip():
                issues.append({'item_id': ident, 'issue': 'Option needs a nonempty '+key})
        refs = option.get('provenance_refs')
        if not isinstance(refs, list) or not refs or any(ref not in provenance_ids for ref in refs):
            issues.append({'item_id': ident, 'issue': 'Option must cite observed brainstorm provenance IDs'})
        assumptions = option.get('assumptions')
        if not isinstance(assumptions, list) or any(not isinstance(value, str) or not value.strip() for value in assumptions):
            issues.append({'item_id': ident, 'issue': 'Option assumptions must be a list of nonempty text'})
    if len(ids) != len(set(ids)):
        issues.append({'item_id': 'options', 'issue': 'Brainstorm option IDs must be unique'})
    if kinds.count('primary') != 1:
        issues.append({'item_id': 'options', 'issue': 'Brainstorm requires exactly one primary formulation'})
    convergence = data.get('convergence')
    if not isinstance(convergence, dict):
        issues.append({'item_id': 'convergence', 'issue': 'Brainstorm requires a convergence record'})
        convergence = {}
    if convergence.get('preferred_option_id') not in ids:
        issues.append({'item_id': 'convergence', 'issue': 'Preferred option must reference an observed option'})
    reasons = convergence.get('selection_reasons')
    if not isinstance(reasons, list) or not reasons or any(not isinstance(value, str) or not value.strip() for value in reasons):
        issues.append({'item_id': 'convergence', 'issue': 'Convergence requires explicit selection reasons'})
    compared = convergence.get('compared_option_ids')
    if not isinstance(compared, list) or any(value not in ids or value == convergence.get('preferred_option_id') for value in compared):
        issues.append({'item_id': 'convergence', 'issue': 'Compared options must reference distinct observed options'})
        compared = []
    exception = data.get('alternative_exception')
    primary_ids = {option.get('id') for option in options if isinstance(option, dict) and option.get('kind') == 'primary'}
    alternative_ids = {option.get('id') for option in options if isinstance(option, dict) and option.get('kind') == 'alternative'}
    if alternative_ids:
        if exception is not None:
            issues.append({'item_id': 'alternative_exception', 'issue': 'Do not claim no alternative when an alternative is recorded'})
        convergence_ids = {convergence.get('preferred_option_id'), *(compared if isinstance(compared, list) else [])}
        if not primary_ids.intersection(convergence_ids) or not alternative_ids.intersection(convergence_ids):
            issues.append({'item_id': 'convergence', 'issue': 'Convergence must include a primary and an alternative across the preferred and compared options'})
    else:
        if not isinstance(exception, dict) or any(not exception.get(k) for k in ('reason', 'owner', 'evidence')):
            issues.append({'item_id': 'alternative', 'issue': 'A pertinent alternative or localized evidence-backed exception is required'})
        else:
            issues.extend(_phase_zero_reference_issues(exception.get('evidence'), 'alternative_exception', path))
    return {'valid': not issues, 'issues': issues}


def _phase_zero_reference_issues(refs, ident, path):
    issues = []
    if not isinstance(refs, list):
        return [dict(item_id=ident, issue='Evidence must be a list')]
    for ref in refs:
        if not isinstance(ref, dict) or not ref.get('locator'):
            issues.append(dict(item_id=ident, issue='Evidence requires a localized locator'))
            continue
        selectors = [key for key in ('local_snapshot', 'path', 'url', 'source_id') if ref.get(key)]
        if len(selectors) != 1:
            issues.append(dict(item_id=ident, issue='Evidence requires exactly one of local_snapshot, path, URL or source_id'))
            continue
        value = ref.get('local_snapshot') or ref.get('path')
        url = ref.get('url')
        if value:
            candidate = Path(value)
            if not candidate.is_absolute():
                candidate = path / candidate
            candidate = candidate.resolve()
            if not candidate.is_relative_to(path.resolve()) or not candidate.is_file():
                issues.append(dict(item_id=ident, issue='Evidence snapshot missing or outside idea lab'))
            elif ref.get('sha256') and hashlib.sha256(candidate.read_bytes()).hexdigest() != ref['sha256']:
                issues.append(dict(item_id=ident, issue='Evidence snapshot hash mismatch'))
        elif url:
            if not str(url).startswith('https://') or not ref.get('verified_at') or not ref.get('version'):
                issues.append(dict(item_id=ident, issue='Online evidence requires HTTPS URL, verification date and version'))
        elif ref.get('source_id'):
            metadata_path = CATALOG_ROOT / 'sources' / str(ref['source_id']) / 'metadata.json'
            if not metadata_path.is_file():
                issues.append(dict(item_id=ident, issue='Evidence source_id does not resolve to the local source catalog'))
                continue
            try:
                metadata = read(metadata_path)
                full_path = metadata_path.parent / 'revisions' / metadata['original_sha256'] / 'full.md'
            except (KeyError, TypeError, json.JSONDecodeError):
                issues.append(dict(item_id=ident, issue='Evidence source_id has invalid catalog metadata'))
                continue
            if not full_path.is_file():
                issues.append(dict(item_id=ident, issue='Evidence source_id lacks an immutable local full document'))
            elif ref.get('sha256') and hashlib.sha256(full_path.read_bytes()).hexdigest() != ref['sha256']:
                issues.append(dict(item_id=ident, issue='Evidence source_id immutable document hash mismatch'))
        else:
            issues.append(dict(item_id=ident, issue='Evidence requires a source_id, URL or local snapshot'))
    return issues


def _phase_zero_route(candidate, state):
    if not isinstance(candidate, dict):
        return None, 'Route candidate must be an object'
    policy = read(CATALOG_ROOT / 'config/phase-zero.json')
    identity_fields = tuple(policy.get('route_identity_fields', ()))
    if identity_fields != IDENTITY:
        return None, 'Phase zero route identity policy differs from the engine identity contract'
    required = ('id', 'status', 'rationale', 'evidence', *identity_fields)
    if any(key not in candidate for key in required):
        return None, 'Route candidate lacks an explicit canonical identity field'
    if any(candidate.get(key) in (None, '') for key in required):
        nullable = {'country', 'agency', 'role', 'round'}
        if any(candidate.get(key) in (None, '') for key in required if key not in nullable):
            return None, 'Route candidate lacks identity, status, rationale or evidence'
    for key in ('country', 'agency', 'role', 'round'):
        if candidate[key] is not None and (not isinstance(candidate[key], str) or not candidate[key].strip()):
            return None, 'Optional route identity fields must be explicit null or nonempty text'
    if candidate['status'] not in ('candidate', 'verified', 'rejected'):
        return None, 'Unknown route candidate status'
    if candidate['year'] != state['year']:
        return None, 'Route candidate annuality differs from idea lab'
    routes = read(CATALOG_ROOT / 'config/actions.json')
    route = next((row for row in routes if row['code'] == candidate['action']), None)
    if not route or brain.route_program(route) != candidate['program'] or candidate['sector'] not in route['sectors']:
        return None, 'Route candidate does not match the action registry'
    if candidate['status'] == 'verified' and candidate.get('current_call_verified') is not True:
        return None, 'Verified route requires a dated current-call verification'
    return route, None


def validate_phase_zero(data, state, path):
    expected = phase_zero_template(state)
    issues, unresolved = [], []
    if not isinstance(data, dict):
        return {'valid': False, 'ready_for_recommendation': False,
                'issues': [{'item_id': 'root', 'issue': 'Checklist must be an object'}],
                'unresolved_items': []}
    for key in ('schema_version', 'phase', 'scope', 'authority', 'limitations'):
        if data.get(key) != expected[key]:
            issues.append(dict(item_id=key, issue='Phase zero checklist contract changed'))
    axes = data.get('axes')
    if not isinstance(axes, list) or [row.get('id') for row in axes if isinstance(row, dict)] != [row['id'] for row in expected['axes']]:
        issues.append(dict(item_id='axes', issue='All Phase zero axes are required once, in canonical order'))
        axes = axes if isinstance(axes, list) else []
    descriptors = {row['id']: (row['question'], row['allowed_outcomes']) for row in expected['axes']}
    policy = read(CATALOG_ROOT / 'config/phase-zero.json')
    proceed = policy['proceed_requires']
    for row in axes:
        if not isinstance(row, dict):
            issues.append(dict(item_id='axes', issue='Each axis must be an object')); continue
        ident = row.get('id', 'unknown')
        descriptor = descriptors.get(ident)
        if not descriptor or row.get('question') != descriptor[0] or row.get('allowed_outcomes') != descriptor[1]:
            issues.append(dict(item_id=ident, issue='Axis question or allowed outcomes changed'))
        status = row.get('outcome')
        if not descriptor or status not in set(descriptor[1])|{'unassessed'}:
            issues.append(dict(item_id=ident, issue='Unknown Phase zero outcome')); continue
        acceptable = proceed.get(ident)
        acceptable = set(acceptable if isinstance(acceptable,list) else [acceptable])
        if status not in acceptable:
            unresolved.append(ident)
        if status != 'unassessed' and not row.get('owner'):
            issues.append(dict(item_id=ident, issue='Assessed axis requires an owner'))
        if status != 'unassessed' and not row.get('reason'):
            issues.append(dict(item_id=ident, issue='Assessed axis requires a reason'))
        if status not in acceptable and status != 'unassessed' and not all(row.get(key) for key in ('reason', 'evidence_plan', 'owner', 'design_implication')):
            issues.append(dict(item_id=ident, issue='Open gap requires reason, plan, owner and design implication'))
        if status in acceptable and not row.get('evidence'):
            issues.append(dict(item_id=ident, issue='PROCEED-compatible outcome requires evidence'))
        issues.extend(_phase_zero_reference_issues(row.get('evidence', []), ident, path))
    candidates = data.get('route_candidates')
    if not isinstance(candidates, list):
        issues.append(dict(item_id='route_candidates', issue='Route candidates must be a list')); candidates = []
    ids = []
    for candidate in candidates:
        ident = candidate.get('id', 'unknown') if isinstance(candidate, dict) else 'unknown'
        ids.append(ident)
        _, problem = _phase_zero_route(candidate, state)
        if problem: issues.append(dict(item_id=ident, issue=problem))
        if isinstance(candidate, dict):
            issues.extend(_phase_zero_reference_issues(candidate.get('evidence', []), ident, path))
            if candidate.get('status') == 'verified' and not candidate.get('evidence'):
                issues.append(dict(item_id=ident, issue='Verified route requires localized current-call evidence'))
    if len(ids) != len(set(ids)):
        issues.append(dict(item_id='route_candidates', issue='Route candidate IDs must be unique'))
    if not candidates:
        unresolved.append('route_candidates')
    return {'valid': not issues, 'ready_for_recommendation': not issues,
            'issues': issues, 'unresolved_items': sorted(set(unresolved))}


def validate_phase_zero_decision(data, checklist_data, state, path):
    issues = []
    required = ('schema_version', 'version', 'authority', 'recommendation', 'summary',
                'strengths', 'reasons', 'changes_required', 'unknowns', 'route_handoff')
    if not isinstance(data, dict) or any(key not in data for key in required):
        return {'valid': False, 'issues': [{'item_id': 'decision', 'issue': 'Incomplete Phase zero decision'}]}
    if data.get('schema_version') != 'phase-zero-decision-v1' or data.get('authority') != 'assistant-recommendation-pending-human-decision':
        issues.append(dict(item_id='decision', issue='Decision schema or authority changed'))
    if not isinstance(data.get('version'), int) or data['version'] < 1:
        issues.append(dict(item_id='version', issue='Decision version must be a positive integer'))
    if data.get('recommendation') not in ('PROCEED', 'REFINE', 'PIVOT', 'STOP'):
        issues.append(dict(item_id='recommendation', issue='Unknown Phase zero recommendation'))
    if not isinstance(data.get('summary'), str) or not data['summary'].strip():
        issues.append(dict(item_id='summary', issue='Recommendation needs a summary'))
    for key in ('strengths', 'reasons', 'changes_required', 'unknowns'):
        if not isinstance(data.get(key), list) or any(not isinstance(v, str) or not v.strip() for v in data.get(key, [])):
            issues.append(dict(item_id=key, issue='Decision narratives must be lists of nonempty text'))
    if not data.get('reasons'):
        issues.append(dict(item_id='reasons', issue='Recommendation needs explicit reasons'))
    forbidden = {'score', 'points', 'official_score', 'funding_probability', 'success_probability'}
    stack = [data]
    while stack:
        value = stack.pop()
        if isinstance(value, dict):
            if forbidden.intersection(value):
                issues.append(dict(item_id='decision', issue='Phase zero cannot contain official scores or funding probabilities'))
            stack.extend(value.values())
        elif isinstance(value, list): stack.extend(value)
    handoff = data.get('route_handoff')
    if data.get('recommendation') == 'PROCEED':
        if not isinstance(handoff, dict):
            issues.append(dict(item_id='route_handoff', issue='PROCEED requires one verified route handoff'))
        else:
            route, problem = _phase_zero_route({**handoff, 'id': handoff.get('candidate_id'), 'status': 'verified',
                                                'rationale': handoff.get('rationale'), 'evidence': handoff.get('evidence', [])}, state)
            if problem: issues.append(dict(item_id='route_handoff', issue=problem))
            verified = [row for row in checklist_data.get('route_candidates', [])
                        if row.get('status') == 'verified' and row.get('id') == handoff.get('candidate_id')]
            if len(verified) != 1 or any(key not in handoff or handoff.get(key) != verified[0].get(key) for key in IDENTITY):
                issues.append(dict(item_id='route_handoff', issue='Handoff must match one verified checklist candidate'))
            else:
                issues.extend(_phase_zero_reference_issues(handoff.get('evidence', []), 'route_handoff', path))
                if handoff.get('evidence') != verified[0].get('evidence'):
                    issues.append(dict(item_id='route_handoff', issue='Handoff evidence must exactly match the selected verified candidate'))
            if route is not None and handoff.get('current_call_verified') is not True:
                issues.append(dict(item_id='route_handoff', issue='PROCEED requires current-call verification'))
        assessment = validate_phase_zero(checklist_data, state, path)
        if assessment['unresolved_items']:
            issues.append(dict(item_id='recommendation', issue='PROCEED cannot leave Phase zero axes or routing unresolved'))
        if data.get('changes_required') or data.get('unknowns'):
            issues.append(dict(item_id='recommendation', issue='PROCEED cannot retain required changes or material unknowns'))
    elif handoff is not None:
        issues.append(dict(item_id='route_handoff', issue='Only PROCEED may carry a dossier handoff'))
    return {'valid': not issues, 'issues': issues}


def source_ref(source_id, pages=None):
    """Locate actual immutable documents; never invent an extraction path."""
    base = CATALOG_ROOT / 'sources' / source_id
    meta = read(base / 'metadata.json')
    revision = base / 'revisions' / meta['original_sha256']
    if pages:
        refs = []
        for page in range(pages[0], pages[1] + 1):
            matches = list((revision / 'pages').glob(f'*{page:04d}.md'))
            if len(matches) != 1:
                raise ValueError(f'Missing immutable page {source_id}:p{page:04d}')
            refs.append(dict(locator=f'p{page:04d}', path=str(matches[0]),
                             sha256=hashlib.sha256(matches[0].read_bytes()).hexdigest()))
    else:
        full = revision / 'full.md'
        if not full.is_file():
            raise ValueError('Missing immutable supporting source ' + source_id)
        refs = [dict(locator='full-document', path=str(full),
                     sha256=hashlib.sha256(full.read_bytes()).hexdigest())]
    return dict(source_id=source_id, original_sha256=meta['original_sha256'],
                version=meta.get('version'), url=meta.get('url'), references=refs)


def template(state, phase, award_context=None):
    routes = read(CATALOG_ROOT / 'config/actions.json')
    route = next((r for r in routes if r['code'] == state['action']), None)
    if not route or brain.route_program(route) != state['program'] or state['sector'] not in route['sectors']:
        raise ValueError('Checklist requires an exact applicable action/sector/program route')
    if state['year'] != 2026:
        raise ValueError('Only the 2026 corpus is indexed; no annuality substitution')
    phases = read(CATALOG_ROOT / 'config/phase-validation.json')['phases']
    if phase not in phases:
        raise ValueError('Unknown checklist phase')
    checks, profiles = stage_gate.compliance(state, phase)
    routing = next(r for r in read(CATALOG_ROOT / 'config/compliance/routing-coverage.json')['actions']
                   if r['action'] == state['action'] and r['program'] == state['program'])
    sections = []

    def section(ident, kind, sources, task):
        sections.append(dict(section_id=ident, kind=kind, sources=sources, task=task,
                             read_locators=[], derived_check_ids=[], **outcome()))

    psid = 'esc-programme-2026' if state['program'] == 'ESC' else 'programme-2026'
    esid = 'esc-expert-2026' if state['program'] == 'ESC' else 'expert-2026'
    section('action-section', 'programme', [source_ref(psid, route['programme_pages'])],
            'Read every listed physical PDF page and adjacent pages if a passage continues; extract all applicable rules and criteria.')
    generals = route.get('general_sources', []) if state['program'] == 'ESC' else [
        {'id': psid, 'pages': [4, 36]}, {'id': psid, 'pages': [413, 442]}]
    for n, source in enumerate(generals):
        section(f'general-conditions-{n + 1}', 'general', [source_ref(source['id'], source['pages'])],
                'Read full listed general conditions; classify applicability and create localized extension checks.')
    if route.get('expert_pages'):
        section('expert-action', 'expert', [source_ref(esid, route['expert_pages'])],
                'Read the exact action assessment grid; do not convert qualitative criteria into eligibility rules.')
        if state['program'] == 'ERASMUS':
            section('expert-general', 'expert', [source_ref(esid, [4, 21])],
                    'Read general assessment instructions and distinguish scores from eligibility.')
    else:
        section('expert-scope', 'expert', [],
                'Document the applicable assessment source or non-applicability; the indexed expert guide does not cover this route.')
    for source in read(CATALOG_ROOT / 'config/sources.json'):
        kind = source['kind']
        if kind not in ('national-priorities', 'national-guidance', 'national-provisions', 'quality-standards', 'funding-handbook'):
            continue
        if kind.startswith('national-') and route['agency'] == 'EACEA':
            continue
        meta = dict(source=source['id'], program=source.get('program', 'ERASMUS'),
                    sectors=source['sectors'], actions=source['actions'])
        if brain.applicable(meta, state['action'], state['sector'], state['program']):
            section('support-' + source['id'], kind, [source_ref(source['id'])],
                    'Read the complete applicable supporting document, confirm scope and extract additional checks.')
    for ident, task in (
        ('current-call', 'Verify current guide/corrigenda, round, deadline, destination and call rules against dated official sources.'),
        ('national-current', 'Verify competent authority and current territory/round provisions; explain and evidence non-applicability for centralised or non-national routes.'),
        ('current-form', 'Acquire the actual current form; map every question, repeated instance, limit, required upload and conditional field.'),
        ('coverage-extension', 'Build the complete project-specific requirements matrix from all readings; reference extension checks and preserve unresolved gaps.')):
        section(ident, 'current-verification', [], task)
    data = dict(schema_version='project-checklist-v1', scope={k: state.get(k) for k in IDENTITY},
                phase=phase, baseline_coverage=copy.deepcopy(routing), profile_coverage=profiles,
                limitation='Partial reusable baseline; neither a substantive eligibility verdict nor certification of all supported routes.',
                checks=[dict(check_id=c['id'], baseline=copy.deepcopy(c), **outcome()) for c in checks],
                extensions=[], section_coverage=sections, coverage_gaps=list(routing.get('gaps', [])))
    if phase in IDEA_PHASES:
        import award_criteria
        data['award_coverage'] = award_criteria.select(state, award_context, CATALOG_ROOT)
    return data


def award_context(path):
    """Read a selector, never confirm it or change the common project model."""
    model = path / 'project.json'
    metadata = read(model).get('metadata', {}) if model.is_file() else {}
    return metadata if isinstance(metadata, dict) else {}


def project(root, identifier):
    path = resolve_project(root, identifier)
    if not (path / 'state.json').is_file():
        raise ValueError('Initialize the real project dossier with workflow.py first')
    return path, read(path / 'state.json')


def bounded_file(path, value):
    candidate = Path(value)
    candidate = (candidate if candidate.is_absolute() else path / candidate).resolve()
    if not candidate.is_relative_to(path.resolve()):
        raise ValueError('Checklist path outside project dossier')
    relative = candidate.relative_to(path.resolve())
    if not relative.parts or relative.parts[0] not in ('research', 'stages') or candidate.suffix != '.json':
        raise ValueError('Checklist must be a JSON file in research/ or stages/')
    return candidate


def initialize(root, identifier, phase, output=None):
    path, state = project(root, identifier)
    target = bounded_file(path, output or f'research/checklist-{phase}.json')
    data = template(state, phase, award_context(path))
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('x') as stream:
        stream.write(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    return target


def validate(data, state, path):
    """Keep validity separate from unresolved checks and substantive independent review."""
    if not isinstance(data, dict) or not isinstance(data.get('phase'), str):
        raise ValueError('Checklist must be an object with a string phase')
    issues = []
    unresolved = []
    reading_todo = []
    expected = template(state, data.get('phase'), award_context(path))

    def issue(ident, text):
        issues.append(dict(item_id=ident, issue=text))

    def refs_ok(ident, refs, artifacts=False):
        if not isinstance(refs, list) or not refs:
            issue(ident, 'Localized evidence/artifact list required')
            return
        for ref in refs:
            if not isinstance(ref, dict) or not ref.get('locator') or (not artifacts and not ref.get('source_id')):
                issue(ident, 'References require locator and evidence source_id')
                continue
            value = ref.get('path') or ref.get('source_path_or_url') or ref.get('url')
            if not isinstance(value, str) or not value:
                issue(ident, 'Reference requires a real path or URL')
            elif str(value).startswith('https://') and not artifacts:
                if not ref.get('verified_at') or not ref.get('version'):
                    issue(ident, 'Online evidence requires verification date and version')
            else:
                candidate = Path(value)
                if not candidate.is_absolute():
                    base = CATALOG_ROOT if not artifacts and candidate.parts and candidate.parts[0] == 'sources' else path
                    candidate = base / candidate
                candidate = candidate.resolve()
                allowed = candidate.is_relative_to(path.resolve()) or (not artifacts and candidate.is_relative_to(CATALOG_ROOT / 'sources'))
                if not allowed or not candidate.is_file():
                    issue(ident, 'Reference missing or outside permitted dossier/source corpus')
                elif ref.get('sha256') and hashlib.sha256(candidate.read_bytes()).hexdigest() != ref['sha256']:
                    issue(ident, 'Reference hash mismatch')

    def result(ident, row, artifacts=True):
        status = row.get('status')
        if ident in ('current-form','shared-form') and data.get('phase') in FORM_REQUIRED_PHASES and status=='not-applicable':
            issue(ident, 'Current form cannot be not-applicable in field planning, writing or final review phases')
        if not isinstance(status, str) or status not in STATUSES:
            issue(ident, 'Unknown status')
        if status in ('to-verify', 'not-satisfied'):
            unresolved.append(ident)
        if status in ('satisfied', 'not-satisfied', 'not-applicable'):
            if not row.get('owner'):
                issue(ident, 'Resolved/assessed status requires owner')
            refs_ok(ident, row.get('evidence'))
            if artifacts and status != 'not-applicable':
                refs_ok(ident, row.get('artifact_locators'), True)
        if status == 'not-applicable' and not row.get('reason'):
            issue(ident, 'Not-applicable requires scope-specific reason and evidence')
        if status == 'not-satisfied' and not all(row.get(k) for k in ('discrepancy', 'severity', 'required_fix')):
            issue(ident, 'Not-satisfied requires discrepancy, severity and required_fix')

    if data.get('phase') in IDEA_PHASES:
        import award_criteria
        award_issues, award_unassessed = award_criteria.validate(data.get('award_coverage'), expected['award_coverage'])
        for text in award_issues:
            issue('award_coverage', text)
        unresolved.extend('award:' + ident for ident in award_unassessed)
        for row in (data.get('award_coverage') or {}).get('entries', []):
            if isinstance(row, dict) and row.get('evidence'):
                refs_ok('award:' + row.get('id', 'unknown'), row['evidence'])

    for key in ('schema_version', 'scope', 'baseline_coverage', 'profile_coverage', 'limitation'):
        if data.get(key) != expected[key]:
            issue(key, 'Checklist scope/baseline changed; initialize a new version for the current route')
    rows = data.get('checks', [])
    if not isinstance(rows, list):
        rows = []; issue('checks', 'Checks must be a list')
    if any(not isinstance(r, dict) for r in rows):
        issue('checks', 'Each check must be an object')
        rows = [r for r in rows if isinstance(r, dict)]
    if [r.get('check_id') for r in rows] != [r['check_id'] for r in expected['checks']]:
        issue('checks', 'Applicable baseline checks omitted, reordered or duplicated')
    baseline = {r['check_id']: r['baseline'] for r in expected['checks']}
    ids = set(baseline)
    for row in rows:
        ident = row.get('check_id', 'unknown')
        if not isinstance(ident, str):
            issue('checks', 'Check ID must be a string')
            continue
        if row.get('baseline') != baseline.get(ident):
            issue(ident, 'Reusable check content or source references modified')
        result(ident, row)
    extensions = data.get('extensions', [])
    if not isinstance(extensions, list):
        extensions = []; issue('extensions', 'Extensions must be a list')
    if any(not isinstance(r, dict) for r in extensions):
        issue('extensions', 'Each extension must be an object')
        extensions = [r for r in extensions if isinstance(r, dict)]
    for row in extensions:
        ident = row.get('check_id', '')
        if not isinstance(ident, str):
            issue('extensions', 'Extension ID must be a string')
            continue
        if not re.fullmatch(r'project-[a-z0-9-]+', ident) or ident in ids:
            issue(ident, 'Extension requires a unique project- check ID')
        ids.add(ident)
        if row.get('classification') not in ('requirement', 'award-criterion', 'recommendation', 'good-practice') or not all(row.get(k) for k in ('check', 'applicability', 'owner')):
            issue(ident, 'Extension requires classification, check, applicability and owner')
        if row.get('scope') != expected['scope']:
            issue(ident, 'Extension requires the exact project scope')
        refs_ok(ident, row.get('sources'))
        result(ident, row)
    sections = data.get('section_coverage', [])
    if not isinstance(sections, list):
        sections = []; issue('section_coverage', 'Section coverage must be a list')
    if any(not isinstance(r, dict) for r in sections):
        issue('section_coverage', 'Each section must be an object')
        sections = [r for r in sections if isinstance(r, dict)]
    if [r.get('section_id') for r in sections] != [r['section_id'] for r in expected['section_coverage']]:
        issue('section_coverage', 'Required route/current-source coverage rows omitted, reordered or duplicated')
    required = {r['section_id']: r for r in expected['section_coverage']}
    for row in sections:
        ident = row.get('section_id', 'unknown')
        if not isinstance(ident, str):
            issue('section_coverage', 'Section ID must be a string')
            continue
        original = required.get(ident)
        if original and any(row.get(k) != original[k] for k in ('sources', 'task', 'kind')):
            issue(ident, 'Required coverage sources/pages/task modified')
        result(ident, row, False)
        known = {s['source_id'] + ':' + ref['locator'] for s in (original or {}).get('sources', []) for ref in s['references']}
        read_locators = row.get('read_locators', [])
        if not isinstance(read_locators, list) or any(not isinstance(v, str) for v in read_locators) or not set(read_locators).issubset(known):
            issue(ident, 'Read locators must reference required source pages/documents')
        elif row.get('status') == 'satisfied' and set(read_locators) != known:
            issue(ident, 'Satisfied coverage requires reading every required page/document')
        if isinstance(read_locators, list) and all(isinstance(v, str) for v in read_locators):
            reading_todo.append(dict(section_id=ident, status=row.get('status'), owner=row.get('owner'),
                                     remaining_read_locators=sorted(known - set(read_locators)),
                                     task=(original or {}).get('task')))
        derived = row.get('derived_check_ids', [])
        if not isinstance(derived, list) or any(not isinstance(check_id, str) or check_id not in ids for check_id in derived):
            issue(ident, 'Derived check IDs must exist in baseline or extension matrix')
        if ident == 'coverage-extension' and row.get('status') == 'satisfied' and not extensions:
            issue(ident, 'Partial baseline requires a source-grounded project-specific extension matrix')
    gaps = data.get('coverage_gaps')
    if not isinstance(gaps, list) or any(not isinstance(g, str) or not g.strip() for g in gaps):
        issue('coverage_gaps', 'Coverage gaps must be a list of explicit unresolved descriptions')
    return dict(valid=not issues, ready_for_independent_review=not issues and not unresolved and not gaps,
                issues=issues, unresolved_items=unresolved, coverage_gaps=gaps,
                reading_todo=reading_todo,
                baseline_coverage=expected['baseline_coverage']['status'],
                limitation=expected['limitation'])


def main():
    parser = argparse.ArgumentParser(description='Create and validate project-specific, evidence-based checklists. Checks cover requirements, not eligibility.')
    sub = parser.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init', help='Create a checklist template for a project phase.')
    init.add_argument('project', help='Project dossier identifier.')
    init.add_argument('--phase', required=True, help='Project phase covered by the checklist.')
    init.add_argument('--output', help='Output JSON path relative to the project dossier.')
    check = sub.add_parser('validate', help='Validate a project checklist.')
    check.add_argument('project', help='Project dossier identifier.')
    check.add_argument('--input', required=True, help='Checklist JSON path relative to the project dossier.')
    args = parser.parse_args()
    if args.command == 'init':
        print(initialize(ROOT, args.project, args.phase, args.output))
    else:
        path, state = project(ROOT, args.project)
        result = validate(read(bounded_file(path, args.input)), state, path)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result['valid'] else 1
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, KeyError, FileNotFoundError, FileExistsError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
