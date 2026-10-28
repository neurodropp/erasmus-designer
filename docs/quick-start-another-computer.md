# Quick start on another computer

This private GitHub distribution contains the reusable engine, public evidence snapshots and sanitized fixtures. It does **not** contain real applications, assessments, user templates, credentials, Codex account state or the maintained `.lwc/` database.

## Requirements

- Git;
- Python 3.11 or later;
- Node.js 22 or later and npm;
- Poppler with `pdftotext`;
- a POSIX shell (macOS, Linux, or a verified WSL environment);
- an authenticated Codex installation with access to the cloned folder.

## Install

The repository owner must first grant the user access to the private repository. Then:

```sh
git clone PRIVATE_REPOSITORY_URL erasmus-designer
cd erasmus-designer

python3 scripts/repository_preflight.py
cd vendor/lwc
npm ci
cd ../..

python3 scripts/install_project_agents.py
scripts/lwc --version
scripts/lwc doctor
python3 scripts/brain.py rebuild --no-cards
python3 scripts/brain.py check
python3 -m unittest discover -s tests
```

`npm ci` uses the committed lockfile. Do not silently replace the pinned LWC version. The evidence-index rebuild requires `pdftotext`. Reload/open the repository root in Codex after generating the local discovery surfaces.

## Initialize local memory

The Git clone starts without canonical LWC memory. Build or import memory only through the documented LWC CLI workflow; never commit `.lwc/` or edit its databases directly. If the owner supplies a separately authorised semantic archive, verify its checksum and follow [the replication guide](replication.md). Otherwise, use the verified public evidence and the knowledge-maintenance process to initialize local memory.

## Start a new application

Real application work stays local and ignored under `projects/<name>--<action>--<year>/`. For a new idea, invoke `$erasmus-designer`; Phase 0 creates an Idea Lab workspace before promotion to a dossier. Provide or acquire the current application form for the actual year/round and verify call, sector, agency, deadline and national provisions online.

Do not commit a dossier, completed form, evaluator report, partner/participant record or user-supplied workbook. Read [PRIVACY.md](../PRIVACY.md), [project creation](project-creation.md), [form intake](form-intake.md) and [path conventions](path-conventions.md).

## Verify runtime capabilities

The clone installs instructions and local tools; it does not copy models, account permissions, plugins or multi-agent capabilities. Verify skill discovery, LWC retrieval and a real constrained validator spawn on the new host. If fresh independent agents are unavailable, the workflow may run sequentially but a `fresh-step-v1` gate cannot be declared accepted.
