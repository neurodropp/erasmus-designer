# Privacy and repository boundaries

This repository contains the reusable Erasmus Designer engine. It must not contain candidate dossiers, application forms completed by real organisations, evaluator reports, partner records, participant data, credentials, local account state, or working-memory databases.

## Data that must stay outside Git

- every real dossier under `projects/<ID>/`;
- Idea Lab workspaces, engine work logs, validation packets, audits, and generated output;
- completed or partially completed application forms;
- National Agency assessments used for evaluator calibration;
- partner, staff, participant, contact, banking, contractual, or reimbursement data;
- user-supplied DOCX/XLSX templates unless a separately reviewed synthetic version is created;
- `.lwc/`, local indexes, Codex account configuration, tokens, cookies, and credentials.

The supplied KA220 profile is a structural, non-current, non-official reference stripped of example answers and source-file provenance. A user must bind a newly verified form for the actual call before drafting or QA.

## Safe operating model

Clone the engine into one directory and keep real work in ignored local folders or, preferably, in a separate encrypted workspace. Do not weaken `.gitignore` to make a dossier convenient to commit. Use synthetic fixtures for tests and aggregate, rewritten lessons for evaluator calibration. Never copy a confidential source document or a case-level extract into the knowledge base.

Before any push, run:

```sh
python3 scripts/repository_preflight.py
git status --short
```

The preflight is a guardrail, not a legal or forensic guarantee. Review the staged diff and the GitHub repository visibility before every release.

## Incident response

If private data is committed, stop sharing the repository, revoke exposed credentials, remove the material from Git history rather than only from the latest commit, and rotate any affected secret. Treat existing clones and caches as potentially containing the removed data.

