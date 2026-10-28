"""Synthetic configuration/reader regressions, not model performance tests.

No confidential input is opened. Every mock document is written from zero.
"""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config/evaluator-calibration.json").read_text())
SCRIPTS = ROOT / "scripts"


def load_module(filename):
    portable_name = {"aggregate_reader.py": "evaluator_aggregate_reader.py", "private_match.py": "evaluator_private_match.py"}[filename]
    spec = importlib.util.spec_from_file_location(filename.replace(".", "_"), SCRIPTS / portable_name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def synthetic_pdf(pages):
    """Minimal standard-library PDF for optional real Poppler regressions."""
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"", b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    kids = []
    for lines in pages:
        page_id = len(objects) + 1
        stream_id = page_id + 1
        kids.append(str(page_id) + " 0 R")
        commands = []
        for x, y, text in lines:
            escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            commands.append(f"BT /F1 12 Tf {x} {y} Td ({escaped}) Tj ET")
        stream = "\n".join(commands).encode("ascii")
        objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents {stream_id} 0 R >>".encode())
        objects.append(f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream")
    objects[1] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(kids)} >>".encode()
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, value in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode() + value + b"\nendobj\n")
    start = len(output)
    output.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        output.extend(f"{offset:010} 00000 n \n".encode())
    output.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n".encode())
    return bytes(output)


class CalibrationContract(unittest.TestCase):
    def test_version_authority_and_nonretention(self):
        self.assertEqual(CONFIG["schema_version"], "evaluator-calibration-v1")
        self.assertEqual(CONFIG["authority"], "derived-practice-not-call-requirement")
        self.assertFalse(CONFIG["confidential_sources_retained"])
        self.assertFalse(CONFIG["private_source_trace_retained"])
        self.assertEqual(CONFIG["source_class"], "anonymized-aggregate-observation")
        self.assertFalse(CONFIG["guards"]["host_performance_claims"])

    def test_each_rule_has_scope_materiality_counterexample_and_fix(self):
        ids = set()
        for rule in CONFIG["rules"]:
            self.assertNotIn(rule["id"], ids)
            ids.add(rule["id"])
            for field in ("criterion_family", "practice", "counterexample", "expected_fix", "required_evidence_fields", "observation_support"):
                self.assertTrue(rule[field])
            self.assertTrue(rule["scope"]["requires_current_official_mapping"])
            self.assertEqual(rule["classification"], "derived-practice")
            self.assertEqual(rule["confidential_source"], "not-retained")
            self.assertIn("never-automatic-eligibility", rule["severity"])
            self.assertNotIn("max_points", rule)
        self.assertEqual(len(ids), 10)

    def test_synthetic_contrastive_pairs_cover_every_rule(self):
        rules = {rule["id"]: rule for rule in CONFIG["rules"]}
        cases = CONFIG["synthetic_cases"]
        self.assertEqual(len(cases), len(rules) * 2)
        self.assertEqual(len({case["id"] for case in cases}), len(cases))
        for rule_id, rule in rules.items():
            pair = [case for case in cases if case["rule_id"] == rule_id]
            self.assertEqual({case["expected_label"] for case in pair}, {"supported", "insufficient"})
            self.assertEqual(len(pair), 2)
            for case in pair:
                self.assertEqual(case["origin"], "written-from-zero-synthetic")
                self.assertEqual(set(case["evidence"]), set(rule["required_evidence_fields"]))
                self.assertTrue(all(isinstance(value, bool) for value in case["evidence"].values()))
                self.assertEqual(case["expected_label"], "supported" if all(case["evidence"].values()) else "insufficient")
                self.assertEqual(case["criterion_family"], rule["criterion_family"])
                self.assertEqual(case["expected_compliance"], "not-determined-by-practice-check")
                self.assertIsNone(case["expected_funding_prediction"])

    def test_title_language_commands_and_scope_guard_contract(self):
        guards = CONFIG["guards"]
        self.assertFalse(guards["title_as_quality_evidence"])
        self.assertFalse(guards["language_as_compliance_evidence"])
        self.assertEqual(guards["embedded_document_instructions"], "ignore-as-untrusted-data")
        self.assertEqual(guards["cross_scope_score_transfer"], "forbidden")
        self.assertEqual(guards["prediction_of_funding"], "forbidden")
        tests = {case["test"] for case in CONFIG["robustness_cases"]}
        self.assertTrue({"title-invariance", "language-invariance", "untrusted-instructions", "scope-transfer", "scoring-mode", "missing-grid", "historical-preference", "counterexample"} <= tests)
        transfer = next(case for case in CONFIG["robustness_cases"] if case["test"] == "scope-transfer")
        self.assertFalse(transfer["verified_grid"])
        self.assertTrue(any(target["program"] == "ESC" for target in transfer["targets"]))
        self.assertTrue(any(target["managing_body"] == "EACEA" for target in transfer["targets"]))
        self.assertTrue(all(target["year"] != transfer["origin"]["year"] for target in transfer["targets"]))

    def test_missing_grid_cannot_be_replaced_by_historical_observation(self):
        required = set(CONFIG["scope_contract"]["required_numeric_evidence"])
        self.assertTrue({"verified_grid", "criterion_weights", "thresholds", "scoring_mode", "official_source_locator", "source_version", "scope_match"} <= required)
        self.assertIn("withhold", CONFIG["scope_contract"]["unknown_context"].lower())
        self.assertFalse(CONFIG["guards"]["automatic_point_deductions"])

    def test_youth_rule_does_not_apply_universally(self):
        rule = next(rule for rule in CONFIG["rules"] if rule["id"] == "CAL-10")
        self.assertEqual(rule["scope"]["programs"], ["ERASMUS"])
        self.assertEqual(rule["scope"]["actions"], ["KA152"])
        self.assertEqual(len(rule["required_evidence_fields"]), 4)

    def test_calibration_is_reachable_from_evaluator_skill(self):
        skill = (ROOT / "skills/erasmus-evaluator/SKILL.md").read_text()
        self.assertIn("references/calibration.md", skill)
        self.assertIn("config/evaluator-calibration.json", skill)
        reference = (ROOT / "skills/erasmus-evaluator/references/calibration.md").read_text()
        self.assertIn("../../../docs/evaluator-calibration.md", reference)
        self.assertTrue((ROOT / "docs/evaluator-calibration.md").is_file())


