# Replicating Erasmus Designer on another computer

This guide prepares a future replication. The inventory was verified on the source computer on September 12, 2026; **no transfer or testing on another computer has been performed**. This is a clean private GitHub distribution of the engine for a new authorised user to clone. It is not an export of AI models: instructions, local software, sources and memory are transferred separately. Models, multi-agent tools and limits depend on the new host and account. Keep private application data and local memory outside Git; transfer them separately only when explicitly selected and authorised.

The tooling for creating a versioned copy is now [release-bundles.md](release-bundles.md), with build/verify/unpack and a SHA256 manifest. The engine, CLI semantic memory and full checkpoint remain distinct. The [read-only mapping](relocation.md) supports audits of copied application files; it does not migrate them or automatically validate gates on the new computer.

## Three separate components

| Component | Contents | Replication |
|---|---|---|
| Engine | `AGENTS.md`, `scripts/`, `skills/`, `config/`, `docs/`, `tests/`, regulatory wiki, sources and extractions | A versioned engine copy with versions and hashes preserved |
| Maintained memory | Canonical SQLite `.lwc/`, immutable sources, citations, history and projections | LWC CLI archive or a consistent full backup; never rebuild it from the editorial wiki alone |
| Applications | `projects/<name>--<type>--<year>/` and historical files in `wiki/projects/` | Separate, selective copy; applications do not need to be transferred to use the engine |

`index/evidence.sqlite` is the locally rebuildable index of Erasmus/ESC pages and filters; it is not the canonical LWC database. `index/lwc-source-map.json` links local source IDs to numeric LWC IDs: preserve it and verify it after import. Also preserve backups/receipts in `index/source-reconciliation/`: release0.2.1 includes them, and the tool verifies a path back to the original identities even after repeated transfers and recurring IDs. `wiki/` contains editorial and delivery materials; `.lwc/wiki/` is a generated projection.

For new applications, the layout is governed by `config/project-layout.json` and `scripts/project_paths.py`: `workflow init BASE --title 'Readable title' --action KA220 --sector YOU` generates `projects/BASE--ka220-youth--2026/`. The full ID avoids ambiguity; BASE is accepted only if unique. Initial, phase and annex folders organize the work; they do not prove that an annex is required or a phase approved. Verify the exact command and layout with `--help` in the transferred version. The resolver detects legacy applications and rejects automatic continuation: plan their migration without mass-renaming them.

## Destination requirements

| Requirement | Function and limitation |
|---|---|
| Python 3.11 or later | The main tools use the standard library; the installer imports `tomllib`, available from 3.11. No Python AI frameworks are needed for the registry. |
| Node.js 22+ and npm | Reinstall the official `@i-xor/lwc` package; the installed package is 0.18.5. |
| POSIX shell and executable permissions | `scripts/lwc` is a `/bin/sh` script that selects project scope, the vendored binary and `LWC_PROJECT_ROOT` for the canonical root, taking precedence over the inherited environment. |
| Authenticated Codex host | Open the local root as a project/folder, allow local configuration and reload discovery. Model, account, policy and tool availability must be checked on the new host. |
| Optional `python-docx` | Needed to re-extract the DOCX template with `extract_application_template.py`, not to read existing extractions. |
| Optional `openpyxl` | Needed to re-extract workbooks with `extract_annex_templates.py`, not for the main tools. |
| Poppler (`pdftotext`) | Required for rebuilding from original PDFs as part of replication testing; `pdftoppm` and other rendering tools are used for visual verification of artifacts. |
| Optional document/spreadsheet/PDF skill runtimes | Needed to produce or render those artifacts on the new host; runtimes and plugins from the source session are not part of the engine. |

OpenAI's official documentation currently describes desktop installation on macOS, Windows and Linux, account sign-in, and opening folders/projects. Recheck downloads, requirements and availability at replication time: the Codex addresses consulted redirect to ChatGPT Learn documentation. [Desktop and sign-in](https://learn.chatgpt.com/docs/app).

