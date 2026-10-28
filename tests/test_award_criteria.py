"""Synthetic checklist contracts, no official rubric or funding assessment."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import award_criteria


class AwardCoverageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        config = self.root / 'config'; (config / 'award-criteria').mkdir(parents=True)
        routes = [{'code': c, 'program': 'ERASMUS', 'sectors': ['HED'], 'agency': 'EACEA'}
                  for c in ('SYNTHETIC-SINGLE', 'SYNTHETIC-VARIANTS')]
        (config / 'actions.json').write_text(json.dumps(routes))
        (config / 'sources.json').write_text(json.dumps([{'id': 'synthetic-guide', 'kind': 'programme-guide'}]))
        refs = [{'source_id': 'synthetic-guide', 'pages': [1, 1]}]
        def profile(ident, route, selector):
            check = {'id': ident + '.need', 'official_focus_it': 'Synthetic need focus',
                     'idea_question_it': 'Is the synthetic need plausible?',
                     'evidence_at_idea_it': 'Synthetic brief or research plan',
                     'later_verification_it': 'Before concept',
                     'design_implication_it': 'Narrow scope if unsupported',
                     'applicability_it': 'Synthetic fixture only', 'source_refs': refs}
            return {'id': ident, 'routes': [route], 'selector': selector,
                    'scoring_mode': 'points', 'source_refs': refs, 'scoring': {},
                    'criteria': [{'id': ident + '.relevance', 'label_en': 'Synthetic relevance',
                                  'max_points': 10, 'source_refs': refs, 'checks': [check]}],
                    'idea_controls': [], 'coverage': {'limits': ['Synthetic test only']}}
        profiles = [profile('single', 'SYNTHETIC-SINGLE', {}),
                    profile('variant-a', 'SYNTHETIC-VARIANTS', {'variant': 'A'}),
                    profile('variant-b', 'SYNTHETIC-VARIANTS', {'variant': 'B'})]
        (config / 'award-criteria/test-2026.json').write_text(json.dumps({
            'schema_version': 'award-idea-profiles-v1', 'program': 'ERASMUS',
            'year': 2026, 'profiles': profiles}))
        self.state = {'action': 'SYNTHETIC-SINGLE', 'program': 'ERASMUS', 'year': 2026, 'sector': 'HED'}

    def tearDown(self):
        self.tmp.cleanup()

    def test_ambiguous_or_unknown_variant_never_selects_first_rubric(self):
        state = {**self.state, 'action': 'SYNTHETIC-VARIANTS'}
        missing = award_criteria.select(state, root=self.root)
        self.assertEqual(missing['selection_status'], 'selector-required')
        self.assertIsNone(missing['selected_profile'])
        selected = award_criteria.select(state, {'award_criteria_variant': 'B'}, self.root)
        self.assertEqual(selected['selected_profile'], 'variant-b')
        unknown = award_criteria.select(state, {'award_criteria_variant': 'UNKNOWN'}, self.root)
        self.assertIsNone(unknown['selected_profile'])

    def test_omitted_subpoint_or_altered_source_is_rejected(self):
        expected = award_criteria.select(self.state, root=self.root)
        omitted = copy.deepcopy(expected); omitted['entries'].clear()
        self.assertTrue(award_criteria.validate(omitted, expected)[0])
        changed = copy.deepcopy(expected)
        changed['entries'][0]['source_refs'][0]['pages'] = [2, 2]
        self.assertTrue(award_criteria.validate(changed, expected)[0])

    def test_credible_research_gap_is_valid_idea_maturity(self):
        expected = award_criteria.select(self.state, root=self.root)
        assessed = copy.deepcopy(expected); row = assessed['entries'][0]
        row.update(maturity='research-needed', reason='Local need still to triangulate',
                   owner='synthetic-researcher', evidence_plan='Triangulate before concept and reduce ambition if unsupported')
        issues, unassessed = award_criteria.validate(assessed, expected)
        self.assertEqual(issues, []); self.assertEqual(unassessed, [])
        row['evidence_plan'] = ''
        self.assertTrue(award_criteria.validate(assessed, expected)[0])

    def test_role_conflict_and_annuality_substitution_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'conflicts'):
            award_criteria.select({**self.state, 'role': 'host'}, {'role': 'support'}, self.root)
        with self.assertRaisesRegex(ValueError, 'annuality'):
            award_criteria.select({**self.state, 'year': 2027}, root=self.root)

    def test_exported_card_preserves_route_program_tags(self):
        rendered = award_criteria.render_route('SYNTHETIC-SINGLE', self.root)
        self.assertIn('program: ERASMUS\naction: SYNTHETIC-SINGLE', rendered)
        self.assertIn('do not assign official scores', rendered)

    def test_conditional_pages_outside_primary_rubric_are_in_the_handoff(self):
        path=self.root/'config/award-criteria/test-2026.json'
        data=json.loads(path.read_text())
        check=data['profiles'][0]['criteria'][0]['checks'][0]
        check['source_refs']=[{'source_id':'synthetic-guide','pages':[2,3]}]
        path.write_text(json.dumps(data))
        selected=award_criteria.select(self.state,root=self.root)
        self.assertEqual(selected['source_refs'],[
            {'source_id':'synthetic-guide','pages':[1,1]},
            {'source_id':'synthetic-guide','pages':[2,3]}])


    def update_profile(self, changes):
        path = self.root / 'config/award-criteria/test-2026.json'
        data = json.loads(path.read_text()); data['profiles'][0].update(changes)
        path.write_text(json.dumps(data))

    def test_incompatible_sector_and_metadata_override_do_not_select_validly(self):
        outside = award_criteria.select({**self.state, 'sector': 'SCH'}, root=self.root)
        self.assertEqual(outside['selection_status'], 'context-conflict')
        with self.assertRaisesRegex(ValueError, 'conflicts.*sector'):
            award_criteria.select(self.state, {'sector': 'SCH'}, self.root)
        path = self.root / 'config/actions.json'; routes = json.loads(path.read_text())
        routes[0]['sectors'].append('SCH'); path.write_text(json.dumps(routes))
        self.update_profile({'sectors': ['HED']})
        variant_conflict = award_criteria.select({**self.state, 'sector': 'SCH'}, root=self.root)
        self.assertEqual(variant_conflict['selection_status'], 'context-conflict')

    def test_incompatible_known_role_is_rejected(self):
        self.update_profile({'allowed_context': {'role': ['host', 'support']}, 'context_required': ['role']})
        for role in ['lead', 'WRONG']:
            with self.subTest(role=role):
                rejected = award_criteria.select({**self.state, 'role': role}, root=self.root)
                self.assertEqual(rejected['selection_status'], 'context-conflict')
        allowed = award_criteria.select({**self.state, 'role': 'support'}, root=self.root)
        self.assertEqual(allowed['selection_status'], 'selected')

    def test_common_rubric_context_gap_requires_plan_without_blocking_selection(self):
        self.update_profile({'context_to_verify': ['call_topic']})
        expected = award_criteria.select(self.state, root=self.root)
        self.assertEqual(expected['selection_status'], 'selected')
        self.assertEqual(expected['context_gaps'], ['call_topic'])
        self.assertEqual(expected['entries'][-1]['kind'], 'method-context-verification')
        self.assertIsNone(expected['entries'][-1]['criterion_max_points'])
        assessed = copy.deepcopy(expected)
        for row in assessed['entries']:
            row.update(maturity='research-needed', owner='synthetic-researcher', reason='Context and need are open hypotheses', evidence_plan='Verify call and need before design; change route if incompatible')
        self.assertEqual(award_criteria.validate(assessed, expected), ([], []))
        assessed['entries'][-1]['evidence_plan'] = ''
        self.assertTrue(award_criteria.validate(assessed, expected)[0])

    def test_missing_sector_is_not_filled_with_first_registered_sector(self):
        missing = award_criteria.select({**self.state, 'sector': None}, root=self.root)
        self.assertEqual(missing['selection_status'], 'context-required')
        self.assertIn('sector', missing['missing_context'])

if __name__ == '__main__':
    unittest.main()
