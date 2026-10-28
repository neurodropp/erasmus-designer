"""Conservative external matching in RAM; stdout is aggregate counts only.

Project codes are internal-primary; an explicit complete original metadata
code/name may corroborate under the documented hierarchy, never alone.
No individual table, extracted text, metadata, identifiers or private hashes
are written. Do not redirect any internal records to a log or add debug prints.
"""
import collections
import json
from pathlib import Path
import re
import subprocess
import sys
import unicodedata


def normalize(value):
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


# Equivalent separators and invisible line-break artifacts only; never O/0,
# I/1, fuzzy digits, a form-ID substitution or filename inference.
CODE_TRANSLATION = str.maketrans({character: "-" for character in "‐‑‒–—−﹘﹣－"})
TITLE_LABEL = re.compile(r"^[ \t]*(?:project title(?: in english)?|title of the project|project name|titolo del progetto|titolo progetto|nome del progetto)\s*:?[ \t]*(.*)", re.I)
FIELD_LABEL = re.compile(r"^(?:project (?:title|name|acronym|code|start|end|duration|budget|number|description)|form (?:id|identification)|application (?:id|code|form)|call|round|action|national agency|applicant|organisation|participating|titolo|nome del progetto|codice|acronimo|durata|data|agenzia|organizzazione|descrizione|declaration|context|content|summary|budget|EN\b|IT\b)", re.I)
PLACEHOLDERS = {"", "-", "_", "n/a", "na", "none", "null", "tbd", "tbc", "not applicable", "not available", "to be defined", "to be completed", "untitled", "project title", "project name", "title", "titolo", "titolo del progetto", "nome del progetto", "da definire", "da compilare", "non applicabile"}
FINAL_REPORT = re.compile(r"(?:final[ -]+(?:beneficiary[ -]+)?report|beneficiary[ -]+(?:final[ -]+)?report|rapporto[ -]+finale|report[ -]+finale|relazione[ -]+finale|rendiconto[ -]+finale|rendicontazione[ -]+finale|final[ -]+project[ -]+report|rapport[ -]+final|informe[ -]+final)", re.I)


def _extract_codes_on_page(text):
    equivalent = unicodedata.normalize("NFKC", text).translate(CODE_TRANSLATION)
    equivalent = equivalent.replace("\u00ad", "").replace("\u200b", "").replace("\ufeff", "")
    return {re.sub(r"\s+", "", value) for value in re.findall(r"(?<![A-Z0-9])20\d{2}\s*-\s*\d+\s*-\s*[A-Z]{2}\d{2}\s*-\s*(?:KA\d{3}|ESC\d{2})(?:\s*-\s*[A-Z]{3})?\s*-\s*\d+(?![A-Z0-9])", equivalent.upper())}


def extract_codes(text):
    """Recognize complete codes within individual pages, never across formfeed."""
    return {code for page in text.split("\f") for code in _extract_codes_on_page(page)}


def extract_titles(text):
    """Preserve page boundaries before splitting lines or normalizing values."""
    return {title for page in text.split("\f") for title in _extract_titles_on_page(page)}


def _extract_titles_on_page(text):
    """Read only labelled title fields; preserve conservative layout boundaries.

    A short title is legitimate. A continuation must be in the value column
    and end before a blank, page break or known field. No substring search in
    arbitrary narrative: it would create false matches for short titles.
    """
    names = set()
    lines = text.splitlines()
    for index, line in enumerate(lines):
        found = TITLE_LABEL.search(line)
        if not found:
            continue
        value = found.group(1).strip()
        value_column = found.start(1)
        next_index = index + 1
        if not value and next_index < len(lines):
            next_line = lines[next_index]
            if not next_line.strip() or FIELD_LABEL.match(next_line.strip()):
                continue
            value = next_line.strip()
            value_column = len(next_line) - len(next_line.lstrip())
            next_index += 1
        if normalize(value) in PLACEHOLDERS or not re.search(r"\w", value):
            continue
        # If another labelled field shares the row, its column is not title.
        columns = re.split(r"[ \t]{2,}", value)
        if len(columns) > 1 and any(FIELD_LABEL.match(column.strip()) for column in columns[1:]):
            value = columns[0].strip()
        continuation_count = 0
        while next_index < len(lines):
            continuation = lines[next_index]
            if not continuation.strip() or FIELD_LABEL.match(continuation.strip()) or extract_codes(continuation):
                break
            indentation = len(continuation) - len(continuation.lstrip())
            if indentation < value_column:
                break
            if continuation_count >= 4:
                # Do not manufacture a partial title from an unbounded block.
                value = ""
                break
            value += " " + continuation.strip()
            continuation_count += 1
            next_index += 1
        normalized = normalize(value)
        if normalized not in PLACEHOLDERS and re.search(r"\w", normalized):
            names.add(normalized)
    return names


