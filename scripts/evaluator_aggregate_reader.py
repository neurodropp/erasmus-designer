"""Read external PDFs locally and retain only aggregate counts from a fixed vocabulary.

The script does not print or write private text, identifiers, paths, metadata,
errors, or document-level records. Classification and polarity are conservative
heuristics, not semantic judgments. Pass the external directory as the sole
argument.
"""
import collections
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

_role_spec = importlib.util.spec_from_file_location("private_roles", Path(__file__).with_name("evaluator_private_match.py"))
_role_module = importlib.util.module_from_spec(_role_spec)
_role_spec.loader.exec_module(_role_module)

THEMES = {
    "needs": r"\b(?:need\w*|bisogn\w*|baseline|fabbisogn\w*)\b",
    "objectives": r"\b(?:objectiv\w*|obiettiv\w*|coheren\w*|coeren\w*)\b",
    "methods": r"\b(?:method\w*|metod\w*|learning|apprendimento)\b",
    "partnership": r"\b(?:partner\w*|cooperat\w*|cooperaz\w*|complementar\w*)\b",
    "inclusion": r"\b(?:inclusion\w*|inclusione|accessibil\w*|fewer opportunities|minori opportunit\w*)\b",
    "monitoring": r"\b(?:monitor\w*|indicat\w*|valutazione|evaluat\w*|misur\w*)\b",
    "impact": r"\b(?:impact\w*|impatto|sustainab\w*|sostenibil\w*)\b",
    "dissemination": r"\b(?:dissemin\w*|diffusione|communication|comunicazione)\b",
    "resources": r"\b(?:budget|cost\w*|costi|risorse|resources|proportion\w*)\b",
    "youth_participation": r"\b(?:youth|young people|giovani)\b.*\b(?:involv\w*|coinvol\w*|partecip\w*|particip\w*)\b",
}
NEGATIVE = re.compile(r"\b(?:not|lack\w*|unclear|insufficien\w*|weak\w*|generic\w*|non|manca\w*|carent\w*|critic\w*|poco|tuttavia|however|but)\b", re.I)
POSITIVE = re.compile(r"\b(?:clear\w*|strong\w*|adequat\w*|appropriat\w*|well|coherent\w*|chiaro|chiaramente|adeguat\w*|buon\w*|efficac\w*)\b", re.I)


def analyze(directory):
    counts = collections.Counter()
    observations = {key: collections.Counter() for key in THEMES}
    for path in Path(directory).rglob("*"):
        if not path.is_file() or path.suffix.lower() != ".pdf":
            continue
        counts["pdfs"] += 1
        result = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True)
        if result.returncode:
            counts["extraction_failures"] += 1
            continue
        text = result.stdout.decode("utf-8", errors="replace")
        pages = text.split("\f")
        if pages and not pages[-1].strip():
            pages.pop()
        counts["pages_extracted"] += len(pages)
        blank = sum(len(re.findall(r"\w", page)) < 40 for page in pages)
        counts["pages_text_insufficient"] += blank
        if blank:
            counts["pdfs_with_text_insufficient_pages"] += 1
        if len(re.findall(r"\w", text)) < 100:
            counts["pdfs_text_insufficient"] += 1
            continue
        counts["pdfs_text_readable"] += 1
        # Inspect full text. Role tests require characteristic combinations.
        lower = text.lower()
        role = _role_module.classify_document(text)
        counts["pdfs_role_" + role] += 1
        header = lower[:12000]
        actions = set(re.findall(r"\b(?:ka\d{3}(?:-[a-z]{3})?|esc\d{2})\b", header))
        years = set(re.findall(r"\b20(?:1\d|2\d)\b", header))
        agencies = set(re.findall(r"\b(?:indire|inapp|eacea|ang|aig)\b", header))
        counts["pdfs_with_action_markers"] += bool(actions)
        counts["pdfs_with_year_markers"] += bool(years)
        counts["pdfs_with_agency_markers"] += bool(agencies)
        if role != "assessment":
            continue
        # Paragraph-level topic + evaluative polarity; a hit is not a finding.
        units = re.split(r"\n\s*\n|(?<=[.!?])\s+", lower)
        for theme, pattern in THEMES.items():
            matching = [unit for unit in units if re.search(pattern, unit, re.S)]
            if matching:
                observations[theme]["assessment_documents_with_topic"] += 1
            if any(NEGATIVE.search(unit) for unit in matching):
                observations[theme]["assessment_documents_with_qualified_or_negative_clause"] += 1
            if any(POSITIVE.search(unit) and not NEGATIVE.search(unit) for unit in matching):
                observations[theme]["assessment_documents_with_positive_clause"] += 1
    return {"method": "complete_local_text_extraction_and_fixed_vocabulary_heuristic_screening",
            "counts": dict(counts), "topic_observations": {key: dict(value) for key, value in observations.items()},
            "interpretation": "topic_or_polarity_hits_are_not_verified_evaluator_findings; matching_is_separate_in_private_match; no_private_case_trace_retained"}


if __name__ == "__main__":
    try:
        print(json.dumps(analyze(sys.argv[1]), ensure_ascii=False, indent=2))
    except Exception:
        print(json.dumps({"error": "Local analysis failed; no private details were emitted."}))
        raise SystemExit(1)
