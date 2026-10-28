---
name: erasmus-application-writing
description: Writes Erasmus+/ESC responses from verified plans and data, checking language, instances, and character counts.
---

# Erasmus+ application writing

Read the [response contract](../../wiki/templates/response-contract.md) and award criteria/response section of the [design methodology](../../docs/design-methodology.md). Use `application/answer-plan-vN.md`, the approved design, and the relevant profile; for the user's KA220 DOCX, consult only the necessary sections of the [playbook](../../wiki/templates/ka220-question-playbook.md). It is an internal2025 template: advice/examples and conflicts do not certify the current form or real data.

Save plain text for each field/instance in `answers.json` and use `scripts/application.py` after every change. Include spaces and line breaks; do not truncate automatically or count only the shortened displayed version. Show the maximum, count, and remaining space. An unknown or unverified call limit means the response cannot be declared ready. The drafting checklist retains specific elements and evidence, not private internal reasoning.

Read the [evidence contract](../erasmus-designer/references/evidence-contract.md). Use the supplied or officially verified form version. If unavailable, produce a content draft mapped to the criteria and state its status: do not invent questions, fields, or limits.

**Input:** plan for each question/instance, model/evidence, form, and requested language. Keep the language chosen by the user; reading an English source does not authorize translating the entire application.

**Steps:** draft the specific elements required by the plan, answering the field at the outset; make operational choices, responsibilities, and mechanisms clear. Where relevant, use the documented gap, cause/objective link, ToC assumptions, SMART objectives, RACER indicators, and adoption pathway. Do not paste a complete logical framework into every field. Link claims and criteria across fields where relevant, distinguishing editorial mapping from official requirements and administrative NA from a missing response.

**Output:** plain text in `answers.json` for each question/instance pair, presented in form order, with a map of supported criteria and open issues. The plan and model remain the references; rewriting creates no new facts or commitments.

**Checks:** show the count result, limit/evidence, and remaining space; check the version that can actually be pasted. Distinguish outputs, outcomes (`results`), and contribution to impact, without substituting participation volumes or visibility for change. Naming a coverage area without evidence or a mechanism does not support the criterion; do not use subscores or limits from Impacttool.

**Stop:** a causal/feasibility gap returns to design before corrective wording; unresolved form, cap, or mandatory data prevent ready-to-submit text. Changes to accepted plans and dependencies require a new version and relevant invalidation through the coordinator.

Keep numbers, target groups, roles, calendar, budget, indicators, and result names consistent across sections. Do not invent statistics, partner experience, endorsements, consultations, or prior results. Retain citations and source IDs for rules in the working file; include citations in the form in the format appropriate to the question and its available space.

Respect the field's actual language, format, and limits; verify counts with a local tool when the limit is known. If mandatory data are missing, use an explicit placeholder in the working draft and record the required data. Do not leave placeholders in text declared ready for submission.

Deliver responses in form order, a map of covered criteria, and a short list of data still to confirm. Editorial changes must not alter approved facts or commitments without notifying the coordinator.
