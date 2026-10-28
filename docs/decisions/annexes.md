---
id: annexes
title: Which annexes should be derived from the user's workbooks, and how should they be kept consistent?
parent: erasmus-designer
labels: ["wayfinder:research"]
status: closed
assignee: research-practices
blocking: []
---

## Question

Define reusable annex blueprints with a single owner, shared project data, and deterministic consistency checks, without distributing user-supplied workbooks or case-level extracts.

## Resolution

Treat any user-supplied workbook as private, non-normative input. Do not carry over organisation details, rates, targets, dates, examples, or historical instructions to another call. Each annex is internal and optional unless the verified application form or call explicitly requires it and supplies the relevant authority. Budget, schedule, work packages, KPIs, and registers are linked views of the same approved data model.

Assets:

- [Annex template catalog](../../wiki/templates/annex-template-catalog.md), containing only reusable, reviewed structures.
- [Operational blueprints and shared data model](../../wiki/templates/annex-blueprints.md), including contracts and participant rules as architecture that is not ready for signature.
- [Machine-readable configuration for the 15 annexes](../../config/annexes.json): exact owner/skill, columns, minimum inputs, checks, and source refs.
- [Reproducible extractor](../../scripts/extract_annex_templates.py), to be used only on inputs the user is authorised to process. Extraction outputs remain outside Git until independently sanitised and reviewed.

Private workbook names, contents, counts, formulas, errors, contacts, project codes, organisations, and extracts are intentionally absent from this distribution. Synthetic fixtures must be used for tests.

The budget distinguishes KA1/KA2/ESC by financial model: no template rate has been verified or inherited; ESC requires its own regulatory research before use. The workbooks do not contain complete contracts/reimbursement/code provisions. Define clauses/fields and issues for future validation without inventing applicable law, jurisdiction, rights, penalties, or rates.

Verification is extraction/structural analysis, not native recalculation or visual QA of the workbooks. These checks will be required for concrete annexes produced from real data. The coordinator integrates LWC/brain/skills/agents; this ticket made no shared changes.
