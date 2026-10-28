# Private and portable engine releases

`scripts/release_bundle.py` prepares private, versioned, verifiable snapshots of the engine. It does not install software, modify LWC memory, or transfer anything to a destination computer. An extraction trial in another folder on the source machine demonstrates that the archive works; it does not test it on another PC.

For this preparation, use the engine version declared in `config/engine-version.json` and retain separate releases for each subsequent change. The manifest format is `erasmus-engine-release-v1`. Releases are private ZIP archives with an external SHA-256 checksum; Git, remotes, cloud uploads, and publication are not required. They do not include AI models or account rights.

## Create and verify

From the project root, when the inputs are ready and not changing:

```sh
python3 scripts/release_bundle.py build --version 0.2.0 --output dist/0.2.0/engine.zip
python3 scripts/release_bundle.py verify dist/0.2.0/engine.zip --sha256 HASH_CONSERVATO
```

Replace `HASH_CONSERVATO` with the 64 characters returned by `build` and written to `engine.zip.sha256`. Keep that checksum separately, together with the release receipts. Internal verification compares all files with the manifest; the external checksum also detects simultaneous replacement of files and manifest. Hashes attest to integrity relative to the retained value; they are not authenticity signatures.

`--root /root/sorgente` allows an explicit input. The output may be outside the root or strictly under its `dist/` folder, which is excluded from export. Outputs inside other engine folders and outputs that already exist are rejected. An output under `dist/` cannot use symlink components. The program does not take arbitrary directories, personal profiles, or all dependencies on the machine.

The archive contains:

- `AGENTS.md`, `README.md`, `.gitignore`, `requirements-import.txt`, the optional `requirements-import.lock.txt`, and `projects/README.md`;
- `config/`, `scripts/`, `skills/` including skill resources, `docs/`, `tests/`, the editorial wiki, `raw/`, and `sources/` with immutable revisions;
- top-level `index/*.json`, `index/*.log`, `index/*.patch` files, such as maps and historical engine receipts; `index/source-reconciliation/source-map.SHA256.json` and `reconciliation.SHA256.json` are also included under a strict allowlist, preserving evidence of subsequent migrations;
- `vendor/lwc/package.json` and `vendor/lwc/package-lock.json`, to reinstall the pinned version at the destination.

Excluded are `.lwc/`, `.codex/`, `.agents/`, `node_modules`, native binaries, virtual environments, caches, `dist`, `build`, temporary files, index SQLite databases, and common credential names (`auth.json`, `credentials.json`, `.env*`, private keys, etc.). Unlisted top-level folders, including a generic `resources/`, are not included in the bundle. The default limit is 1 GiB of payload and 100,000 files. Selected symlink or special files are rejected.

The common-name filter reduces accidental inclusion; it does not detect secrets embedded in ordinary documents or scripts. Before sharing a release, inspect the included files and user originals. This preparation produces a private archive and does not authorize external sharing.

The manifest records the version, source root as provenance, sizes, executable flags, and SHA-256 of every file. ZIPs, internal timestamps, and file order are deterministic: the same inputs, version, root, and compression implementation produce the same archive. Identical compressed output across different Python/zlib versions is not promised. A change to the provenance root changes the manifest; history is not rewritten to obtain the same checksum. The optional extractor lock preserves the observed closure without attesting to package hashes or wheel availability on every OS.

## Candidates only by explicit choice

```sh
python3 scripts/release_bundle.py build --version 0.2.0-with-dossier --output dist/0.2.0-with-dossier/engine.zip --include-project project-name--ka220-youth--2026
```

Repeat `--include-project` for each exact full ID. `--include-legacy-project NOME_CARTELLA` is a separate choice for dossiers under `wiki/projects/`. Without these options, the engine contains only the common instructions in `projects/README.md`, and no new or historical dossiers. Missing folders, IDs with path traversal, and symlinks are rejected.

Receipts, frozen packages, and other selected files retain their own bytes. Security and runtime filters continue to apply: the engine bundle is not an integral forensic backup of the dossiers. Any intentionally excluded files needed for preservation must be handled separately. A historical accepted package remains evidence of the source session; it does not attest to a new spawn and does not become a validation of the destination. Historical absolute paths remain unchanged: the command performs no relocation or dossier migration. To resume work on them, see [relocation.md](relocation.md) and [replication.md](replication.md).

## Separate canonical memory

Do not add `.lwc/` to the engine ZIP or recompile memory maintained by the wiki. When export is chosen, use the project's official CLI, suspend active writes and MCP readers, and record the version and results:

```sh
scripts/lwc --version
scripts/lwc lint
scripts/lwc checkpoint create before-release-0.2.0
scripts/lwc compress /authorized/path/memory-0.2.0.lwc.zst
```

The checkpoint preserves a complete database state for recovery in the source memory; `compress` produces the portable semantic archive. Keep the archive, its SHA-256, and the command receipt separately from the ZIP. Do not assume historical preservation is equivalent between a checkpoint and a semantic archive. A complete forensic backup requires the specific procedure in [replication.md](replication.md), including any WAL/SHM files present, with no direct database writes.

Import only into a root with empty memory, after pinned reinstallation and reading `decompress --help`, using `scripts/lwc decompress ARCHIVIO`. Do not use `--overwrite` automatically. Verify sources, counts, numeric IDs against `index/lwc-source-map.json`, cited content, citations, and retrieval, as well as `doctor` and `lint`. `source.origin` may contain absolute source paths: the archive does not certify that they resolve at the destination, and IDs must not be assumed unchanged before comparison.

## Protected extraction, then explicit installation

```sh
python3 scripts/release_bundle.py unpack dist/0.2.0/engine.zip --destination /nuova/root/ERASMUS-DESIGNER --sha256 HASH_CONSERVATO
```

The destination must be new; even an existing empty folder is rejected. The parent must exist and be a canonical path without symlinks; on macOS use `/private/tmp` instead of its `/tmp` alias, or use the resolved parent. The command verifies the entire archive before publishing the directory, rejecting absolute names, `..`, ambiguous Windows paths, symbolic links, special files, duplicates, name collisions, files outside the scope, undeclared files, and altered hashes. It does not merge a bundle with an operational root or rewrite documents or receipts.

Extraction returns `runtime_installed: false` and `relocation_performed: false`. It preserves the manifest in the new root. Actual installation is a separate step on the authorized destination:

```sh
cd /nuova/root/ERASMUS-DESIGNER/vendor/lwc
npm ci
cd ../..
python3 scripts/install_project_agents.py
scripts/lwc --version
```

These commands reinstall the pinned dependency and generate the Codex surfaces for the new root; they are not run by the bundle. Codex authentication, plugins, optional runtimes, platform, discovery, multi-agent tools, and testing require the checks in the [replication guide](replication.md). Release certification receipts are kept outside the already frozen bundle, to avoid a cycle between the archive hash and the hash of its own attestation.

Command regressions use temporary fixtures only:

```sh
python3 -m unittest discover -s tests -p test_release_bundle.py
```

The local preparation import confirmed that LWC0.18.5 remaps source IDs. The final bundle must contain index/lwc-source-identities.json; after decompress, use [the reconciliation](lwc-source-reconciliation.md) at the destination before using the numeric map. Always preserve the original released map and historical receipts; verify citations through content_hash.
