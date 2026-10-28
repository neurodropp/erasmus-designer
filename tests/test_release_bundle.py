import hashlib
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import release_bundle as release


class ReleaseBundleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name).resolve()
        self.root = self.base / 'source'
        self.root.mkdir()
        self.write('AGENTS.md', 'Rules\n')
        self.write('scripts/lwc', '#!/bin/sh\nexit 0\n')
        (self.root / 'scripts/lwc').chmod(0o755)
        self.write('skills/test/resources/example.txt', 'Required skill resource')
        self.write('sources/immutable/page.json', '{"hash":"existing"}\n')
        self.write('raw/template.docx', 'Original template')
        self.write('index/lwc-source-map.json', '{"local":1}\n')
        self.write('vendor/lwc/package-lock.json', '{"version":"0.18.5"}\n')
        self.write('requirements-import.lock.txt', 'package==1.0\n')
        self.write('projects/README.md', 'Project rules\n')
        self.write('index/history-packet.json', '{"old_root":"/source/root"}\n')
        self.write('index/test-history.log', 'Archived historical result\n')
        self.archive = self.base / 'engine.zip'

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, relative, content):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def build(self, **kwargs):
        return release.build(self.root, self.archive, '2026.09.12-1', **kwargs)

    def rewrite(self, change):
        with zipfile.ZipFile(self.archive) as archive:
            items = [(info, archive.read(info.filename)) for info in archive.infolist()]
        with zipfile.ZipFile(self.archive, 'w') as archive:
            for info, data in items:
                altered = change(info, data)
                if altered is not None:
                    archive.writestr(*altered)

    def test_roundtrip_hashes_modes_new_root_and_source_preservation(self):
        before = release.digest(self.root / 'sources/immutable/page.json')
        result = self.build()
        manifest = release.verify(self.archive, result['sha256'])
        target = self.base / 'other-root'
        outcome = release.unpack(self.archive, target, result['sha256'])
        self.assertFalse(outcome['runtime_installed'])
        self.assertFalse(outcome['relocation_performed'])
        for entry in manifest['files']:
            self.assertEqual(release.digest(target / entry['path']), entry['sha256'])
        self.assertEqual((target / 'scripts/lwc').stat().st_mode & 0o777, 0o755)
        self.assertEqual(release.digest(self.root / 'sources/immutable/page.json'), before)
        self.assertFalse((target / '.codex').exists())
        self.assertEqual(manifest['source_root'], str(self.root))

    def test_explicit_selection_excludes_native_memory_secrets_generated_and_large_root(self):
        for relative in ['.lwc/wiki.db', '.codex/config.toml', '.agents/skills/test/x',
                         'vendor/lwc/node_modules/@i-xor/lwc/vendor/lwc', 'index/evidence.sqlite-wal',
                         'scripts/__pycache__/code.pyc', 'scripts/.env.local', 'config/credentials.json',
                         'resources/huge.bin', 'dist/previous.zip', 'scripts/native.dll',
                         'projects/private--ka220-youth--2026/state.json', 'wiki/projects/old/state.json']:
            self.write(relative, 'DO NOT EXPORT')
        self.build()
        with zipfile.ZipFile(self.archive) as archive:
            self.assertEqual(set(archive.namelist()), {release.MANIFEST, 'AGENTS.md', 'scripts/lwc',
                'skills/test/resources/example.txt', 'sources/immutable/page.json', 'raw/template.docx',
                'index/lwc-source-map.json', 'vendor/lwc/package-lock.json', 'requirements-import.lock.txt',
                'projects/README.md', 'index/history-packet.json', 'index/test-history.log'})

    def test_opt_in_project_receipts_preserved_without_relocation(self):
        project = 'private--ka220-youth--2026'
        original = '{"packet":"/old/root/packet.json","sha256":"frozen"}\n'
        self.write(f'projects/{project}/reviews/receipt.json', original)
        self.write('wiki/projects/old/reviews/receipt.json', original)
        self.build(projects=[project], legacy=['old'])
        target = self.base / 'destination'
        release.unpack(self.archive, target)
        self.assertEqual((target / f'projects/{project}/reviews/receipt.json').read_text(), original)
        self.assertEqual((target / 'wiki/projects/old/reviews/receipt.json').read_text(), original)

    def test_engine_working_memory_roundtrips_without_private_project_or_update_staging(self):
        log=self.write('work/engine-memory/events.jsonl','{"decision":"shared engine design"}\n')
        self.write('work/engine-memory/context.md','Confirmed engine decisions\n')
        self.write('work/knowledge-updates/candidate/private-form.json','Not an active source')
        self.write('work/another-project/notes.md','Private project notes')
        self.write('projects/private--ka220-youth--2026/memory/events.jsonl','Private decisions')
        result=self.build();target=self.base/'restored'
        release.unpack(self.archive,target,result['sha256'])
        self.assertEqual((target/'work/engine-memory/events.jsonl').read_bytes(),log.read_bytes())
        self.assertTrue((target/'work/engine-memory/context.md').is_file())
        self.assertFalse((target/'work/knowledge-updates').exists())
        self.assertFalse((target/'work/another-project').exists())
        self.assertFalse((target/'projects/private--ka220-youth--2026').exists())

    def test_engine_memory_symlink_is_refused_without_exporting_other_work(self):
        outside=self.base/'outside';outside.mkdir()
        self.write('work/private/secret.md','Never export')
        (self.root/'work/engine-memory').symlink_to(outside,target_is_directory=True)
        with self.assertRaisesRegex(release.BundleError,'Symlink'):
            self.build()
        self.assertFalse(self.archive.exists())

    def test_reconciliation_history_roundtrips_and_unknown_nested_index_is_excluded(self):
        receipt='index/source-reconciliation/reconciliation.'+'a'*64+'.json'
        backup='index/source-reconciliation/source-map.'+'b'*64+'.json'
        self.write(receipt,'Frozen reconciliation receipt\n');self.write(backup,'Frozen exact old source map\n')
        self.write('index/other-directory/private.json','Not in export scope')
        self.build();target=self.base/'restored';release.unpack(self.archive,target)
        self.assertEqual((target/receipt).read_bytes(),(self.root/receipt).read_bytes())
        self.assertEqual((target/backup).read_bytes(),(self.root/backup).read_bytes())
        self.assertFalse((target/'index/other-directory').exists())
    def test_reconciliation_directory_escape_and_unknown_files_are_refused(self):
        folder=self.root/'index/source-reconciliation';folder.symlink_to(self.base,target_is_directory=True)
        with self.assertRaisesRegex(release.BundleError,'Symlink'):self.build()
        folder.unlink();folder.mkdir();(folder/'unexpected.json').write_text('{}')
        with self.assertRaisesRegex(release.BundleError,'Unexpected'):self.build()
        self.assertFalse(self.archive.exists())

    def test_reproducible_and_no_overwrite_or_self_inclusion(self):
        result = self.build()
        second = self.base / 'second.zip'
        release.build(self.root, second, '2026.09.12-1')
        self.assertEqual(release.digest(second), result['sha256'])
        with self.assertRaisesRegex(release.BundleError, 'already exists'):
            self.build()
        with self.assertRaisesRegex(release.BundleError, 'outside'):
            release.build(self.root, self.root / 'raw/bundle.zip', 'test')
        with self.assertRaisesRegex(release.BundleError, 'outside'):
            release.build(self.root, self.base / 'not-there/../source/bundle.zip', 'test')
        self.assertEqual(release.digest(self.archive), result['sha256'])

    def test_in_root_dist_is_safe_but_source_tree_outputs_are_refused(self):
        output = self.root / 'dist/0.2.0/engine.zip'
        first = release.build(self.root, output, '0.2.0')
        second = release.build(self.root, self.base / 'copy.zip', '0.2.0')
        self.assertEqual(first['sha256'], second['sha256'])
        with zipfile.ZipFile(output) as archive:
            self.assertFalse(any(name.startswith('dist/') for name in archive.namelist()))
        for tree in ('scripts', 'config'):
            with self.assertRaisesRegex(release.BundleError, 'outside'):
                release.build(self.root, self.root / tree / 'engine.zip', 'test')
        linked = self.root / 'dist/linked'
        linked.symlink_to(self.base, target_is_directory=True)
        with self.assertRaisesRegex(release.BundleError, 'symlink'):
            release.build(self.root, linked / 'engine.zip', 'test')

    def test_existing_different_root_and_symlink_destinations_preserved(self):
        self.build()
        target = self.base / 'existing'
        target.mkdir()
        sentinel = target / 'keep.txt'
        sentinel.write_text('DO NOT OVERWRITE')
        with self.assertRaisesRegex(release.BundleError, 'already exists'):
            release.unpack(self.archive, target)
        self.assertEqual(sentinel.read_text(), 'DO NOT OVERWRITE')
        linked = self.base / 'linked'
        linked.symlink_to(target, target_is_directory=True)
        with self.assertRaises(release.BundleError):
            release.unpack(self.archive, linked)
        with self.assertRaises(release.BundleError):
            release.unpack(self.archive, linked / 'new')
        self.assertFalse((target / 'new').exists())

    def test_source_symlinks_and_project_escape_rejected(self):
        secret = self.base / 'external.txt'
        secret.write_text('outside')
        (self.root / 'scripts/link').symlink_to(secret)
        with self.assertRaisesRegex(release.BundleError, 'regular files'):
            self.build()
        (self.root / 'scripts/link').unlink()
        with self.assertRaises(release.BundleError):
            self.build(projects=['../external'])
        vendor = self.root / 'vendor'
        import shutil
        shutil.rmtree(vendor)
        vendor.symlink_to(self.base, target_is_directory=True)
        (self.base / 'lwc').mkdir()
        (self.base / 'lwc/package.json').write_text('external')
        with self.assertRaisesRegex(release.BundleError, 'Symlink'):
            self.build()

    def test_tamper_and_trusted_archive_checksum_rejected_before_unpack(self):
        result = self.build()
        self.rewrite(lambda info, data: (info, b'Other\n') if info.filename == 'AGENTS.md' else (info, data))
        target = self.base / 'new'
        with self.assertRaisesRegex(release.BundleError, 'SHA-256'):
            release.verify(self.archive)
        with self.assertRaisesRegex(release.BundleError, 'trusted checksum'):
            release.verify(self.archive, result['sha256'])
        with self.assertRaises(release.BundleError):
            release.unpack(self.archive, target)
        self.assertFalse(target.exists())
        self.assertFalse(list(self.base.glob('.release-unpack-*')))

    def test_traversal_absolute_windows_paths_and_unlisted_entries_rejected(self):
        self.build()
        original = self.archive.read_bytes()
        for name in ['../escape', '/absolute', 'C:/drive', 'scripts\\escape', 'scripts/./escape',
                     'scripts//escape', 'scripts/CON.txt', 'scripts/trailing.', 'unlisted.txt']:
            self.archive.write_bytes(original)
            with zipfile.ZipFile(self.archive, 'a') as archive:
                archive.writestr(release.zip_info(name), b'bad')
            with self.subTest(name=name), self.assertRaises(release.BundleError):
                release.unpack(self.archive, self.base / 'new')
            self.assertFalse((self.base / 'new').exists())
            self.assertFalse((self.base / 'escape').exists())

    def test_archive_symlink_special_file_collision_and_byte_limit_rejected(self):
        self.build()
        original = self.archive.read_bytes()
        for mode, name in [(stat.S_IFLNK | 0o777, 'scripts/link'),
                           (stat.S_IFIFO | 0o644, 'scripts/pipe'),
                           (stat.S_IFREG | 0o644, 'scripts'),
                           (stat.S_IFREG | 0o644, 'agents.md')]:
            self.archive.write_bytes(original)
            info = release.zip_info(name)
            info.external_attr = mode << 16
            with zipfile.ZipFile(self.archive, 'a') as archive:
                archive.writestr(info, 'outside')
            with self.subTest(name=name), self.assertRaises(release.BundleError):
                release.verify(self.archive)
        self.archive.write_bytes(original)
        with self.assertRaisesRegex(release.BundleError, 'byte limit'):
            release.verify(self.archive, max_bytes=1)
        with self.assertRaisesRegex(release.BundleError, 'byte limit'):
            release.build(self.root, self.base / 'tiny.zip', 'tiny', max_bytes=1)
        self.assertFalse((self.base / 'tiny.zip').exists())

    def test_valid_hash_cannot_authorize_memory_or_generated_runtime_in_engine_archive(self):
        self.build()
        original = self.archive.read_bytes()
        for name in ('.lwc/wiki.db', '.codex/auth.json', 'projects/unselected/receipt.json',
                     'vendor/lwc/node_modules/native', 'config/credentials.json'):
            self.archive.write_bytes(original)
            payload = b'forbidden'
            def change(info, data):
                if info.filename == release.MANIFEST:
                    manifest = json.loads(data)
                    manifest['files'].append({'path': name, 'size': len(payload),
                        'sha256': hashlib.sha256(payload).hexdigest(), 'executable': False})
                    manifest['total_bytes'] += len(payload)
                    data = release.canonical(manifest)
                return info, data
            self.rewrite(change)
            with zipfile.ZipFile(self.archive, 'a') as archive:
                archive.writestr(release.zip_info(name), payload)
            with self.subTest(name=name), self.assertRaisesRegex(release.BundleError, 'scope'):
                release.unpack(self.archive, self.base / 'new')
            self.assertFalse((self.base / 'new').exists())

    def test_invalid_manifest_and_missing_files_rejected(self):
        self.build()
        self.rewrite(lambda info, data: (info, b'{"format":"wrong"}') if info.filename == release.MANIFEST else (info, data))
        with self.assertRaisesRegex(release.BundleError, 'Unsupported'):
            release.verify(self.archive)


if __name__ == '__main__':
    unittest.main()
