import unittest
from scripts.evaluation import grade

class EvaluationTests(unittest.TestCase):
    def routing(self,selected='none',clarify=False,candidates=None):
        return {'labels_read':False,'cases':[{'id':'R','primary_skill':selected,'needclarification':clarify,'candidate_skills':candidates or []}]}

    def test_ambiguous_request_can_defer_with_all_candidates(self):
        labels={'cases':[{'id':'R','acceptable_primary_skills':['a','b'],'ambiguous':True}]}
        self.assertEqual(grade(labels,self.routing(clarify=True,candidates=['b','a']),'routing')['label_agreement_count'],1)
        self.assertEqual(grade(labels,self.routing(),'routing')['label_agreement_count'],0)

    def test_outside_domain_does_not_force_a_skill(self):
        labels={'cases':[{'id':'R','acceptable_primary_skills':[],'ambiguous':False}]}
        self.assertEqual(grade(labels,self.routing(),'routing')['label_agreement_count'],1)
        self.assertEqual(grade(labels,self.routing('a'),'routing')['label_agreement_count'],0)

    def test_selected_skill_needs_actual_read_manifest(self):
        labels={'cases':[{'id':'R','acceptable_primary_skills':['a'],'ambiguous':False}]}
        prediction=self.routing('a')
        self.assertEqual(grade(labels,prediction,'routing')['label_agreement_count'],0)
        prediction['cases'][0]['files_actually_read']=[{'path':'skills/a/SKILL.md','sha256':'0'*64}]
        self.assertEqual(grade(labels,prediction,'routing')['label_agreement_count'],1)

    def test_missing_duplicate_or_extra_case_rejected(self):
        labels={'cases':[{'id':'R','acceptable_primary_skills':[],'ambiguous':False}]}
        for rows in [[],[{'id':'X'}],[{'id':'R'},{'id':'R'}]]:
            with self.assertRaises(ValueError):grade(labels,{'labels_read':False,'cases':rows},'routing')

    def test_label_leakage_declared_is_rejected(self):
        with self.assertRaises(ValueError):grade({'cases':[]},{'labels_read':True,'cases':[]},'routing')

    def test_no_grid_qualitative_run_cannot_claim_compliance_or_vote(self):
        labels={'cases':[{'id':'E','expected_label':'supported'}]}
        row={'id':'E','label':'supported','reason':'Evidence in excerpt','evidence_location':'sentence 1','score':None,'compliance':'not-determined','funding_prediction':None}
        self.assertEqual(grade(labels,{'labels_read':False,'cases':[row]},'evaluator')['label_agreement_count'],1)
        for field,value in [('score',80),('compliance','eligible'),('funding_prediction','funded')]:
            with self.assertRaises(ValueError):grade(labels,{'labels_read':False,'cases':[{**row,field:value}]},'evaluator')

    def test_equivalent_missing_evidence_vocabulary_and_unknown_label(self):
        labels={'cases':[{'id':'E','expected_label':'insufficient'}]}
        row={'id':'E','label':'needs-evidence','reason':'Missing localized evidence','evidence_location':'sentence 1','score':None,'compliance':'not-determined','funding_prediction':None}
        self.assertEqual(grade(labels,{'labels_read':False,'cases':[row]},'evaluator')['label_agreement_count'],1)
        with self.assertRaises(ValueError):grade(labels,{'labels_read':False,'cases':[{**row,'label':'funded'}]},'evaluator')
