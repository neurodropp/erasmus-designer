---
name: erasmus-wayfinder
description: Manages dependent project decisions and research to resume an application; the map does not replace tasks, the model, or gates.
---

# Project decision map

Identify the engine root and the complete application folder. First open the memory with [erasmus-project-memory](../erasmus-project-memory/SKILL.md), then run `python3 scripts/wayfinder.py context ID`. Retrieve the current map and only the tickets needed for the work. In new folders the map is empty: starting it does not confirm the idea, target groups, or partners.

When alternatives have dependencies, define an objective and real questions, distinguishing independent research from human choices. Use the research frontier to assign independent work to an owner; a question that still depends on another or is already claimed is unavailable. The human frontier identifies decisions to ask about when needed: an agent's agreement does not resolve them.

The [operating contract](../../docs/wayfinder.md) describes payloads, claims, blocks, resolution, and resumption. Before resolving, record the actual decision in memory, with the ticket tag and evidence. Link confirmed IDs from the application folder; a human choice requires observed `user-instruction` provenance. Do not invent consent or research outcomes.

A superseded premise or changed evidence blocks dependencies. `reopen` reopens the chain while preserving historical snapshots; a substantive requirement change also requires invalidating the relevant workflow. The map and memory do not by themselves modify `project.json`, close gates, or authorize submission, signatures, or contact. A phase review still requires a fresh validator.
