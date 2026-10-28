# Recorded and Recoverable Working Memory

Each application keeps its own memory in `projects/ID/memory/`. The shared corpus contains rules and methods; the application memory contains what has emerged from its work: facts, decisions, relevant alternatives, hypotheses, open questions, contradictions, and status changes. The brief remains the readable request, and `project.json` the shared model. Memory records the basis for choices without becoming a second project model.

The responsible person records new information when it affects the project, with a summary and observable provenance. They do not record internal reasoning, full conversations, unnecessary personal data, simulated signatures, invented consent, or funding forecasts. An agent confirmation identifies one of its decisions on the stated basis; it does not attest to a user instruction or a partner agreement.

## Files and Authority

| File | Function |
|---|---|
| `events.jsonl` | Canonical append-only log, one JSON entry per line, schema `project-working-memory-v1` |
| `seal.json` | File/route identity, event count, hash of the last event, and hash of the entire log |
| `index.json` | Deterministic stdlib lexical index, rebuildable from the verified log |
| `history.md` | Readable history, with effective states and links to superseding entries |
| `context.md` | View of active confirmed items, proposals, hypotheses, questions, and contradictions |

The log and seal are canonical together: do not edit them manually. Each event contains the hash of the previous event and the hash of its own content. The index and views are compared byte for byte with the expected projection; an index copied from another project, altered, or out of date is flagged as stale and recovery stops. The CLI uses only the Python standard library; it does not create LWC databases or indexes in the shared corpus.

IDs include the file identifier, for example `ID::MEM-000001`; relations to entries in another file are rejected even if they have the same sequence number. The folder, `state.id`, program, action, sector, and year must match the seal and every event. Moving a copy that retains its IDs does not introduce absolute paths into records. Symbolic aliases and paths outside the file are rejected through the shared resolver.

These checks detect inconsistency, accidental changes, and alterations relative to the seal. They are not an external signature: anyone who coherently rewrites the log, chain, and seal can recreate the hashes. No protection against a concurrent hostile author or attestation of the claimed identity is promised.

## CLI

Examples to adapt to the actual ID; do not create applications to test the command:

```sh
python3 scripts/project_memory.py init ID
python3 scripts/project_memory.py record ID --file inbox/memory-record.json
python3 scripts/project_memory.py search ID "pilot capacity" --limit 10
python3 scripts/project_memory.py search ID "pilot" --include-history
python3 scripts/project_memory.py context ID --phase intervention-design
python3 scripts/project_memory.py check ID
python3 scripts/project_memory.py check ID --rebuild-index
```

`workflow init` creates empty memory without inferring decisions from initial values or simulating confirmations. `project_memory init` is idempotent: it does not rewrite existing memory. For earlier files, initialization is explicit; `workflow status` reports its absence without changing data. For files that have memory, status includes `working_memory_context` in the output only, leaving `state.json` unchanged. File instructions require reading it when opening each phase and recording by the responsible person.

`--root PATH` identifies an engine other than the one containing the script. Ambiguous short names are rejected; always use the complete ID in mandates. The input to `record --file` must remain within the assigned file. Search uses all query words, Unicode normalization, and case-insensitive matching, with the most recent results first. It is not semantic search. `--include-history` includes rejected and superseded items. `context --phase` annotates the opening phase and keeps all active entries visible, without excluding global decisions.

## Records

A record input uses this structure; the content is only an example:

```json
{
  "kind": "decision",
  "status": "proposed",
  "title": "Pilot size to be verified",
  "summary": "Assess a limited pilot based on partner capacity; confirmation remains open.",
  "author": "coordinator",
  "provenance": {
    "type": "agent-analysis",
    "reference": "Coordinator's analysis during the design phase; replace with an actual reference"
  },
  "evidence": [],
  "supersedes": [],
  "contradicts": [],
  "tags": ["design", "pilot"]
}
```

| Field | Contract |
|---|---|
| `kind` | `decision`, `fact`, `hypothesis`, `open-question`, `contradiction` |
| `status` | `proposed`, `confirmed`, `rejected`, `superseded` |
| `title`, `summary`, `author` | Non-empty text; stated author, without simulating observed identities |
| `provenance` | Type `user-instruction`, `user-provided`, `agent-observed`, `agent-analysis`, or `source-reading`, and an observed `reference` |
| `evidence` | List of evidence with `locator` and at least one of `source_id`, `path`, HTTP(S) `url`, or explicit `reference` |
| `supersedes` | Complete IDs of earlier active entries withdrawn by the new record |
| `contradicts` | Earlier complete IDs from the same memory; required for `kind=contradiction` |
| `tags` | List of distinct words/labels useful for retrieval |

