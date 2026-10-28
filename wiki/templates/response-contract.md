---
program: SHARED
status: operational-method
---
# Design contract and response control

For each field, keep the exact question, form version/year/action, locator, counting maximum and convention, relevant criteria, data, sources and structure. Apply [the design method](../../docs/design-methodology.md) using the approved design and canonical model as input, in the language of your choice. The [KA220](ka220-question-playbook.md) playbook collects user document content per question; its year 2025 and the examples do not certify the 2026 form.

`application/answer-plan-vN.md` is the versioned product of the `answer-outlines` phase in the integrated process (`draft` in the compact: plan before writing and freeze plan and texts in the same gate), relating to the file: it includes plans and criterion/question/instance matrix, referring to `design/design-plan-vN.md`, `project.json` and tests. Pass it explicitly as a step-product to the gate and writer. `answer-outlines.md` can present its content, without a second truth. An accepted plan cannot be rewritten: new version and invalidation of the proprietary phase with dependent checks.

## Planning before writing

To limit the context use `python3 scripts/form_profile.py list` and `python3 scripts/form_profile.py show wp-main-results --max-chars 8000`. The result states offset, coverage and next window: if incomplete, continue with `--offset` until you read the entire relevant section. The `occurrence_id` field explicitly associates the instance boundary and locator; don't use another WP to get a higher cap.

Internal planning controls: what the field asks, what criteria it supports, what information is needed, what evidence supports it, what details are missing, what structure makes it understandable, and how much space to allocate to each part. Keep a **checklist and a summary reason for the choice**, not an internal chain of thought.

The plan selects the elements required by the question from the participatory diagnosis/gap analysis, from the problem/objective trees, from the ToC and from the logical framework. Maintains observable links and relevant assumptions; it doesn't paste the entire framework into each field. SMART/RACER supports objectives and measures when relevant, with evidence or feasibility gaps and sharing. For example, needs: documented problem/target, current/desired situation, gap and addressable cause; partners: proven capabilities, role in ToC and complementarity; activities: mechanism and resources; WP results: verifiable outputs, plausible outcomes, use/adoption and acceptance; impact: lasting change, contributing factors, monitoring and contribution. For KA152 include young people's real choices/tasks and learning in the relevant fields.

## Criterion/question/instance matrix

| Official criterion/subpoint and source/version/scope | Application/instance and locator | Claim/design element and ID | Proof or gap | Official/interpretive mapping or reasoned NA | Structure and editorial fees |
|---|---|---|---|---|---|
| Verified route grid | Exact pair of form | Return to plan/model | Real data or collection necessary | Origin of the association | Within verified cap of the same couple |

Consider cross-coverage: a criterion can be supported in multiple fields and an item support multiple criteria; check consistency and repetitions. Official association only with relevant proof, otherwise reasoned interpretation. An administrative field has NA for evaluation coverage, with reason and control of its obligations; he doesn't receive a made-up grade. The sub-points guide the criterion, without official sub-marks per question. Named coverage and project support are different.

The methodological sources do not certify the question, limit or obligation of the form. Handbook2026 for your own KA2 Partnerships for Cooperation NA only; Impacttool KA1/KA2 only for formulating/verifying change logic. Your 20 words or exercise time windows do not become response caps or deadlines; no transfer of Erasmus+ rules to ESC.

## Character budget

1. Read the limit from the current field, not from a similar question. Maximum unknown: Record `null` and verify it; Don't make up a number.
2. When known, use approximately 95% as the initial operating target, without a mandatory minimum. The length needed depends on the answer. The limit remains 100%.
3. Distribute the target among specific elements of the plan. Each quota is an editorial choice, not an award criterion. The sum of the odds must remain within the target.
4. Write the text that will actually be pasted into the field. Checklists, internal quotes, working titles and notes remain separate; if they are glued, they enter the count.
5. Count spaces, punctuation and carriage returns. Local control shows Unicode code points and UTF-16 units, with raw counts and normalized LF; use maximum conservatively. Confirm the counter online, especially for emoji and CRLF.
6. Reduce repetitions, vague formulas and irrelevant details first. Do not eliminate decisive evidence or conditions for re-entry; do not truncate automatically. Double-check all fields affected by the change.

## Response record

