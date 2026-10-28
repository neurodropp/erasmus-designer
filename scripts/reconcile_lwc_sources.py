#!/usr/bin/env python3
"""Reconcile active destination source IDs by immutable hash; read-only by default."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'lwc-source-identities-v1'


class ReconciliationError(ValueError):
    pass


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode('utf-8')


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ReconciliationError('Duplicate JSON key: ' + key)
        result[key] = value
    return result


def parse(data):
    try:
        return json.loads(data, object_pairs_hook=unique_object)
    except (ValueError, UnicodeError) as exc:
        raise ReconciliationError('Invalid JSON: ' + str(exc)) from exc


def safe_path(path, *, file=False):
    """Reject every symlink component, including broken links and ancestors."""
    path = Path(os.path.abspath(path))
    for component in reversed((path, *path.parents)):
        if component.is_symlink():
            raise ReconciliationError('Symlink path refused: ' + str(component))
    if file and (not path.is_file() or not stat.S_ISREG(path.stat().st_mode)):
        raise ReconciliationError('Regular file required: ' + str(path))
    return path


def positive_id(value):
    return type(value) is int and value > 0


def metadata(row, field):
    if not isinstance(row, dict) or not positive_id(row.get(field)):
        raise ReconciliationError('Invalid source numeric ID')
    if not isinstance(row.get('content_hash'), str) or not re.fullmatch('[0-9a-f]{64}', row['content_hash']):
        raise ReconciliationError('Invalid source content_hash')
    if type(row.get('bytes')) is not int or row['bytes'] < 0:
        raise ReconciliationError('Invalid source bytes')
    if not isinstance(row.get('title'), str) or not isinstance(row.get('origin'), str):
        raise ReconciliationError('Invalid source title/origin')


def list_sources(root, runner=subprocess.run, limit=100):
    wrapper = safe_path(root / 'scripts/lwc', file=True)
    rows, offset, last_id = [], 0, 0
    while True:
        result = runner([str(wrapper), 'source', 'list', '--limit', str(limit), '--offset', str(offset)],
                        cwd=root, text=True, capture_output=True, check=False)
        if result.returncode:
            raise ReconciliationError('LWC source list failed: ' + result.stderr[:1000])
        page = parse(result.stdout)
        if (not isinstance(page, dict) or type(page.get('offset')) is not int or page['offset'] != offset
                or type(page.get('limit')) is not int or page['limit'] != limit
                or type(page.get('has_more')) is not bool or not isinstance(page.get('sources'), list)):
            raise ReconciliationError('Invalid LWC pagination metadata')
        batch = page['sources']
        if len(batch) > limit or (page['has_more'] and len(batch) != limit):
            raise ReconciliationError('Incomplete LWC pagination')
        for row in batch:
            metadata(row, 'id')
            if row['id'] <= last_id:
                raise ReconciliationError('Repeated or unordered LWC source ID')
            last_id = row['id']
            rows.append(row)
        if not page['has_more']:
            return rows
        offset += page['limit']


def verified_history(root, old_bytes, originals, expected, identity_hash):
    """Anchor an intermediate map to original IDs through preserved receipts.

    A prepared receipt alone is insufficient: its after digest must match the
    current map or the next verified backup. Historical root paths are data.
    This is local integrity checking, not an external authenticity signature.
    """
    folder=safe_path(root/'index/source-reconciliation')
    if not folder.is_dir():raise ReconciliationError('Active map has no verified reconciliation history')
    receipts=[]
    for path in sorted(folder.iterdir()):
        safe_path(path,file=True)
        if re.fullmatch(r'source-map\.[0-9a-f]{64}\.json',path.name):continue
        if not re.fullmatch(r'reconciliation\.[0-9a-f]{64}\.json',path.name):
            raise ReconciliationError('Unexpected reconciliation history entry')
        data=path.read_bytes();receipt=parse(data)
        keys=('identities_sha256','before_map_sha256','after_map_sha256','source_list_sha256')
        if not isinstance(receipt,dict) or receipt.get('schema_version') not in ('lwc-source-reconciliation-receipt-v1','lwc-source-reconciliation-receipt-v2') or any(not isinstance(receipt.get(k),str) or not re.fullmatch('[0-9a-f]{64}',receipt[k]) for k in keys):
            raise ReconciliationError('Invalid reconciliation history receipt')
        name_hash=sha256(data) if receipt['schema_version']=='lwc-source-reconciliation-receipt-v2' else sha256(encode({k:receipt[k] for k in keys}))
        if receipt['identities_sha256']!=identity_hash or path.name!='reconciliation.'+name_hash+'.json':
            raise ReconciliationError('Reconciliation history identity/name mismatch')
        if receipt.get('operation')!='prepared-active-destination-map-replacement':
            raise ReconciliationError('Invalid reconciliation history operation')
        matches=receipt.get('matches');dest=receipt.get('destination_map')
        if not isinstance(matches,list) or not isinstance(dest,dict) or set(dest)!=set(expected) or any(not positive_id(v) for v in dest.values()) or len(set(dest.values()))!=len(dest):
            raise ReconciliationError('Invalid reconciliation history destination map')
        seen=set()
        for match in matches:
            if not isinstance(match,dict) or match.get('local_id') not in expected or match['local_id'] in seen:
                raise ReconciliationError('Invalid reconciliation history matches')
            local=match['local_id'];seen.add(local);identity=expected[local]
            if any(match.get(k)!=identity[k] for k in ('original_lwc_id','content_hash','bytes')) or match.get('destination_lwc_id')!=dest[local]:
                raise ReconciliationError('Reconciliation history content mismatch')
        if seen!=set(expected) or sha256(encode(dest))!=receipt['after_map_sha256']:
            raise ReconciliationError('Reconciliation history after-map mismatch')
        backup_name='source-map.'+receipt['before_map_sha256']+'.json'
        if receipt.get('backup')!='index/source-reconciliation/'+backup_name:
            raise ReconciliationError('Invalid reconciliation history backup locator')
        backup=safe_path(folder/backup_name,file=True);backup_bytes=backup.read_bytes();before=parse(backup_bytes)
        if sha256(backup_bytes)!=receipt['before_map_sha256'] or not isinstance(before,dict) or set(before)!=set(expected) or any(not positive_id(v) for v in before.values()) or len(set(before.values()))!=len(before):
            raise ReconciliationError('Reconciliation history backup changed')
        receipts.append((receipt,path,sha256(data),backup,backup_bytes))
    # Numeric maps can recur after an import. Valid receipts then form a graph,
    # rather than a unique chain; select a shortest verified path to the origin.
    # Cycles alone never constitute proof, and all receipts/backups above have
    # already been checked, including branches not used in the chosen path.
    queue=[(old_bytes,[])];visited=set()
    while queue:
        current,chain=queue.pop(0)
        if parse(current)==originals:return chain
        key=sha256(current)
        if key in visited:continue
        visited.add(key)
        for receipt,path,receipt_hash,backup,previous in receipts:
            if receipt['after_map_sha256']!=key:continue
            if parse(current)!=receipt['destination_map']:raise ReconciliationError('Active map history mismatch')
            edge=[{'path':str(path.relative_to(root)),'sha256':receipt_hash},
                  {'path':str(backup.relative_to(root)),'sha256':sha256(previous)}]
            queue.append((previous,chain+edge))
    raise ReconciliationError('Active map has no verified reconciliation history to original identities')


def plan(root=ROOT, runner=subprocess.run):
    root = safe_path(root)
    if not root.is_dir():
        raise ReconciliationError('Destination root required')
    reference_path = safe_path(root / 'index/lwc-source-identities.json', file=True)
    map_path = safe_path(root / 'index/lwc-source-map.json', file=True)
    reference_bytes, old_bytes = reference_path.read_bytes(), map_path.read_bytes()
    reference, old = parse(reference_bytes), parse(old_bytes)
    if (not isinstance(reference, dict) or reference.get('schema_version') != SCHEMA
            or not isinstance(reference.get('provenance'), str) or not reference['provenance']
            or not isinstance(reference.get('sources'), dict) or not reference['sources']):
        raise ReconciliationError('Invalid immutable identity reference')
    expected = reference['sources']
    hashes, originals = {}, {}
    for local, row in expected.items():
        if not isinstance(local, str) or not re.fullmatch('[A-Za-z0-9][A-Za-z0-9._-]*', local):
            raise ReconciliationError('Invalid local source ID')
        metadata(row, 'original_lwc_id')
        if row['content_hash'] in hashes or row['original_lwc_id'] in originals.values():
            raise ReconciliationError('Ambiguous immutable source identities')
        hashes[row['content_hash']] = local
        originals[local] = row['original_lwc_id']
    if (not isinstance(old, dict) or set(old) != set(expected)
            or any(not positive_id(value) for value in old.values())
            or len(set(old.values())) != len(old)):
        raise ReconciliationError('Invalid active source map')
    live = list_sources(root, runner)
    target, matches, seen = {}, [], set()
    for row in live:
        key = row['content_hash']
        if key in seen:
            raise ReconciliationError('Ambiguous live content_hash: ' + key)
        seen.add(key)
        if key not in hashes:
            raise ReconciliationError('Unknown live source content_hash: ' + key)
        local = hashes[key]
        identity = expected[local]
        if row['bytes'] != identity['bytes']:
            raise ReconciliationError('Source bytes mismatch: ' + local)
        target[local] = row['id']
        matches.append({'local_id': local, 'original_lwc_id': identity['original_lwc_id'],
                        'destination_lwc_id': row['id'], 'content_hash': key, 'bytes': row['bytes'],
                        'numeric_id_unchanged': row['id'] == identity['original_lwc_id'],
                        'title_unchanged': row['title'] == identity['title'],
                        'origin_unchanged': row['origin'] == identity['origin']})
    missing = sorted(set(expected) - set(target))
    if missing:
        raise ReconciliationError('Missing destination sources: ' + ', '.join(missing))
    history=[]
    if old != originals and old != target:
        history=verified_history(root,old_bytes,originals,expected,sha256(reference_bytes))
    after_bytes = old_bytes if old == target else encode(target)
    result = {'schema_version': 'lwc-source-reconciliation-plan-v1', 'root': str(root),
              'read_only': True, 'changed': old != target, 'source_count': len(target),
              'numeric_ids_unchanged': target == originals,
              'identities_sha256': sha256(reference_bytes), 'before_map_sha256': sha256(old_bytes),
              'after_map_sha256': sha256(after_bytes), 'source_list_sha256': sha256(encode(live)),
              'matches': sorted(matches, key=lambda row: row['local_id']), 'destination_map': target,
              'verified_previous_history':history}
    return result, old_bytes, after_bytes


def store_evidence(path, data):
    safe_path(path)
    if path.exists():
        safe_path(path, file=True)
        if path.read_bytes() != data:
            raise ReconciliationError('Evidence conflict: ' + str(path))
        return
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def reconcile(root=ROOT, *, apply=False, runner=subprocess.run):
    result, old_bytes, after_bytes = plan(root, runner)
    if not apply or not result['changed']:
        result['applied'] = False
        result['read_only'] = not apply
        return result
    root = Path(result['root'])
    map_path = safe_path(root / 'index/lwc-source-map.json', file=True)
    evidence_dir = safe_path(root / 'index/source-reconciliation')
    if evidence_dir.exists() and not evidence_dir.is_dir():
        raise ReconciliationError('Evidence directory required')
    evidence_dir.mkdir(exist_ok=True)
    backup = evidence_dir / ('source-map.' + result['before_map_sha256'] + '.json')
    receipt = dict(result, schema_version='lwc-source-reconciliation-receipt-v2', read_only=False)
    receipt['backup'] = str(backup.relative_to(root))
    receipt['operation'] = 'prepared-active-destination-map-replacement'
    receipt['completion_evidence'] = 'Active map SHA256 equals after_map_sha256; receipt records intent, not a separate atomic commit.'
    receipt_bytes=encode(receipt)
    receipt_path = evidence_dir / ('reconciliation.' + sha256(receipt_bytes) + '.json')
    # Evidence is durable before replacing the map; a crash cannot lose the old map.
    store_evidence(backup, old_bytes)
    store_evidence(receipt_path, receipt_bytes)
    sync_directory(evidence_dir)
    sync_directory(evidence_dir.parent)
    fd, temp_name = tempfile.mkstemp(prefix='.lwc-source-map.', dir=map_path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            os.fchmod(stream.fileno(), map_path.stat().st_mode & 0o666)
            stream.write(after_bytes)
            stream.flush()
            os.fsync(stream.fileno())
        # Fail closed if a non-cooperating writer changed either input during CLI reads.
        safe_path(map_path, file=True)
        if map_path.read_bytes() != old_bytes:
            raise ReconciliationError('Active map changed concurrently')
        ref_path = safe_path(root / 'index/lwc-source-identities.json', file=True)
        if sha256(ref_path.read_bytes()) != result['identities_sha256']:
            raise ReconciliationError('Immutable identity reference changed concurrently')
        for item in result['verified_previous_history']:
            if sha256(safe_path(root/item['path'],file=True).read_bytes())!=item['sha256']:
                raise ReconciliationError('Reconciliation history changed concurrently')
        os.replace(temp_name, map_path)
        sync_directory(map_path.parent)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    result.update(applied=True, read_only=False, backup=receipt['backup'],
                  receipt=str(receipt_path.relative_to(root)))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Atomically replace only the active destination map and retain evidence')
    args = parser.parse_args()
    try:
        print(json.dumps(reconcile(apply=args.apply), ensure_ascii=False, indent=2, sort_keys=True))
    except (ReconciliationError, OSError) as exc:
        print('Source reconciliation refused: ' + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
