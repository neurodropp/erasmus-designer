# Decision on the sanitised KA220 reference profile

The clean distribution retains only a sanitised structural profile and a reusable question playbook. The user-supplied DOCX, its extracts, hashes, metadata, examples, and provenance are private and are not shipped. The profile is not a verified official application form for the current call.

- Structural profile: `config/forms/ka220-user-template.json`, marked non-official and not current-call verified.
- Reusable playbook: `wiki/templates/ka220-question-playbook.md`.
- Required next input: the actual form for the selected year, round, action, sector, country, and agency.

## Distinguishing sources of authority

The relationship between each question and award sub-criterion is an interpretive mapping. A structural profile, example, or internal playbook does not establish a rule, character limit, upload requirement, or score. These must be verified against the applicable call, official guide, expert guide, and live form.

For a relevant KA220 route, Programme Guide 2026 p.243 and the expert guide p.49 confirm a maximum 20% management allocation. Do not infer a 10% minimum or 25% tolerance from non-normative examples. Re-verify the rule for the actual call before use.

The guide p.243 recommends a maximum of four implementation work packages. This is a recommendation rather than a universal hard limit; any departure requires justification and verification against the actual form and call.

Annex materials are preparation guides. Whether annexes are required or may be uploaded, and any file limits, must be checked against the current call and form. Any example content is non-normative and must never be treated as data for a user's project.

## Coverage and checks

The sanitised profile preserves structural field and occurrence identities needed by the checking scripts, but removes rich example answers, user-file paths, source metadata, and private provenance. Changes to structure, prompts, conditional fields, repetition, or limits require a new verified form intake; the existing profile does not certify another form.

No real application is generated and no score is estimated. No API or provider calls are made, and nothing is written to LWC; integration is left to the coordinator after review.

## Gaps to resolve before use

- Confirm the year, round, sector, agency, and current official form.
- Compare fields, questions, counting modes, and maximums against the actual form.
- Replace historical priorities and template references to pages 200–206 with applicable 2026 sources.
- Confirm which annexes are permitted or required and the attachment limits.
- Confirm partner, participant, activity, resource, and result data before drafting.

## Reproduction

Run with the bundled Python: `python3 scripts/extract_application_template.py --source '<path-to-template.docx>'`. Output is deterministic for the same input; the original file is not modified. Excluded private evidence and audit materials are not shipped.
