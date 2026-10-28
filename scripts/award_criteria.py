#!/usr/bin/env python3
"""Route-specific award checklists: methodological idea review, never official scoring."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MATURITY = {'unassessed', 'evidence-supported', 'plausible', 'research-needed',
            'redesign-needed', 'not-applicable'}
OUTCOME_FIELDS = ('maturity', 'evidence', 'reason', 'evidence_plan', 'owner')
MODES = {'points', 'pass-fail', 'qualitative', 'no-new-award-rubric'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def catalog(root=ROOT):
    routes = json.loads((root / 'config/actions.json').read_text())
    route_map = {r['code']: r for r in routes}
    profiles, files, ids = [], [], set()
    for path in sorted((root / 'config/award-criteria').glob('*-2026.json')):
        data = json.loads(path.read_text())
        if data.get('schema_version') != 'award-idea-profiles-v1' or data.get('year') != 2026:
            raise ValueError('Invalid award profile schema/year: ' + str(path))
        files.append({'path': str(path.relative_to(root)), 'sha256': digest(path)})
        for profile in data.get('profiles', []):
            ident = profile.get('id')
            if not isinstance(ident, str) or not ident or ident in ids:
                raise ValueError('Duplicate/missing award profile identity')
            ids.add(ident)
            if profile.get('scoring_mode') not in MODES or not profile.get('source_refs'):
                raise ValueError('Award profile requires explicit mode and sources: ' + ident)
            if not isinstance(profile.get('selector', {}), dict):
                raise ValueError('Award selector must be an object: ' + ident)
            for code in profile.get('routes', []):
                if code not in route_map or route_map[code].get('program', 'ERASMUS') != data['program']:
                    raise ValueError('Award profile outside route/program: ' + ident)
            if not profile.get('routes'):
                raise ValueError('Award profile without routes: ' + ident)
            sectors=profile.get('sectors')
            if sectors is not None and (not isinstance(sectors,list) or not sectors or any(not isinstance(x,str) for x in sectors) or any(set(sectors)-set(route_map[code]['sectors']) for code in profile['routes'])):
                raise ValueError('Invalid award variant sector scope: '+ident)
            allowed=profile.get('allowed_context',{})
            if not isinstance(allowed,dict) or any(not isinstance(k,str) or not isinstance(values,list) or not values or any(not isinstance(v,str) for v in values) for k,values in allowed.items()):
                raise ValueError('Invalid award context value contract: '+ident)
            if not isinstance(profile.get('context_to_verify',[]),list) or any(not isinstance(k,str) or not k for k in profile.get('context_to_verify',[])):
                raise ValueError('Invalid context verification field list: '+ident)
            seen = set()
            for criterion in profile.get('criteria', []):
                if not criterion.get('id') or not criterion.get('label_en') or not criterion.get('source_refs'):
                    raise ValueError('Criterion lacks identity/label/source: ' + ident)
                points = criterion.get('max_points')
                if points is not None and (type(points) not in (int, float) or points < 0):
                    raise ValueError('Invalid criterion maximum: ' + ident)
                if not criterion.get('checks'):
                    raise ValueError('Criterion lacks idea checks: ' + ident)
            if profile['scoring_mode'] == 'no-new-award-rubric' and profile.get('criteria'):
                raise ValueError('Allocation cannot invent an award rubric: ' + ident)
            for check in profile_checks(profile):
                for field in ('id', 'official_focus_it', 'idea_question_it', 'evidence_at_idea_it',
                              'later_verification_it', 'design_implication_it', 'applicability_it'):
                    if not isinstance(check.get(field), str) or not check[field].strip():
                        raise ValueError('Missing checklist field ' + field + ': ' + ident)
                if check['id'] in seen or not check.get('source_refs'):
                    raise ValueError('Duplicate/unlocalized idea check: ' + ident)
                seen.add(check['id'])
            all_refs = profile['source_refs'] + [ref for c in profile.get('criteria', [])
                                                  for ref in c['source_refs']] + [ref for c in profile_checks(profile)
                                                                               for ref in c['source_refs']]
            source_map = {s['id']: s for s in json.loads((root / 'config/sources.json').read_text())}
            for ref in all_refs:
                pages = ref.get('pages')
                source = source_map.get(ref.get('source_id'))
                if not source or source.get('kind') in ('user-template', 'methodological-resource'):
                    raise ValueError('Award criterion requires a grant/assessment source: ' + ident)
                if not isinstance(pages, list) or len(pages) != 2 or any(type(p) is not int or p < 1 for p in pages) or pages[0] > pages[1]:
                    raise ValueError('Award source requires physical PDF page interval: ' + ident)
            profiles.append({**profile, 'program': data['program'], 'catalog_path': str(path.relative_to(root))})
    covered = {code for p in profiles for code in p['routes']}
    return {'profiles': profiles, 'files': files, 'routes': routes,
            'missing_routes': sorted(set(route_map) - covered)}


def profile_checks(profile):
    return [check for c in profile.get('criteria', []) for check in c['checks']] + profile.get('idea_controls', [])


def select(state, context=None, root=ROOT):
    if state.get('year') != 2026:
        raise ValueError('No silent award checklist annuality substitution')
    data = catalog(root)
    candidates = [p for p in data['profiles'] if state['action'] in p['routes'] and p['program'] == state['program']]
    supplied = context or {}
    for key in ('program','year','action','sector','country','agency','role','round'):
        if state.get(key) not in (None, '') and supplied.get(key) not in (None, '') and state[key] != supplied[key]:
            raise ValueError('Award selector conflicts with project state: ' + key)
    context = {**{k: state.get(k) for k in ('program','year','action','sector','country','agency','role','round')}, **supplied}
    variant = context.get('award_criteria_variant')
    matches = [p for p in candidates if not p.get('selector') or
               all(context.get('award_criteria_variant' if k == 'variant' else k) == v
                   for k, v in p['selector'].items())]
    # An explicit variant must never silently fall back to an unselected profile.
    if variant is not None:
        matches = [p for p in matches if p.get('selector', {}).get('variant') == variant]
    route=next((r for r in data['routes'] if r['code']==state['action'] and r.get('program','ERASMUS')==state['program']),None)
    if not route:raise ValueError('Award selection requires exact registered action/program')
    chosen = matches[0] if len(matches) == 1 else None
    status = 'selected' if chosen else ('missing-profile' if not candidates else 'selector-required')
    missing = [k for k in chosen.get('context_required', []) if context.get(k) in (None, '', [])] if chosen else []
    if context.get('sector') in (None,'',[]):missing.append('sector')
    conflicts=[]
    if context.get('sector') not in (None,'',[]) and context['sector'] not in route['sectors']:
        conflicts.append('sector outside registered route')
    if chosen:
        if chosen.get('sectors') and context.get('sector') not in (None,'',[]) and context['sector'] not in chosen['sectors']:
            conflicts.append('sector outside selected rubric variant')
        for key,values in chosen.get('allowed_context',{}).items():
            if context.get(key) not in (None,'',[]) and context[key] not in values:
                conflicts.append(key+' outside selected rubric context')
    if route.get('roles') and context.get('role') not in (None,'',[]) and context['role'] not in route['roles']:
        conflicts.append('role outside registered route')
    if missing and chosen:
        status = 'context-required'
    if conflicts:
        status = 'context-conflict'
    entries = []
    if chosen:
        for criterion in chosen.get('criteria', []):
            for check in criterion['checks']:
                entries.append({**copy.deepcopy(check), 'kind': 'award-criterion',
                                'criterion_id': criterion['id'], 'criterion_label_en': criterion['label_en'],
                                'criterion_max_points': criterion.get('max_points'), **outcome()})
        for check in chosen.get('idea_controls', []):
            entries.append({**copy.deepcopy(check), 'kind': 'non-award-prerequisite-or-allocation',
                            'criterion_id': None, 'criterion_label_en': None,
                            'criterion_max_points': None, **outcome()})
        for key in chosen.get('context_to_verify',[]):
            entries.append(context_verification_row(chosen,key,context.get(key)))
    return {'schema_version': 'award-idea-coverage-v1', 'route': state['action'],
            'program': state['program'], 'year': 2026, 'selection_status': status,
            'selected_profile': chosen['id'] if chosen else None,
            'candidate_profiles': [{'id': p['id'], 'selector': p.get('selector', {}),
                                    'label_it': p.get('selector_label_it', p['id']), 'sectors':p.get('sectors',route['sectors']), 'allowed_context':copy.deepcopy(p.get('allowed_context',{}))} for p in candidates],
            'missing_context': sorted(set(missing)), 'context_conflicts':conflicts,
            'context_gaps':[k for k in chosen.get('context_to_verify',[]) if context.get(k) in (None,'',[])] if chosen else [], 'catalog_files': [f for f in data['files']
                                                        if f['path'] in {p['catalog_path'] for p in candidates}],
            'selected_catalog_path': chosen['catalog_path'] if chosen else None,
            'source_refs': complete_source_refs(chosen) if chosen else [],
            'scoring_mode': chosen['scoring_mode'] if chosen else None,
            'scoring': copy.deepcopy(chosen.get('scoring', {})) if chosen else {},
            'coverage_limits': copy.deepcopy(chosen.get('coverage', {}).get('limits', [])) if chosen else [],
            'evaluation_policy': 'Idea maturity and credible verification plan; not final satisfaction, official scores or funding probability',
            'entries': entries}


def outcome():
    return {'maturity': 'unassessed', 'evidence': [], 'reason': '', 'evidence_plan': '', 'owner': ''}


def context_verification_row(profile,key,value):
    """Method-only research row; a common rubric can be reviewed with open context."""
    return {'id':profile['id']+'.context.'+key, 'kind':'method-context-verification',
            'criterion_id':None, 'criterion_label_en':None, 'criterion_max_points':None,
            'official_focus_it':'Applicability context for conditional subpoints; a methodological check, not a new award criterion.',
            'idea_question_it':'Which '+key+' context applies, or how and when will it be verified?',
            'evidence_at_idea_it':'A choice or datum with observed provenance, or a hypothesis with an owner and a credible verification plan.',
            'later_verification_it':'Before finalising design, finance, and answers, verify the actual call/topic, scope, and conditions.',
            'design_implication_it':'If the context is incompatible, reopen the premise and correct the proposal; do not invent confirmation.',
            'applicability_it':'The common rubric is already determined; a non-selector detail may remain explicit research during the idea phase.',
            'source_refs':complete_source_refs(profile), 'context_key':key, 'current_context_value':value,
            **outcome()}


def complete_source_refs(profile):
    """Include conditional/prerequisite pages, even outside the main rubric."""
    refs = profile['source_refs'] + [r for c in profile.get('criteria', [])
                                      for r in c['source_refs']] + [r for c in profile_checks(profile)
                                                                   for r in c['source_refs']]
    distinct = {(r['source_id'], *r['pages']) for r in refs}
    return [{'source_id': sid, 'pages': [first, last]}
            for sid, first, last in sorted(distinct)]


def validate(coverage, expected):
    issues, unassessed = [], []
    if not isinstance(coverage, dict):
        return ['Award coverage missing or not an object'], []
    for key in expected:
        if key != 'entries' and coverage.get(key) != expected[key]:
            issues.append('Award coverage descriptor changed: ' + key)
    rows = coverage.get('entries')
    if not isinstance(rows, list):
        return issues + ['Award coverage entries must be a list'], []
    if [r.get('id') for r in rows if isinstance(r, dict)] != [r['id'] for r in expected['entries']]:
        issues.append('Official rubric subpoints omitted, reordered or duplicated')
    lookup = {r['id']: r for r in expected['entries']}
    for row in rows:
        if not isinstance(row, dict):
            issues.append('Award entry must be an object'); continue
        baseline = lookup.get(row.get('id'))
        if not baseline:
            issues.append('Unknown award entry'); continue
        if {k: v for k, v in row.items() if k not in OUTCOME_FIELDS} != {k: v for k, v in baseline.items() if k not in OUTCOME_FIELDS}:
            issues.append('Award source/check content changed: ' + row['id'])
        if row.get('maturity') not in MATURITY or not isinstance(row.get('evidence'), list):
            issues.append('Invalid idea maturity/evidence: ' + row['id'])
        if row.get('maturity') == 'unassessed':
            unassessed.append(row['id'])
        elif not row.get('owner') or not row.get('reason'):
            issues.append('Assessed idea item requires owner and reason: ' + row['id'])
        elif row['maturity'] == 'research-needed' and not row.get('evidence_plan'):
            issues.append('Idea research gap requires a verification plan: ' + row['id'])
        elif row['maturity'] == 'evidence-supported' and not row['evidence']:
            issues.append('Evidence-supported idea requires actual evidence: ' + row['id'])
    return issues, unassessed


def sources_md(refs):
    return '; '.join(ref['source_id'] + ' PDF ' + str(ref['pages'][0]) +
                     ('–' + str(ref['pages'][1]) if ref['pages'][1] != ref['pages'][0] else '') for ref in refs)


def render_route(code, root=ROOT):
    data = catalog(root); route = next((r for r in data['routes'] if r['code'] == code), None)
    if not route:
        raise ValueError('Unknown exact award checklist route')
    profiles = [p for p in data['profiles'] if code in p['routes']]
    lines = ['---', 'program: ' + route.get('program', 'ERASMUS'), 'action: ' + code,
             'year: 2026', 'status: source-grounded-operational-checklist', '---',
             '# Award criteria — idea checklist: ' + code, '',
             '2026 corpus; ' + route.get('program', 'ERASMUS') + ', sectors ' + ', '.join(route['sectors']) + ', agency ' + route['agency'] + '.', '',
             'Route-specific methodological checklist. At the idea stage, assess relevance and plausibility, available evidence, and plans for addressing gaps; do not assign official scores or claim that all final criteria are satisfied. Before applying, verify the call and corrigenda, national provisions, and actual form. Check IDs are internal; PDF page numbers refer to physical pages, starting at 1.', '',
             'For each check, record one outcome: evidence-supported, plausible, research-needed, redesign-needed, or justified not-applicable; retain the evidence, rationale, plan, and owner. An unresolved selector or incompatible sector/role prevents the gate from using the selected rubric. Non-selector details may remain open research when accompanied by a credible plan.', '']
    for profile in profiles:
        lines += ['## ' + profile.get('selector_label_it', profile['id']), '',
                  'Profile `' + profile['id'] + '`. Selector: `' + json.dumps(profile.get('selector', {}), ensure_ascii=False) + '`; no default to the first variant.', '',
                  'Scoring mode: ' + profile['scoring_mode'] + '. ' + profile.get('scoring', {}).get('note_en', profile.get('scoring', {}).get('note_it', '')), '',
                  'Sources: ' + sources_md(profile['source_refs']) + '.', '']
        scoring = profile.get('scoring', {})
        if scoring.get('total_max_points') is not None:
            lines += ['Final application: maximum ' + str(scoring['total_max_points']) +
                      '; overall threshold ' + str(scoring.get('total_minimum_points')) +
                      '. Criterion thresholds and tie-break rules remain as specified above; do not score at the idea stage.', '']
        if profile.get('context_required'):
            lines += ['Required context: ' + ', '.join(profile['context_required']) + '.', '']
        if profile.get('context_to_verify'):
            lines += ['Context to verify: '+', '.join(profile['context_to_verify'])+'. At the idea stage, the common rubric may be selected while these details remain open; complete the methodological checks with an owner, rationale, and credible plan. These are not new award criteria.', '']
        if profile.get('sectors'):
            lines += ['Rubric sectors: '+', '.join(profile['sectors'])+'. Do not apply this variant to other sectors.', '']
        if profile.get('allowed_context'):
            lines += ['Allowed context values: `'+json.dumps(profile['allowed_context'],ensure_ascii=False)+'`. Values outside this scope do not validly select the rubric.', '']
        for criterion in profile.get('criteria', []):
            lines += ['### ' + criterion['label_en'] + (' — massimo ' + str(criterion['max_points']) if criterion.get('max_points') is not None else ''), '',
                      'Sources: ' + sources_md(criterion['source_refs']) + '.', '']
            for check in criterion['checks']:
                lines += render_check(check)
        if profile.get('idea_controls'):
            lines += ['### Prerequisite/allocation checks — not award criteria', '']
            for check in profile['idea_controls']:
                lines += render_check(check)
        for limit in profile.get('coverage', {}).get('limits', []):
            lines += ['Limit: ' + str(limit), '']
    return '\n'.join(lines).rstrip() + '\n'


def render_check(check):
    return ['#### ' + check['id'], '', '- [ ] ' + check['idea_question_it'], '',
            '  Rephrased official focus: ' + check['official_focus_it'],
            '  Scope: ' + check['applicability_it'],
            '  Evidence at idea stage: ' + check['evidence_at_idea_it'],
            '  Later verification: ' + check['later_verification_it'],
            '  Design implication: ' + check['design_implication_it'],
            '  Source: ' + sources_md(check['source_refs']) + '.', '']


def main():
    parser = argparse.ArgumentParser(description='Route-specific award checklists: methodological idea review, never official scoring.')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('catalog')
    show = sub.add_parser('show'); show.add_argument('--action', required=True); show.add_argument('--variant'); show.add_argument('--role'); show.add_argument('--max-chars', type=int, default=8000); show.add_argument('--offset', type=int, default=0)
    export = sub.add_parser('export'); export.add_argument('--output', required=True)
    args = parser.parse_args(); data = catalog()
    if args.command == 'catalog':
        print(json.dumps({'profiles': [{'id': p['id'], 'routes': p['routes'], 'selector': p.get('selector', {})} for p in data['profiles']], 'missing_routes': data['missing_routes']}, ensure_ascii=False, indent=2))
    elif args.command == 'show':
        candidates = [p for p in data['profiles'] if args.action in p['routes']
                      and (not args.variant or p.get('selector', {}).get('variant') == args.variant)
                      and (not args.role or p.get('selector', {}).get('role', args.role) == args.role)]
        if not candidates: raise ValueError('No matching award profile; verify the route and selector')
        text = json.dumps(candidates, ensure_ascii=False, indent=2)
        if args.offset < 0 or args.max_chars < 1: raise ValueError('Invalid award profile window')
        end = min(len(text), args.offset + args.max_chars)
        print(json.dumps({'content': text[args.offset:end], 'offset': args.offset, 'next_offset': end if end < len(text) else None, 'total_chars': len(text), 'has_more': end < len(text)}, ensure_ascii=False, indent=2))
    else:
        target = Path(args.output).resolve()
        if not target.is_relative_to(ROOT / 'wiki') and not target.is_relative_to(ROOT / 'audits'):
            raise ValueError('Reusable checklist delivery must stay in engine wiki/audits')
        if data['missing_routes']: raise ValueError('Incomplete award route coverage: ' + ','.join(data['missing_routes']))
        target.mkdir(parents=True, exist_ok=True)
        for route in data['routes']:
            (target / ('award-idea-' + route['code'].lower() + '-2026.md')).write_text(render_route(route['code']), encoding='utf-8')
        print(json.dumps({'routes': len(data['routes']), 'profiles': len(data['profiles']), 'output': str(target)}, ensure_ascii=False))


if __name__ == '__main__':
    try: main()
    except (ValueError, KeyError, FileNotFoundError) as error:
        print(str(error), file=sys.stderr); sys.exit(1)