`answers.json` contains `form_instance` and `answers`. Each answer has `question_id`, `instance` for repeating WPs/partners/tasks and `text` plain text. A different maximum from the profile requires `max_chars`, `limit_verified=true` and `verification_source` of the real field. In the form_instance, record program/year/action/sector/round, form test, `current_call_verified`, `coverage_verified`, `all_limits_verified` or field confirmations, and the actual `required_instances`s. Do not declare these checks completed solely due to the availability of the template.

```bash
python3 scripts/application.py projects/nome--ka220-youth--2026/answers.json --profile config/forms/ka220-user-template.json --output projects/nome--ka220-youth--2026/reports/character-check.json
```

The `--strict` check requires confirmation of the current scoresheet, coverage, required responses, limits and no placeholders. In the integrated workflow the same check is applied before concluding QA. The profile of questions must be specific to the action: ESC and other categories require their own forms.

## Review and verification

Current coverage requires a `form_instance.applicable_fields` array: for each profile ID indicate instance, boolean `required` and form test/locator. For a field outside the current form indicate `not_applicable=true`, `required=false` and reason. The examples and editorial fields of the DOCX are not automatically fields to be sent. The checker compares the matrix with the answers and flags no-decision IDs, missing required answers, and texts in non-applicable fields. The matrix makes coverage verifiable; the correct interpretation of the form remains with the evidence specialist.

For each answer, check relevance, completeness with respect to the field, credibility of the evidence, difference between fact and hypothesis, consistency with the model and annexes and maximum limit. Distinguish output, outcome (`results`) and contribution to impact; participation/diffusion does not automatically demonstrate change. Criteria coverage is a motivated association; do not invent official subscores per question. No text can remedy a substantial design problem without changing the design.

**Stop and return to owner:** unsupported need/mechanism/target requires research or redesign and coordinated update of dependencies; unresolved field/form/limit or mandatory data keeps the response in draft form. Deliver plans, texts, reports of checks carried out and open issues, without certifying checks not carried out. [[ka220-question-playbook]] · [[workflow-erasmus-esc]] · [[project-memory-contract]]

## Instance identity and profile integrity

`form_profile.validate_profile` precedes reading and counting: question and occurrence IDs must be unique and contract structured fields have valid types. `questions` is the regulatory register of the acquired profile; `fields` preserves editorial enrichments for the same IDs without overwriting them. The provided template maintains 98 patterns/346 occurrences, year2025, with test2026 and current limits still open.

In strict each answer must belong to the matrix for the exact pair `(question_id, instance)`; an NA on another instance doesn't resolve that answer. The pairs in the matrix are unique. `required_instances` must refer to pairs already declared. For the current form the motivated matrix governs obligations and conditions, including template fields that do not belong to the actual form.

The canonical contexts are `partner_id`, `wp_id`, `activity_id`, `role`. The reader accepts the editorial aliases `partner`, `work_package` (intero2 → WP2), `activity`, `contact_role`; conflicting aliases are errors. `P2`, `WP2`, `A2` in `instance` declare those identities: they cannot use the physical occurrence of another partner/WP/task. In multiple cases, for example two contact roles of the same partner, specify `context` and `occurrence_id`. Sample task numbers and workbook layouts are not transformed into real identities.

An additional repeating field of the current form can be declared in the array with instance, context and its own `verification_source`. If the previous profile indicated it was not repeatable, the matrix also requires `current_repeatable=true` and proof of the current repeat. The new limit requires verification for that field/override; if the matrix records `max_chars`, the response boundary must agree. A response with an unlisted instance or a non-existent physical ID remains an error, even when the cap is numerically respected.

## Occurrence identity dimensions

The context of a selected occurrence must represent **all** explicit/inferred identities of the response and the array, with equal values. A `instance=WP9` cannot select a field whose context represents only partner/role, even if the dimensions have no common keys. Unknown runtime keys are not ignored.

An unconventional alias registered in the array can select an occurrence by ID, maintaining its identity and a compatible context. An additional current repeating field, for example P3 after P1/P2, requires its own context and evidence and must use dimensions already represented by the field type in the profile. If the current form introduces a different dimension, update and verify the profile with the new occurrence; do not borrow an occurrence of another type for its limit. A profile without physical occurrences can instead use the new contextualized and documented instances of the current matrix. [Repairs and limitations](../../docs/model-form-repairs-0.2.1.md).
