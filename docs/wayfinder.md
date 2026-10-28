# Wayfinder for an application

This is a local adaptation of the [Wayfinder method](https://github.com/mattpocock/skills/blob/321658273cb1d20b76026717d027d505790106d4/skills/engineering/wayfinder/SKILL.md): it tracks a destination, questions, dependencies, assignments, and real decisions. The original method allows Markdown trackers; here, JSON and verifiable snapshots power the Markdown view. The old [bootstrap map](wayfinder-map.md) remains historical.

`workflow.py init` generates an empty `projects/<ID>/wayfinder/`. For an existing case, explicitly use `python3 scripts/wayfinder.py init ID`: no decisions are imported from the brief. After reviewing memory, open `context ID` whenever resuming a project with connected decisions. For a simple task, the map may remain empty; do not turn every writing task into a ticket.

The current source of truth is `head.json` plus the concatenated, immutable snapshots in `history/`. `map.json` and `map.md` are reconstructible views produced with `render ID`; do not edit them as the canonical source. `check ID` verifies history and active premises. Local hashes and authors are not signatures or authentication of consent.

| Command | Use |
|---|---|
| `context ID` | Retrieves research frontier, human frontier, claimed items, blocks, and premises that are no longer valid |
| `destination ID --file inbox/decision.json` | Defines the work destination from the brief |
| `add ID --file inbox/decision.json` | Adds a research question or a human choice with dependencies |
| `claim ID --file inbox/decision.json` | Assigns available open research to an owner; does not start an agent |
| `resolve ID --file inbox/decision.json` | Links a decision confirmed in memory and located evidence |
| `block ID --file inbox/decision.json` | Records the missing information or impediment |
| `reopen ID --file inbox/decision.json` | Reopens the premise and dependent decisions without rewriting history |
| `cancel ID --file inbox/decision.json` | Withdraws a question; dependencies remain blocked until redesigned |

Run commands from the engine root. The input file is internal to the case folder; every mutation requires `author` and `reason`. An addition uses `title`, `question`, `kind` (`research` or `human-decision`), and `dependencies` (a list of existing IDs). A claim uses `id` and `assignee`. A block uses `id` and `blocker`; reopen/cancel use `id`. Destination uses `destination`.

A resolution uses `id`, `resolution`, `memory_ids`, and `evidence` with `path` and `locator`. First, actually record the decision through `project_memory.py`: `kind=decision`, `status=confirmed`, tag `wayfinder:D-0001`, and the wording of the choice in `summary`. The resolution must match that wording. A human choice requires an entry with `user-instruction` provenance, containing the observed decision and its evidence; a proposal or an agent decision is not enough. An owner may resolve only research claimed by that owner.

The code prevents unknown or cyclic dependencies, duplicate claims, and resolutions with invalid evidence or memory. Changed evidence and superseded entries also invalidate transitive premises. The shared lock prevents two cooperative writers from writing simultaneously. It is not a safeguard against a hostile writer, nor an LLM runner or budget manager.

The map does not modify shared data or the workflow. If a need, recipient, or activity that has already been validated changes, the coordinator separately applies `workflow.py invalidate` to the first affected phase. A choice on the map is not [human approval of the package](human-approval.md).