def classify_document(text):
    lower = text.lower()
    header = lower[:12000]
    assessment = bool(re.search(r"(?:quality assessment|assessment sheet|assessment report|scheda di valutazione|valutazione qualitativa|commenti dell.esperto|comments for the applicant|commenti per il richiedente|evaluation summary report)", lower))
    application = bool(re.search(r"(?:application form|formulario di candidatura|declaration on honour|declaration of honour)", lower)) and bool(re.search(r"(?:project description|descrizione del progetto|participating organisations|organizzazioni partecipanti|applicant organisation)", lower))
    final_report = any(FINAL_REPORT.match(line.strip()) for line in header.splitlines())
    # Beneficiary Module plus explicit reporting interface and retrospective
    # form questions establishes reporting stage, without guessing finalness.
    retrospective = bool(re.search(r"(?:how\s+did\s+you|how\s+were\s+the|what\s+were\s+the|what\s+was\s+the)", lower))
    flat = normalize(text)
    self_report_module = bool(re.search(r"(?:this|your) report.{0,300}beneficiary module|beneficiary module.{0,300}(?:this|your) report", flat))
    reporting_document = self_report_module and retrospective
    if final_report:
        return "assessment_final_report" if assessment else "final_report"
    if reporting_document:
        return "assessment_reporting_document" if assessment else "beneficiary_report"
    if assessment and not application:
        return "assessment"
    if application and not assessment:
        return "application"
    return "ambiguous"


METADATA_LABELS = ("scheda di valutazione", "quality assessment", "assessment report", "evaluation report", "valutazione", "valutazioni", "assessment", "evaluation", "esito", "esiti")


def normalize_title_delimiters(value):
    return normalize(value.replace("_", " ").replace("-", " "))


def metadata_title_identity(filename):
    """Predetermined labels + explicit complete code only; no fuzzy cleanup."""
    if "\f" in filename:
        return ""
    value = unicodedata.normalize("NFKC", filename).translate(CODE_TRANSLATION)
    value = value.replace("\u00ad", "").replace("\u200b", "").replace("\ufeff", "")
    value = re.sub(r"(?<![A-Z0-9])20\d{2}\s*-\s*\d+\s*-\s*[A-Z]{2}\d{2}\s*-\s*(?:KA\d{3}|ESC\d{2})(?:\s*-\s*[A-Z]{3})?\s*-\s*\d+(?![A-Z0-9])", " ", value, flags=re.I)
    value = normalize_title_delimiters(value)
    for label in METADATA_LABELS:
        # Prefix/suffix labels only: never delete words from the project title.
        value = re.sub(r"^" + re.escape(label) + r"(?:\s+|$)", "", value).strip()
        value = re.sub(r"(?:^|\s+)" + re.escape(label) + r"$", "", value).strip()
    return value


def scope_not_contradictory(text, code):
    header = unicodedata.normalize("NFKC", text[:12000]).translate(CODE_TRANSLATION).upper()
    parts = code.split("-")
    years = set(re.findall(r"\b(?:CALL|ANNO|YEAR)\s*:?\s*(20\d{2})\b", header))
    actions = set(re.findall(r"\b(?:KA\d{3}|ESC\d{2})(?:-[A-Z]{3})?\b", header))
    expected_action = parts[3] + ("-" + parts[4] if len(parts) == 6 else "")
    return (not years or years == {parts[0]}) and (not actions or actions <= {parts[3], expected_action})


def application_stage_verified(text):
    header = text[:12000]
    if re.search(r"(?:application form|formulario di candidatura|(?m:^\s*application\s*$))", header, re.I):
        return True
    # Form-ID verifies the kind of form, never substitutes for a grant code.
    return bool(re.search(r"form[ -]+id", header, re.I) and re.search(r"\bcall\s*:?\s*20\d{2}\b", header, re.I) and re.search(r"action[ -]+type", header, re.I))


def metadata_scope_matches(text, code):
    header = unicodedata.normalize("NFKC", text[:12000]).translate(CODE_TRANSLATION).upper()
    parts = code.split("-")
    years = set(re.findall(r"\b(?:CALL|ANNO|YEAR)\s*:?\s*(20\d{2})\b", header))
    actions = set(re.findall(r"\b(?:KA\d{3}|ESC\d{2})(?:-[A-Z]{3})?\b", header))
    expected_action = parts[3] + ("-" + parts[4] if len(parts) == 6 else "")
    # No absent/ambiguous year, incompatible sector, or historical inference.
    return years == {parts[0]} and bool(actions) and actions <= {parts[3], expected_action}


