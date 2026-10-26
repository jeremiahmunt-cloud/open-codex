"""Functional privacy checks in disposable Git repos; no real private files."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
CHECKER = ROOT / 'tools/check_privacy.py'
INSTALLER = ROOT / 'tools/install_privacy_hook.py'
ALLOWLIST = 'tools/privacy-allowlist.json'
SENTINEL = 'SYNTHETIC_CONFIDENTIAL_DO_NOT_PRINT_731'


class PrivacyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='privacy tests ')
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / 'checkout with spaces'
        self.repo.mkdir()
        self.env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
        self.env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_TERMINAL_PROMPT='0')
        self.git('-c', 'init.defaultBranch=main', 'init', '--quiet')
        self.git('config', 'user.name', 'Synthetic Privacy Test')
        self.git('config', 'user.email', 'privacy-tests@example.invalid')
        self.git('config', 'commit.gpgsign', 'false')

    def git(self, *args, ok=True):
        result = subprocess.run(['git', '-C', str(self.repo), *args],
                                env=self.env, capture_output=True)
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
        return result

    def write(self, path, value):
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        if not isinstance(value, bytes):
            value = value.encode('utf-8')
        target.write_bytes(value)
        return target

    def stage(self, path, value=b'synthetic fixture only'):
        target = self.write(path, value)
        self.git('add', '-f', '--', path)
        return target

    def allow(self, path, *, digest=None, kind='synthetic-fixture'):
        entry = {'path': path, 'sha256': digest or hashlib.sha256((self.repo / path).read_bytes()).hexdigest(),
                 'kind': kind, 'reason': 'Entirely synthetic bytes for isolated functional verification.'}
        self.stage(ALLOWLIST, json.dumps({'version': 1, 'entries': [entry]}))
        return entry

    def run_tool(self, tool=CHECKER, expected=0, *, env=None):
        result = subprocess.run([sys.executable, str(tool), '--repo', str(self.repo)],
                                cwd=self.temp.name, env=env or self.env, capture_output=True)
        output = (result.stdout + result.stderr).decode(errors='replace')
        self.assertEqual(result.returncode, expected, output)
        self.assertNotIn(SENTINEL, output)
        return output

    def test_unborn_repository_and_regular_resources_pass(self):
        self.run_tool()
        for path, content in [('README.md', '# Synthetic package'),
                              ('assets/editorial.css', 'body {}'),
                              ('scripts/maison-brief.json', '{"sections":[]}'),
                              ('assets/content-record.example.json', '{"publicationScope":"public-demo"}'),
                              ('.env.example', 'EXAMPLE_KEY=')]:
            self.stage(path, content)
        self.assertIn('5 indexed files', self.run_tool())

    def test_force_added_artifacts_and_credentials_fail(self):
        paths = ['private-output/research-index.json', 'nested/private-custom/note.txt',
                 'original.PDF', 'evidence.docx', 'ledger.csv', 'archive.zip',
                 'nested/extracted-images/scan.png', 'PRIVATE-CASE/notes.txt',
                 'research-index (1).json', 'maison-visual-manifest-2026.json',
                 'website-plan.json', 'asset-manifest.json', 'pdf-182.png',
                 'nested/.env.production', '.env.example.local', '.git-credentials',
                 '.aws/config', 'keys/id_ed25519', 'keys/private.pem',
                 'credentials-local.json', 'service-account.json', '.npmrc']
        for path in paths:
            self.stage(path, '{}' if path.endswith('.json') else SENTINEL)
        output = self.run_tool(expected=1)
        for path in paths:
            self.assertIn(json.dumps(path), output)

    def test_existing_tracked_artifact_fails_but_staged_removal_passes(self):
        self.stage('already-tracked.pdf', SENTINEL)
        self.git('commit', '--no-verify', '-qm', 'synthetic initial artifact')
        self.run_tool(expected=1)
        self.git('rm', '--cached', '--', 'already-tracked.pdf')
        self.assertTrue((self.repo / 'already-tracked.pdf').exists())
        self.run_tool()

    def test_untracked_files_are_not_read_or_scanned(self):
        self.write('private-output/research-index.json', SENTINEL)
        self.write('original.pdf', SENTINEL)
        self.run_tool()

    def test_inspects_staged_bytes_even_if_working_copy_is_redacted(self):
        self.stage('renamed.json', json.dumps({'scope': 'private-research', 'text': SENTINEL}))
        self.write('renamed.json', '{}')
        self.assertIn('private/confidential JSON scope', self.run_tool(expected=1))

    def test_safe_staged_bytes_not_confidential_unstaged_working_copy(self):
        self.stage('renamed.json', '{}')
        self.write('renamed.json', json.dumps({'scope': 'private-research', 'text': SENTINEL}))
        self.run_tool()

    def test_renamed_json_and_nested_json_lines_detected(self):
        self.stage('innocent.json', json.dumps({'outer': [{'publicationScope': 'CONFIDENTIAL'}]}))
        self.stage('index-copy.json', '{"document":{},"chunks":[]}')
        self.stage('review-copy.json', '{"manifestKind":"maison-visual-review"}')
        self.stage('renamed.jsonl', '{"public":true}\n{"scope":"private-review"}\n')
        self.stage('bom.json', json.dumps({'scope': 'private-research'}).encode('utf-8-sig'))
        output = self.run_tool(expected=1)
        for path in ('innocent.json', 'index-copy.json', 'review-copy.json', 'renamed.jsonl', 'bom.json'):
            self.assertIn(path, output)

    def test_credential_json_cannot_be_renamed_or_allowlisted(self):
        self.stage('auth-copy.json', json.dumps({'nested': {'private_key': SENTINEL}}))
        self.allow('auth-copy.json')
        self.assertIn('allowlist cannot exempt this rule', self.run_tool(expected=1))

    def test_invalid_duplicate_and_deep_json_fail_without_content(self):
        self.stage('invalid.json', SENTINEL)
        self.stage('duplicates.json', '{"scope":"private-review","scope":"public"}')
        self.stage('case-duplicates.json', '{"scope":"private-review","Scope":"public"}')
        self.stage('deep.json', '[' * 2000 + '0' + ']' * 2000)
        self.stage('nonfinite.json', '{"number":NaN}')
        self.stage('utf16.json', json.dumps({'scope': 'private-review'}).encode('utf-16'))
        output = self.run_tool(expected=1)
        for path in ('invalid.json', 'duplicates.json', 'case-duplicates.json', 'deep.json', 'nonfinite.json', 'utf16.json'):
            self.assertIn(path, output)

    def test_json_depth_guard_ignores_braces_and_escaped_quotes_in_strings(self):
        self.stage('safe.json', json.dumps({'text': '[{\\"}]' * 1000, 'scope': 'public-demo'}))
        self.run_tool()

    def test_oversized_json_is_rejected_before_parsing(self):
        self.stage('large.json', b' ' * (4 * 1024 * 1024 + 1))
        self.assertIn('4 MiB inspection limit', self.run_tool(expected=1))

    def test_allowlist_permits_exact_synthetic_research_fixture(self):
        self.stage('tests/fixtures/research-index.json', '{"scope":"private-research","document":{},"pages":[]}')
        self.allow('tests/fixtures/research-index.json')
        self.assertIn('1 documented exceptions', self.run_tool())
        self.stage('tests/fixtures/research-index-copy.json', '{"scope":"private-research"}')
        self.assertIn('research-index-copy.json', self.run_tool(expected=1))

    def test_allowlist_permits_reviewed_reusable_document(self):
        self.stage('assets/reference.pdf', b'%PDF-synthetic-only\n')
        self.allow('assets/reference.pdf', kind='reusable-resource')
        self.run_tool()

    def test_changed_allowlisted_fixture_requires_new_digest(self):
        self.stage('fixtures/sample.json', '{"scope":"private-research"}')
        self.allow('fixtures/sample.json')
        self.stage('fixtures/sample.json', '{}')
        self.assertIn('SHA-256 does not match', self.run_tool(expected=1))

    def test_unstaged_allowlist_changes_do_not_authorize_staged_fixture(self):
        self.stage('fixtures/sample.json', '{"scope":"private-research"}')
        entry = self.allow('fixtures/sample.json')
        self.stage('fixtures/sample.json', '{"scope":"private-review"}')
        entry['sha256'] = hashlib.sha256((self.repo / 'fixtures/sample.json').read_bytes()).hexdigest()
        self.write(ALLOWLIST, json.dumps({'version': 1, 'entries': [entry]}))
        self.run_tool(expected=1)

    def test_untracked_allowlist_is_not_trusted(self):
        self.stage('fixture.pdf', SENTINEL)
        self.allow('fixture.pdf')
        self.git('rm', '--cached', '--', ALLOWLIST)
        self.run_tool(expected=1)

    def test_allowlist_cannot_exempt_reserved_directories_or_keys(self):
        for path in ('private-output/example.json', 'keys/test.key'):
            with self.subTest(path=path):
                self.stage(path, '{}')
                self.allow(path)
                self.assertIn('allowlist cannot exempt this rule', self.run_tool(expected=1))
                self.git('rm', '--cached', '--', path)

    def test_allowlist_schema_and_unsafe_paths_fail_closed(self):
        good = {'path': 'fixture.pdf', 'sha256': '0' * 64, 'kind': 'synthetic-fixture',
                'reason': 'Synthetic document used only in this temporary repository.'}
        self.stage('fixture.pdf', SENTINEL)
        cases = [{'version': 2, 'entries': []}, {'version': True, 'entries': []},
                 {'version': 1, 'entries': [{**good, 'path': path} for path in ['../outside.pdf']]},
                 {'version': 1, 'entries': [good, good]}]
        for path in ('/outside.pdf', 'fixtures/*.pdf', 'fixtures\\file.pdf',
                     'C:/file.pdf', './fixture.pdf', 'fixtures/../fixture.pdf'):
            cases.append({'version': 1, 'entries': [{**good, 'path': path}]})
        for change in ({'sha256': 'bad'}, {'kind': 'private'}, {'reason': ''}, {'path': 'absent.pdf'}):
            cases.append({'version': 1, 'entries': [{**good, **change}]})
        for value in cases:
            with self.subTest(value=value):
                self.stage(ALLOWLIST, json.dumps(value))
                self.run_tool(expected=2)
        self.stage(ALLOWLIST, SENTINEL)
        self.run_tool(expected=2)

    def test_allowlist_checks_its_indexed_json_even_after_local_repair(self):
        self.stage(ALLOWLIST, SENTINEL)
        self.write(ALLOWLIST, '{"version":1,"entries":[]}')
        self.run_tool(expected=2)

    @unittest.skipIf(os.name == 'nt', 'Windows disallows control characters in filenames')
    def test_filenames_with_tabs_newlines_and_unicode_are_safe_in_logs(self):
        path = 'dossier\t\n\u00e9.pdf'
        self.stage(path, SENTINEL)
        output = self.run_tool(expected=1)
        self.assertIn(json.dumps(path), output)
        self.assertNotIn('dossier\t\n', output)

    def test_symlink_cannot_hide_unsupported_content(self):
        target = self.write('outside.txt', SENTINEL)
        try:
            (self.repo / 'alias.json').symlink_to(target)
        except OSError:
            self.skipTest('Symlink creation unavailable for this Windows account')
        self.git('add', '--', 'alias.json')
        self.assertIn('symlinks and submodules', self.run_tool(expected=1))

    def test_submodule_cannot_bypass_index_policy(self):
        self.stage('README.md', 'Synthetic')
        self.git('commit', '--no-verify', '-qm', 'synthetic base')
        oid = self.git('rev-parse', 'HEAD').stdout.decode().strip()
        self.git('update-index', '--add', '--cacheinfo', f'160000,{oid},nested')
        self.assertIn('symlinks and submodules', self.run_tool(expected=1))

    def test_unmerged_index_is_rejected(self):
        self.stage('conflict.txt', 'Synthetic')
        oid = self.git('hash-object', '-w', '--', 'conflict.txt').stdout.decode().strip()
        self.git('update-index', '--force-remove', '--', 'conflict.txt')
        result = subprocess.run(['git', '-C', str(self.repo), 'update-index', '--index-info'],
                                input=f'100644 {oid} 1\tconflict.txt\n100644 {oid} 2\tconflict.txt\n'.encode(),
                                env=self.env, capture_output=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn('unresolved Git index conflict', self.run_tool(expected=1))

    def test_git_errors_fail_closed(self):
        env = dict(self.env, PATH=str(Path(self.temp.name) / 'missing-bin'))
        self.run_tool(expected=2, env=env)
        shutil.rmtree(self.repo / '.git')
        self.run_tool(expected=2)

    def test_ignore_rules_cover_generated_outputs_without_hiding_reusable_sources(self):
        self.write('.gitignore', (ROOT / '.gitignore').read_bytes())
        ignored = ['private-output/notes.txt', 'nested/private-originals/pdf-182.png',
                   'research-index (1).json', 'maison-visual-manifest.json', 'source.pdf',
                   'extracted-documents/chapter.txt', 'research-assets/original.jpg',
                   '.env.production', 'secrets/token.txt', 'keys/id_rsa', 'credentials.json',
                   'website-plan.json', 'stock-originals/asset.jpg', 'web-variants/1280.webp']
        for path in ignored:
            with self.subTest(path=path):
                self.assertEqual(self.git('check-ignore', '-q', '--', path, ok=False).returncode, 0)
        for path in ('.env.example', 'assets/visual-atelier/sample-index.json',
                     'scripts/maison-brief.json', 'assets/content-record.example.json',
                     'assets/visual-atelier/index.html', 'tools/privacy-allowlist.json'):
            with self.subTest(path=path):
                self.assertEqual(self.git('check-ignore', '-q', '--', path, ok=False).returncode, 1)

    def prepare_hook(self):
        for path in ('.githooks/pre-commit', 'tools/check_privacy.py'):
            self.stage(path, (ROOT / path).read_bytes())
        (self.repo / '.githooks/pre-commit').chmod(0o755)
        self.git('update-index', '--chmod=+x', '--', '.githooks/pre-commit')

    def test_hook_installer_is_local_idempotent_and_hook_blocks_commit(self):
        self.prepare_hook()
        self.run_tool(INSTALLER)
        self.assertEqual(self.git('config', '--local', '--get', 'core.hooksPath').stdout.strip(), b'.githooks')
        self.assertIn('already enabled', self.run_tool(INSTALLER))
        self.git('commit', '-qm', 'synthetic clean hook installation')
        before = self.git('rev-parse', 'HEAD').stdout
        self.stage('forced.pdf', SENTINEL)
        commit = self.git('commit', '-qm', 'must be blocked', ok=False)
        self.assertNotEqual(commit.returncode, 0)
        self.assertIn(b'forced.pdf', commit.stderr)
        self.assertEqual(self.git('rev-parse', 'HEAD').stdout, before)
        self.git('rm', '--cached', '--', 'forced.pdf')
        self.stage('safe.txt', 'Synthetic safe resource')
        self.git('commit', '-qm', 'synthetic safe commit after unstage')

    def test_hook_installer_preserves_existing_custom_directory(self):
        self.prepare_hook()
        self.git('config', '--local', 'core.hooksPath', 'my-hooks')
        self.assertIn('preserved', self.run_tool(INSTALLER, expected=2))
        self.assertEqual(self.git('config', '--get', 'core.hooksPath').stdout.strip(), b'my-hooks')

    def test_hook_blocks_private_index_blob_after_working_tree_redaction(self):
        self.prepare_hook()
        self.run_tool(INSTALLER)
        self.git('commit', '-qm', 'synthetic clean hook installation')
        self.stage('renamed.json', '{"scope":"private-review"}')
        self.write('renamed.json', '{}')
        result = self.git('commit', '-qm', 'must reject indexed export', ok=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'private/confidential JSON scope', result.stderr)

    def test_installer_preserves_global_hook_configuration(self):
        self.prepare_hook()
        config = Path(self.temp.name) / 'synthetic-global-config'
        config.write_text('[core]\n\thooksPath = custom-global-hooks\n')
        self.env['GIT_CONFIG_GLOBAL'] = str(config)
        self.assertIn('preserved', self.run_tool(INSTALLER, expected=2))
        self.assertEqual(config.read_text(), '[core]\n\thooksPath = custom-global-hooks\n')
        self.assertEqual(self.git('config', '--local', '--get', 'core.hooksPath', ok=False).returncode, 1)

    def test_hook_installer_preserves_all_existing_default_hooks(self):
        self.prepare_hook()
        path = self.write('.git/hooks/pre-push', '#!/bin/sh\nexit 0\n')
        self.assertIn('preserved', self.run_tool(INSTALLER, expected=2))
        self.assertEqual(path.read_text(), '#!/bin/sh\nexit 0\n')
        self.assertEqual(self.git('config', '--local', '--get', 'core.hooksPath', ok=False).returncode, 1)

    def test_hook_installer_requires_repository_files(self):
        self.run_tool(INSTALLER, expected=2)


if __name__ == '__main__':
    unittest.main()
