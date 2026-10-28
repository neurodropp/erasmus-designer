---
program: SHARED
---
# Erasmus Designer — Erasmus+ and ESC second brain

Consult the relevant action first, then the original evidence. The initial corpus concerns the 2026 call; the maps do not replace the actual application form or the online check before applying.

- [Actions and sectors](indice-azioni.md): 50 routes, 43 Erasmus+ and 7 ESC, with guide sections and usual National Agency.
- [Sources](indice-fonti.md): PDF, EU site and Italian provisions with local snapshots.
- [Italian priorities](research/priorita-italiane-2026.md): INDIRE, INAPP and AIG areas verified separately.
- [Good practices](research/buone-pratiche-application.md): distinct requirements, criteria, methods and recommendations.
- [Conflicts and limitations of sources](topics/conflitti-fonti.md).
- [KA210 and KA220 2026](topics/griglie-ka210-ka220-2026.md) scoring grids: maximum scores, thresholds and limits of simulation.
- [Review template](templates/revisione-application.md).
- [Project design dossier](templates/progettazione.md).
- [Multi-agent loop](../docs/multiagent-loop.md) and [coordinator skill](../skills/erasmus-designer/SKILL.md).
- [Pipeline and usage](../README.md).

## Form, annexes and integrated workflow

- [Ten-step workflow](topics/workflow-erasmus-esc.md), with criticism and intermediate checks.
- [KA220 question playbook](templates/ka220-question-playbook.md): 98 patterns and 346 occurrences; criteria, table guidance, examples, structure and limits of template2025.
- [Response contract](templates/response-contract.md): planning, sources and validation against the current form.
- [Application memory](templates/project-memory-contract.md): shared data and IDs across all views.
- [Workbook catalogue](templates/annex-template-catalog.md) and [15 blueprints with dedicated owners](templates/annex-blueprints.md).
- [ESC2026](research/esc-2026-routing.md): two guides, actions/roles, priorities and own rubrics.

Search: `python3 scripts/brain.py search "evaluation criteria" --action KA220 --sector ADU`.
Evidence: add `--layer evidence` and open the ID with `show`. Dossier: `python3 scripts/brain.py dossier --action KA220 --sector ADU`.

LWC memory is canonical and uses `scripts/lwc search "question" --limit 5`; `wiki/` retains readable editorial pages and compilation materials. Do not manually edit `.lwc/wiki` projections.

[[orchestrator-architecture]] · [[compliance-checklists]]

## Design and initial validation

- [Phase 0 Idea Lab](../docs/phase-zero-idea-lab.md) and [decision contract](templates/phase-zero-decision-contract.md): brainstorming, route, priorities, target groups, results chain, scale and `PROCEED|REFINE|PIVOT|STOP` before dossier creation.
- [Design method](../docs/design-methodology.md): diagnosis, ToC, logical framework, SMART/RACER and applicable criteria.
- [Award checklist by typology](checklists/award-criteria/index-award-idea-2026.md): 50 routes, 45 profiles for 2026, maturity and gap plans at the idea stage.
- [Use and gate of checklists](../docs/award-idea-checklists.md).