| System | Concrete path |
|---|---|
| macOS | Python 3.11+, Node 22+, POSIX shell; reinstall the LWC binary for the Mac architecture. Verify script permissions and Codex discovery. |
| Linux | Same dependencies; the official LWC installer supports Linux glibc x64/arm64. This guide does not attest musl/Alpine distributions. Verify the Codex runtime actually available. |
| Windows | The upstream LWC binary supports Windows, but **this wrapper and local workflow have not been tested in PowerShell/native Windows**. WSL with a glibc distribution provides the POSIX path: install Python, Node and LWC inside WSL, keep the project in the WSL filesystem and verify that Codex runs MCP in the same environment. A Windows wrapper and its MCP configuration require specific implementation and testing. |

## What to copy and what to regenerate

Also copy requirements-import.txt. Copy the engine files, npm manifests `vendor/lwc/package.json` and `vendor/lwc/package-lock.json`, `raw/`, `sources/` **with all revisions by hash**, the editorial wiki, source configurations and JSON indexes. Include user sources and original templates only if they are intended for replication; without them, some checks will correctly report missing materials. Also preserve historical documentation and receipts for traceability, distinguishing them from new checks.

Exclude `vendor/**/node_modules/`, native binaries, virtualenvs, caches, `__pycache__/`, `*.pyc`, temporary files and the rebuildable index `index/evidence.sqlite*` from the operational copy. Regenerate `.codex/config.toml`, `.codex/agents/` and `.agents/skills` from the registry and skills in the new root. Reusable instructions use [engine-relative references](path-conventions.md); the installer resolves the command and MCP working directory for the destination. If the copy retains the previous surfaces, explicitly use `python3 scripts/install_project_agents.py --relocate-owned-paths`: it converts only recognized paths and preserves customizations. Installer preflight rejects unknown configurations and symlinks before any write; the normal command does not overwrite conflicts.

Do not copy the entire personal profile `~/.codex`, credentials, tokens, cookies, plugin caches, client sessions, MCP processes or global settings as if they were repository dependencies. Sign in again on the destination computer and reconnect required plugins. Observed spawn receipts inside an application are historical evidence to preserve; they do not start an agent and cannot be reused as attestation of a new spawn.

## Clean private GitHub distribution

The maintainer publishes the reusable engine to a **private GitHub repository**. A new authorised user clones that repository into a fresh directory using their own GitHub access:

```sh
git clone <PRIVATE_REPOSITORY_URL> erasmus-designer
cd erasmus-designer
```

Use the repository's actual private clone URL. Do not make the repository public. The clone contains reusable engine code and documentation only. Keep private application files, `.lwc/` local memory, credentials, tokens, personal Codex configuration, runtime caches and generated local integrations outside Git. `.gitignore` excludes `.lwc/`, `node_modules`, index databases and historical application files; review it before committing any new paths. Never commit private application data or local memory to the shared repository.

After cloning, follow the dependency installation and native-surface regeneration instructions below. To move maintained memory or selected application files, prepare and verify separate authorised backups and manifests; a Git clone does not transfer them. Keep their provenance and frozen receipts intact.

To re-extract DOCX/XLSX, create a local venv and use requirements-import.lock.txt: it preserves the five dependencies in the observed closure, including lxml, typing_extensions and et-xmlfile. It contains no distribution hashes and does not guarantee wheels/runtimes on every OS; test on the destination. requirements-import.txt preserves the two direct pins. The extractors require explicit --source/--input-dir inputs and rewrite outputs: do not run them during a replication that must preserve existing extractions and hashes. Rendering runtimes and plugins remain to be checked when the relevant artifacts are produced.

## Canonical memory: two modes

