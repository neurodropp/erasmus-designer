# Acquiring the Current Application Form

The actual application form is an input required to start an application. There are two supported methods: the user provides an up-to-date export, or authorizes the assistant to read it on the platform using an authenticated session on the computer. Credentials do not need to be provided in chat. No platform access or new form has been provided at this time.

The orchestrator verifies the programme, year, action code, sector, agency, round, and language. It archives the original in `projects/ID/inbox/forms/` and a provenance record containing the URL or user-provided source, acquisition date, version, and SHA256. The sample PDF/DOCX remains distinct from the actual application. The template already indexed is the internal 2025 KA220-YOU template: its good practices remain available for reference, while its questions and limits are not evidence of a 2026 call.

## Reading the Form on the Platform

Prefer the official form export/print when available. If it does not contain all the data, read the sections in the interface: exact text, help text, whether each field is mandatory, maximum limit, live counter, tables, fields repeated for partners/WPs/activities, conditions that reveal other fields, attachments, and upload formats. Keep evidence localized to each item. A printed PDF may omit counters and conditional sections.

Reading the form does not authorize submission, signing, or changes to application data. If a section depends on data that has not yet been entered, mark it as unverified and agree on any necessary completion; do not change organizations, amounts, or answers to explore the form without a specific mandate. Screenshots and exports may contain personal data: keep them in the selected application file, excluded from the shared engine and the default export.

## Profile and Plan for Each Question

The specialist prepares `application/form-profile.json` in the format used by [application.py](../scripts/application.py): exact identity, stable IDs, questions, input types, instances, and limits with their sources. In `answers.json`, prepare the `form_instance.applicable_fields` matrix, including all conditional questions and actual instances. Set `current_call_verified`, `coverage_verified`, and `all_limits_verified` only after comparison with complete evidence, not to pass the gate.

Also link the acquired original in `answers.form_instance.form_source` with `path` relative to the application file and `sha256` of the actual bytes, for example the export in `inbox/forms/`. This binding allows the original, profile, and matrix to be frozen together during QA and human approval. Do not set it using a historical template in place of the current form, or recalculate only the hash to validate a modified original: reacquire it, compare it, and reopen the necessary checks. `bind-form` does not invent this provenance, and old receipts remain immutable.

Each question has a Markdown plan stating its objective, relevant award criteria, necessary content/evidence, response structure, missing data, and character budget. Practices and examples in the template are suggestions, distinct from the rules. No internal chain of thought is archived. The response must fit within the verified maximum, including spaces and line breaks; the checker retains conservative Unicode and UTF16 counts and does not automatically truncate the text.

The new validator compares the profile with the acquired form, including conditional sections, repeated fields, and limits. The coordinator binds the profile with `workflow.py bind-form ID --profile projects/ID/application/form-profile.json --report projects/ID/reports/form-binding.json`, using actual local evidence. Replacing a form invalidates dependent phases according to the workflow. The profile is required before answer-outlines; complete verification of the current form is required before QA. Idea, research, and concept work may proceed with the gap explicitly recorded.

This is the acquisition procedure: a universal extractor for every platform/form does not yet exist. The current DOCX extractor is specific to the user's template and must not be applied automatically to KA1 or ESC.
