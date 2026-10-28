import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from email.message import Message

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import knowledge_maintenance as km


class KnowledgeMaintenance(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='erasmus-maintenance-test-')
        self.base = Path(self.temp.name).resolve()
        self.workspace = self.base / 'staging'

    def tearDown(self):
        self.temp.cleanup()

    def metadata(self, kind='form-profile', year=2026, program='ERASMUS', **updates):
        value = {'program': program, 'year': year, 'kind': kind,
                 'action': 'KA220-YOU' if program == 'ERASMUS' else 'ESC30',
                 'sector': 'YOU' if program == 'ERASMUS' else 'ESC', 'round': 'R1',
                 'language': 'en', 'agency': 'AIG', 'jurisdiction': 'NA',
                 'scope_note': 'Synthetic fixture, no official call assertion',
                 'data_classification': 'public', 'identity_verified': False}
        return value | updates

    def profile(self, year=2026, cap=100):
        return {'program': 'ERASMUS', 'action': 'KA220-YOU', 'sector': 'YOU',
                'call_year': year, 'round': 'R1', 'language': 'en', 'agency': 'AIG',
                'current_call_verified': False,
                'stable_id_namespace': 'fixture-platform-fields',
                'stable_id_evidence': ['Synthetic platform ID evidence, not a current form'],
                'questions': [{'id': 'Q1', 'prompt': 'Explain the need.', 'kind': 'textarea',
                               'required': True, 'max_chars': cap, 'limit_source': 'Synthetic field counter',
                               'repeatable': False, 'conditional': {'when': 'always'}}],
                'fields': [{'id': 'Q1', 'max_chars': cap, 'criteria': ['relevance'],
                            'award_mapping': {'criterion': 'relevance', 'source': 'Synthetic guide'}}]}

    def stage(self, profile=None, metadata=None, evidence=()):
        file = self.base / 'input.json'
        file.write_bytes(km.encoded(profile or self.profile()))
        result = km.stage(self.workspace, file, metadata or self.metadata(), evidence)
        return self.workspace / result['revision']

    def codes(self, result):
        return {i['code'] for i in result['issues']}

    def test_missing_zero_negative_and_boolean_limits_fail_closed(self):
        for cap in (None, 0, -1, True):
            with self.subTest(cap=cap):
                profile = self.profile(cap=cap)
                result = km.profile_check(profile, self.metadata())
                self.assertFalse(result['passed'])
                self.assertIn('missing-or-invalid-limit', self.codes(result))
                revision = self.stage(profile)
                self.assertFalse(km.check_revision(revision)['ready_for_review'])
        profile = self.profile(); profile['questions'][0].pop('max_chars')
        self.assertFalse(km.profile_check(profile, self.metadata())['passed'])

    def test_explicit_occurrence_missing_cap_cannot_borrow_field_cap(self):
        profile = self.profile()
        profile['questions'][0]['occurrences'] = [{'id': 'Q1-WP2', 'context': {'wp_id': 'WP2'}, 'max_chars': None}]
        self.assertIn('missing-or-invalid-limit', self.codes(km.profile_check(profile, self.metadata())))
        profile['questions'][0]['occurrences'][0]['max_chars'] = 80
        self.assertTrue(km.profile_check(profile, self.metadata())['passed'])

    def test_hash_tamper_manifest_tamper_extra_and_expected_anchor(self):
        revision = self.stage()
        self.assertTrue(km.check_revision(revision, revision.name)['passed'])
        with self.assertRaisesRegex(ValueError, 'Manifest digest'):
            km.check_revision(revision, '0' * 64)
        payload = revision / 'payload.json'; original = payload.read_bytes()
        payload.write_bytes(original + b' ')
        with self.assertRaisesRegex(ValueError, 'Artifact digest'):
            km.check_revision(revision)
        payload.write_bytes(original)
        (revision / 'unknown.txt').write_text('not captured')
        with self.assertRaisesRegex(ValueError, 'Unmanifested'):
            km.check_revision(revision)
        (revision / 'unknown.txt').unlink()
        (revision / 'manifest.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'Manifest digest'):
            km.check_revision(revision)

    def test_same_bytes_same_metadata_are_idempotent_new_revision_preserves_old(self):
        first = self.stage()
        self.assertEqual(first, self.stage())
        second = self.stage(metadata=self.metadata(scope_note='New scope observation'))
        self.assertNotEqual(first, second)
        self.assertEqual(first.parent, second.parent)
        self.assertTrue(km.check_revision(first)['passed'])
        self.assertTrue(km.check_revision(second)['passed'])

    def test_changed_validator_keeps_historical_integrity_and_requires_new_snapshot(self):
        revision = self.stage()
        with patch.object(km, 'validator_fingerprints', return_value={'maintenance_sha256': 'changed'}):
            result = km.check_revision(revision)
        self.assertTrue(result['passed'])
        self.assertFalse(result['validation_snapshot_current'])
        self.assertTrue(result['new_snapshot_required'])
        self.assertTrue(km.check_revision(revision)['validation_snapshot_current'])

    def test_program_year_action_sector_incoherence_is_rejected_before_staging(self):
        for change in ({'program': 'ESC'}, {'call_year': 2027}, {'action': 'KA220-ADU'}, {'sector': 'ADU'}):
            profile = self.profile() | change
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, 'identity mismatch'):
                self.stage(profile)
        with self.assertRaisesRegex(ValueError, 'Action and program'):
            km.identity(self.metadata(action='ESC30'))
        with self.assertRaisesRegex(ValueError, 'scope'):
            km.identity(self.metadata(kind='expert-guide', jurisdiction='general'))

    def test_future_year_staged_does_not_activate_call_or_mutate_existing_catalogues(self):
        paths = [ROOT / 'config/actions.json', ROOT / 'config/sources.json', ROOT / 'scripts/brain.py', ROOT / 'scripts/workflow.py']
        baseline = {str(p): km.digest(p.read_bytes()) for p in paths}
        revision = self.stage(self.profile(2027), self.metadata(year=2027))
        result = km.check_revision(revision)
        self.assertFalse(result['active'])
        self.assertFalse(result['manifest']['runtime_support']['supported'])
        self.assertEqual(result['manifest']['runtime_support']['indexed_years'], [2026])
        self.assertEqual(baseline, {str(p): km.digest(p.read_bytes()) for p in paths})
        with self.assertRaisesRegex(ValueError, 'activate'):
            self.stage(metadata=self.metadata(status='active'))

    def test_unrecognized_runtime_guards_fail_closed_even_if_json_has_new_year(self):
        engine = self.base / 'engine'
        (engine / 'config').mkdir(parents=True); (engine / 'scripts').mkdir()
        for name in ('actions.json', 'sources.json'):
            (engine / 'config' / name).write_bytes((ROOT / 'config' / name).read_bytes())
        (engine / 'scripts/brain.py').write_text('if args.year != 2027: raise ValueError()')
        (engine / 'scripts/workflow.py').write_text('if a.year != 2027: raise ValueError()')
        result = km.runtime_support(self.metadata(year=2027), engine)
        self.assertFalse(result['supported']); self.assertFalse(result['guard_adapter_verified'])

    def test_reduced_limit_never_migrates_or_truncates_response(self):
        old = self.profile(cap=100); new = self.profile(cap=60)
        result = km.diff_profiles(old, new, self.metadata(), self.metadata())
        self.assertEqual(result['reduced_limits'][0]['new'], 60)
        self.assertFalse(result['ready_for_response_reuse']); self.assertFalse(result['migration_allowed'])
        self.assertIn('limit-reduced-response-review-required', self.codes({'issues': result['blockers']}))
        self.assertEqual(old['questions'][0]['max_chars'], 100)

    def test_ambiguous_same_label_and_unproven_same_id_are_not_matches(self):
        old = self.profile(); new = self.profile()
        new['questions'][0]['id'] = 'Q2'; new['fields'][0]['id'] = 'Q2'
        extra = copy.deepcopy(new['questions'][0]); extra['id'] = 'Q3'
        new['questions'].append(extra)
        result = km.diff_profiles(old, new, self.metadata(), self.metadata())
        self.assertEqual(result['ambiguous'][0]['candidate_new_ids'], ['Q2', 'Q3'])
        self.assertEqual(result['changed'], []); self.assertEqual(result['removed'], ['Q1'])
        new = self.profile(); new.pop('stable_id_namespace')
        result = km.diff_profiles(old, new, self.metadata(), self.metadata())
        self.assertEqual(result['ambiguous'][0]['candidate_new_ids'], ['Q1'])
        with self.assertRaisesRegex(ValueError, 'Ambiguous ID map'):
            km.diff_profiles(old, new, self.metadata(), self.metadata(),
                             [{'from': 'Q1', 'to': 'Q1', 'evidence': 'fixture'},
                              {'from': 'Q1', 'to': 'Q1', 'evidence': 'fixture'}])

    def test_explicit_evidenced_map_retains_id_change_without_fuzzy_matching(self):
        old = self.profile(); new = self.profile()
        new['questions'][0]['id'] = 'Q2'; new['fields'][0]['id'] = 'Q2'
        result = km.diff_profiles(old, new, self.metadata(), self.metadata(),
                                  [{'from': 'Q1', 'to': 'Q2', 'evidence': 'Synthetic form control locator'}])
        self.assertEqual(result['ambiguous'], []); self.assertEqual(result['added'], [])
        self.assertEqual(result['changed'][0]['new_id'], 'Q2')

    def test_full_schema_conditional_occurrences_help_uploads_and_award_mapping_diff(self):
        old = self.profile(); new = self.profile()
        new['questions'][0].update(help_text='New guidance', conditional={'when': 'budget > 0'},
                                   repeatable=True, occurrences=[{'id': 'Q1-WP2', 'max_chars': 70,
                                   'context': {'wp_id': 'WP2'}, 'limit_source': 'Fixture counter'}],
                                   upload={'extensions': ['pdf'], 'max_bytes': 2048})
        new['fields'][0]['award_mapping']['criterion'] = 'impact'
        result = km.diff_profiles(old, new, self.metadata(), self.metadata())
        paths = {c['path'] for c in result['changed'][0]['changes']}
        self.assertTrue({'/conditional/when', '/occurrences', '/help_text', '/upload',
                         '/rich_field/award_mapping/criterion'} <= paths)

    def test_profile_diff_detects_nested_boolean_number_types_and_keeps_identical_json(self):
        old = self.profile()
        old['questions'][0]['conditional'] = {'operator': 'equals', 'value': False}
        old['questions'][0]['options'] = [True, {'branches': [False, {'enabled': True}]}]
        old['fields'][0]['award_mapping']['rules'] = {'condition': [False, {'value': True}]}
        new = copy.deepcopy(old)
        new['questions'][0]['conditional']['value'] = 0
        new['questions'][0]['options'] = [1, {'branches': [0, {'enabled': 1}]}]
        new['fields'][0]['award_mapping']['rules'] = {'condition': [0, {'value': 1}]}
        result = km.diff_profiles(old, new, self.metadata(), self.metadata())
        self.assertTrue(result['candidate_validation']['passed'])
        self.assertFalse(result['ready_for_response_reuse'])
        changes = {c['path']: c for c in result['changed'][0]['changes']}
        self.assertTrue({'/conditional/value', '/options', '/rich_field/award_mapping/rules/condition'} <= changes.keys())
        self.assertIs(changes['/conditional/value']['old'], False)
        self.assertIs(type(changes['/conditional/value']['new']), int)
        self.assertIs(changes['/options']['old'][0], True)
        self.assertIs(type(changes['/options']['new'][0]), int)
        identical = copy.deepcopy(old)
        identical['questions'][0]['conditional'] = {'value': False, 'operator': 'equals'}
        unchanged = km.diff_profiles(old, identical, self.metadata(), self.metadata())
        self.assertEqual(unchanged['changed'], [])
        self.assertEqual(unchanged['profile_changes'], [])
        self.assertTrue(unchanged['ready_for_response_reuse'])
        self.assertTrue(km.leaf_changes(1, 1.0))

    def test_revision_diff_preserves_boolean_number_changes_and_identical_revisions(self):
        old = self.profile()
        old['questions'][0]['conditional'] = {'cases': [{'value': True}, {'value': False}]}
        old['questions'][0]['options'] = [{'selected': [False, True]}]
        old['fields'][0]['award_mapping']['rules'] = [{'enabled': False, 'values': [True]}]
        new = copy.deepcopy(old)
        new['questions'][0]['conditional'] = {'cases': [{'value': 1}, {'value': 0}]}
        new['questions'][0]['options'] = [{'selected': [0, 1]}]
        new['fields'][0]['award_mapping']['rules'] = [{'enabled': 0, 'values': [1]}]
        baseline = self.stage(old)
        original_files = {str(p.relative_to(baseline)): km.digest(p.read_bytes())
                          for p in baseline.rglob('*') if p.is_file()}
        candidate = self.stage(new)
        result = km.diff_revisions(baseline, candidate)
        self.assertTrue(result['content_changed'])
        self.assertTrue(result['candidate_validation_snapshot_current'])
        self.assertTrue(result['form']['candidate_validation']['passed'])
        self.assertFalse(result['form']['ready_for_response_reuse'])
        changes = {c['path']: c for c in result['form']['changed'][0]['changes']}
        self.assertTrue({'/conditional/cases', '/options', '/rich_field/award_mapping/rules'} <= changes.keys())
        self.assertIs(changes['/conditional/cases']['old'][0]['value'], True)
        self.assertIs(type(changes['/conditional/cases']['new'][0]['value']), int)
        self.assertIs(changes['/rich_field/award_mapping/rules']['old'][0]['enabled'], False)
        self.assertIs(type(changes['/rich_field/award_mapping/rules']['new'][0]['enabled']), int)
        unchanged = km.diff_revisions(baseline, self.stage(copy.deepcopy(old)))
        self.assertFalse(unchanged['content_changed'])
        self.assertEqual(unchanged['form']['changed'], [])
        self.assertTrue(unchanged['form']['ready_for_response_reuse'])
        self.assertEqual(original_files, {str(p.relative_to(baseline)): km.digest(p.read_bytes())
                                         for p in baseline.rglob('*') if p.is_file()})

    def test_rich_registry_order_diff_preserves_full_fields_and_dict_order_invariance(self):
        old = self.profile()
        question = copy.deepcopy(old['questions'][0]); question['id'] = 'Q2'
        question['prompt'] = 'Second synthetic question.'
        rich = copy.deepcopy(old['fields'][0]); rich['id'] = 'Q2'
        old['questions'].append(question); old['fields'].append(rich)
        new = copy.deepcopy(old); new['fields'].reverse()
        self.assertTrue(km.validate_profile(old)['passed'])
        self.assertTrue(km.validate_profile(new)['passed'])
        result = km.diff_profiles(old, new, self.metadata(), self.metadata())
        self.assertTrue(result['candidate_validation']['passed'])
        self.assertEqual(result['changed'], [])  # ID-indexed individual payloads are unchanged
        self.assertIsNone(result['question_order_changes'])
        self.assertFalse(result['ready_for_response_reuse'])
        self.assertFalse(result['migration_allowed'])
        change = next(c for c in result['profile_changes'] if c['path'] == '/profile/fields')
        self.assertEqual(change['change'], 'changed')
        self.assertEqual(change['old'], old['fields'])
        self.assertEqual(change['new'], new['fields'])
        self.assertEqual([f['id'] for f in change['old']], ['Q1', 'Q2'])
        self.assertEqual([f['id'] for f in change['new']], ['Q2', 'Q1'])
        identical = copy.deepcopy(old)
        identical['fields'] = [dict(reversed(list(f.items()))) for f in identical['fields']]
        for f in identical['fields']:
            f['award_mapping'] = dict(reversed(list(f['award_mapping'].items())))
        invariant = km.diff_profiles(old, identical, self.metadata(), self.metadata())
        self.assertEqual(invariant['changed'], [])
        self.assertEqual(invariant['profile_changes'], [])
        self.assertTrue(invariant['ready_for_response_reuse'])
        semantic = copy.deepcopy(old)
        semantic['fields'][0]['award_mapping']['criterion'] = 'impact'
        changed = km.diff_profiles(old, semantic, self.metadata(), self.metadata())
        self.assertTrue(changed['candidate_validation']['passed'])
        self.assertFalse(changed['ready_for_response_reuse'])
        self.assertIn('/rich_field/award_mapping/criterion', [c['path'] for c in changed['changed'][0]['changes']])
        raw = next(c for c in changed['profile_changes'] if c['path'] == '/profile/fields')
        self.assertEqual(raw['new'], semantic['fields'])

    def test_revision_diff_detects_empty_fields_added_removed_and_profile_metadata(self):
        absent = self.profile(); absent.pop('fields')
        empty = copy.deepcopy(absent); empty['fields'] = []
        self.assertTrue(km.validate_profile(absent)['passed'])
        self.assertTrue(km.validate_profile(empty)['passed'])
        absent_revision = self.stage(absent); empty_revision = self.stage(empty)
        for before, after, kind in ((absent_revision, empty_revision, 'added'),
                                    (empty_revision, absent_revision, 'removed')):
            result = km.diff_revisions(before, after)
            self.assertTrue(result['content_changed'])
            self.assertTrue(result['candidate_validation_snapshot_current'])
            self.assertTrue(result['form']['candidate_validation']['passed'])
            self.assertEqual(result['form']['changed'], [])
            self.assertFalse(result['form']['ready_for_response_reuse'])
            self.assertFalse(result['form']['migration_allowed'])
            change = next(c for c in result['form']['profile_changes'] if c['path'] == '/profile/fields')
            self.assertEqual(change['change'], kind)
            if kind == 'added':
                self.assertEqual(change['new'], []); self.assertNotIn('old', change)
            else:
                self.assertEqual(change['old'], []); self.assertNotIn('new', change)
        identical = km.diff_revisions(empty_revision, self.stage(copy.deepcopy(empty)))
        self.assertFalse(identical['content_changed'])
        self.assertEqual(identical['form']['profile_changes'], [])
        self.assertTrue(identical['form']['ready_for_response_reuse'])
        before_metadata = copy.deepcopy(empty)
        before_metadata['screen_context'] = {'section': 'needs', 'help_text': 'Synthetic first instruction'}
        after_metadata = copy.deepcopy(before_metadata)
        after_metadata['screen_context']['help_text'] = 'Synthetic revised instruction'
        self.assertTrue(km.validate_profile(after_metadata)['passed'])
        metadata_diff = km.diff_revisions(self.stage(before_metadata), self.stage(after_metadata))
        self.assertTrue(metadata_diff['form']['candidate_validation']['passed'])
        self.assertFalse(metadata_diff['form']['ready_for_response_reuse'])
        change = next(c for c in metadata_diff['form']['profile_changes']
                      if c['path'] == '/profile/screen_context/help_text')
        self.assertEqual(change['old'], before_metadata['screen_context']['help_text'])
        self.assertEqual(change['new'], after_metadata['screen_context']['help_text'])

    def test_export_relative_paths_preserves_hashes_and_excludes_private(self):
        revision = self.stage()
        destination = self.base / 'candidate.tar.gz'
        km.export_revision(revision, destination)
        with tarfile.open(destination) as archive:
            names = archive.getnames()
            self.assertTrue(all(not n.startswith('/') and '..' not in Path(n).parts for n in names))
            exported = json.load(archive.extractfile('revision/manifest.json'))
            self.assertEqual(exported, km.check_revision(revision)['manifest'])
            for entry in exported['artifacts']:
                self.assertFalse(Path(entry['path']).is_absolute())
                self.assertEqual(km.digest(archive.extractfile('revision/' + entry['path']).read()), entry['sha256'])
        private = self.stage(metadata=self.metadata(data_classification='project-private'))
        with self.assertRaisesRegex(ValueError, 'excludes private'):
            km.export_revision(private, self.base / 'private.tar.gz')

    def test_discovery_hints_do_not_verify_year_or_follow_external_links(self):
        file = self.base / 'page.html'
        file.write_text('<a href="guide-2027.pdf">Guide 2027</a><a href="https://example.com/forms">Forms</a>')
        staged = km.stage(self.workspace, file, self.metadata(kind='official-page', url='https://youth.europa.eu/solidarity/'))
        rows = km.discover(self.workspace / staged['revision'])['links']
        self.assertEqual(rows[0]['possible_years'], [2027])
        self.assertFalse(rows[0]['identity_verified']); self.assertFalse(rows[1]['capture_allowed'])
        for url in ('http://youth.europa.eu/', 'https://evil.example/', 'https://user:pass@youth.europa.eu/',
                    'https://youth.europa.eu/login'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                km.validate_url(url, km.configuration())

    def test_allowed_official_national_hosts_include_existing_aig_sources(self):
        sources = km.read_json(ROOT / 'config/sources.json')
        urls = [s['url'] for s in sources if 'agenziagioventu.gov.it' in s.get('url', '')]
        self.assertGreaterEqual(len(urls), 4)
        for url in urls:
            km.validate_url(url, km.configuration())

    def test_capture_size_bound_and_redirect_are_checked_before_staging(self):
        settings = km.configuration() | {'max_capture_bytes': 16}
        class Response(io.BytesIO):
            url = 'https://youth.europa.eu/solidarity/'
            headers = Message()
        Response.headers['Content-Type'] = 'text/html'
        class Opener:
            def open(self, request, timeout):
                self.request = request
                return Response(b'x' * 17)
        with patch.object(km, 'configuration', return_value=settings), patch.object(km, 'build_opener', return_value=Opener()):
            with self.assertRaisesRegex(ValueError, 'exceeds configured limit'):
                km.capture(self.workspace, Response.url, self.metadata(kind='official-page'))
        self.assertFalse(self.workspace.exists())
        with self.assertRaisesRegex(ValueError, 'allowed official host'):
            km.PublicRedirect(settings).redirect_request(None, None, 302, '', {}, 'https://example.com/login')

    def test_paths_cannot_escape_or_write_live_engine(self):
        self.assertEqual(km.workspace_path('audits/example'), ROOT / 'audits/example')
        for path in (ROOT / 'raw/new-year', ROOT / 'config/staged', ROOT / 'sources/new-year', ROOT / '.lwc/staged'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                km.workspace_path(path)
        for relative in ('../live.json', '/tmp/report.json'):
            with self.assertRaises(ValueError):
                km.confined(self.workspace, relative)
        self.workspace.mkdir(); (self.workspace / 'link').symlink_to(self.base)
        with self.assertRaisesRegex(ValueError, 'Symlink'):
            km.confined(self.workspace, 'link/output.json')

    def test_public_esc30_sample_field_has_no_invented_limit_or_platform_id(self):
        profile = {'program': 'ESC', 'action': 'ESC30', 'official_action_code': 'ESC30-SOL',
                   'sector': 'ESC', 'call_year': 2026, 'round': 'R1', 'language': 'en',
                   'source_url': 'https://youth.europa.eu/sites/default/files/inline-files/Call-2026-Solidarity-projects-ESC30-SOL_watermark.pdf',
                   'artifact_role': 'public-sample-partial-fixture', 'current_call_verified': False,
                   'coverage_verified': False, 'all_limits_verified': False,
                   'questions': [{'id': 'local-sample-p7-coach', 'kind': 'textarea',
                                  'prompt': 'Do you plan to have coaches supporting you in your project?',
                                  'max_chars': None, 'source_locator': {'physical_pdf_page': 7},
                                  'conditional': {'status': 'not-observed-in-public-sample'}}]}
        revision = self.stage(profile, self.metadata(program='ESC'))
        result = km.check_revision(revision)
        self.assertFalse(result['ready_for_review'])
        self.assertIn('stable-id-registry-unverified', self.codes(result['manifest']['profile_validation']))
        self.assertIn('missing-or-invalid-limit', self.codes(result['manifest']['profile_validation']))

    def test_cli_strict_check_and_diff_blockers_return_nonzero(self):
        old = self.stage(); new = self.stage(self.profile(cap=0))
        with contextlib.redirect_stdout(io.StringIO()):
            code = km.main(['--workspace', str(self.workspace), 'check', '--revision',
                            str(new.relative_to(self.workspace)), '--strict'])
        self.assertEqual(code, 1)
        with contextlib.redirect_stdout(io.StringIO()):
            code = km.main(['--workspace', str(self.workspace), 'diff', '--baseline',
                            str(old.relative_to(self.workspace)), '--candidate',
                            str(new.relative_to(self.workspace)), '--fail-on-blockers'])
        self.assertEqual(code, 1)

    def test_real_local_form_registry_diff_as_unverified_fixture(self):
        # Full existing 98-question/346-occurrence user model, never a 2026 form.
        old = km.read_json(ROOT / 'config/forms/ka220-user-template.json')
        new = copy.deepcopy(old)
        target = next(q for q in new['questions'] if isinstance(q.get('max_chars'), int))
        target['prompt'] += ' [TEST CHANGE]'
        target['max_chars'] -= 1
        rich = next(q for q in new['fields'] if q['id'] == target['id'])
        if 'max_chars' in rich: rich['max_chars'] = target['max_chars']
        result = km.diff_profiles(old, new, self.metadata(year=2025), self.metadata(year=2025))
        self.assertEqual(len(old['questions']), 98)
        self.assertEqual(sum(len(q['occurrences']) for q in old['questions']), 346)
        self.assertFalse(result['ready_for_response_reuse'])
        self.assertTrue(result['ambiguous'])  # local label-derived IDs are not platform identity
        mapped = km.diff_profiles(old, new, self.metadata(year=2025), self.metadata(year=2025),
                                 [{'from': q['id'], 'to': q['id'],
                                   'evidence': q.get('source_locator') or 'Existing immutable local registry fixture'}
                                  for q in old['questions']])
        self.assertIn(target['id'], [q['old_id'] for q in mapped['changed']])
        self.assertTrue(mapped['reduced_limits']); self.assertFalse(mapped['migration_allowed'])


if __name__ == '__main__':
    unittest.main()