`confirmed` requires at least one located piece of evidence. A user statement may use an observed reference to the request with a locator; a local evidence file uses `path` and automatically receives the observed SHA256 hash. The CLI verifies containment, existence, and the file hash at the time of recording. References to shared sources use the actual `source_id` and locator, or the URL; the command does not certify the source's content, applicability, or online currency.

Evidence files refer to their observed state; they are not snapshots produced by memory. `context`, `search`, and `check` return `evidence-changed`/`evidence-missing` warnings when a file no longer matches its hash. These warnings do not rewrite the recorded state: the responsible person verifies the change and records a superseding entry if it affects the conclusion. `check.passed` concerns the local integrity of memory and projections; evidence warnings are separate and do not attest to the project's merits.

An alternative proposal cannot supersede an active decision. To confirm a proposal, add a `confirmed` record with `supersedes` set to the proposal; to reject it, use `rejected`. To change a decision, add the new confirmed decision with `supersedes`; to withdraw it without a replacement, use `superseded` with at least one predecessor. No relation changes the predecessor: its view becomes superseded and indicates the successor. A resolved question may be superseded by the decision that resolves it. Contradictions remain declared, without automatic inference from the text; the context exposes pairs that are still active.

A confirmed decision does not modify `project.json`, `state.json`, receipts, or revision budgets. The coordinator updates the model separately and regenerates dependent outputs, applying the invalidation and validation protocol where necessary. Memory is not a gate and does not imply promotion of a proposal to a verified fact.

For new packages, `stage_gate prepare` verifies existing memory and freezes `events.jsonl`, `seal.json`, and `context.md` as file inputs. Complete relevant records before the freeze; a change during review requires a new package. Historical snapshots remain unchanged. The event that records phase closure is entered after a successful `workflow record`, without pre-empting validation. Historical accepted receipts retain the snapshot read by their validator; the current context may include later work events.

## Index and Interrupted Writes

`check --rebuild-index` rebuilds only `index.json`, `history.md`, and `context.md`, after verifying the log and seal. It does not correct a changed event or update an inconsistent seal. Invalid JSON input, an unknown relation, or a confirmation without evidence is rejected before append.

Writes use an exclusive lock, append with flush/fsync, and atomic replacement of the seal and views. A second write is rejected if `memory/.write.lock` exists. The protocol is not an atomic transaction across all files: an interruption after append and before the seal leaves a visible inconsistency; an interruption after the seal may leave only stale views. Keep a checkpoint of the files and verify whether the writer is still active before removing a leftover lock. For stale views only, use rebuild. For inconsistent log/seal, compare against a verified copy and document the recovery; do not recalculate the seal to make an altered log acceptable.

## Engine Project Memory

Effective decisions about maintaining Erasmus Designer use a dedicated space `work/engine-memory/`, schema `engine-working-memory-v1`, `workspace_id=erasmus-designer-engine`, and `scope=engine-maintenance`. The CLI requires `--engine-memory`, without an application ID:

```sh
python3 scripts/project_memory.py --engine-memory init
python3 scripts/project_memory.py --engine-memory record --file proposals/decision.json
python3 scripts/project_memory.py --engine-memory context --phase maintenance
python3 scripts/project_memory.py --engine-memory search "working memory"
python3 scripts/project_memory.py --engine-memory check
```

The coordinator creates the record input inside `work/engine-memory/`, with real `author` and provenance, and references to the observed instruction or verified engine artifacts. Local evidence may use paths relative to the engine, such as `scripts/project_memory.py` and an audit report; artifacts from `projects/` and `.lwc/` internals are rejected. The namespace and IDs `engine:erasmus-designer::MEM-NNNNNN` prevent reuse as application memory. This memory is not read by a file's `workflow status` and is not automatically published to the second brain.

For the structure of other data, read [the application contract](../wiki/templates/project-memory-contract.md) and [the creation instructions](project-creation.md). The operational skill is [erasmus-project-memory](../skills/erasmus-project-memory/SKILL.md).