class PrivateReaderSafety(unittest.TestCase):
    def match_synthetic(self, documents, filenames=None, metadata_fallback=False):
        matcher = load_module("private_match.py")
        with tempfile.TemporaryDirectory() as directory:
            filenames = filenames or [str(index) + ".pdf" for index in range(len(documents))]
            document_map = dict(zip(filenames, documents))
            for name in filenames:
                (Path(directory) / name).parent.mkdir(parents=True, exist_ok=True)
                (Path(directory) / name).write_bytes(b"synthetic placeholder")
            def extraction(command, **kwargs):
                relative = str(Path(command[-2]).relative_to(directory))
                return subprocess.CompletedProcess([], 0, document_map[relative].encode(), b"")
            with patch.object(matcher.subprocess, "run", side_effect=extraction):
                return matcher.match_in_memory(directory, metadata_fallback=metadata_fallback)

    def synthetic_documents(self):
        # Artificial territory marker; assembled from zero, no real identifier.
        code = "-".join(("2025", "1", "ZZ00", "KA152", "YOU", "000001"))
        application = "Application form\nProject description\nApplicant organisation\nProject Title: Synthetic shared draft\n" + code
        assessment = "Quality assessment\nProject Title: SYNTHETIC   SHARED DRAFT\n" + code
        return application, assessment, code

    def test_compact_and_poppler_shape_title_page_boundaries(self):
        matcher = load_module("private_match.py")
        for separator in ("\f", "\n\f", "\r\n\f"):
            text = "Project Title: Alpha" + separator + " " * 15 + "Beta\nCall: 2025"
            self.assertEqual(matcher.extract_titles(text), {"alpha"})

    def test_title_label_value_and_independent_titles_stay_on_their_pages(self):
        matcher = load_module("private_match.py")
        self.assertEqual(matcher.extract_titles("Project Title:\fAlpha\nCall: 2025"), set())
        self.assertEqual(matcher.extract_titles("Project Title: Alpha\fProject Title: Beta"), {"alpha", "beta"})

    def test_same_page_wrapped_title_and_code_remain_valid(self):
        matcher = load_module("private_match.py")
        _, _, code = self.synthetic_documents()
        self.assertEqual(matcher.extract_titles("Project Title: Alpha\n" + " " * 15 + "Beta\nCall: 2025"), {"alpha beta"})
        self.assertEqual(matcher.extract_codes(code.replace("-YOU-", "-\nYOU-")), {code})

    def test_compact_false_pair_rejected_and_same_page_pair_supported(self):
        _, _, code = self.synthetic_documents()
        application = "Application form\nProject description\nApplicant organisation\n" + code + "\nProject Title: Alpha\f" + " " * 15 + "Beta\nCall: 2025"
        assessment = "Quality assessment\n" + code + "\nProject Title: Alpha Beta\nCall: 2025"
        for metadata in (False, True):
            counts, pairs = self.match_synthetic([application, assessment], metadata_fallback=metadata)
            self.assertEqual(counts["both_name_and_project_code_pairs_confirmed"], 0)
            self.assertEqual(counts["assessment_rejection_title_disagreement"], 1)
            self.assertEqual(pairs, [])
        counts, pairs = self.match_synthetic([application.replace("\f", "\n"), assessment])
        self.assertEqual(counts["both_name_and_project_code_pairs_confirmed"], 1)
        pairs.clear()
        application = "Application form\nProject description\nApplicant organisation\nProject Title: Alpha\nCall: 2025\n" + code.replace("-YOU-", "-\fYOU-")
        assessment = "Quality assessment\nProject Title: Alpha\nCall: 2025\n" + code
        counts, pairs = self.match_synthetic([application, assessment])
        self.assertEqual(counts["both_name_and_project_code_pairs_confirmed"], 0)
        self.assertEqual(pairs, [])
        counts, pairs = self.match_synthetic([application.replace("\f", "\n"), assessment])
        self.assertEqual(counts["both_name_and_project_code_pairs_confirmed"], 1)
        pairs.clear()

    def test_code_cannot_cross_formfeed_in_compact_or_poppler_shapes(self):
        matcher = load_module("private_match.py")
        _, _, code = self.synthetic_documents()
        for separator in ("\f", "\n\f", "\r\n\f"):
            self.assertEqual(matcher.extract_codes(code.replace("-YOU-", "-" + separator + "YOU-")), set())
        other = code[:-1] + "2"
        self.assertEqual(matcher.extract_codes(code + "\f" + other), {code, other})

    @unittest.skipUnless(shutil.which("pdftotext"), "Optional real Poppler regression requires pdftotext")
    def test_actual_synthetic_poppler_page_breaks_for_titles_and_codes(self):
        matcher = load_module("private_match.py")
        _, _, code = self.synthetic_documents()
        cases = [
            ([[(72, 720, "Project Title: Alpha")], [(162, 720, "Beta")]], {"alpha"}, set()),
            ([[(72, 720, code.split("-YOU-")[0] + "-")], [(72, 720, "YOU-" + code.split("-YOU-")[1])]], set(), set()),
            ([[(72, 720, "Project Title: Alpha"), (162, 706, "Beta"), (72, 692, "Project Acronym: AB")]], {"alpha beta"}, set()),
        ]
        with tempfile.TemporaryDirectory() as directory:
            for index, (pages, titles, codes) in enumerate(cases):
                path = Path(directory) / (str(index) + ".pdf")
                path.write_bytes(synthetic_pdf(pages))
                result = subprocess.run([shutil.which("pdftotext"), "-layout", str(path), "-"], capture_output=True, check=True)
                text = result.stdout.decode("utf-8")
                self.assertIn("\f", text)
                self.assertEqual(matcher.extract_titles(text), titles)
                self.assertEqual(matcher.extract_codes(text), codes)

    def test_metadata_identity_does_not_normalize_formfeed_into_a_title(self):
        matcher = load_module("private_match.py")
        self.assertEqual(matcher.metadata_title_identity("assessment_Alpha\fBeta"), "")

    def test_matching_confirms_both_internal_keys_without_filename_evidence(self):
        application, assessment, _ = self.synthetic_documents()
        counts, pairs = self.match_synthetic([application, assessment])
        self.assertEqual(counts["both_internal_name_and_code_pairs_confirmed"], 1)
        self.assertEqual(len(pairs), 1)
        self.assertNotIn("Synthetic shared draft", json.dumps(counts))
        pairs.clear()

    def test_short_labelled_title_is_valid_and_not_found_in_arbitrary_prose(self):
        application, assessment, _ = self.synthetic_documents()
        application = application.replace("Synthetic shared draft", "AI")
        assessment = assessment.replace("SYNTHETIC   SHARED DRAFT", "AI")
        counts, pairs = self.match_synthetic([application, assessment])
        self.assertEqual(counts["both_internal_name_and_code_pairs_confirmed"], 1)
        pairs.clear()
        altered = assessment.replace("Project Title: AI", "Unrelated narrative about AI")
        counts, pairs = self.match_synthetic([application, altered])
        self.assertEqual(counts["both_internal_name_and_code_pairs_confirmed"], 0)
        self.assertEqual(counts["assessment_rejection_missing_title"], 1)

    def test_labelled_title_multiline_and_value_column_continuation(self):
        matcher = load_module("private_match.py")
        self.assertEqual(matcher.extract_titles("Project Title\nShort\nPlan\nProject Acronym: SP"), {"short plan"})
        line = "Project Title: Short"
        column = line.index("Short")
        text = line + "\n" + " " * column + "Plan\nProject Acronym: SP"
        self.assertEqual(matcher.extract_titles(text), {"short plan"})
        text = "Project Title: Short    Project Code: synthetic field"
        self.assertEqual(matcher.extract_titles(text), {"short"})

    def test_placeholder_title_is_rejected_without_length_filter(self):
        matcher = load_module("private_match.py")
        for placeholder in ("TBD", "n/a", "---", "Project Title", "da definire", ""):
            self.assertEqual(matcher.extract_titles("Project Title: " + placeholder), set())
        self.assertEqual(matcher.extract_titles("Project Title: Go"), {"go"})

    def test_unicode_code_separators_are_equivalent_without_digit_repair(self):
        matcher = load_module("private_match.py")
        application, assessment, code = self.synthetic_documents()
        assessment = assessment.replace(code, code.replace("-", "\u2011\u200b"))
        counts, pairs = self.match_synthetic([application, assessment])
        self.assertEqual(counts["both_internal_name_and_code_pairs_confirmed"], 1)
        pairs.clear()
        self.assertEqual(matcher.extract_codes(code[:-1] + "O"), set())

    def test_explicit_reporting_document_is_excluded_without_guessing_finalness(self):
        matcher = load_module("private_match.py")
        synthetic = "Application form\nProject description\nApplicant organisation\nFor this report the information is from Beneficiary Module.\nHow did you assess the outcome?"
        self.assertEqual(matcher.classify_document(synthetic), "beneficiary_report")
        application = "Application form\nProject description\nApplicant organisation\nThe final report will be submitted after implementation."
        self.assertEqual(matcher.classify_document(application), "application")

    def test_metadata_grant_code_fallback_requires_internal_title_stage_and_scope(self):
        application, assessment, code = self.synthetic_documents()
        application = application.replace(code, "Call: 2025\nAction Type: KA152-YOU\nForm ID: synthetic form")
        names = ["application-" + code + ".pdf", "assessment.pdf"]
        counts, pairs = self.match_synthetic([application, assessment], names, True)
        self.assertEqual(counts["both_internal_name_and_code_pairs_confirmed"], 0)
        self.assertEqual(counts["metadata_corroborated_pairs_confirmed"], 1)
        pairs.clear()
        for altered in (application.replace("Call: 2025", "Call: 2026"), application.replace("KA152-YOU", "KA220-YOU")):
            counts, pairs = self.match_synthetic([altered, assessment], names, True)
            self.assertEqual(counts["both_name_and_project_code_pairs_confirmed"], 0)
            self.assertEqual(counts["assessment_rejection_metadata_scope_unverified_or_discordant"], 1)

    def test_exact_original_assessment_metadata_title_can_corroborate(self):
        application, assessment, code = self.synthetic_documents()
        assessment = assessment.replace("Project Title: SYNTHETIC   SHARED DRAFT\n", "")
        names = ["application.pdf", "assessment_Synthetic-shared-draft_" + code + ".pdf"]
        counts, pairs = self.match_synthetic([application, assessment], names, True)
        self.assertEqual(counts["metadata_corroborated_pairs_confirmed"], 1)
        self.assertEqual(counts["both_internal_name_and_code_pairs_confirmed"], 0)
        pairs.clear()
        names[1] = names[1].replace("shared-draft_", "shared-drafts_")
        counts, pairs = self.match_synthetic([application, assessment], names, True)
        self.assertEqual(counts["both_name_and_project_code_pairs_confirmed"], 0)

    def test_internal_title_or_code_conflict_wins_over_metadata(self):
        application, assessment, code = self.synthetic_documents()
        names = ["application.pdf", "assessment_Synthetic-shared-draft_" + code + ".pdf"]
        counts, pairs = self.match_synthetic([application, assessment.replace("SYNTHETIC   SHARED DRAFT", "Different synthetic title")], names, True)
        self.assertEqual(counts["assessment_rejection_title_disagreement"], 1)
        self.assertEqual(pairs, [])
        names[0] = "application_" + code[:-1] + "2.pdf"
        counts, pairs = self.match_synthetic([application, assessment], names, True)
        self.assertEqual(counts["assessment_rejection_internal_metadata_code_conflict"], 1)
        self.assertEqual(pairs, [])

    def test_filename_name_and_code_alone_are_not_sufficient(self):
        application, assessment, code = self.synthetic_documents()
        application = application.replace("Project Title: Synthetic shared draft\n", "")
        names = ["application_Synthetic-shared-draft_" + code + ".pdf", "assessment.pdf"]
        counts, pairs = self.match_synthetic([application, assessment], names, True)
        self.assertEqual(counts["assessment_rejection_missing_application_internal_title"], 1)
        self.assertEqual(pairs, [])
        application, assessment, code = self.synthetic_documents()
        application = application.replace(code, "Form ID: synthetic form")
        counts, pairs = self.match_synthetic([application, assessment], ["application-form.pdf", "assessment.pdf"], True)
        self.assertEqual(counts["both_name_and_project_code_pairs_confirmed"], 0)
        self.assertEqual(pairs, [])

    def test_metadata_pairs_require_application_stage_in_body(self):
        application, assessment, code = self.synthetic_documents()
        application = application.replace("Application form", "Declaration on honour")
        names = ["application_" + code + ".pdf", "assessment.pdf"]
        counts, pairs = self.match_synthetic([application, assessment], names, True)
        self.assertEqual(counts["assessment_rejection_phase_unverified"], 1)
        self.assertEqual(pairs, [])

    def test_matching_rejects_name_only_or_code_only(self):
        application, assessment, code = self.synthetic_documents()
        for altered in (assessment.replace(code, "no matching code"), assessment.replace("SYNTHETIC   SHARED DRAFT", "Different synthetic document")):
            counts, pairs = self.match_synthetic([application, altered])
            self.assertEqual(counts["both_internal_name_and_code_pairs_confirmed"], 0)
            self.assertEqual(pairs, [])

    def test_matching_rejects_duplicate_or_multiple_project_references(self):
        application, assessment, code = self.synthetic_documents()
        for documents in ([application, application, assessment], [application, assessment + "\n" + code[:-1] + "2"]):
            counts, pairs = self.match_synthetic(documents)
            self.assertEqual(counts["both_internal_name_and_code_pairs_confirmed"], 0)
            self.assertEqual(pairs, [])

    def test_extraction_failure_emits_no_private_error_or_record(self):
        reader = load_module("aggregate_reader.py")
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "input.pdf").write_bytes(b"synthetic placeholder")
            failure = subprocess.CompletedProcess([], 1, b"synthetic nonpublic text", b"synthetic nonpublic diagnostic")
            with patch.object(reader.subprocess, "run", return_value=failure):
                result = reader.analyze(directory)
            rendered = json.dumps(result)
            self.assertEqual(result["counts"]["extraction_failures"], 1)
            self.assertNotIn("nonpublic", rendered)
            self.assertNotIn(directory, rendered)
            self.assertNotIn("input.pdf", rendered)

    def test_final_report_is_not_an_application(self):
        matcher = load_module("private_match.py")
        synthetic = b"Final report\nApplication form\nProject description\nApplicant organisation\nDeclaration on honour"
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "input.pdf").write_bytes(b"synthetic placeholder")
            with patch.object(matcher.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, synthetic, b"")):
                counts, pairs = matcher.match_in_memory(directory)
            self.assertEqual(counts["final_report_documents"], 1)
            self.assertEqual(counts.get("application_documents", 0), 0)
            self.assertEqual(pairs, [])
            self.assertNotIn("input.pdf", json.dumps(counts))

    def test_matching_policy_requires_name_code_stage_and_scope(self):
        policy = CONFIG["matching_policy"]
        self.assertEqual(policy["storage"], "RAM-only-no-private-case-table")
        self.assertTrue({"project-code-agreement", "verified-application-internal-title", "unique-on-both-sides", "application-stage-confirmed", "scope-not-contradictory"} <= set(policy["required"]))
        self.assertIn("never-sufficient-alone", policy["filename"])
        self.assertIn("final-reports-as-applications", policy["exclude"])
        self.assertIn("no-invented-pair", policy["zero_pairs"])


if __name__ == "__main__":
    unittest.main()
