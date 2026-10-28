import copy
import json
import shutil
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import reconcile_lwc_sources as reconcile


class SourceReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve() / 'destination'
        (self.root / 'scripts').mkdir(parents=True)
        (self.root / 'scripts/lwc').write_text('#!/bin/sh\nexit 0\n')
        (self.root / 'index').mkdir()
        self.identity = {'schema_version': reconcile.SCHEMA, 'provenance': 'Official CLI source list',
                         'created_at': '2026-09-12', 'sources': {
                             'alpha': {'original_lwc_id': 3, 'content_hash': 'a' * 64,
                                       'bytes': 12, 'title': 'Alpha', 'origin': '/old/alpha'},
                             'beta': {'original_lwc_id': 7, 'content_hash': 'b' * 64,
                                      'bytes': 16, 'title': 'Beta', 'origin': '/old/beta'}}}
        self.reference = self.root / 'index/lwc-source-identities.json'
        self.map = self.root / 'index/lwc-source-map.json'
        self.write_reference()
        self.map.write_text('{"alpha": 3, "beta": 7}\n')
        self.live = [{'id': 1, 'content_hash': 'b' * 64, 'bytes': 16, 'title': 'Renamed Beta', 'origin': '/new/beta'},
                     {'id': 2, 'content_hash': 'a' * 64, 'bytes': 12, 'title': 'Alpha', 'origin': '/new/alpha'}]
        self.calls = []
        for path in ['.lwc/wiki.db', 'raw/alpha.txt', 'sources/alpha/revisions/hash/page.md',
                     'projects/history/reviews/frozen.json']:
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('Original historical source ID 3')
        self.original = self.snapshot()

    def tearDown(self):
        self.tmp.cleanup()

    def write_reference(self):
        self.reference.write_bytes(reconcile.encode(self.identity))

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}

    def runner(self, command, **kwargs):
        self.calls.append((command, kwargs))
        self.assertEqual(command[:3], [str(self.root / 'scripts/lwc'), 'source', 'list'])
        self.assertEqual(kwargs['cwd'], self.root)
        self.assertNotIn('--json', command)
        limit = int(command[command.index('--limit') + 1])
        offset = int(command[command.index('--offset') + 1])
        page = {'sources': self.live[offset:offset + limit], 'limit': limit, 'offset': offset,
                'has_more': offset + limit < len(self.live)}
        return SimpleNamespace(returncode=0, stdout=json.dumps(page), stderr='')

    def run_reconcile(self, apply=False):
        return reconcile.reconcile(self.root, apply=apply, runner=self.runner)

    def assert_refused_unchanged(self, match):
        before = self.snapshot()
        with self.assertRaisesRegex(reconcile.ReconciliationError, match):
            self.run_reconcile(apply=True)
        self.assertEqual(before, self.snapshot())

    def test_remapped_hash_match_default_read_only_preserves_every_file(self):
        result = self.run_reconcile()
        self.assertTrue(result['changed'])
        self.assertTrue(result['read_only'])
        self.assertFalse(result['applied'])
        self.assertFalse(result['numeric_ids_unchanged'])
        self.assertEqual(result['destination_map'], {'alpha': 2, 'beta': 1})
        self.assertEqual(result['matches'][0]['original_lwc_id'], 3)
        self.assertFalse(result['matches'][1]['title_unchanged'])
        self.assertEqual(self.original, self.snapshot())

    def test_apply_exact_backup_receipt_atomic_map_and_idempotent_rerun(self):
        old = self.map.read_bytes()
        result = self.run_reconcile(apply=True)
        self.assertTrue(result['applied'])
        self.assertEqual(json.loads(self.map.read_bytes()), {'alpha': 2, 'beta': 1})
        self.assertEqual((self.root / result['backup']).read_bytes(), old)
        receipt = json.loads((self.root / result['receipt']).read_bytes())
        self.assertEqual(receipt['before_map_sha256'], reconcile.sha256(old))
        self.assertEqual(receipt['after_map_sha256'], reconcile.sha256(self.map.read_bytes()))
        self.assertEqual(receipt['identities_sha256'], reconcile.sha256(self.reference.read_bytes()))
        for name, data in self.original.items():
            if name != 'index/lwc-source-map.json':
                self.assertEqual((self.root / name).read_bytes(), data)
        after = self.snapshot()
        second = self.run_reconcile(apply=True)
        self.assertFalse(second['changed'])
        self.assertFalse(second['applied'])
        self.assertEqual(after, self.snapshot())
        self.assertFalse(list((self.root / 'index').glob('.lwc-source-map.*')))

    def test_missing_unknown_duplicate_hash_and_bytes_fail_closed(self):
        baseline = copy.deepcopy(self.live)
        self.live.pop()
        self.assert_refused_unchanged('Missing')
        self.live = copy.deepcopy(baseline)
        self.live[0]['content_hash'] = 'c' * 64
        self.assert_refused_unchanged('Unknown')
        self.live = copy.deepcopy(baseline)
        duplicate = copy.deepcopy(self.live[0]); duplicate['id'] = 4
        self.live.append(duplicate)
        self.assert_refused_unchanged('Ambiguous live')
        self.live = copy.deepcopy(baseline)
        self.live[1]['bytes'] = 99
        self.assert_refused_unchanged('bytes mismatch')

    def test_invalid_or_duplicate_reference_hash_refused(self):
        self.identity['sources']['alpha']['content_hash'] = 'not-a-hash'
        self.write_reference()
        self.assert_refused_unchanged('content_hash')
        self.identity['sources']['alpha']['content_hash'] = 'b' * 64
        self.write_reference()
        self.assert_refused_unchanged('Ambiguous immutable')

    def test_malicious_old_map_refused_without_matching_by_old_numeric_id(self):
        for document in [ {'alpha': '../.lwc/wiki.db', 'beta': 7}, {'alpha': True, 'beta': 7},
                          {'alpha': 99, 'beta': 7}, {'alpha': 2, 'beta': 7},
                          {'alpha': 3, 'beta': 3}, {'../escape': 3, 'beta': 7} ]:
            self.map.write_text(json.dumps(document))
            self.assert_refused_unchanged('active source map|Active map')
        self.map.write_text('{"alpha":3,"alpha":99,"beta":7}')
        self.assert_refused_unchanged('Duplicate JSON key')
        self.assertFalse((self.root.parent / 'escape').exists())

    def test_symlink_map_reference_wrapper_index_root_or_receipt_directory_refused(self):
        for relative in ['index/lwc-source-map.json', 'index/lwc-source-identities.json', 'scripts/lwc']:
            path = self.root / relative
            data = path.read_bytes()
            external = self.root.parent / 'external'
            external.write_bytes(data)
            path.unlink(); path.symlink_to(external)
            with self.assertRaisesRegex(reconcile.ReconciliationError, 'Symlink'):
                self.run_reconcile(apply=True)
            self.assertEqual(external.read_bytes(), data)
            path.unlink(); path.write_bytes(data)
        directory = self.root / 'index/source-reconciliation'
        directory.symlink_to(self.root.parent, target_is_directory=True)
        with self.assertRaisesRegex(reconcile.ReconciliationError, 'Symlink'):
            self.run_reconcile(apply=True)
        directory.unlink()
        linked = self.root.parent / 'linked'
        linked.symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(reconcile.ReconciliationError, 'Symlink'):
            reconcile.reconcile(linked, apply=True, runner=self.runner)
        index = self.root / 'index'
        saved = self.root / 'saved-index'
        index.rename(saved); index.symlink_to(saved, target_is_directory=True)
        with self.assertRaisesRegex(reconcile.ReconciliationError, 'Symlink'):
            self.run_reconcile(apply=True)

    def test_paginated_official_cli_and_unordered_or_incomplete_pages_refused(self):
        rows = reconcile.list_sources(self.root, runner=self.runner, limit=1)
        self.assertEqual(rows, self.live)
        self.assertEqual([call[0][-1] for call in self.calls], ['0', '1'])
        self.live[1]['id'] = 1
        self.assert_refused_unchanged('Repeated or unordered')
        def bad_page(command, **kwargs):
            return SimpleNamespace(returncode=0, stdout=json.dumps({'sources': [], 'limit': 100,
                'offset': 0, 'has_more': True}), stderr='')
        with self.assertRaisesRegex(reconcile.ReconciliationError, 'Incomplete'):
            reconcile.reconcile(self.root, runner=bad_page)

    def test_cli_failure_and_bad_json_refused(self):
        for response, match in [(SimpleNamespace(returncode=1, stdout='', stderr='CLI error'), 'failed'),
                                (SimpleNamespace(returncode=0, stdout='not-json', stderr=''), 'Invalid JSON')]:
            before = self.snapshot()
            with self.assertRaisesRegex(reconcile.ReconciliationError, match):
                reconcile.reconcile(self.root, apply=True, runner=lambda *a, **kw: response)
            self.assertEqual(before, self.snapshot())

    def test_conflicting_backup_refused_and_concurrent_map_change_never_replaced(self):
        directory = self.root / 'index/source-reconciliation'; directory.mkdir()
        backup = directory / ('source-map.' + reconcile.sha256(self.map.read_bytes()) + '.json')
        backup.write_text('Conflicting evidence')
        self.assert_refused_unchanged('Evidence conflict')
        backup.unlink()
        original_store = reconcile.store_evidence
        def mutate_map(path, data):
            original_store(path, data)
            self.map.write_text('Concurrent owner update')
        from unittest.mock import patch
        with patch.object(reconcile, 'store_evidence', side_effect=mutate_map):
            with self.assertRaisesRegex(reconcile.ReconciliationError, 'changed concurrently'):
                self.run_reconcile(apply=True)
        self.assertEqual(self.map.read_text(), 'Concurrent owner update')
        self.assertFalse(list((self.root / 'index').glob('.lwc-source-map.*')))

    def test_repeated_migrations_are_anchored_to_preserved_receipts(self):
        first=self.run_reconcile(apply=True)
        first_backup=(self.root/first['backup']).read_bytes()
        first_receipt=(self.root/first['receipt']).read_bytes()
        self.live[0]['id']=5;self.live[1]['id']=6
        second=self.run_reconcile(apply=True)
        self.assertTrue(second['applied']);self.assertEqual(json.loads(self.map.read_bytes()),{'alpha':6,'beta':5})
        self.assertEqual(len(second['verified_previous_history']),2)
        self.assertEqual((self.root/first['backup']).read_bytes(),first_backup)
        self.assertEqual((self.root/first['receipt']).read_bytes(),first_receipt)
        self.live[0]['id']=8;self.live[1]['id']=9
        third=self.run_reconcile(apply=True)
        self.assertEqual(len(third['verified_previous_history']),4);self.assertTrue(third['applied'])
        self.assertFalse(self.run_reconcile(apply=True)['applied'])
    def test_revisited_numeric_map_can_migrate_again_without_losing_history(self):
        first=self.run_reconcile(apply=True)
        first_files={p: (self.root/first[p]).read_bytes() for p in ('receipt','backup')}
        self.live[0]['id']=5;self.live[1]['id']=6
        second=self.run_reconcile(apply=True)
        self.live[0]['id']=1;self.live[1]['id']=2
        third=self.run_reconcile(apply=True)
        self.live[0]['id']=9;self.live[1]['id']=10
        fourth=self.run_reconcile(apply=True)
        self.assertTrue(fourth['applied'])
        self.assertEqual(fourth['destination_map'],{'alpha':10,'beta':9})
        self.assertEqual(len(fourth['verified_previous_history']),2)
        for key,data in first_files.items():self.assertEqual((self.root/first[key]).read_bytes(),data)
        for result in (second,third):self.assertTrue((self.root/result['receipt']).is_file())
        unchanged=self.snapshot();self.assertFalse(self.run_reconcile(apply=True)['applied'])
        self.assertEqual(unchanged,self.snapshot())

    def test_repeated_transition_after_copy_keeps_both_destination_receipts(self):
        self.run_reconcile(apply=True)
        self.live[0]['id']=5;self.live[1]['id']=6
        second=self.run_reconcile(apply=True);receipt_bytes=(self.root/second['receipt']).read_bytes()
        self.live[0]['id']=1;self.live[1]['id']=2
        self.run_reconcile(apply=True)
        new_root=self.root.parent/'another-destination';shutil.copytree(self.root,new_root)
        self.root=new_root;self.map=self.root/'index/lwc-source-map.json'
        self.reference=self.root/'index/lwc-source-identities.json'
        self.live[0]['id']=5;self.live[1]['id']=6
        fourth=self.run_reconcile(apply=True)
        self.assertTrue(fourth['applied']);self.assertNotEqual(fourth['receipt'],second['receipt'])
        self.assertEqual((self.root/second['receipt']).read_bytes(),receipt_bytes)
        self.live[0]['id']=9;self.live[1]['id']=10
        self.assertTrue(self.run_reconcile(apply=True)['applied'])

    def test_legacy_v1_receipts_remain_usable_without_rewriting(self):
        first=self.run_reconcile(apply=True);path=self.root/first['receipt']
        receipt=json.loads(path.read_bytes());receipt['schema_version']='lwc-source-reconciliation-receipt-v1'
        keys=('identities_sha256','before_map_sha256','after_map_sha256','source_list_sha256')
        name='reconciliation.'+reconcile.sha256(reconcile.encode({k:receipt[k] for k in keys}))+'.json'
        legacy_path=path.parent/name;legacy_bytes=reconcile.encode(receipt)
        legacy_path.write_bytes(legacy_bytes);path.unlink()
        self.live[0]['id']=5;self.live[1]['id']=6
        second=self.run_reconcile(apply=True);self.assertTrue(second['applied'])
        self.assertEqual(legacy_path.read_bytes(),legacy_bytes)
        self.assertTrue(any(p['path'].endswith(name) for p in second['verified_previous_history']))

    def test_changed_history_backup_or_receipt_refuses_next_migration(self):
        first=self.run_reconcile(apply=True)
        self.live[0]['id']=5;self.live[1]['id']=6
        backup=self.root/first['backup'];original=backup.read_bytes();backup.write_text('{"alpha":99,"beta":7}')
        self.assert_refused_unchanged('history backup changed')
        backup.write_bytes(original)
        receipt=self.root/first['receipt'];value=json.loads(receipt.read_bytes());value['destination_map']['alpha']=99;receipt.write_bytes(reconcile.encode(value))
        self.assert_refused_unchanged('history content mismatch|after-map mismatch|history identity/name mismatch')


if __name__ == '__main__':
    unittest.main()
