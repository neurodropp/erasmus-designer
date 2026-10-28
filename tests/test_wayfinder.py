import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import wayfinder
from project_memory import ProjectMemory

class WayfinderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'projects/demo--ka220-youth--2026'; self.path.mkdir(parents=True)
        self.state = {'id': self.path.name, 'program': 'ERASMUS', 'action': 'KA220-YOU', 'sector': 'YOU', 'year': 2026}
        (self.path / 'state.json').write_text(json.dumps(self.state))
        (self.path / 'proof.md').write_text('Synthetic evidence: observed choice and research.')
        self.memory = ProjectMemory(self.root, self.path.name); self.memory.initialize()
        wayfinder.initialize(self.path, self.state)

    def change(self, op, **payload):
        return wayfinder.change(self.root, self.path, op, {'author': 'root', 'reason': 'Synthetic test', **payload})

    def add(self, kind='research', dependencies=None):
        self.change('add', title='Define target', question='Which target and evidence?', kind=kind, dependencies=dependencies or [])
        return next(reversed(wayfinder.load(self.path)[0]['decisions']))

    def memory_record(self, ident, provenance='agent-analysis', supersedes=None):
        return self.memory.record({'kind': 'decision', 'status': 'confirmed', 'title': 'Synthetic decision',
            'summary': 'Choice: collect a needs baseline', 'author': 'root',
            'provenance': {'type': provenance, 'reference': 'Synthetic observed record'},
            'evidence': [{'path': 'proof.md', 'locator': 'Synthetic choice'}],
            'tags': ['wayfinder:' + ident], 'supersedes': supersedes or []})['id']

    def resolve(self, ident, mem):
        return self.change('resolve', id=ident, memory_ids=[mem], resolution='collect a needs baseline',
                           evidence=[{'path': 'proof.md', 'locator': 'Synthetic evidence'}])

    def test_empty_init_does_not_invent_decisions(self):
        result = wayfinder.context(self.path)
        self.assertEqual(result['research_frontier'], []); self.assertEqual(result['human_frontier'], [])
        self.assertEqual(wayfinder.initialize(self.path, self.state)['revision'], 0)

    def test_dependency_frontier_and_owner_claim(self):
        first = self.add(); second = self.add(dependencies=[first])
        with self.assertRaises(ValueError): self.change('claim', id=second, assignee='root')
        self.change('claim', id=first, assignee='root')
        with self.assertRaises(ValueError): self.change('claim', id=first, assignee='other')
        result = self.resolve(first, self.memory_record(first))
        self.assertEqual([r['id'] for r in result['research_frontier']], [second])

    def test_cycle_and_unknown_dependencies_fail_without_history_write(self):
        before = wayfinder.context(self.path)['revision']
        with self.assertRaises(ValueError): self.add(dependencies=['D-0001'])
        with self.assertRaises(ValueError): self.add(dependencies=['D-9999'])
        self.assertEqual(wayfinder.context(self.path)['revision'], before)

    def test_human_choice_not_resolved_by_agent_agreement(self):
        ident = self.add(kind='human-decision')
        with self.assertRaises(ValueError): self.change('claim', id=ident, assignee='root')
        with self.assertRaises(ValueError): self.resolve(ident, self.memory_record(ident))
        self.resolve(ident, self.memory_record(ident, 'user-instruction'))
        self.assertEqual(wayfinder.context(self.path)['human_frontier'], [])

    def test_memory_must_match_question_and_choice(self):
        first = self.add(); second = self.add()
        with self.assertRaises(ValueError): self.resolve(second, self.memory_record(first))
        mem = self.memory_record(first)
        with self.assertRaises(ValueError):
            self.change('resolve', id=first, memory_ids=[mem], resolution='different option',
                        evidence=[{'path': 'proof.md', 'locator': 'Synthetic'}])

    def test_cancelled_dependency_remains_blocking(self):
        first = self.add(); second = self.add(dependencies=[first]); self.change('cancel', id=first)
        self.assertIn(second, [r['id'] for r in wayfinder.context(self.path)['blocked']])

    def test_reopen_cascades_and_preserves_history(self):
        first = self.add(); second = self.add(dependencies=[first])
        self.resolve(first, self.memory_record(first)); self.resolve(second, self.memory_record(second))
        before = {p.name: p.read_bytes() for p in (self.path / 'wayfinder/history').glob('*.json')}
        self.change('reopen', id=first)
        state, _ = wayfinder.load(self.path)
        self.assertTrue(all(r['status'] == 'open' for r in state['decisions'].values()))
        self.assertTrue(all((self.path / 'wayfinder/history' / n).read_bytes() == b for n, b in before.items()))

    def test_changed_evidence_invalidates_transitive_premises(self):
        first = self.add(); second = self.add(dependencies=[first]); third = self.add(dependencies=[second])
        self.resolve(first, self.memory_record(first)); self.resolve(second, self.memory_record(second))
        (self.path / 'proof.md').write_text('changed')
        result = wayfinder.context(self.path)
        self.assertEqual(set(result['invalid_resolutions']), {first, second})
        with self.assertRaises(ValueError): self.change('claim', id=third, assignee='root')

    def test_superseded_memory_reopens_research_requirement(self):
        ident = self.add(); original = self.memory_record(ident); self.resolve(ident, original)
        self.memory_record(ident, supersedes=[original])
        self.assertIn(ident, wayfinder.context(self.path)['invalid_resolutions'])

    def test_projection_rebuild_and_hash_tampering(self):
        self.add(); (self.path / 'wayfinder/map.json').write_text('{}')
        self.assertEqual(len(wayfinder.context(self.path)['research_frontier']), 1)
        wayfinder.render(self.path)
        self.assertEqual(json.loads((self.path / 'wayfinder/map.json').read_text())['schema'], wayfinder.SCHEMA)
        _, head = wayfinder.load(self.path); (self.path / 'wayfinder' / head['file']).write_text('{}')
        with self.assertRaises(ValueError): wayfinder.load(self.path)

    def test_symlink_evidence_not_accepted(self):
        ident = self.add(); mem = self.memory_record(ident)
        (self.path / 'alias.md').symlink_to(self.path / 'proof.md')
        with self.assertRaises(ValueError):
            self.change('resolve', id=ident, memory_ids=[mem], resolution='collect a needs baseline',
                        evidence=[{'path': 'alias.md', 'locator': 'Synthetic'}])

if __name__ == '__main__': unittest.main()
