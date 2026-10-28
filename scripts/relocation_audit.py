#!/usr/bin/env python3
"""Audit a copied dossier without rewriting frozen paths or accepting its gates."""
import argparse
import hashlib
import json
from pathlib import Path
from project_paths import resolve_project

ROOT = Path(__file__).resolve().parents[1]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def audit(root, dossier, old_root):
    root = root.resolve()
    dossier = dossier.resolve()
    old_root = Path(old_root)
    if not old_root.is_absolute():
        raise ValueError('Old root must be an absolute historical path')
    if not dossier.is_relative_to(root / 'projects'):
        raise ValueError('Dossier outside projects')
    def read_local(path):
        if not path.resolve().is_relative_to(dossier):
            raise ValueError('Audit input outside dossier')
        return json.loads(path.read_text())
    state = read_local(dossier / 'state.json')
    rows = []
    def inspect(value, expected, base, kind, active=False):
        p = Path(value)
        historical = str(p)
        remapped = False
        if p.is_absolute():
            if p.is_relative_to(old_root):
                p = root / p.relative_to(old_root)
                remapped = str(p) != historical
            elif not p.is_relative_to(root):
                rows.append(dict(kind=kind, historical=historical, status='outside-mapping', active=active))
                return
        else:
            p = base / p
        resolved = p.resolve()
        if not resolved.is_relative_to(root):
            status = 'outside-mapping'
        elif not isinstance(expected, str) or len(expected) != 64:
            status = 'missing-expected-hash'
        elif not resolved.is_file():
            status = 'missing'
        else:
            status = 'match' if sha(resolved) == expected else 'changed'
        rows.append(dict(kind=kind, historical=historical, mapped=str(p), status=status,
                         remapped=remapped, active=active))
    for receipt in state.get('receipts', []):
        inspect(receipt['path'], receipt['sha256'], root, 'phase-receipt')
    active = {s['packet_id'] for s in state.get('validator_sessions', []) if not s.get('superseded')}
    for manifest in sorted((dossier / 'validation/packets').glob('*/manifest.json')):
        m = read_local(manifest)
        current = m.get('packet_id') in active
        for f in m.get('files', []):
            inspect(f['snapshot'], f['sha256'], dossier, 'frozen-snapshot')
            inspect(f['original'], f['sha256'], root, 'original-' + f.get('role', 'input'),
                    current and f.get('role') == 'step-product')
        if m.get('production_report'):
            inspect(m['production_report'], m.get('production_sha256'), root, 'production-report')
    for dispatch in sorted((dossier / 'validation/dispatches').glob('*.json')):
        d = read_local(dispatch)
        inspect('validation/packets/' + d['packet_id'] + '/manifest.json',
                d['packet_sha256'], dossier, 'dispatched-manifest')
        inspect(d['observation'], d['observation_sha256'], dossier, 'spawn-observation')
    frozen = [r for r in rows if r['kind'] in ('phase-receipt', 'frozen-snapshot',
                                             'dispatched-manifest', 'spawn-observation')]
    preserved = all(r['status'] == 'match' for r in frozen)
    remapped_active = any(r.get('remapped') and r['active'] for r in rows)
    failures = [r for r in rows if r['status'] != 'match']
    return dict(schema_version='relocation-audit-v1', project_id=state.get('id', dossier.name),
                mapping={'old_root': str(old_root), 'new_root': str(root)}, rows=rows,
                archived_bytes_preserved=preserved if frozen else None,
                archived_objects_checked=len(frozen), mapping_complete=not failures,
                new_baseline_required=remapped_active or bool(failures),
                acceptance_granted=False,
                limits=['Read-only path/hash audit, not a fresh validation or full gate-history verifier',
                        'Original paths remain unchanged; workflow does not consume this mapping',
                        'Legacy wiki/projects migration requires a separate plan',
                        'No checked archives means no archive-preservation evidence'])

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('project'); p.add_argument('--old-root', required=True)
    a = p.parse_args()
    result = audit(ROOT, resolve_project(ROOT, a.project), a.old_root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['mapping_complete'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
