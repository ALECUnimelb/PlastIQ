import json
import unittest
from copy import deepcopy
from plastprior.ready_biodegradability import make_evidence, MODEL_NAME, RAW_FIELDS


class ReadyBiodegradabilityTests(unittest.TestCase):
    def setUp(self):
        self.model={'name':MODEL_NAME,'version':'1.0.10'}
        self.predictions=[dict({'qsar_inchikey':'Q'},**{MODEL_NAME+' | '+f:'-' for f in RAW_FIELDS.values()})]
        self.predictions[0].update({MODEL_NAME+' | Predicted RB activity':'Readily Biodegradable',
                                   MODEL_NAME+' | Assessment':'Readily Biodegradable (GOOD reliability)'})
        self.audit=[{'qsar_inchikey':'Q','identity_verified':'True','identity_status':'exact_key_match',
                     'report_inchikey':'Q','vega_row_no':'37','reason':'exact_key_match'}]
        self.compounds=[{'inchikey':key,'qsar_inchikey':'Q','qsar_identity_verified':'True',
                         'qsar_identity_status':'exact_key_match','vega_row_no':37,
                         'Persistence_evidence':'{"final_selection":{"score":2}}'} for key in ['FULL-B','FULL-A']]

    def run_mapping(self):
        return make_evidence(self.compounds,self.predictions,self.audit,self.model,{})

    def test_many_full_keys_share_one_qsar_prediction_without_row_alignment(self):
        output,counts=self.run_mapping()
        self.assertEqual(set(output),{'FULL-A','FULL-B'})
        self.assertEqual(counts['associated_compounds'],2)
        for row in output.values():
            e=json.loads(row['Persistence_evidence'])
            self.assertEqual(e['final_selection'],{'score':2})
            self.assertEqual(e['ready_biodegradability']['prediction'],'Readily Biodegradable')
            self.assertFalse(e['ready_biodegradability']['used_in_scoring'])
        self.compounds.reverse();self.assertEqual(output,self.run_mapping()[0])

    def test_missing_adi_is_null_but_actual_zero_is_zero(self):
        row=self.run_mapping()[0]['FULL-A']
        self.assertEqual(row['Ready_Biodegradability_ADI_raw'],'-')
        self.assertIsNone(row['Ready_Biodegradability_ADI'])
        self.predictions[0][MODEL_NAME+' | ADI']='0'
        self.assertEqual(self.run_mapping()[0]['FULL-A']['Ready_Biodegradability_ADI'],0)

    def test_unassociated_full_identity_has_no_fabricated_prediction(self):
        self.compounds.append({'inchikey':'UNASSOCIATED','qsar_inchikey':'OTHER','qsar_identity_verified':'False',
                               'qsar_identity_status':'no_report_association','vega_row_no':None,'Persistence_evidence':'{}'})
        row=self.run_mapping()[0]['UNASSOCIATED']
        self.assertEqual(row['Ready_Biodegradability_status'],'missing')
        self.assertIsNone(row['Ready_Biodegradability_prediction_raw'])
        self.assertIsNone(row['Ready_Biodegradability_ADI'])

    def test_identity_review_keeps_raw_values_with_explicit_isolation(self):
        self.audit[0].update(identity_verified='False',identity_status='review_required',report_inchikey='DIFFERENT')
        for r in self.compounds:r.update(qsar_identity_verified='False',qsar_identity_status='review_required')
        row=self.run_mapping()[0]['FULL-A']
        self.assertEqual(row['Ready_Biodegradability_status'],'identity_review_required')
        self.assertFalse(row['Ready_Biodegradability_identity_verified'])
        self.assertEqual(row['Ready_Biodegradability_prediction_raw'],'Readily Biodegradable')

    def test_duplicate_or_inconsistent_mapping_rejected(self):
        for target in [self.compounds,self.predictions,self.audit]:
            target.append(deepcopy(target[0]))
            with self.assertRaisesRegex(ValueError,'duplicate'):self.run_mapping()
            target.pop()
        self.compounds[0]['vega_row_no']=1
        with self.assertRaisesRegex(ValueError,'association disagrees'):self.run_mapping()

    def test_experimental_assessment_is_not_invented_reliability(self):
        self.predictions[0][MODEL_NAME+' | Assessment']='Readily Biodegradable (EXPERIMENTAL value)'
        e=json.loads(self.run_mapping()[0]['FULL-A']['Persistence_evidence'])['ready_biodegradability']
        self.assertIsNone(e['reliability']);self.assertEqual(e['assessment_basis'],'experimental_value')

    def test_model_error_and_unclassifiable_are_distinct(self):
        self.predictions[0][MODEL_NAME+' | Predicted RB activity']='-'
        self.assertEqual(self.run_mapping()[0]['FULL-A']['Ready_Biodegradability_status'],'model_error')
        self.predictions[0][MODEL_NAME+' | Predicted RB activity']='Not classifiable'
        self.assertEqual(self.run_mapping()[0]['FULL-A']['Ready_Biodegradability_status'],'not_classifiable')

    def test_scenario_export_carries_supplement_into_all_current_views(self):
        import csv
        import sqlite3
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from plastprior.scenario_export import export_scenario, sha
        from plastprior.scoring_scenarios import COMPONENT_MAXIMA
        from plastprior.ready_biodegradability import FIELDS
        supplement,report=self.run_mapping()
        row=dict.fromkeys(COMPONENT_MAXIMA,'0')
        row.update(inchikey='FULL-A',Hazard_score='0',Exposure_score='0',Priority_score='0',Persistence_evidence='{"final_selection":{"score":2}}')
        fields=list(row)
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);source=root/'baseline';source.mkdir()
            with (source/'PlastPrior_results.csv').open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerow(row)
            with sqlite3.connect(source/'PlastPrior_results.sqlite') as db:
                db.execute('CREATE TABLE compounds ('+','.join('"'+f+'" TEXT' for f in fields)+')')
                db.execute('INSERT INTO compounds VALUES ('+','.join('?' for _ in fields)+')',list(row.values()))
                db.execute('CREATE TABLE artifacts (path TEXT)')
            with sqlite3.connect(source/'PlastPrior_dashboard.sqlite') as db:
                db.execute('CREATE TABLE compound_audit (inchikey_std TEXT,'+','.join('"'+f+'" TEXT' for f in fields)+')')
                db.execute('INSERT INTO compound_audit VALUES ('+','.join('?' for _ in range(len(fields)+1))+')',['FULL-A',*row.values()])
                db.execute('CREATE TABLE metadata (key TEXT PRIMARY KEY,value TEXT)')
                db.executemany('INSERT INTO metadata VALUES (?,?)',[('csv_sha256',sha(source/'PlastPrior_results.csv')),('run_id','test'),('row_count','1')])
                db.execute('CREATE TABLE data_dictionary (field TEXT PRIMARY KEY,specification_json TEXT)')
            with patch('plastprior.ready_biodegradability.load_evidence',return_value=({'FULL-A':supplement['FULL-A']},report)):
                summary=export_scenario(source,root/'new')
            self.assertEqual(summary['delivery_status'],'pending_matching_figure_preparation_and_packaging')
            with (root/'new/PlastIQ_results.csv').open(newline='') as f: exported=next(csv.DictReader(f))
            for filename,table in [('PlastIQ_results.sqlite','scenario_results'),('PlastIQ_results.sqlite','current_compounds'),('PlastIQ_dashboard.sqlite','compound_audit')]:
                with sqlite3.connect(root/'new'/filename) as db:
                    cols=[*FIELDS,'Persistence_evidence']
                    actual=db.execute('SELECT '+','.join('"'+f+'"' for f in cols)+' FROM '+table).fetchone()
                    self.assertEqual(actual,tuple(exported[f] for f in cols))
            with sqlite3.connect(root/'new/PlastIQ_results.sqlite') as db:
                self.assertEqual(db.execute('SELECT Persistence_evidence FROM compounds').fetchone()[0],row['Persistence_evidence'])
