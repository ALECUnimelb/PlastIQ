import csv
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from plastprior.figure_evidence import digest
from plastprior.sankey_evidence import prepare,package_sankey,validate_publication_figures,FIGURE_ID


class SankeyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.folder=self.root/'figure_data/ExtendedDataFig1'
        (self.root/'PlastPrior_results.csv').write_text('inchikey\nA\nB\n')
        with sqlite3.connect(self.root/'PlastPrior_results.sqlite') as db:
            db.execute('CREATE TABLE source_records (record_id TEXT)');db.executemany('INSERT INTO source_records VALUES (?)',[('a',),('b',)])
            db.execute('CREATE TABLE compound_memberships (record_id TEXT)');db.executemany('INSERT INTO compound_memberships VALUES (?)',[('a',),('b',)])
            db.execute('CREATE TABLE current_compounds (inchikey TEXT,keep_for_vega TEXT)');db.executemany('INSERT INTO current_compounds VALUES (?,?)',[('A','True'),('B','False')])
        with sqlite3.connect(self.root/'PlastPrior_dashboard.sqlite') as db:
            db.execute('CREATE TABLE metadata (key TEXT PRIMARY KEY,value TEXT)');db.executemany('INSERT INTO metadata VALUES (?,?)',[('csv_sha256',digest(self.root/'PlastPrior_results.csv')),('row_count','2')])
            db.execute('CREATE TABLE compound_audit (inchikey_std TEXT,n_records TEXT,keep_for_vega TEXT)');db.executemany('INSERT INTO compound_audit VALUES (?,?,?)',[('A','1','True'),('B','1','False')])
            db.execute('CREATE TABLE publication_figures (figure_id TEXT PRIMARY KEY,format TEXT,csv_sha256 TEXT,payload_sha256 TEXT,payload_json TEXT)')
            db.execute("INSERT INTO publication_figures VALUES ('Fig4','keep','keep','keep','keep')")
        specs=[('source',1,2),('identifier',2,2),('route',3,2),('resolution:resolved_records',4,2),
               ('dedup:unique_compounds',5,2),('qsar:eligible',6,1),('qsar:ineligible',6,1)]
        self.nodes=[dict(node_id=k,node_value=str(n),layer=str(i),x=str(i),ymin='0',ymax='1',label_x=str(i),label_y='0.5') for k,i,n in specs]
        pairs=[('source','identifier',2),('identifier','route',2),('route','resolution:resolved_records',2),
               ('resolution:resolved_records','dedup:unique_compounds',2),
               ('dedup:unique_compounds','qsar:eligible',1),('dedup:unique_compounds','qsar:ineligible',1)]
        self.edges=[dict(source_id=a,target_id=b,value=str(n),stage='test',unit='records',source_flow_ymin='0',source_flow_ymax='1',target_flow_ymin='0',target_flow_ymax='1') for a,b,n in pairs]
        summary=dict(source_records=2,resolved_records=2,unresolved_records=0,unique_compounds=2,collapsed_duplicate_records=0,qsar_eligible_compounds=1,qsar_ineligible_compounds=1)
        self.write('flow/summary.csv',[dict(metric=k,value=v) for k,v in summary.items()])
        for sub in ['flow','layout']:
            self.write(sub+('/nodes.csv' if sub=='flow' else '/plotted_nodes.csv'),self.nodes)
            self.write(sub+('/edges.csv' if sub=='flow' else '/plotted_edges.csv'),self.edges)
        self.write('layout/connector_segments.csv',[],['connector_id','segment_index','x','y','xend','yend'])
        self.refresh_manifest()

    def write(self,path,rows,fields=None):
        path=self.folder/path;path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=fields or list(rows[0]));w.writeheader();w.writerows(rows)

    def refresh_manifest(self):
        path=self.root/'figure_data/_metadata/ExtendedDataFig1/preparation.json';path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(dict(source=dict(run_id='test',files={k:{'sha256':digest(self.root/n)} for k,n in [('publication','PlastPrior_results.csv'),('analysis','PlastPrior_results.sqlite')]}),source_data={str(p.relative_to(self.folder)):digest(p) for p in self.folder.rglob('*.csv')})))

    def test_packages_missing_sankey_and_preserves_fig4_and_compound_data(self):
        package_sankey(self.root)
        with sqlite3.connect(self.root/'PlastPrior_dashboard.sqlite') as db:
            self.assertEqual(db.execute("SELECT payload_json FROM publication_figures WHERE figure_id='Fig4'").fetchone()[0],'keep')
            self.assertEqual(db.execute('SELECT count(*) FROM compound_audit').fetchone()[0],2)
            self.assertEqual(db.execute('SELECT format FROM publication_figures WHERE figure_id=?',(FIGURE_ID,)).fetchone()[0],'plastprior-sankey-v1')

    def test_final_delivery_rejects_omitted_sankey(self):
        with patch('plastprior.sankey_evidence.prepare_fig4',return_value={}):
            with self.assertRaisesRegex(ValueError,'missing ExtendedDataFig1a'):validate_publication_figures(self.root)

    def test_mixed_csv_and_analysis_batches_rejected(self):
        for name in ['PlastPrior_results.csv','PlastPrior_results.sqlite']:
            original=(self.root/name).read_bytes()
            with (self.root/name).open('ab') as f:f.write(b'changed')
            with self.assertRaisesRegex(ValueError,'source mismatch'):prepare(self.root)
            (self.root/name).write_bytes(original)

    def test_layout_or_flow_tampering_rejected(self):
        self.edges[0]['value']='1';self.write('layout/plotted_edges.csv',self.edges)
        with self.assertRaisesRegex(ValueError,'checksum'):prepare(self.root)
        self.refresh_manifest()
        with self.assertRaisesRegex(ValueError,'layout/flow mismatch'):prepare(self.root)
        self.write('flow/edges.csv',self.edges);self.refresh_manifest()
        with self.assertRaisesRegex(ValueError,'node totals'):prepare(self.root)

    def test_corrupt_geometry_rejected_even_with_updated_manifest(self):
        self.edges[0]['target_flow_ymax']='1.1'
        self.write('layout/plotted_edges.csv',self.edges);self.refresh_manifest()
        with self.assertRaisesRegex(ValueError,'outside node'):prepare(self.root)
