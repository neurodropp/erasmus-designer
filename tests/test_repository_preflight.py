import importlib.util
from pathlib import Path
import tempfile
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts/repository_preflight.py"
SPEC = importlib.util.spec_from_file_location("repository_preflight", MODULE_PATH)
preflight = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preflight)


class RepositoryPreflightTests(unittest.TestCase):
    def test_clean_minimal_tree_passes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "config/forms").mkdir(parents=True)
            (root / "config/sources.json").write_text("[]\n")
            (root / "config/forms/ka220-user-template.json").write_text(
                '{"distribution_note":"synthetic","questions":[]}\n'
            )
            self.assertEqual(preflight.check(root), [])

    def test_private_project_and_absolute_home_fail(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "projects/case").mkdir(parents=True)
            private_path = "/" + "Users/example/private/file.docx\n"
            (root / "projects/case/person.md").write_text(private_path)
            codes = {issue["code"] for issue in preflight.check(root)}
            self.assertIn("project-data-present", codes)
            self.assertIn("absolute-user-home", codes)

    def test_user_template_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "config").mkdir()
            (root / "config/sources.json").write_text(
                '[{"id":"template-ka220-user","kind":"user-template"}]\n'
            )
            codes = {issue["code"] for issue in preflight.check(root)}
            self.assertIn("private-source-catalogue-entry", codes)


if __name__ == "__main__":
    unittest.main()
