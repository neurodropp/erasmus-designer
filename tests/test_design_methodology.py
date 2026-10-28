"""Synthetic regression fixtures; no real validation or causal-quality claim."""
import unittest
from pathlib import Path
import tempfile
from unittest.mock import patch

import test_stage_gate as fixture_module
import stage_gate as gate
import brain


class DesignMethodologyTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture_module.StageGateTests('test_complete_fresh_review_advances_and_archives')
        self.fixture.setUp()

    def tearDown(self):
        self.fixture.tearDown()

    def test_method_contracts_are_frozen_and_checked_against_originals(self):
        fixture = self.fixture
        captured = {row['role']: row for row in fixture.m['files']
                    if row['role'].startswith('design-methodology-')}
        self.assertEqual(set(captured), {'design-methodology-controls', 'design-methodology-contract'})
        fixture.verify()
        contract = captured['design-methodology-contract']
        original = gate.original_file(fixture.root, fixture.path, contract)
        self.assertEqual(original, gate.CATALOG_ROOT / 'docs/design-methodology.md')
        real_digest = gate.digest
        def changed_digest(path):
            return '0' * 64 if Path(path) == original else real_digest(path)
        with patch.object(gate, 'digest', side_effect=changed_digest):
            with self.assertRaisesRegex(ValueError, 'changed'):
                fixture.verify()

    def test_reviewer_cannot_omit_award_design_method_check(self):
        fixture = self.fixture
        self.assertIn('method-award-design', {row['id'] for row in fixture.r['checks']})
        fixture.r['checks'] = [row for row in fixture.r['checks']
                               if row['id'] != 'method-award-design']
        fixture.save_review()
        with self.assertRaisesRegex(ValueError, 'exactly once'):
            fixture.verify()

    def test_accepted_idea_checklist_cannot_be_changed_without_invalidation(self):
        fixture = self.fixture
        captured = next(row for row in fixture.m['files'] if row['role']=='project-checklist')
        self.assertTrue(captured['accepted_product'])
        fixture.cli('record', 'demo', '--phase', 'idea-validation', '--report', str(fixture.report),
                    '--validation-packet', fixture.ident, '--validation-report', str(fixture.review))
        current = fixture.path / 'research/checklist-idea-validation.json'
        current.write_text(current.read_text() + '\n')
        with self.assertRaisesRegex(ValueError, 'Accepted step product changed'):
            gate.verify_history(fixture.path, fixture.state())


class HtmlMethodScopeTests(unittest.TestCase):
    def test_explicit_scope_preserves_method_prose_and_table_cells(self):
        with tempfile.TemporaryDirectory() as temp:
            page = Path(temp) / 'method.html'
            page.write_text('<html><body><div id="main"><h1>Impact method</h1>'
                            '<p>Outputs need actual use before outcomes.</p>'
                            '<table><tr><td>Baseline</td><td>Unknown</td></tr></table>'
                            '<p>Measure changed practice with the target group.</p>'
                            '<script>Never index script payload</script></div></body></html>')
            self.assertEqual(brain.parse_html(page)[1], '')
            title, text, _ = brain.parse_html(page, 'full-static-document')
            self.assertEqual(title, 'Impact method')
            self.assertIn('Outputs need actual use before outcomes.', text)
            self.assertIn('Measure changed practice with the target group.', text)
            self.assertIn(' | Baseline | Unknown', text)
            self.assertNotIn('Never index script payload', text)

    def test_default_scope_and_unknown_adapter_remain_restricted(self):
        with tempfile.TemporaryDirectory() as temp:
            page = Path(temp) / 'official.html'
            page.write_text('<body><nav>Site navigation</nav>'
                            '<main><h1>Grant rules</h1><p>Verified scope.</p>'
                            '<style>Hidden stylesheet</style></main><footer>Footer</footer></body>')
            _, text, _ = brain.parse_html(page)
            self.assertIn('Verified scope.', text)
            self.assertNotIn('Site navigation', text)
            self.assertNotIn('Footer', text)
            self.assertNotIn('Hidden stylesheet', text)
            with self.assertRaisesRegex(ValueError, 'Unknown HTML content scope'):
                brain.parse_html(page, 'implicit-whole-site')


if __name__ == '__main__':
    unittest.main()
