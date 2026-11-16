"""Publication labels must not change internal evidence identity or mix outputs."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
import json
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'FigureCode/_shared'))
import publication

class PublicationOrderTests(TestCase):
    def test_renaming_is_single_step_and_leaves_tables_alone(self):
        self.assertEqual(publication.output_name('Fig4','Fig4.png'),'ExtendedDataFig4.png')
        self.assertEqual(publication.output_name('Fig3','Fig3.png'),'Fig2.png')
        self.assertEqual(publication.output_name('ExtendedDataFig3','ExtendedDataFig3.pdf'),'Fig3.pdf')
        self.assertEqual(publication.output_name('Fig4','compound_membership.csv'),'compound_membership.csv')
        self.assertEqual(publication.output_name('SILevel1Evidence','SILevel1Evidence.pdf'),'SILevel1Evidence.pdf')

    def test_order_has_four_main_and_six_extended_figures(self):
        rows=publication.entries()
        self.assertEqual([r['name'] for r in rows], [f'Fig{i}' for i in range(1,5)]+[f'ExtendedDataFig{i}' for i in range(1,7)])
        self.assertEqual(next(r['id'] for r in rows if r['name']=='Fig3'),'ExtendedDataFig3')

    def test_rejects_duplicate_destinations(self):
        with TemporaryDirectory() as temp:
            root=Path(temp);(root/'FigureCode').mkdir()
            (root/'FigureCode/publication_order.json').write_text(json.dumps({'figures':[
                {'id':'A','name':'Fig1','label':'Fig. 1'}, {'id':'B','name':'Fig1','label':'Fig. 2'}]}))
            with patch.object(publication,'ROOT',root):
                with self.assertRaisesRegex(ValueError,'Duplicate publication name'):publication.entries()
