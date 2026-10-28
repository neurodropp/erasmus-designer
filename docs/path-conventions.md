# Portable paths for the engine and application files

## Two directories with different responsibilities

The **engine root** is the shared directory containing `config/agent-registry.json`, `scripts/lwc`, `skills/`, `wiki/` and `projects/`. The **application root** is `projects/<ID>/`: it contains data, documents and receipts for a single project. Skills remain in the shared engine.

The orchestrator identifies both directories in its mandate. Text references such as `skills/...`, `config/...`, `scripts/...` and `projects/<ID>/...` in agent instructions are resolved relative to the engine root. They are not resolved relative to a personal home directory or the shell's current directory. If the mandate does not identify the engine, search the ancestors of the application file for the directory containing both `config/agent-registry.json` and `scripts/lwc`; a frozen copy of the engine may be explicitly identified by the mandate. If no verifiable root is available, report the missing context.

## Links in documents and skills

Markdown links are relative to the file containing them: from `wiki/templates/`, reach a PDF in `raw/pdf/` with `../../raw/pdf/...`; from `skills/<name>/SKILL.md`, reach a document in `docs/` with `../../docs/...`. Use `<...>` around a destination containing spaces. Preserve page fragments and evidence identifiers.

A path in the assistant's response may instead be absolute and resolved for the current computer so the file is clickable. Do not copy that interface link into reusable agent instructions.

LWC memory has its own page space. Links between pages use LWC slugs; source links use source pages and local engine references. Do not automatically copy relative links from the editorial wiki into canonical bodies: publication converts links and preserves citations and provenance.

## Executable configurations

Scripts resolve the engine from their own location. The installer generates the command and MCP working directory from the effective root: these executable paths may be absolute, but must not hard-code a personal location. `mcp_servers.<id>.cwd` is the server's startup directory in the [OpenAI documentation](https://learn.chatgpt.com/docs/config-file/config-reference).

On a fresh clone, regenerate native surfaces with `python3 scripts/install_project_agents.py`. For a copy retaining previous configurations, use the explicit migration described in [replication.md](replication.md). Preflight must verify all destinations before writing; unknown configurations and symlinks do not authorize overwriting. Preserve custom instructions and settings unrelated to path conversion.

## Provenance and frozen history

Source origins, paths of originally uploaded materials, and paths in historical reports, manifests and receipts describe where artifacts were located when observed. They are not operational links to convert in bulk. Preserve them with their hashes; to resume a transferred application file, use the [relocation audit](relocation.md) and the required new gates.

Verified releases remain unchanged. A correction to operational links or generators belongs in a new version, with new verification and a new archive; it does not retroactively modify a previous package.
