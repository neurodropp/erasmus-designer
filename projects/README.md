# Application files

This directory contains application files only. The shared engine is in the parent root: scripts, skills, config, sources and the second brain are not duplicated in each application file.

To create new work, read [project-creation.md](../docs/project-creation.md). From the root, run:

```sh
python3 scripts/workflow.py init bridge --title "BRIDGE" --action KA220 --sector YOU --country IT --agency AIG
```

Result: `projects/bridge--ka220-youth--2026/`. The name is an example: these instructions do not create a BRIDGE project. Status and gates should use the complete directory ID; the short name is valid only when unique.

Do not create application data, approved product.md files, receipts or spawn attestations manually. The generator prepares folders and empty registers; project verification takes place in subsequent work. The presence of an annex folder does not prove that uploading it is required.

To resume a file, open the engine root in Codex and provide the ID; do not rename a file that has already been validated. Application data is not published in the regulatory wiki. Files are excluded from any shared Git versioning: prepare separate backups when they contain real work.
