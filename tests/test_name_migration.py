"""Filename compatibility and rollback must preserve the entire scientific set."""
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from plastprior.name_migration import migrate, inventory, SOURCE_LOCK, RECEIPT, SCENARIO
from plastprior.result_names import CURRENT, LEGACY, NAMES, result_files
from plastprior.result_storage import sha, install_package


class NameMigrationTests(TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.result = self.root/'result'
        (self.result/RECEIPT).parent.mkdir(parents=True)
        self.lock = self.root/SOURCE_LOCK
        self.lock.parent.mkdir()
        for role, name in LEGACY.items():
            (self.result/name).write_bytes(('original ' + role).encode())
        for name in ['figures/manual.png', 'figure_data/Example/plot_data.rds',
                     'figure_data/_dependencies/baseline/PlastPrior_results.csv',
                     'Figures_manual.pptx', 'Solène.xlsx']:
            p = self.result/name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(('preserve ' + name).encode())
        self.hashes = {n: sha(self.result/n) for n in LEGACY.values()}
        (self.result/RECEIPT).write_text('{}\n')
        (self.result/SCENARIO).write_text(json.dumps({
            'output_sha256': self.hashes,
            'source_sha256': {'PlastPrior_results.csv': 'historical'},
            'run_id': 'unchanged', 'policy': {'unchanged': True}}))
        self.lock.write_text(json.dumps({'files': {role: {
            'path': 'result/' + n, 'sha256': self.hashes[n]}
            for role, n in LEGACY.items()}}))
        self.before = inventory(self.result)
        self.code = {SOURCE_LOCK: sha(self.lock)}
        self.old_lock = self.lock.read_bytes()

    def validate(self, directory):
        paths = result_files(directory)
        self.assertEqual([p.name for p in paths.values()], list(NAMES))
        for role, p in paths.items():
            self.assertEqual(sha(p), self.hashes[LEGACY[role]])
        return {'unchanged': True}

    def test_rename_preserves_data_assets_attachment_and_historical_provenance(self):
        report = migrate(root=self.root, code_before=self.code,
                         expected_before=self.before, validate=self.validate)
        self.validate(self.result)
        for name, digest in self.before.items():
            if name not in (*LEGACY.values(), RECEIPT, SCENARIO):
                self.assertEqual(sha(self.result/name), digest)
        self.assertFalse(any((self.result/n).exists() for n in LEGACY.values()))
        manifest = json.loads((self.result/SCENARIO).read_text())
        self.assertEqual(manifest['source_sha256'], {'PlastPrior_results.csv': 'historical'})
        self.assertEqual(set(manifest['output_sha256']), set(NAMES))
        self.assertEqual(manifest['run_id'], 'unchanged')
        self.assertEqual(report['scoring_execution'], 'not invoked')
        lock = json.loads(self.lock.read_text())
        self.assertEqual(lock['files']['analysis']['path'], 'result/PlastIQ_results.sqlite')
        self.assertFalse(list(self.root.glob('.result-*')))

    def test_post_install_failure_restores_old_directory_and_source_lock(self):
        def reject_installed(directory):
            self.validate(directory)
            if directory.resolve() == self.result.resolve():
                raise RuntimeError('post-install failure')
            return {'unchanged': True}
        with self.assertRaisesRegex(RuntimeError, 'post-install failure'):
            migrate(root=self.root, code_before=self.code, validate=reject_installed)
        self.assertEqual(inventory(self.result), self.before)
        self.assertEqual(self.lock.read_bytes(), self.old_lock)
        self.assertFalse(list(self.root.glob('.result-*')))

    def test_staging_failure_leaves_live_files_and_lock_untouched(self):
        def reject_stage(directory):
            raise ValueError('staging failure')
        with self.assertRaisesRegex(ValueError, 'staging failure'):
            migrate(root=self.root, code_before=self.code, validate=reject_stage)
        self.assertEqual(inventory(self.result), self.before)
        self.assertEqual(self.lock.read_bytes(), self.old_lock)

    def test_changed_baseline_aborts_before_replacement(self):
        (self.result/'Solène.xlsx').write_bytes(b'user edit')
        with self.assertRaisesRegex(ValueError, 'reviewed migration baseline'):
            migrate(root=self.root, code_before=self.code,
                    expected_before=self.before, validate=self.validate)
        self.assertEqual((self.result/'Solène.xlsx').read_bytes(), b'user edit')
        self.assertEqual(self.lock.read_bytes(), self.old_lock)

    def test_broken_figure_path_resolution_aborts_before_install(self):
        p = self.result/'figure_data/_metadata/Fig2/preparation.json'
        p.parent.mkdir()
        p.write_text(json.dumps({'source': json.loads(self.old_lock)}))
        before = inventory(self.result)
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'FigureCode/_shared'))
        with patch('result_paths.relocated', side_effect=lambda value, **kw: value):
            with self.assertRaisesRegex(ValueError, 'Figure path migration failed before install'):
                migrate(root=self.root, code_before=self.code, validate=self.validate)
        self.assertEqual(inventory(self.result), before)
        self.assertEqual(self.lock.read_bytes(), self.old_lock)

    def test_mixed_names_and_missing_pairs_are_rejected(self):
        self.assertEqual(result_files(self.result)['analysis'].name, LEGACY['analysis'])
        (self.result/CURRENT['dashboard']).write_bytes(b'not paired')
        with self.assertRaisesRegex(ValueError, 'Mixed'):
            result_files(self.result)
        (self.result/CURRENT['dashboard']).unlink()
        (self.result/LEGACY['analysis']).unlink()
        with self.assertRaises(FileNotFoundError):
            result_files(self.result)
        self.assertFalse((self.result/CURRENT['analysis']).exists())

    def test_new_mapping_overrides_historical_self_mapping_and_preserves_baseline(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'FigureCode/_shared'))
        from result_paths import relocated
        old = 'result/PlastPrior_results.csv'
        new = 'result/PlastIQ_results.csv'
        baseline = 'result/figure_data/_dependencies/baseline/PlastPrior_results.csv'
        record = {'storage_migration': {'paths': [[old, old], ['output/current.csv', old]]},
                  'brand_rename': {'paths': [[old, new]]}}
        self.assertEqual(relocated(old, record=record), new)
        self.assertEqual(relocated('output/current.csv', record=record), new)
        self.assertEqual(relocated(baseline, record=record), baseline)
        self.assertEqual(relocated({'path': old, 'sha256': 'unchanged'}, record=record),
                         {'path': new, 'sha256': 'unchanged'})

    def test_merge_does_not_reintroduce_legacy_root_names_or_modify_baseline(self):
        package = self.root/'package'; package.mkdir()
        for role, name in CURRENT.items():
            (package/name).write_bytes((self.result/LEGACY[role]).read_bytes())
        install_package(package, self.result)
        self.assertFalse(any((self.result/n).exists() for n in LEGACY.values()))
        self.assertEqual(set(result_files(self.result)), set(CURRENT))
        baseline = 'figure_data/_dependencies/baseline/PlastPrior_results.csv'
        self.assertEqual(sha(self.result/baseline), self.before[baseline])
