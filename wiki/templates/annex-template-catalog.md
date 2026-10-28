---
program: SHARED
title: Sanitized annex template catalogue
type: template-catalog
official: false
distribution: clean
---

# Annex template catalogue

The clean distribution does not include user-supplied workbooks, completed examples, organisation data, historical budgets, contacts, document hashes, or cell-level extracts. Annexes are generated from the verified project model and the owner declared in `config/annexes.json`.

| Annex family | Owner skill | Canonical input |
|---|---|---|
| Detailed budget | `erasmus-annex-budget` | approved activities, partners, financial model and verified rates |
| Work packages and deliverables | `erasmus-annex-work-packages` | project model IDs, responsibilities, outputs and milestones |
| Gantt and milestones | `erasmus-annex-gantt` | accepted tasks, dependencies and dates |
| Dissemination | `erasmus-annex-dissemination` | audiences, channels, owners, indicators and evidence |
| Monitoring and risk | `erasmus-annex-monitoring-risk` | indicators, quality gates, risks, owners and responses |
| KPI and evidence plan | `erasmus-annex-kpi` | objectives, baselines, targets, measurement method and evidence |
| KA2 task file | `erasmus-annex-ka2-task-file` | common task, result, partner and reporting registries |
| Agreements and participant rules | corresponding contract/rules owner | verified legal, programme and organisational inputs |

These are internal management artefacts unless the current call or form explicitly requires an upload. A template never establishes eligibility, rates, mandatory annex status, or reporting evidence. Users may import their own workbook locally, but it must remain outside Git and must be reviewed for privacy, formula integrity, applicability and current-call alignment.
