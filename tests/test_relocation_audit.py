import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from relocation_audit import audit

class RelocationTests(unittest.TestCase):
    def test_mapping_checks_bytes_but_never_accepts_or_rewrites_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); path = root / 'projects/demo--ka220-youth--2026'
            folder = path / 'validation/packets/idea-1'; folder.mkdir(parents=True)
            product = path / 'stages/idea/product.md'; product.parent.mkdir(parents=True)
            product.write_text('synthetic product'); h = hashlib.sha256(product.read_bytes()).hexdigest()
            snapshot = folder / 'snapshot.md'; snapshot.write_bytes(product.read_bytes())
            (path / 'state.json').write_text(json.dumps({'validator_sessions': [{'packet_id': 'idea-1'}]}))
            mp = folder / 'manifest.json'
            mp.write_text(json.dumps({'packet_id': 'idea-1', 'files': [{
                'snapshot': str(snapshot.relative_to(path)), 'original': '/old/engine/' + str(product.relative_to(root)),
                'sha256': h, 'role': 'step-product'}]}))
            before = mp.read_bytes()
            result = audit(root, path, '/old/engine')
            self.assertTrue(result['mapping_complete']); self.assertTrue(result['archived_bytes_preserved'])
            self.assertTrue(result['new_baseline_required']); self.assertFalse(result['acceptance_granted'])
            self.assertEqual(before, mp.read_bytes())
            snapshot.write_text('changed')
            self.assertFalse(audit(root, path, '/old/engine')['archived_bytes_preserved'])

    def test_outside_mapping_and_symlink_are_not_followed(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside:
            root = Path(tmp); path = root / 'projects/demo'; path.mkdir(parents=True)
            f = Path(outside) / 'secret'; f.write_text('outside')
            h = hashlib.sha256(f.read_bytes()).hexdigest()
            link = path / 'escape'; link.symlink_to(f)
            (path / 'state.json').write_text(json.dumps({'receipts': [{'path': str(link.relative_to(root)), 'sha256': h}]}))
            result = audit(root, path, '/old/engine')
            self.assertEqual(result['rows'][0]['status'], 'outside-mapping')
            self.assertFalse(result['mapping_complete'])
            with self.assertRaises(ValueError): audit(root, path, 'relative/root')
