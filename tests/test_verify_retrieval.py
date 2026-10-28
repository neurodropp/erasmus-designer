import unittest
from scripts.verify_retrieval import evaluate_page

class RetrievalScopeTests(unittest.TestCase):
    def setUp(self):
        self.mapping={'er':1,'esc':90,'expert':91}
        self.case={'sources':['esc'],'forbidden_sources':['er'],'required_text':['year: 2026','program: ESC']}

    def test_scoped_support_passes(self):
        self.assertTrue(all(evaluate_page(self.case,{'source_ids':[90,91],'body':'year: 2026\nprogram: ESC'},self.mapping).values()))

    def test_wrong_program_support_is_rejected_even_when_expected_present(self):
        checks=evaluate_page(self.case,{'source_ids':[90,1],'body':'year: 2026\nprogram: ESC'},self.mapping)
        self.assertTrue(checks['source_trace']); self.assertFalse(checks['forbidden_sources_absent'])

    def test_wrong_year_is_rejected(self):
        self.assertFalse(evaluate_page(self.case,{'source_ids':[90],'body':'year: 2027\nprogram: ESC'},self.mapping)['scope_text_checked'])

    def test_missing_specific_support_is_rejected(self):
        self.assertFalse(evaluate_page(self.case,{'source_ids':[91],'body':'year: 2026\nprogram: ESC'},self.mapping)['source_trace'])

    def test_unknown_source_fails_instead_of_skipping(self):
        with self.assertRaises(KeyError):
            evaluate_page({'sources':['missing']},{'source_ids':[],'body':''},self.mapping)
