"""Fig. 4 packaging checks: reject corruption; preserve original data and other figures."""
import csv
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from plastprior import figure_evidence as module


def attach(root, output):
    import shutil
    shutil.copy2(root / 'PlastPrior_dashboard.sqlite', output)
    try:
        with sqlite3.connect(output) as db:
            module.add_fig4(db, root / 'PlastPrior_results.csv', root, required=True)
    except Exception:
        output.unlink()
        raise


class PackagingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'figure_data/Fig4'
        self.source.mkdir(parents=True)
        self.members = [dict(inchikey=f'compound-{i}', Name=f'Compound {i}', CAS='', SMILES='C',
                             Hazard_score='12', Exposure_score='12', Priority_score='24', Priority_rank='1',
                             Top_n_selected='TRUE', GIC_regulatory_status=f'R{i % 5}', Figure_priority_level='1',
                             primary_use=f'U{i % 16}', structure_group=f'S{i % 9}') for i in range(101)]
        self.publication = self.root / 'PlastPrior_results.csv'
        self.write(self.publication, [{**r, 'Top_n_selected': 'True'} for r in self.members])
        self.write(self.source / 'compound_membership.csv', self.members)
        for key, field, n in [('use', 'primary_use', 16), ('structure', 'structure_group', 9), ('reg', 'GIC_regulatory_status', 5)]:
            self.write(self.source / f'{key}_counts.csv', [dict(category=self.members[i][field], label=f'Label {i}',
                       n=sum(m[field] == self.members[i][field] for m in self.members)) for i in range(n)])
        self.manifest = self.root / 'figure_data/_metadata/Fig4/manifest.json'
        self.manifest.parent.mkdir(parents=True)
        self.lock()
        self.db = self.root / 'PlastPrior_dashboard.sqlite'
        with sqlite3.connect(self.db) as db:
            db.executescript('CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT); CREATE TABLE compound_audit(inchikey TEXT,score INTEGER); CREATE TABLE publication_figures(figure_id TEXT PRIMARY KEY,format TEXT,csv_sha256 TEXT,payload_sha256 TEXT,payload_json TEXT);')
            db.executemany('INSERT INTO metadata VALUES (?,?)', [('csv_sha256', module.digest(self.publication)), ('row_count', '101')])
            db.execute("INSERT INTO compound_audit VALUES ('unchanged',24)")
            db.execute("INSERT INTO publication_figures VALUES ('ExtendedDataFig1a','kept','hash','hash','{}')")
        self.output = self.root / 'packaged.sqlite'

    def write(self, path, rows):
        with path.open('w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)

    def lock(self):
        self.manifest.write_text(json.dumps({'source': {'files': {'publication': {'sha256': module.digest(self.publication)}}},
                                             'source_data': {p.name: module.digest(p) for p in self.source.iterdir()}}))

    def test_preserves_sources_scores_and_sankey(self):
        original = module.digest(self.db)
        attach(self.root, self.output)
        self.assertEqual(original, module.digest(self.db))
        with sqlite3.connect(self.output) as db:
            self.assertEqual(db.execute('select * from compound_audit').fetchall(), [('unchanged', 24)])
            self.assertEqual(db.execute('select figure_id from publication_figures order by figure_id').fetchall(), [('ExtendedDataFig1a',), ('Fig4',)])

    def test_rejects_altered_source(self):
        with (self.source / 'use_counts.csv').open('a') as f:
            f.write('unexpected')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            attach(self.root, self.output)
        self.assertFalse(self.output.exists())

    def test_rejects_wrong_counts_even_with_updated_checksum(self):
        rows = module.read_rows(self.source / 'use_counts.csv'); rows[0]['n'] = '100'
        self.write(self.source / 'use_counts.csv', rows); self.lock()
        with self.assertRaisesRegex(ValueError, 'counts differ'):
            attach(self.root, self.output)

    def test_rejects_duplicate_members_even_with_updated_checksum(self):
        self.members[0] = self.members[1].copy()
        self.write(self.source / 'compound_membership.csv', self.members); self.lock()
        with self.assertRaisesRegex(ValueError, 'membership differs'):
            attach(self.root, self.output)

    def test_rejects_unpaired_database(self):
        with sqlite3.connect(self.db) as db:
            db.execute("UPDATE metadata SET value='wrong' WHERE key='csv_sha256'")
        with self.assertRaisesRegex(ValueError, 'do not match'):
            attach(self.root, self.output)
        self.assertFalse(self.output.exists())

    def test_stale_prepared_data_never_attached(self):
        self.publication.write_text(self.publication.read_text() + '\n')
        with sqlite3.connect(self.db) as db:
            report = module.add_fig4(db, self.publication, self.root)
            self.assertEqual(report['status'], 'unavailable')
            self.assertIsNone(db.execute("select * from publication_figures where figure_id='Fig4'").fetchone())

    def test_preparation_manifest_takes_precedence(self):
        preparation = self.manifest.with_name('preparation.json')
        preparation.write_text(self.manifest.read_text())
        self.manifest.write_text('{}')
        attach(self.root, self.output)

    def test_staging_breaks_hardlinks(self):
        import os
        original = module.digest(self.db)
        stage = self.root / 'stage'
        import shutil
        shutil.copytree(self.root, stage, ignore=shutil.ignore_patterns('stage'), copy_function=os.link)
        report = module.package_fig4(stage)
        self.assertEqual(report, {'status': 'ready', 'members': 101})
        self.assertEqual(module.digest(self.db), original)
        with sqlite3.connect(stage / self.db.name) as db:
            self.assertIsNotNone(db.execute("select * from publication_figures where figure_id='Fig4'").fetchone())


if __name__ == '__main__':
    unittest.main()
