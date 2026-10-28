import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import project_memory as pm
import workflow


class WorkingMemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.a = self.fixture('same--ka220-youth--2026', 'KA220-YOU')
        self.b = self.fixture('same--ka152-youth-exchange--2026', 'KA152')
        self.memory = pm.ProjectMemory(self.root, self.a.name)
        self.memory.initialize()

    def tearDown(self):
        self.tmp.cleanup()

    def fixture(self, identifier, action):
        path = self.root / 'projects' / identifier
        path.mkdir(parents=True)
        state = {'id': identifier, 'name': 'same', 'program': 'ERASMUS', 'action': action,
                 'sector': 'YOU', 'year': 2026, 'next_phase': 'idea-validation',
                 'state': 'collecting-data', 'receipts': [], 'validator_sessions': []}
        (path / 'state.json').write_text(json.dumps(state))
        (path / 'project.json').write_text(json.dumps({'schema_version': 'project-model-v2', 'project': state}))
        (path / 'inbox').mkdir()
        (path / 'inbox' / 'instruction.md').write_text('SYNTHETIC fixture: bounded local pilot selected.')
        (path / 'receipts').mkdir()
        (path / 'receipts' / 'frozen.json').write_text('{"synthetic":true}')
        return path

    def payload(self, **extra):
        return {'kind': 'decision', 'status': 'confirmed', 'title': 'SYNTHETIC local pilot',
                'summary': 'Use a bounded local pilot with documented learning outcomes.', 'author': 'synthetic-coordinator',
                'provenance': {'type': 'user-instruction', 'reference': 'SYNTHETIC fixture instruction, not a live user decision'},
                'evidence': [{'path': 'inbox/instruction.md', 'locator': 'SYNTHETIC complete fixture paragraph'}], **extra}

    def test_record_is_recovered_in_fresh_process_and_readable_views(self):
        event = self.memory.record(self.payload())
        result = subprocess.run([sys.executable, str(Path(pm.__file__)), '--root', str(self.root),
                                 'search', self.a.name, 'bounded pilot'], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['results'][0]['id'], event['id'])
        context = pm.ProjectMemory(self.root, self.a.name).context('concept-note')
        self.assertEqual(context['confirmed_active'][0]['id'], event['id'])
        self.assertEqual(context['phase'], 'concept-note')
        self.assertIn('documented learning outcomes', (self.a / 'memory/history.md').read_text())
        self.assertIn('[artifact](<../inbox/instruction.md>)', (self.a / 'memory/context.md').read_text())
        self.assertEqual(event['evidence'][0]['sha256'], pm.digest((self.a / 'inbox/instruction.md').read_bytes()))

    def test_initialization_is_idempotent_and_does_not_rewrite_history(self):
        self.memory.record(self.payload())
        before = {f.name: f.read_bytes() for f in (self.a / 'memory').iterdir()}
        self.assertTrue(pm.ProjectMemory(self.root, self.a.name).initialize()['passed'])
        after = {f.name: f.read_bytes() for f in (self.a / 'memory').iterdir()}
        self.assertEqual(before, after)

    def test_supersession_preserves_log_prefix_and_retires_prior_decision(self):
        prior = self.memory.record(self.payload())
        prefix = (self.a / 'memory/events.jsonl').read_bytes()
        replacement = self.memory.record(self.payload(title='SYNTHETIC revised pilot', summary='Narrow the pilot to one organization.',
                                                       supersedes=[prior['id']]))
        self.assertTrue((self.a / 'memory/events.jsonl').read_bytes().startswith(prefix))
        self.assertEqual([r['id'] for r in self.memory.context()['confirmed_active']], [replacement['id']])
        history = self.memory.search('documented', include_history=True)['results']
        self.assertEqual(history[0]['effective_status'], 'superseded')
        self.assertEqual(history[0]['superseded_by'], replacement['id'])
        self.assertEqual(self.memory.search('documented')['total'], 0)
        with self.assertRaisesRegex(ValueError, 'active previous'):
            self.memory.record(self.payload(supersedes=[prior['id']]))

    def test_proposal_cannot_silently_retire_confirmation(self):
        prior = self.memory.record(self.payload())
        before = (self.a / 'memory/events.jsonl').read_bytes()
        with self.assertRaisesRegex(ValueError, 'proposal cannot retire'):
            self.memory.record(self.payload(status='proposed', supersedes=[prior['id']]))
        self.assertEqual(before, (self.a / 'memory/events.jsonl').read_bytes())

    def test_rejection_and_explicit_retirement_are_append_only(self):
        proposed = self.memory.record(self.payload(status='proposed', evidence=[]))
        rejected = self.memory.record(self.payload(status='rejected', supersedes=[proposed['id']], summary='Option rejected based on fixture evidence.'))
        self.assertEqual(self.memory.context()['proposals'], [])
        history = self.memory.search('rejected', include_history=True)['results']
        self.assertEqual(history[0]['id'], rejected['id'])
        self.assertEqual(history[0]['effective_status'], 'rejected')
        confirmed = self.memory.record(self.payload())
        self.memory.record(self.payload(status='superseded', supersedes=[confirmed['id']], summary='Retired without a replacement.'))
        self.assertEqual(self.memory.context()['confirmed_active'], [])

    def test_opening_context_exposes_hypotheses_questions_and_contradictions(self):
        confirmed = self.memory.record(self.payload())
        self.memory.record(self.payload(kind='hypothesis', status='proposed', evidence=[], title='SYNTHETIC baseline hypothesis'))
        self.memory.record(self.payload(kind='open-question', status='proposed', evidence=[], title='SYNTHETIC partner capacity question'))
        contradiction = self.memory.record(self.payload(kind='contradiction', status='proposed', evidence=[],
                                                        title='SYNTHETIC conflicting capacity', contradicts=[confirmed['id']]))
        context = self.memory.context()
        self.assertEqual(len(context['confirmed_active']), 1)
        self.assertEqual(len(context['hypotheses']), 1)
        self.assertEqual(len(context['open_questions']), 1)
        self.assertEqual(context['contradictions'][0]['id'], contradiction['id'])
        self.assertEqual(context['conflicting_pairs'], [{'record_id': contradiction['id'], 'contradicts': confirmed['id']}])

    def test_project_collisions_and_copied_memory_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Ambiguous'):
            pm.ProjectMemory(self.root, 'same')
        other = pm.ProjectMemory(self.root, self.b.name)
        other.initialize()
        event_a = self.memory.record(self.payload())
        event_b = other.record(self.payload())
        self.assertNotEqual(event_a['id'], event_b['id'])
        self.assertEqual(other.search('bounded')['results'][0]['id'], event_b['id'])
        with self.assertRaisesRegex(ValueError, 'active previous'):
            other.record(self.payload(supersedes=[event_a['id']]))
        for name in ('events.jsonl', 'seal.json', *pm.DERIVED):
            (self.b / 'memory' / name).write_bytes((self.a / 'memory' / name).read_bytes())
        result = other.check(rebuild_index=True)
        self.assertFalse(result['canonical_valid'])
        self.assertIn('another dossier', result['issues'][0]['detail'])

    def test_confirmed_ingestion_never_changes_model_gate_or_receipts(self):
        paths = [self.a / 'project.json', self.a / 'state.json', self.a / 'receipts/frozen.json']
        before = {str(p): p.read_bytes() for p in paths}
        record = self.a / 'inbox/record.json'
        record.write_text(json.dumps(self.payload()))
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(pm.main(['--root', str(self.root), 'record', self.a.name, '--file', 'inbox/record.json']), 0)
        self.assertEqual(before, {str(p): p.read_bytes() for p in paths})
        self.assertFalse((self.root / '.lwc').exists())
        self.assertFalse((self.root / 'index').exists())

    def test_log_tampering_and_tail_truncation_cannot_be_resealed_by_reindex(self):
        self.memory.record(self.payload())
        canonical = (self.a / 'memory/events.jsonl').read_bytes()
        seal = (self.a / 'memory/seal.json').read_bytes()
        index = (self.a / 'memory/index.json').read_bytes()
        for modified in (canonical.replace(b'bounded', b'BROKEN', 1), b'', canonical[:-1]):
            (self.a / 'memory/events.jsonl').write_bytes(modified)
            result = self.memory.check(rebuild_index=True)
            self.assertFalse(result['canonical_valid'])
            self.assertFalse(result['rebuilt_index'])
            self.assertEqual((self.a / 'memory/seal.json').read_bytes(), seal)
            self.assertEqual((self.a / 'memory/index.json').read_bytes(), index)
            with self.assertRaisesRegex(ValueError, 'differs from its seal'):
                self.memory.context()
        (self.a / 'memory/events.jsonl').write_bytes(canonical)
        self.assertTrue(self.memory.check()['passed'])

    def test_hash_chain_detects_changes_even_if_log_hash_is_reset(self):
        self.memory.record(self.payload())
        path = self.a / 'memory/events.jsonl'
        event = json.loads(path.read_text())
        event['summary'] = 'Tampered synthetic summary'
        path.write_bytes(pm.encoded(event))
        seal = json.loads((self.a / 'memory/seal.json').read_text())
        seal['log_sha256'] = pm.digest(path.read_bytes())
        (self.a / 'memory/seal.json').write_bytes(pm.encoded(seal))
        result = self.memory.check(rebuild_index=True)
        self.assertFalse(result['canonical_valid'])
        self.assertIn('event changed', result['issues'][0]['detail'])

    def test_index_and_markdown_tampering_are_stale_and_rebuilt_from_log(self):
        self.memory.record(self.payload())
        log_before = (self.a / 'memory/events.jsonl').read_bytes()
        seal_before = (self.a / 'memory/seal.json').read_bytes()
        expected = {name: (self.a / 'memory' / name).read_bytes() for name in pm.DERIVED}
        (self.a / 'memory/index.json').write_text('{}')
        (self.a / 'memory/context.md').write_text('Wrong projection')
        stale = self.memory.check()
        self.assertTrue(stale['canonical_valid'])
        self.assertTrue(stale['index_stale'])
        with self.assertRaisesRegex(ValueError, 'stale'):
            self.memory.search('pilot')
        self.assertTrue(self.memory.check(rebuild_index=True)['passed'])
        self.assertEqual(log_before, (self.a / 'memory/events.jsonl').read_bytes())
        self.assertEqual(seal_before, (self.a / 'memory/seal.json').read_bytes())
        self.assertEqual(expected, {name: (self.a / 'memory' / name).read_bytes() for name in pm.DERIVED})

    def test_evidence_changes_are_visible_without_mutating_decision_status(self):
        event = self.memory.record(self.payload())
        (self.a / 'inbox/instruction.md').write_text('Changed fixture input')
        context = self.memory.context()
        self.assertEqual(context['confirmed_active'][0]['status'], 'confirmed')
        self.assertEqual(context['evidence_warnings'][0]['issue'], 'evidence-changed')
        self.assertEqual(context['evidence_warnings'][0]['record_id'], event['id'])
        self.assertTrue(self.memory.check()['canonical_valid'])
        (self.a / 'inbox/instruction.md').unlink()
        self.assertEqual(self.memory.context()['evidence_warnings'][0]['issue'], 'evidence-missing')

    def test_paths_symlinks_and_foreign_record_sources_do_not_escape_dossier(self):
        with self.assertRaises(ValueError):
            self.memory.record(self.payload(evidence=[{'path': str(self.b / 'inbox/instruction.md'), 'locator': 'foreign'}]))
        outside = self.root / 'outside.md'
        outside.write_text('Foreign file')
        link = self.a / 'inbox/link.md'
        link.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'Symbolic'):
            self.memory.record(self.payload(evidence=[{'path': 'inbox/link.md', 'locator': 'foreign'}]))
        link.unlink()
        with self.assertRaises(ValueError):
            with contextlib.redirect_stdout(io.StringIO()):
                pm.main(['--root', str(self.root), 'record', self.a.name, '--file', str(outside)])
        (self.a / 'memory/index.json').unlink()
        (self.a / 'memory/index.json').symlink_to(outside)
        result = self.memory.check(rebuild_index=True)
        self.assertFalse(result['passed'])
        self.assertEqual(outside.read_text(), 'Foreign file')

    def test_confirmation_requires_proof_and_unknown_fields_are_not_silently_accepted(self):
        for payload in (self.payload(evidence=[]), self.payload(provenance={'type': 'agent-analysis', 'reference': ''}),
                        self.payload(chain_of_thought='Do not store this'), self.payload(supersedes=['missing-id'])):
            with self.assertRaises(ValueError):
                self.memory.record(payload)
        self.assertEqual(self.memory.check()['count'], 0)

    def test_route_change_and_dossier_symlink_do_not_reuse_existing_memory(self):
        state = json.loads((self.a / 'state.json').read_text())
        state['year'] = 2027
        (self.a / 'state.json').write_text(json.dumps(state))
        self.assertFalse(pm.ProjectMemory(self.root, self.a.name).check()['canonical_valid'])
        alias = self.root / 'projects/alias'
        alias.symlink_to(self.a, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Symbolic'):
            pm.ProjectMemory(self.root, 'alias')

    def test_read_only_opening_context_reports_missing_legacy_memory(self):
        before = (self.b / 'state.json').read_bytes()
        context = pm.opening_context(self.root, self.b.name, 'idea-validation')
        self.assertFalse(context['available'])
        self.assertFalse((self.b / 'memory').exists())
        self.assertEqual(before, (self.b / 'state.json').read_bytes())

    def test_writer_lock_refuses_a_second_writer(self):
        with self.memory.lock():
            with self.assertRaisesRegex(ValueError, 'writer lock exists'):
                self.memory.record(self.payload())
        self.assertEqual(self.memory.check()['count'], 0)


class WorkflowMemoryIntegrationTests(unittest.TestCase):
    def test_init_status_and_confirmation_keep_workflow_state_separate(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(workflow, 'ROOT', Path(temp)):
            root = Path(temp)
            with patch.object(sys, 'argv', ['workflow', 'init', 'fixture', '--action', 'KA152', '--sector', 'YOU']), contextlib.redirect_stdout(io.StringIO()):
                workflow.main()
            path = workflow.project('fixture')
            self.assertTrue((path / 'memory/events.jsonl').is_file())
            state_before = (path / 'state.json').read_bytes()
            model_before = (path / 'project.json').read_bytes()
            pm.ProjectMemory(root, path.name).record({'kind': 'decision', 'status': 'confirmed', 'title': 'SYNTHETIC test decision',
                'summary': 'Record a local fixture choice only.', 'author': 'synthetic-agent',
                'provenance': {'type': 'agent-observed', 'reference': 'SYNTHETIC isolated test'},
                'evidence': [{'path': 'brief.md', 'locator': 'SYNTHETIC generated brief'}]})
            output = io.StringIO()
            with patch.object(sys, 'argv', ['workflow', 'status', path.name]), contextlib.redirect_stdout(output):
                workflow.main()
            result = json.loads(output.getvalue())
            self.assertEqual(len(result['working_memory_context']['confirmed_active']), 1)
            self.assertEqual((path / 'state.json').read_bytes(), state_before)
            self.assertEqual((path / 'project.json').read_bytes(), model_before)
            self.assertEqual(result['next_phase'], 'idea-validation')
            self.assertEqual(result['receipts'], [])


class EngineMemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / 'config').mkdir()
        (self.root / 'scripts').mkdir()
        (self.root / 'config/agent-registry.json').write_text('{}')
        (self.root / 'scripts/lwc').write_text('SYNTHETIC marker only')
        (self.root / 'scripts/change.py').write_text('# SYNTHETIC fixture change')
        self.memory = pm.EngineMemory(self.root)
        self.memory.initialize()

    def tearDown(self):
        self.tmp.cleanup()

    def test_engine_memory_has_distinct_namespace_and_relative_evidence(self):
        record = self.memory.folder / 'fixture.json'
        record.write_text(json.dumps({'kind': 'decision', 'status': 'confirmed', 'title': 'SYNTHETIC engine choice',
            'summary': 'Use a separate engine working memory.', 'author': 'orchestrator',
            'provenance': {'type': 'agent-observed', 'reference': 'SYNTHETIC isolated test'},
            'evidence': [{'path': 'scripts/change.py', 'locator': 'SYNTHETIC complete fixture file'}]}))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(pm.main(['--root', str(self.root), '--engine-memory', 'record', '--file', 'fixture.json']), 0)
        event = json.loads(out.getvalue())
        self.assertEqual(event['schema_version'], pm.ENGINE_SCHEMA)
        self.assertEqual(event['workspace_id'], 'erasmus-designer-engine')
        self.assertNotIn('project_id', event)
        self.assertTrue(event['id'].startswith('engine:erasmus-designer::'))
        self.assertIn('[artifact](<../../scripts/change.py>)', (self.memory.folder / 'context.md').read_text())
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(pm.main(['--root', str(self.root), '--engine-memory', 'search', 'separate engine']), 0)
        self.assertEqual(json.loads(out.getvalue())['results'][0]['id'], event['id'])
        self.assertFalse((self.root / 'projects').exists())
        self.assertFalse((self.root / '.lwc').exists())

    def test_engine_evidence_cannot_ingest_candidatures_or_lwc_internals(self):
        for parent in ('projects/real', '.lwc'):
            path = self.root / parent / 'private.md'
            path.parent.mkdir(parents=True)
            path.write_text('SYNTHETIC unrelated private artifact')
            with self.assertRaisesRegex(ValueError, 'cannot include'):
                self.memory.record({'kind': 'decision', 'status': 'confirmed', 'title': 'SYNTHETIC foreign claim',
                    'summary': 'Attempt foreign ingestion.', 'author': 'orchestrator',
                    'provenance': {'type': 'agent-analysis', 'reference': 'SYNTHETIC test'},
                    'evidence': [{'path': str(path), 'locator': 'SYNTHETIC fixture'}]})
        self.assertEqual(self.memory.check()['count'], 0)


if __name__ == '__main__':
    unittest.main()
