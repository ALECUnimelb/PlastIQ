"""Validate paired composition tables without depending on local research data."""
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory
import csv
import importlib.util
import json
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('fig4_approved', ROOT/'FigureCode/Fig4/verify.py')
fig4 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fig4)


class ApprovedDataTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.publication = self.folder/'publication.csv'
        self.prepare_cohort(115)

    def prepare_cohort(self, size):
        rows = [dict(inchikey=f'compound-{i}', Name=f'Compound {i}', CAS='', SMILES='C',
                     Hazard_score='12', Exposure_score='12', Priority_score='24',
                     Priority_rank='1', Top_n_selected='True', Figure_priority_level='1',
                     GIC_regulatory_status='Listed', structure_group='Group A',
                     primary_use='Known use' if i < 101 else 'Pending use review')
                for i in range(size)]
        def write(name, records):
            with (self.folder/name).open('w', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=records[0].keys())
                writer.writeheader()
                writer.writerows(records)
        write('publication.csv', rows + [dict(rows[0], inchikey='outside-cohort', Hazard_score='11')])
        for name in ('compound_membership.csv', 'compound_identity.csv', 'primary_use_annotations.csv'):
            write(name, rows)
        for name, field in [('use_counts.csv', 'primary_use'), ('structure_counts.csv', 'structure_group'),
                            ('reg_counts.csv', 'GIC_regulatory_status')]:
            write(name, [dict(category=key, n=value) for key, value in Counter(row[field] for row in rows).items()])
        (self.folder/'classification.json').write_text(json.dumps({'group_counts': {'Group A': size}}))

    def mutate(self, name, change):
        path = self.folder/name
        rows = fig4.read_rows(path)
        change(rows)
        with path.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

    def test_approved_tables_pass(self):
        for size in (101, 115):
            with self.subTest(cohort=size):
                self.prepare_cohort(size)
                self.assertEqual(fig4.verify_tables(self.folder, self.publication)['panel_totals'], [size] * 3)

    def test_missing_use_annotation_is_rejected(self):
        self.mutate('primary_use_annotations.csv', lambda rows: rows.pop())
        with self.assertRaises(AssertionError):
            fig4.verify_tables(self.folder, self.publication)

    def test_wrong_panel_count_is_rejected(self):
        self.mutate('use_counts.csv', lambda rows: rows[0].update(n='999'))
        with self.assertRaises(AssertionError):
            fig4.verify_tables(self.folder, self.publication)

    def test_modified_rank_is_rejected(self):
        self.mutate('compound_membership.csv', lambda rows: rows[0].update(Priority_rank='999'))
        with self.assertRaises(AssertionError):
            fig4.verify_tables(self.folder, self.publication)

    def test_duplicate_compound_is_rejected(self):
        self.mutate('compound_membership.csv', lambda rows: rows[1].update(rows[0]))
        with self.assertRaises(AssertionError):
            fig4.verify_tables(self.folder, self.publication)


if __name__ == '__main__':
    unittest.main()
