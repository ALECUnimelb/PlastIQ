import csv
import json
from pathlib import Path
import sqlite3
from contextlib import closing
import tempfile
import unittest
from unittest.mock import patch
from plastprior.scenario_export import export_scenario, sha
from plastprior.scoring_scenarios import COMPONENT_MAXIMA, three_level_policy, three_level_exposure_policy
from plastprior.result_names import canonicalise_names

class ExportTests(unittest.TestCase):
    def test_preserves_audit_and_builds_paired_current_results(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); source=root/'baseline 中文 # 100%';source.mkdir()
            row={field:'0' for field in COMPONENT_MAXIMA}
            row.update(inchikey='A',Hazard_score='0.5',Exposure_score='0',Priority_score='0.5',Priority_tier='Low priority',Persistence_score='0.25')
            row['Name'] = '化合物 α'
            fields=list(row)
            csv_path=source/'PlastPrior_results.csv'
            with csv_path.open('w',encoding='utf-8',newline='') as f:
                writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerow(row)
            archive=source/'PlastPrior_results.sqlite'
            with closing(sqlite3.connect(archive)) as db, db:
                db.execute('CREATE TABLE compounds ('+','.join('"'+f+'" TEXT' for f in fields)+')')
                db.execute('INSERT INTO compounds VALUES ('+','.join('?' for _ in fields)+')',list(row.values()))
                db.execute('CREATE TABLE audit_records (evidence TEXT)');db.execute("INSERT INTO audit_records VALUES ('unchanged')")
            detail=source/'PlastPrior_dashboard.sqlite'
            with closing(sqlite3.connect(detail)) as db, db:
                db.execute('CREATE TABLE metadata (key TEXT PRIMARY KEY,value TEXT)')
                db.executemany('INSERT INTO metadata VALUES (?,?)',[('csv_sha256',sha(csv_path)),('run_id','baseline')])
                db.execute('CREATE TABLE compound_audit (inchikey_std TEXT,'+','.join('"'+f+'" TEXT' for f in fields)+')')
                db.execute('INSERT INTO compound_audit VALUES ('+','.join('?' for _ in range(len(fields)+1))+')',['A',*row.values()])
                db.execute('CREATE TABLE data_dictionary (field TEXT PRIMARY KEY,specification_json TEXT)')
            before={p.name:sha(p) for p in source.iterdir()}
            connections = []
            connect = sqlite3.connect
            def track(*args, **kwargs):
                db = connect(*args, **kwargs)
                connections.append(db)
                return db
            output=root/'new'
            with patch('sqlite3.connect', side_effect=track):
                summary=export_scenario(source,output)
            self.addCleanup(lambda: [db.close() for db in connections])
            for db in connections:
                with self.assertRaises(sqlite3.ProgrammingError):
                    db.execute('SELECT 1')
            with (output/'PlastIQ_results.csv').open(encoding='utf-8',newline='') as f:
                self.assertEqual(next(csv.DictReader(f))['Name'], '化合物 α')
            self.assertEqual(before,{p.name:sha(p) for p in source.iterdir()})
            self.assertEqual(summary['rows'],1)
            with closing(sqlite3.connect(output/'PlastIQ_results.sqlite')) as db, db:
                self.assertEqual(db.execute('SELECT Hazard_score FROM compounds').fetchone()[0],'0.5')
                self.assertEqual(db.execute('SELECT Hazard_score,Hazard_score_raw,Priority_level FROM current_compounds').fetchone(),('1','0.50','5'))
                self.assertEqual(db.execute('SELECT evidence FROM audit_records').fetchone()[0],'unchanged')
            with closing(sqlite3.connect(output/'PlastIQ_dashboard.sqlite')) as db, db:
                meta=dict(db.execute('SELECT key,value FROM metadata'))
                self.assertEqual(meta['csv_sha256'],sha(output/'PlastIQ_results.csv'))
            # A byte-identical baseline with the new filenames remains usable.
            canonicalise_names(source)
            renamed_before={p.name:sha(p) for p in source.iterdir()}
            export_scenario(source,output)
            self.assertFalse(output.is_symlink())
            self.assertFalse(list(root.glob('.new-previous')))
            self.assertEqual(renamed_before,{p.name:sha(p) for p in source.iterdir()})

    def test_three_level_export_preserves_source_evidence_and_updates_all_current_views(self):
        self._assert_three_level_export(three_level_policy())

    def test_exposure_rules_export_uses_raw_inputs_and_updates_all_current_views(self):
        self._assert_three_level_export(three_level_exposure_policy())

    def _assert_three_level_export(self, policy):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'baseline'; source.mkdir()
            evidence = json.dumps({'curated_db': {'selected': {'score': .25}},
                                   'final_selection': {'selected': {'score': .25}}})
            rows = []
            for key, value in [('A', '0.25'), ('B', '0.5'), ('C', '')]:
                rows.append({**dict.fromkeys(COMPONENT_MAXIMA, '0'), 'inchikey': key,
                             'Persistence_score': value, 'Persistence_evidence': evidence,
                             'Aquatic_M_score': value, 'LRTP_M_score': '',
                             'Exposure_production_score': {'A': '0.5', 'B': '2', 'C': ''}[key],
                             'Exposure_inventory_listing_count': '0', 'Exposure_inventory_data_status': 'available',
                             'Exposure_patent_count': '0', 'Exposure_patent_data_status': 'available',
                             'Exposure_literature_count': '0', 'Exposure_literature_data_status': 'available',
                             'Exposure_scale_value_tonnes': {'A': '0.1', 'B': '100000', 'C': ''}[key],
                             'Exposure_scale_market_presence': 'unknown'})
            fields = list(rows[0])
            csv_path = source / 'PlastPrior_results.csv'
            with csv_path.open('w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader(); writer.writerows(rows)
            with closing(sqlite3.connect(source / 'PlastPrior_results.sqlite')) as db, db:
                db.execute('CREATE TABLE compounds (' + ','.join('"'+f+'" TEXT' for f in fields) + ')')
                db.executemany('INSERT INTO compounds VALUES (' + ','.join('?' for _ in fields) + ')',
                               [list(r.values()) for r in rows])
            with closing(sqlite3.connect(source / 'PlastPrior_dashboard.sqlite')) as db, db:
                db.execute('CREATE TABLE metadata (key TEXT PRIMARY KEY,value TEXT)')
                db.executemany('INSERT INTO metadata VALUES (?,?)', [('csv_sha256', sha(csv_path)), ('run_id', 'baseline')])
                db.execute('CREATE TABLE compound_audit (inchikey_std TEXT,' + ','.join('"'+f+'" TEXT' for f in fields) + ')')
                db.executemany('INSERT INTO compound_audit VALUES (' + ','.join('?' for _ in range(len(fields)+1)) + ')',
                               [[r['inchikey'], *r.values()] for r in rows])
                db.execute('CREATE TABLE data_dictionary (field TEXT PRIMARY KEY,specification_json TEXT)')
            original_hashes = {p.name: sha(p) for p in source.iterdir()}
            output = root / 'new'
            summary = export_scenario(source, output, policy)
            self.assertEqual(original_hashes, {p.name: sha(p) for p in source.iterdir()})
            with (output / 'PlastIQ_results.csv').open(newline='') as f:
                exported = {r['inchikey']: r for r in csv.DictReader(f)}
            for filename, tables, key in [
                ('PlastIQ_results.sqlite', ['scenario_results', 'current_compounds'], 'inchikey'),
                ('PlastIQ_dashboard.sqlite', ['compound_audit'], 'inchikey_std'),
            ]:
                with closing(sqlite3.connect(output / filename)) as db:
                    for table in tables:
                        for row in rows:
                            fields_to_check = ['Persistence_score', 'Persistence_score_original', 'Persistence_evidence',
                                               'Aquatic_M_score', 'Aquatic_M_score_original', 'LRTP_M_score',
                                               'Exposure_production_score', 'Hazard_score', 'Exposure_score', 'Priority_score']
                            actual = db.execute('SELECT '+','.join(fields_to_check)+' FROM '+table+' WHERE '+key+'=?',
                                                (row['inchikey'],)).fetchone()
                            self.assertEqual(actual, tuple(exported[row['inchikey']][f] for f in fields_to_check))
            with closing(sqlite3.connect(output / 'PlastIQ_results.sqlite')) as db:
                self.assertEqual(db.execute('SELECT Persistence_score,Persistence_evidence FROM compounds ORDER BY inchikey').fetchall(),
                                 [(r['Persistence_score'], evidence) for r in rows])
                self.assertEqual(db.execute('SELECT Exposure_production_score FROM compounds ORDER BY inchikey').fetchall(),
                                 [(r['Exposure_production_score'],) for r in rows])
            self.assertEqual(exported['A']['Persistence_score_original'], '0.25')
            self.assertEqual(exported['B']['Persistence_score_original'], '0.5')
            self.assertEqual(exported['C']['Persistence_score'], '')
            self.assertEqual(exported['A']['Persistence_evidence'], evidence)
            self.assertEqual(exported['A']['Persistence_score'], '1')
            self.assertEqual(exported['A']['Hazard_score'], '2')
            self.assertEqual(exported['A']['Exposure_score'], '1')
            if 'exposure_score_policy' in policy:
                self.assertEqual(float(exported['A']['Exposure_production_score']), 1)
                self.assertNotIn('Exposure_production_score_original', exported['A'])
                self.assertEqual(float(exported['B']['Exposure_production_score']), 2)
                self.assertEqual(exported['C']['Exposure_production_score'], '')
                self.assertIn('exposure_policy.json', summary['implementation_sha256'])
                with closing(sqlite3.connect(output / 'PlastIQ_dashboard.sqlite')) as db:
                    self.assertEqual(db.execute('SELECT Exposure_production_score FROM baseline_scoring ORDER BY inchikey_std').fetchall(),
                                     [(r['Exposure_production_score'],) for r in rows])
                    meta = dict(db.execute('SELECT key,value FROM metadata'))
                    self.assertEqual(meta['priority_policy'], policy['policy_version'])
                    self.assertIn('Exposure components are recalculated directly from selected counts', meta['readme'])
                    self.assertNotIn('Exposure scores are unchanged', meta['readme'])
            else:
                self.assertEqual(exported['A']['Exposure_production_score'], '0.5')
                self.assertNotIn('Exposure_production_score_original', exported['A'])
            self.assertFalse(list(root.glob('.scenario-*')))
            self.assertFalse(list(root.glob('.new-*')))
