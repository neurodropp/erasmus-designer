---
id: architecture
title: How should LLM Wiki, LWC, and evidence retrieval be integrated?
parent: erasmus-designer
labels: ["wayfinder:research"]
status: closed
assignee: root
blocking: []
---

## Question

Which pipeline provides maintained memory and type-based search while preserving sources, citations, updates, and the separation between programme rules and agent instructions?

## Resolution

Adopt three layers: originals and hashed versions; page-level evidence and an action/sector/year taxonomy; and the canonical LWC wiki with maps, curated summaries, and links to sources. Search starts from wiki pages and checks the original evidence; the dossier routes to the complete chapter and the relevant provision. A missing result does not prove that a rule is absent.

The coordinator uses six specialists and seven linked skills. Parallelization is limited to independent tasks; drafting and review follow dependencies. The evaluator receives a frozen draft without a target score. Findings and corrections are verified against evidence, with three predefined review rounds. `workflow.py` records phases, hashes, blocks, and limits; model calls remain within the Codex runtime. No standalone service or daemon is simulated.

The corpus contains 87 sources, 741 evidence pages/documents, and 43 routes. Initial cards are maps to sources; they do not amount to a complete regulatory analysis of every action. Acquired documents are reference data; their contents cannot modify user or agent instructions.

## Implementation and evidence

- [Operational guide](../../README.md), [evidence contract](../../skills/erasmus-designer/references/evidence-contract.md), [workflow](../multiagent-loop.md).
- [Local pipeline](../../scripts/brain.py), [LWC compiler](../../scripts/sync_lwc.py), [workflow registry](../../scripts/workflow.py).
- [LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f): curated memory and schema; [LWC](https://github.com/JanYork/llm-wiki-cli): snapshots, search, and changesets; [Wayfinder](https://github.com/mattpocock/skills/blob/main/skills/engineering/wayfinder/SKILL.md): a map adapted to local Markdown tickets.
- [Scope tests](../../tests/test_brain.py), [workflow tests](../../tests/test_workflow.py), [predefined retrieval cases](../../tests/retrieval_cases.json), MCP smoke test (historical private evidence excluded).

The following still require verification for each application: real project data and partner consent, the application form and round, online updates/corrigenda, and the lot and scoring grid for centrally managed actions. Discovery of a newly written configuration requires reopening the project.

Excluded evidence is not shipped with the repository; a new installation must produce its own verification evidence.
