import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import workflow
import stage_gate
import project_paths
from project_paths import bounded,resolve_project

class ProjectDossierTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.patch=patch.object(workflow,'ROOT',self.root);self.patch.start()
    def tearDown(self):self.patch.stop();self.tmp.cleanup()
    def cli(self,*args):
        with patch.object(sys,'argv',['workflow',*args]),contextlib.redirect_stdout(io.StringIO()):workflow.main()
    def test_creation_separates_dossier_and_preserves_identity(self):
        self.cli('init','bridge','--title','BRIDGE — Youth cooperation','--action','KA220','--sector','YOU')
        path=self.root/'projects/bridge--ka220-youth--2026'
        self.assertEqual(workflow.project('bridge'),path)
        self.assertEqual(stage_gate.dossier(self.root,path.name),path)
        self.assertFalse((self.root/'wiki/projects').exists())
        state=json.loads((path/'state.json').read_text());model=json.loads((path/'project.json').read_text())
        self.assertEqual(state['id'],path.name);self.assertEqual(model['project']['title'],state['title'])
        self.assertEqual(state['checklist_protocol'],'project-checklist-v1')
        self.assertEqual(state['action_mode'],'grant')
        self.assertTrue((path/'stages/qa').is_dir());self.assertTrue((path/'production/answer-outlines').is_dir())
        self.assertTrue((path/'annexes/budget-table').is_dir())
        self.assertFalse(json.loads((path/'annex-manifest.json').read_text())['coverage_verified'])
        self.assertEqual((path/'draft.md').read_text(),'')
    def test_same_name_on_different_routes_requires_explicit_id(self):
        self.cli('init','bridge','--action','KA220','--sector','YOU')
        self.cli('init','bridge','--action','KA152','--sector','YOU')
        with self.assertRaisesRegex(ValueError,'Ambiguous'):workflow.project('bridge')
        path=workflow.project('bridge--ka152-youth-exchange--2026')
        self.assertTrue((path/'annexes/ka1-activity-timetable').is_dir())
        self.assertEqual(stage_gate.dossier(self.root,path.name),path)
    def test_short_name_cannot_collide_with_an_existing_full_folder_id(self):
        self.cli('init','alpha','--action','KA152','--sector','YOU')
        full='alpha--ka152-youth-exchange--2026'
        with self.assertRaisesRegex(ValueError,'reserved --'):self.cli('init',full,'--action','KA220','--sector','YOU')
        self.assertEqual(workflow.project(full),self.root/'projects'/full)
        self.assertEqual(len(list((self.root/'projects').glob('*/state.json'))),1)
    def test_existing_folder_is_not_overwritten(self):
        path=self.root/'projects/bridge--ka220-youth--2026';path.mkdir(parents=True)
        f=path/'input.md';f.write_text('Real user input to preserve')
        with self.assertRaisesRegex(ValueError,'already exists'):self.cli('init','bridge','--action','KA220','--sector','YOU')
        self.assertEqual(f.read_text(),'Real user input to preserve');self.assertFalse((path/'state.json').exists())
    def test_invalid_layout_cannot_partially_initialize_a_dossier(self):
        spec=project_paths.layout();spec['base_directories']=list(spec['base_directories'])+['../../outside-layout']
        with patch.object(project_paths,'layout',return_value=spec),self.assertRaisesRegex(ValueError,'outside permitted'):
            self.cli('init','bad-layout','--action','KA220','--sector','YOU')
        self.assertFalse((self.root/'projects').exists());self.assertFalse((self.root/'outside-layout').exists())
    def test_bad_route_or_annex_does_not_create_dossier(self):
        for args in [('KA210','HED',[]),('KA152','YOU',['--annex','invented-annex'])]:
            with self.assertRaises(ValueError):self.cli('init','bad','--action',args[0],'--sector',args[1],*args[2])
        self.assertFalse((self.root/'projects').exists())
    def test_path_escape_and_external_symlink_are_rejected(self):
        with self.assertRaises(ValueError):bounded(self.root,'../elsewhere')
        with tempfile.TemporaryDirectory() as outside:
            (self.root/'projects').symlink_to(outside,target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'outside workspace'):bounded(self.root,'demo')
    def test_legacy_dossier_requires_explicit_migration(self):
        path=self.root/'wiki/projects/old';path.mkdir(parents=True);(path/'state.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'Legacy dossier'):resolve_project(self.root,'old')
    def test_extra_annex_is_workspace_only(self):
        self.cli('init','demo','--action','KA220','--sector','ADU','--annex','gantt-table')
        path=workflow.project('demo');self.assertTrue((path/'annexes/gantt-table').is_dir())
        self.assertEqual(json.loads((path/'annex-manifest.json').read_text())['annexes'],[])
    def test_form_profile_cannot_be_bound_from_a_different_dossier(self):
        self.cli('init','selected','--action','KA220','--sector','YOU');self.cli('init','other','--action','KA220','--sector','YOU')
        selected=workflow.project('selected');other=workflow.project('other');profile=other/'application/form.json';profile.write_text(json.dumps({'questions':[{'id':'Q1','kind':'text','max_chars':100}]}))
        report=selected/'reports/bind.json';report.write_text(json.dumps(dict(summary='SYNTHETIC',evidence=[dict(source_id='programme-2026',locator='SYNTHETIC')],critical_review=dict(weaknesses=['SYNTHETIC'],alternative='SYNTHETIC',decision_basis='SYNTHETIC'))))
        before=(selected/'state.json').read_bytes()
        with self.assertRaisesRegex(ValueError,'different project dossier'):
            self.cli('bind-form',selected.name,'--profile',str(profile),'--report',str(report))
        self.assertEqual((selected/'state.json').read_bytes(),before);self.assertEqual(list((selected/'receipts').iterdir()),[])
    def test_accreditation_does_not_initialize_a_fictional_grant(self):
        self.cli('init','accredit','--action','KA150','--sector','YOU')
        model=json.loads((workflow.project('accredit')/'project.json').read_text())['project']
        self.assertEqual(model['action_mode'],'accreditation');self.assertEqual(model['financial_model'],'not-applicable')
        self.assertIsNone(model['requested_grant']);self.assertEqual(model['accreditation_requirements_evidence'],[])

if __name__=='__main__':unittest.main()