def match_in_memory(directory, metadata_fallback=False):
    counts = collections.Counter()
    records = []
    root = Path(directory)
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() != ".pdf":
            continue
        result = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True)
        if result.returncode:
            counts["extraction_failure"] += 1
            continue
        text = result.stdout.decode("utf-8", errors="replace")
        role = classify_document(text)
        internal_codes = extract_codes(text)
        # Original relative filename/folders are private metadata in RAM only.
        metadata_codes = extract_codes(" ".join((root.name, *path.relative_to(root).parts))) if metadata_fallback else set()
        conflict = bool(internal_codes and metadata_codes and internal_codes != metadata_codes)
        codes = internal_codes or metadata_codes
        origin = "internal" if internal_codes else "original-metadata" if metadata_codes else "missing"
        names = extract_titles(text)
        counts[role + "_documents"] += 1
        counts[role + "_with_internal_code"] += bool(internal_codes)
        counts[role + "_with_original_metadata_code"] += bool(metadata_codes)
        counts[role + "_with_internal_title_field"] += bool(names)
        counts["documents_internal_metadata_code_conflict"] += conflict
        records.append((role, codes, names, text, origin, conflict, metadata_title_identity(path.stem) if metadata_fallback else ""))
    provisional = []
    for index, (role, codes, names, text, origin, conflict, metadata_title) in enumerate(records):
        if role in {"assessment_final_report", "assessment_reporting_document"}:
            counts["assessment_rejection_phase"] += 1
            counts["assessments_not_confirmed"] += 1
            continue
        if role != "assessment":
            continue
        reason = None
        if conflict:
            reason = "internal_metadata_code_conflict"
        elif not codes:
            reason = "missing_code"
        elif len(codes) != 1:
            reason = "multiple_or_discordant_codes"
        candidates = [other for other, (other_role, other_codes, _, _, _, _, _) in enumerate(records)
                      if other_role == "application" and codes & other_codes]
        excluded_phase = any(other_role in {"final_report", "beneficiary_report", "assessment_final_report", "assessment_reporting_document", "ambiguous"} and codes & other_codes
                             for other_role, other_codes, _, _, _, _, _ in records)
        if reason is None and not candidates:
            reason = "phase" if excluded_phase else "no_counterpart_code"
        elif reason is None and len(candidates) != 1:
            reason = "duplicate_counterpart"
        if reason is None:
            counts["unique_project_code_candidates"] += 1
            other = candidates[0]
            application = records[other]
            if application[5]:
                reason = "internal_metadata_code_conflict"
            elif len(application[1]) != 1:
                reason = "multiple_or_discordant_codes"
            elif not application_stage_verified(application[3]):
                reason = "phase_unverified"
            elif (origin == "original-metadata" and not metadata_scope_matches(text, next(iter(codes)))) or (application[4] == "original-metadata" and not metadata_scope_matches(application[3], next(iter(codes)))):
                reason = "metadata_scope_unverified_or_discordant"
            elif not application[2]:
                reason = "missing_application_internal_title"
            elif names and not names & application[2]:
                # An internal title conflict wins over an agreeing filename.
                reason = "title_disagreement"
            elif not names and (not metadata_fallback or metadata_title not in {normalize_title_delimiters(name) for name in application[2]}):
                reason = "missing_title"
            elif not scope_not_contradictory(text, next(iter(codes))) or not scope_not_contradictory(application[3], next(iter(codes))):
                reason = "scope_discordant"
            else:
                title_origin = "internal" if names else "original-metadata"
                counts["code_candidates_with_internal_name_agreement" if names else "code_candidates_with_exact_original_metadata_name_agreement"] += 1
                provisional.append((index, other, "metadata-corroborated" if origin == "original-metadata" or application[4] == "original-metadata" or title_origin == "original-metadata" else "internal"))
        if reason is not None:
            counts["assessment_rejection_" + reason] += 1
            counts["assessments_not_confirmed"] += 1
    application_count = collections.Counter(other for _, other, _ in provisional)
    accepted = [(index, other, origin) for index, other, origin in provisional if application_count[other] == 1]
    pairs = [(records[index][3], records[other][3]) for index, other, _ in accepted]
    counts["both_internal_name_and_code_pairs_confirmed"] = sum(origin == "internal" for _, _, origin in accepted)
    counts["metadata_corroborated_pairs_confirmed"] = sum(origin == "metadata-corroborated" for _, _, origin in accepted)
    counts["both_name_and_project_code_pairs_confirmed"] = len(pairs)
    duplicate_count = sum(application_count[other] != 1 for _, other, _ in provisional)
    counts["assessment_rejection_duplicate_counterpart"] += duplicate_count
    counts["assessments_not_confirmed"] += duplicate_count
    records.clear()
    return dict(counts), pairs


if __name__ == "__main__":
    try:
        counts, pairs = match_in_memory(sys.argv[1], metadata_fallback=True)
        pairs.clear()
        print(json.dumps({"procedure": "Complete project code matched from document content, with explicit original-metadata fallback; internal application title matched to an internal assessment title or exact original-metadata identity; unique counterpart required; application stage and metadata scope verified; form-ID-only and filename-only matches excluded", "aggregate_counts": counts}, indent=2))
    except Exception:
        print(json.dumps({"error": "Local matching failed; no private details were emitted."}))
        raise SystemExit(1)
