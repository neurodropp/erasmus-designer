import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import checklist


class ProjectChecklistTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.path = self.root / 'projects/sample--ka152-youth-exchange--2026'
        self.path.mkdir(parents=True)
        self.state = dict(name='sample', program='ERASMUS', year=2026, action='KA152',
                          sector='YOU', country='IT', agency='AIG', role='applicant', round='R1')
        (self.path / 'state.json').write_text(json.dumps(self.state))
        self.data = checklist.template(self.state, 'intervention-design')
        self.proof = self.path / 'research/proof.md'
        self.proof.parent.mkdir()
        self.proof.write_text('Fixture evidence, not a real consultation.')
        self.ref = dict(source_id='fixture-proof', locator='paragraph 1', path=str(self.proof))

    def tearDown(self):
        self.tmp.cleanup()

    def validate(self, data=None):
        return checklist.validate(data or self.data, self.state, self.path)

    def test_initial_instance_is_valid_open_and_preserves_sources(self):
        result = self.validate()
        self.assertTrue(result['valid'])
        self.assertFalse(result['ready_for_independent_review'])
        self.assertTrue(result['coverage_gaps'])
        self.assertTrue(result['reading_todo'][0]['remaining_read_locators'])
        self.assertTrue(all(r['status'] == 'to-verify' for r in self.data['checks']))
        youth = next(r for r in self.data['checks'] if r['check_id'] == 'ka152-participation-proof')
        self.assertTrue(youth['baseline']['sources'])

    def test_stage_and_action_filter_without_transferring_youth_rules(self):
        early = checklist.template(self.state, 'idea-validation')
        self.assertNotEqual(len(early['checks']), len(self.data['checks']))
        other = dict(self.state, action='KA220-ADU', sector='ADU', agency='INDIRE')
        data = checklist.template(other, 'intervention-design')
        self.assertEqual(data['baseline_coverage']['status'], 'routing-only-not-assessed')
        self.assertFalse(any(r['check_id'].startswith('ka152-') for r in data['checks']))
        self.assertIn('current-form', {r['section_id'] for r in data['section_coverage']})

    def test_full_route_has_every_action_and_general_page(self):
        action = next(r for r in self.data['section_coverage'] if r['section_id'] == 'action-section')
        route = next(r for r in checklist.read(checklist.CATALOG_ROOT / 'config/actions.json') if r['code'] == 'KA152')
        refs = action['sources'][0]['references']
        self.assertEqual(len(refs), route['programme_pages'][1] - route['programme_pages'][0] + 1)
        self.assertTrue(all(Path(r['path']).is_file() and r['sha256'] for r in refs))
        general = next(r for r in self.data['section_coverage'] if r['section_id'] == 'general-conditions-2')
        self.assertEqual(len(general['sources'][0]['references']), 30)

    def test_initialize_uses_project_resolver_and_never_overwrites(self):
        target = checklist.initialize(self.root, 'sample', 'intervention-design')
        self.assertEqual(target, self.path / 'research/checklist-intervention-design.json')
        with self.assertRaises(FileExistsError):
            checklist.initialize(self.root, self.path.name, 'intervention-design')
        with self.assertRaises(ValueError):
            checklist.initialize(self.root, 'missing', 'intervention-design')

    def test_path_escape_and_symlink_escape_are_rejected(self):
        for value in ('../outside.json', 'state.json', 'research/check.md'):
            with self.assertRaises(ValueError):
                checklist.initialize(self.root, 'sample', 'intervention-design', value)
        (self.path / 'stages').symlink_to(self.root)
        with self.assertRaises(ValueError):
            checklist.initialize(self.root, 'sample', 'intervention-design', 'stages/escape.json')

    def test_satisfied_requires_proof_and_project_artifact(self):
        row = self.data['checks'][0]
        row.update(status='satisfied', owner='fixture-owner')
        self.assertFalse(self.validate()['valid'])
        row.update(evidence=[self.ref], artifact_locators=[dict(path=str(self.proof), locator='paragraph 1')])
        self.assertTrue(self.validate()['valid'])
        self.assertFalse(self.validate()['ready_for_independent_review'])

    def test_na_requires_reason_and_evidence(self):
        row = self.data['checks'][0]
        row.update(status='not-applicable', owner='fixture-owner', reason='Not applicable to the fixture scope')
        self.assertFalse(self.validate()['valid'])
        row['evidence'] = [self.ref]
        self.assertTrue(self.validate()['valid'])
        row['reason'] = ''
        self.assertFalse(self.validate()['valid'])

    def test_current_form_cannot_be_skipped_after_field_planning_begins(self):
        for phase in checklist.FORM_REQUIRED_PHASES:
            with self.subTest(phase=phase):
                data=checklist.template(self.state,phase)
                row=next(r for r in data['section_coverage'] if r['section_id']=='current-form')
                row.update(status='not-applicable',owner='fixture',reason='Attempt to skip current form',evidence=[self.ref])
                result=self.validate(data)
                self.assertFalse(result['valid']);self.assertFalse(result['ready_for_independent_review'])
                self.assertTrue(any(i['item_id']=='current-form' for i in result['issues']))
                row.update(status='to-verify')
                shared=next(r for r in data['checks'] if r['check_id']=='shared-form')
                shared.update(status='not-applicable',owner='fixture',reason='Attempt to skip form check',evidence=[self.ref])
                self.assertFalse(self.validate(data)['valid'])

    def test_not_satisfied_requires_actionable_finding(self):
        row = self.data['checks'][0]
        row.update(status='not-satisfied', owner='fixture-owner', evidence=[self.ref],
                   artifact_locators=[dict(path=str(self.proof), locator='paragraph 1')])
        self.assertFalse(self.validate()['valid'])
        row.update(discrepancy='Missing fixture scope', severity='major', required_fix='Complete scope')
        self.assertTrue(self.validate()['valid'])

    def test_reading_a_snippet_does_not_close_full_section(self):
        row = self.data['section_coverage'][0]
        row.update(status='satisfied', owner='fixture-owner', evidence=[self.ref],
                   read_locators=['programme-2026:' + row['sources'][0]['references'][0]['locator']])
        self.assertFalse(self.validate()['valid'])
        row['read_locators'] = [s['source_id'] + ':' + ref['locator'] for s in row['sources'] for ref in s['references']]
        self.assertTrue(self.validate()['valid'])

    def test_baseline_scope_and_required_coverage_cannot_disappear(self):
        for transform in (
            lambda d: d['checks'].pop(),
            lambda d: d['checks'][0]['baseline'].update(check='changed'),
            lambda d: d['section_coverage'].pop(),
            lambda d: d['scope'].update(year=2025),
            lambda d: d['baseline_coverage'].update(status='complete'),
            lambda d: d['section_coverage'][0]['sources'][0]['references'].pop(),
        ):
            data = copy.deepcopy(self.data)
            transform(data)
            self.assertFalse(self.validate(data)['valid'])

    def test_extensions_are_source_grounded_and_scoped(self):
        extension = dict(check_id='project-fixture-rule', check='Fixture additional check',
                         classification='requirement', applicability='Fixture only',
                         scope=self.data['scope'], sources=[self.ref], **checklist.outcome())
        extension['owner'] = 'fixture-owner'
        self.data['extensions'] = [extension]
        self.assertTrue(self.validate()['valid'])
        extension['sources'] = []
        self.assertFalse(self.validate()['valid'])
        extension['sources'] = [self.ref]
        self.data['extensions'].append(copy.deepcopy(extension))
        self.assertFalse(self.validate()['valid'])

    def test_esc_uses_own_route_and_programme(self):
        data = checklist.template(dict(self.state, program='ESC', action='ESC30', sector='ESC'), 'intervention-design')
        self.assertEqual(data['section_coverage'][0]['sources'][0]['source_id'], 'esc-programme-2026')
        self.assertFalse(any(r['check_id'].startswith('ka152-') for r in data['checks']))
        with self.assertRaises(ValueError):
            checklist.template(dict(self.state, year=2025), 'intervention-design')


if __name__ == '__main__':
    unittest.main()