Before transferring, stop active writes and MCP readers and use the project CLI. In this version, `compress` exports an exact wiki to a portable archive and `decompress` validates/imports it without implicit overwrite; a checkpoint, by contrast, is a complete database copy made with SQLite online backup. They serve different purposes. [Official LWC README](https://github.com/JanYork/llm-wiki-cli/blob/main/README.md); the specific commands below were verified with local `--help` for 0.18.5.

```sh
scripts/lwc --version
scripts/lwc lint
scripts/lwc checkpoint create before-replication-2026-09-12
scripts/lwc compress /authorized/path/erasmus-memory.lwc.zst
```

**CLI semantic archive, recommended for a new location:** preserve the archive, checksum, LWC version and export receipt. On the new computer, with the runtime reinstalled and a memory-empty root, use `scripts/lwc decompress /authorized/path/erasmus-memory.lwc.zst`; first read `decompress --help`. Do not pass `--overwrite` to bypass an existing memory: that requires a separate decision and specific confirmation. Verify counts, sources, citations, source-map IDs and retrieval. The upstream term portable does not certify portability of embedded paths, workflow receipts or perfect byte-for-byte identity of the imported database.

Before import, read `scripts/lwc doctor`: `project.wiki_database` must refer exclusively to `NEW-ROOT/.lwc/wiki.db`. The same selection applies to MCP through the wrapper. Installer preflight rejects symlink components in native surfaces, including files and dangling links; the only exception is the exact discovery link to the root skills. Do not bypass this check by writing configurations through a symlink.

**Complete canonical backup, for forensic preservation and recovery:** after a CLI checkpoint and with LWC stopped, copy the entire `.lwc/`, including the database, any WAL/SHM files, checkpoint and associated artifacts. Do not copy only `wiki.db` while the WAL may be in use; do not delete these files to reduce archive size. The complete archive also preserves history and checkpoints that must not be assumed equivalent to the semantic archive. `maintenance compact` may reclaim WAL during inactivity, but it is not `compress`; check `busy` and sizes and do not report success if a reader blocks the checkpoint.

In both cases, SQLite remains authoritative. Do not edit databases or generated Markdown; knowledge changes must go exclusively through the CLI. Do not run `sync_lwc.py` as a shortcut to rebuild maintained memory: it is a bootstrap compiler and may lose richer conclusions. The reproducible sparse-draft issue in LWC0.18.5 is documented in [knowledge-maintenance process](knowledge-maintenance.md): explicit recovery with checkpoint and manifest, not automatic fallback and not direct DB writes.

## Reinstall and connect locally

The upstream README documents npm installation and download of the platform-specific binary with SHA-256 verification. In this repository, retain **0.18.5** instead of implicitly taking latest. `package.json` contains `^0.18.5`, but the lockfile pins 0.18.5: `npm ci` uses the lock. Do not update the lockfile during replication. [Official LWC installation](https://github.com/JanYork/llm-wiki-cli/blob/main/README.md).

On the destination computer, run these commands only when the transfer is to be performed; this preparation does not execute them:

```sh
cd /nuova/root/ERASMUS-DESIGNER/vendor/lwc
npm ci
cd ../..
python3 scripts/install_project_agents.py
scripts/lwc --version
```

If `npm ci` cannot obtain the pinned release, stop and document the blocker; do not silently substitute the source machine's version or binary. Node is used by the npm installer; the current wrapper directly runs the native binary installed in the package.

The current inventory has **30 skills and 29 native definitions**: 28 specialists plus the orchestrator, including 16 annex owners. These are definitions and instructions, not 29 permanent processes. Wayfinder is a skill invoked by the orchestrator or memory owner: it does not require another permanent process. Verify the counts from the catalogs in the transferred version. The TOML files omit model selection: they inherit the coordinator's setting unless overridden by the new host/account. The project limit is **four agents total**, including the coordinator, so at most three specialists. The generated configuration sets `max_concurrent_threads_per_session=3`. OpenAI documentation describes `max_concurrent_threads_per_session` as the number of children, excluding the primary: the transfer configuration must respect this semantics and actual runtime limits. [Subagents and configuration](https://learn.chatgpt.com/docs/agent-configuration/subagents).

The installer registers MCP `erasmus_wiki` with the wrapper in the new root and `serve --mcp`. It is a read-only LWC surface for retrieval; memory publication remains through the authorized CLI. Do not automatically use upstream `lwc agent install`: it could introduce global surfaces that this project does not require. Reopen/reload the project, verify discovery of the 30 skills, definitions and MCP, and run a test search. If the new host does not offer multi-agent tools, production can proceed sequentially, but independent fresh-step-v1 gates cannot be closed as accepted without genuine new `fork_turns="none"` spawns and observed identities.

If the engine is moved on the same computer, rerun the installer with `--relocate-owned-paths` in the new root and reload Codex. Instructions and editorial links remain relative; executable MCP paths must point to the actual location. Native configurations are not a copy of the account's personal profile.

## Paths, hashes and receipts are not automatically portable

LWC may retain absolute source `source.origin` paths. A no-longer-existing origin does not destroy the cited immutable text, but leaves comparison with the live file unresolved. Preserve old origins as provenance; record their mapping to copied files and hashes in a relocation manifest. The evidence index uses revisions by hash and repository paths: preserve their versions and IDs. The corpus is **2026**; import does not certify online freshness, the current call/round or form.

Validation packets, dependencies and archived receipts may contain absolute paths. Changing those JSON/Markdown files to make them reachable changes hashes and frozen attestations. Do not automatically rewrite accepted/review archives or invent equivalent new attestations. Record mappings of old roots; when resuming an application, create a new verifiable baseline on the destination and invalidate from the first affected phase if inputs change. Any relocation audit must be read-only and report unresolved items; verify that the transferred version exposes the command before using it.

## Testing to perform when replication takes place

1. Compare manifests and SHA-256 values for the engine, sources, revisions and selected applications; check that user originals and source-map are present.
2. Verify Python, Node/npm, LWC version 0.18.5 and platform; check the new root in regenerated Codex surfaces.
3. After import/backup, run `scripts/lwc doctor`, `scripts/lwc lint`, maintained-memory search and read a cited page/source. Compare IDs and citations, not only a search result.
4. Rebuild only the local index with `python3 scripts/brain.py rebuild --no-cards`, then run `python3 scripts/brain.py check`. The flag preserves maintained editorial summaries; regenerating them requires a separate update and review of differences. Rebuilding requires Poppler for PDF sources. Do not delete existing revisions.
5. Run relevant regressions with `python3 -m unittest discover -s tests`; retrieval regressions may generate new receipts, which must be distinguished from archived ones.
6. Check application statuses and any relocation audit. An error involving historical paths does not authorize rewriting frozen packets.
7. Verify Codex discovery and, if available, a genuine bounded spawn. Record outcomes and limits before declaring the destination operational.

SSH synchronization, cloud upload, submission, signing, partner contact and installation on the new computer are not included. The most conservative choice is to transfer a versioned copy with both memory-preservation forms, test it and leave the source computer unchanged until checks are complete.

After semantic import, use [reconcile_lwc_sources](lwc-source-reconciliation.md) to update only the operational map on the destination, with an exact backup and receipt. The index/lwc-source-identities.json reference derives from CLI discovery and must be verified in the bundle. Original IDs remain in the complete backup and archives; do not reuse the old map for coincident numbers without comparing contents.

## Working memory in version0.2.3

The package includes `work/engine-memory/`, the engine project's register. Each application instead keeps `projects/<ID>/memory/`: canonical log, seal, rebuildable index and views. These memories enter the package only when the application is explicitly selected. Do not copy all of work/ or treat maintenance candidates as active sources. After replication, verify the log and rebuild only the indexes as described in [project-working-memory.md](project-working-memory.md).

The added skills are `erasmus-project-memory` and `erasmus-knowledge-maintenance`. The latter prepares guide/form revisions and guides verified promotion without automatically changing application inputs. For essential steps, use [the quick guide](quick-start-another-computer.md) and INSTALLA in container0.2.5; read checksums from the new package, not historical releases.

## Operational corrections dated September 13, 2026

Also transfer `scripts/wayfinder.py`, `scripts/project_lock.py`, `scripts/human_approval.py`, `scripts/evaluation.py` and the updated catalogs. The [layout](project-creation.md) creates empty maps for new applications; existing maps and approvals are application data and should be copied only if authorized. Historical receipts remain unchanged. The cooperative lock uses POSIX `fcntl`: the Windows path remains WSL, not native Windows. Read [Wayfinder](wayfinder.md), [exact approval](human-approval.md), [recovery](dispatch-recovery.md), [protected bootstrap](bootstrap-safety.md) and [synthetic evidence](evaluation.md). Bootstrap requires a complete manifest and separates staging from map publication; it does not blindly recompile memory.

Private applications and evaluations used for calibration remain outside the packages. Only anonymized practices and invented fixtures are transferred. No model trained on agency scores or benchmark is included. Discovery and genuine spawns must be retested on the destination; local tests did not authenticate provider exports or certify the new host.
