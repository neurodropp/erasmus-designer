#!/usr/bin/env python3
"""Private, reproducible engine snapshots; no runtime install or LWC mutation."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tempfile
import zipfile

FORMAT = "erasmus-engine-release-v1"
MANIFEST = "release-manifest.json"
TREES = ("config", "scripts", "skills", "docs", "tests", "wiki", "raw", "sources")
FILES = ("AGENTS.md", "README.md", ".gitignore", "requirements-import.txt", "requirements-import.lock.txt", "projects/README.md",
         "index/lwc-source-map.json", "vendor/lwc/package.json", "vendor/lwc/package-lock.json", "work/engine-memory")
EXCLUDED_DIRS = {".git", ".codex", ".agents", ".lwc", "node_modules", "__pycache__",
                 ".venv", "venv", ".cache", "cache", ".pytest_cache", ".mypy_cache", ".ruff_cache",
                 ".tox", "tmp", "temp", "dist", "build"}
SECRET_NAMES = {"credentials.json", "auth.json", "tokens.json", "cookies.json",
                "id_rsa", "id_ed25519", ".netrc", ".npmrc", ".pypirc"}
NATIVE_SUFFIXES = {".pyc", ".pyo", ".so", ".dylib", ".dll", ".exe", ".pem", ".key"}
MAX_BYTES = 1024 * 1024 * 1024
MAX_FILES = 100000
RECONCILIATION_NAME = re.compile(r'(?:source-map|reconciliation)\.[0-9a-f]{64}\.json')


class BundleError(ValueError):
    pass


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(data)
    return h.hexdigest()


def canonical(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def safe_name(name: str) -> str:
    """Reject ambiguous names on POSIX and Windows, including drive/ADS paths."""
    if not isinstance(name, str):
        raise BundleError("Archive path must be text")
    parts = name.split("/")
    if (not name or "\\" in name or ":" in name or any(ord(c) < 32 or ord(c) == 127 or c in '<>"|?*' for c in name)
            or name.startswith("/") or any(p in {"", ".", ".."} for p in parts)
            or any(p.endswith((" ", ".")) for p in parts)
            or any(re.match(r"^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)", p, re.I) for p in parts)):
        raise BundleError(f"Unsafe archive path: {name!r}")
    return PurePosixPath(name).as_posix()


def excluded(relative: Path, legacy: set[str]) -> bool:
    parts = relative.parts
    if any(p in EXCLUDED_DIRS for p in parts):
        return True
    name = relative.name.lower()
    if (name in SECRET_NAMES or name.startswith(".env") or name.endswith((".sqlite", ".sqlite-wal", ".sqlite-shm", ".tmp"))
            or relative.suffix.lower() in NATIVE_SUFFIXES):
        return True
    if parts[:2] == ("wiki", "projects"):
        return len(parts) < 3 or parts[2] not in legacy
    return False


def project_ids(values: list[str]) -> set[str]:
    result = set()
    for value in values:
        if safe_name(value) != value or "/" in value or value.startswith("."):
            raise BundleError(f"Use an exact project folder ID: {value!r}")
        result.add(value)
    return result


def selected_files(root: Path, projects: set[str], legacy: set[str]) -> list[Path]:
    selected = set()
    starts = [root / p for p in TREES + FILES]
    # Bounded engine-history receipts referenced by operational docs; no index recursion.
    for suffix in ("*.json", "*.log", "*.patch"):
        starts += sorted((root / "index").glob(suffix))
    receipts = root / 'index/source-reconciliation'
    if receipts.is_symlink():raise BundleError('Symlink reconciliation evidence directory refused')
    if receipts.exists():
        if not receipts.is_dir():raise BundleError('Reconciliation evidence directory required')
        for entry in sorted(receipts.iterdir()):
            if entry.is_symlink():raise BundleError('Symlink reconciliation evidence refused')
            if not entry.is_file() or not RECONCILIATION_NAME.fullmatch(entry.name):
                raise BundleError('Unexpected reconciliation evidence entry: '+entry.name)
            starts.append(entry)
    starts += [root / "projects" / p for p in sorted(projects)]
    # Legacy projects are reached through the wiki tree, but require explicit existence.
    for relative in ["projects/" + p for p in projects] + ["wiki/projects/" + p for p in legacy]:
        target = root / relative
        if not target.is_dir() or target.is_symlink():
            raise BundleError(f"Project directory unavailable or symlinked: {relative}")
    for start in starts:
        if not start.exists() and not start.is_symlink():
            continue
        relative = start.relative_to(root)
        for ancestor in (start, *start.parents):
            if ancestor == root:
                break
            if ancestor.is_symlink():
                raise BundleError(f"Symlink is not exportable: {relative}")
        if excluded(relative, legacy) or (relative == Path("wiki/projects") and not legacy):
            continue
        if start.is_symlink():
            raise BundleError(f"Symlink is not exportable: {relative}")
        if start.is_file():
            selected.add(start)
            continue
        for directory, dirs, files in os.walk(start, followlinks=False):
            base = Path(directory)
            retained = []
            for name in sorted(dirs):
                child = base / name
                rel = child.relative_to(root)
                # Allow traversing wiki/projects only to selected IDs.
                if rel == Path("wiki/projects"):
                    if legacy:
                        if child.is_symlink():
                            raise BundleError(f"Symlink is not exportable: {rel}")
                        retained.append(name)
                    continue
                if excluded(rel, legacy):
                    continue
                if child.is_symlink():
                    raise BundleError(f"Symlink is not exportable: {rel}")
                retained.append(name)
            dirs[:] = retained
            for name in sorted(files):
                path = base / name
                rel = path.relative_to(root)
                if excluded(rel, legacy):
                    continue
                if path.is_symlink() or not path.is_file():
                    raise BundleError(f"Only regular files are exportable: {rel}")
                selected.add(path)
    return sorted(selected, key=lambda p: p.relative_to(root).as_posix())


def engine_path(name: str, projects: set[str], legacy: set[str]) -> bool:
    relative = Path(name)
    parts = relative.parts
    if excluded(relative, legacy):
        return False
    if name in FILES:
        return True
    if len(parts)>=3 and parts[:2]==('work','engine-memory'):
        return True
    if len(parts) >= 2 and parts[0] in TREES:
        return True
    if len(parts) == 2 and parts[0] == "index" and relative.suffix in {".json", ".log", ".patch"}:
        return True
    if len(parts)==3 and parts[:2]==('index','source-reconciliation'):
        return bool(RECONCILIATION_NAME.fullmatch(parts[2]))
    return len(parts) >= 3 and parts[0] == "projects" and parts[1] in projects


def zip_info(name: str, executable: bool = False) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | (0o755 if executable else 0o644)) << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    return info


def build(root: Path, output: Path, version: str, projects=(), legacy=(), max_bytes=MAX_BYTES) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}", version):
        raise BundleError("Version must be a short filename-safe release label")
    root = root.resolve(strict=True)
    original_output = output.absolute()
    if original_output.is_relative_to(root):
        for ancestor in original_output.parent.parents:
            if ancestor == root:
                break
            if ancestor.is_symlink():
                raise BundleError("In-root output may not use symlink components")
        if original_output.parent.is_symlink():
            raise BundleError("In-root output may not use symlink components")
    output = output.parent.resolve() / output.name
    if not root.is_dir():
        raise BundleError("Root must be a directory")
    # Prevent self-inclusion and accidental exports into an engine input tree.
    if output.is_relative_to(root) and not output.is_relative_to(root / "dist"):
        raise BundleError("Output must be outside the source root or strictly inside its excluded dist directory")
    sidecar = Path(str(output) + ".sha256")
    if output.exists() or output.is_symlink() or sidecar.exists() or sidecar.is_symlink():
        raise BundleError("Release output or checksum already exists; choose a new version/path")
    selected_projects, selected_legacy = project_ids(list(projects)), project_ids(list(legacy))
    paths = selected_files(root, selected_projects, selected_legacy)
    if not paths or len(paths) > MAX_FILES:
        raise BundleError("Empty export or too many files")
    entries = []
    total = 0
    case_names = set()
    for path in paths:
        name = safe_name(path.relative_to(root).as_posix())
        if name.casefold() in case_names:
            raise BundleError(f"Case-insensitive path collision: {name}")
        case_names.add(name.casefold())
        size = path.stat().st_size
        total += size
        if total > max_bytes:
            raise BundleError("Export exceeds byte limit")
        entries.append({"path": name, "size": size, "sha256": digest(path),
                        "executable": bool(path.stat().st_mode & 0o111)})
    manifest = {"format": FORMAT, "version": version, "source_root": str(root),
                "files": entries, "total_bytes": total,
                "projects": sorted(selected_projects), "legacy_projects": sorted(selected_legacy),
                "canonical_memory": "excluded; separate official LWC CLI archive/checkpoint",
                "relocation": "not performed; immutable historical paths and receipts preserved",
                "generated_runtime": "excluded; reinstall pinned LWC and regenerate local Codex surfaces"}
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".release-", suffix=".zip", dir=output.parent)
    os.close(fd)
    temporary = Path(temp)
    published = False
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            archive.writestr(zip_info(MANIFEST), canonical(manifest))
            for path, entry in zip(paths, entries):
                with path.open("rb") as source, archive.open(zip_info(entry["path"], entry["executable"]), "w") as target:
                    shutil.copyfileobj(source, target, 1024 * 1024)
        verify(temporary, max_bytes=max_bytes)  # Also detects inputs changed during export.
        # Exclusive publication does not overwrite a release created concurrently.
        os.link(temporary, output)
        published = True
        checksum = digest(output)
        with sidecar.open("x", encoding="ascii") as stream:
            stream.write(f"{checksum}  {output.name}\n")
        return {"archive": str(output), "sha256": checksum, "files": len(entries),
                "total_bytes": total, "version": version}
    except Exception:
        if published:
            output.unlink(missing_ok=True)
        raise
    finally:
        temporary.unlink(missing_ok=True)


def validate_archive(archive: zipfile.ZipFile, max_bytes: int) -> dict:
    infos = archive.infolist()
    if len(infos) > MAX_FILES + 1:
        raise BundleError("Too many archive entries")
    names, folded = set(), set()
    total = 0
    for info in infos:
        safe_name(info.filename)
        mode = info.external_attr >> 16
        if (info.is_dir() or stat.S_ISLNK(mode) or (stat.S_IFMT(mode) not in {0, stat.S_IFREG})
                or info.flag_bits & 1):
            raise BundleError(f"Only unencrypted regular files are allowed: {info.filename}")
        if info.filename in names or info.filename.casefold() in folded:
            raise BundleError(f"Duplicate/colliding archive path: {info.filename}")
        names.add(info.filename)
        folded.add(info.filename.casefold())
        total += info.file_size
        if total > max_bytes + 32 * 1024 * 1024:
            raise BundleError("Archive exceeds byte limit")
    # A file may not also be an ancestor directory of another entry.
    for name in names:
        for parent in PurePosixPath(name).parents:
            if str(parent) in names:
                raise BundleError(f"File/directory collision: {name}")
    if MANIFEST not in names or archive.getinfo(MANIFEST).file_size > 32 * 1024 * 1024:
        raise BundleError("Missing or oversized manifest")
    try:
        manifest = json.loads(archive.read(MANIFEST))
    except (ValueError, UnicodeError) as exc:
        raise BundleError("Invalid manifest JSON") from exc
    if (not isinstance(manifest, dict) or manifest.get("format") != FORMAT or not isinstance(manifest.get("files"), list)
            or not isinstance(manifest.get("version"), str)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}", manifest["version"])):
        raise BundleError("Unsupported manifest")
    if (not isinstance(manifest.get("projects"), list)
            or not isinstance(manifest.get("legacy_projects"), list)):
        raise BundleError("Manifest must declare explicitly selected projects")
    projects = project_ids(manifest["projects"])
    legacy = project_ids(manifest["legacy_projects"])
    expected = {MANIFEST}
    payload_bytes = 0
    for entry in manifest["files"]:
        if not isinstance(entry, dict):
            raise BundleError("Invalid file record")
        name = safe_name(entry.get("path", ""))
        if not engine_path(name, projects, legacy):
            raise BundleError(f"File is outside the engine release scope: {name}")
        if name in expected:
            raise BundleError(f"Duplicate manifest path: {name}")
        expected.add(name)
        if (type(entry.get("size")) is not int or entry["size"] < 0
                or not isinstance(entry.get("sha256"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", entry["sha256"])
                or type(entry.get("executable")) is not bool):
            raise BundleError(f"Invalid manifest metadata: {name}")
        if name not in names or archive.getinfo(name).file_size != entry["size"]:
            raise BundleError(f"Missing file or size mismatch: {name}")
        expected_mode = 0o755 if entry["executable"] else 0o644
        if (archive.getinfo(name).external_attr >> 16) & 0o777 != expected_mode:
            raise BundleError(f"Permission mismatch: {name}")
        payload_bytes += entry["size"]
        if payload_bytes > max_bytes:
            raise BundleError("Payload exceeds byte limit")
        h = hashlib.sha256()
        with archive.open(name) as source:
            for data in iter(lambda: source.read(1024 * 1024), b""):
                h.update(data)
        if h.hexdigest() != entry["sha256"]:
            raise BundleError(f"SHA-256 mismatch: {name}")
    if names != expected or manifest.get("total_bytes") != payload_bytes:
        raise BundleError("Unlisted archive entries or incorrect total size")
    return manifest


def verify(path: Path, expected_sha256: str | None = None, max_bytes=MAX_BYTES) -> dict:
    if expected_sha256 and digest(path) != expected_sha256.lower():
        raise BundleError("Archive SHA-256 does not match trusted checksum")
    with zipfile.ZipFile(path) as archive:
        return validate_archive(archive, max_bytes)


def unpack(path: Path, destination: Path, expected_sha256=None, max_bytes=MAX_BYTES) -> dict:
    destination = destination.absolute()
    if destination.exists() or destination.is_symlink():
        raise BundleError("Destination already exists; unpack only into a new directory")
    parent = destination.parent
    if not parent.is_dir() or parent.resolve() != parent:
        raise BundleError("Destination parent must already exist and contain no symlink components")
    if expected_sha256 and digest(path) != expected_sha256.lower():
        raise BundleError("Archive SHA-256 does not match trusted checksum")
    temporary = Path(tempfile.mkdtemp(prefix=".release-unpack-", dir=parent))
    try:
        with zipfile.ZipFile(path) as archive:
            manifest = validate_archive(archive, max_bytes)
            for entry in manifest["files"]:
                target = temporary / entry["path"]
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(entry["path"]) as source, target.open("xb") as stream:
                    shutil.copyfileobj(source, stream, 1024 * 1024)
                os.chmod(target, 0o755 if entry["executable"] else 0o644)
            (temporary / MANIFEST).write_bytes(archive.read(MANIFEST))
        # An existing empty destination is also refused. Never merge/overwrite files.
        # Reserve with exclusive mkdir, so a concurrent destination is never overwritten.
        destination.mkdir()
        try:
            temporary.rename(destination)
        except Exception:
            # Only remove our empty reservation; preserve any concurrent content.
            try:
                destination.rmdir()
            except OSError:
                pass
            raise
        return {"destination": str(destination), "files": len(manifest["files"]),
                "version": manifest["version"], "runtime_installed": False, "relocation_performed": False}
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    make = commands.add_parser("build", help="Create a new engine archive and external checksum")
    make.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    make.add_argument("--output", type=Path, required=True)
    make.add_argument("--version", required=True)
    make.add_argument("--include-project", action="append", default=[], metavar="EXACT_FOLDER_ID")
    make.add_argument("--include-legacy-project", action="append", default=[], metavar="EXACT_FOLDER_ID")
    for command in ("verify", "unpack"):
        sub = commands.add_parser(command)
        sub.add_argument("archive", type=Path)
        sub.add_argument("--sha256", help="Trusted external archive SHA-256 (recommended)")
        if command == "unpack":
            sub.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            result = build(args.root, args.output, args.version, args.include_project, args.include_legacy_project)
        elif args.command == "verify":
            manifest = verify(args.archive, args.sha256)
            result = {"verified": True, "version": manifest["version"], "files": len(manifest["files"]),
                      "external_checksum_checked": bool(args.sha256)}
        else:
            result = unpack(args.archive, args.destination, args.sha256)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (BundleError, OSError, zipfile.BadZipFile, RuntimeError) as exc:
        parser.exit(1, f"release_bundle: {exc}\n")


if __name__ == "__main__":
    main()
