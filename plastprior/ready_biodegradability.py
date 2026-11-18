"""Display-only Ready Biodegradability, joined through the frozen QSAR key audit.

No scoring function, threshold or candidate selection is called here. Historical
compounds and all archived model artifacts are immutable.
"""
from collections import Counter
import json
import math
from pathlib import Path
import re

from .export import archived_bytes, read_artifact_records

MODEL_NAME = 'Ready Biodegradability model (IRFMN)'
EVIDENCE_KEY = 'ready_biodegradability'
PREFIX = 'Ready_Biodegradability_'
RAW_FIELDS = {'prediction_raw': 'Predicted RB activity', 'assessment_raw': 'Assessment',
              'ADI_raw': 'ADI', 'similarity_index_raw': 'Similarity index',
              'accuracy_index_raw': 'Accuracy index', 'concordance_index_raw': 'Concordance index',
              'ACF_index_raw': 'ACF index', 'remarks_raw': 'Remarks'}
FIELDS = [PREFIX + f for f in [*RAW_FIELDS, 'ADI', 'reliability', 'status',
          'identity_verified', 'identity_status', 'qsar_inchikey', 'model_name', 'model_version']]
MISSING = {'', '-', 'N/A', 'NA', 'NaN', 'nan'}


def unique(rows, key):
    result = {}
    for row in rows:
        value = row[key]
        if not value or value in result:
            raise ValueError('Missing or duplicate QSAR mapping key: ' + str(value))
        result[value] = row
    return result


def truth(value):
    if value in (True, 'True', 'true', '1', 1): return True
    if value in (False, 'False', 'false', '0', 0): return False
    raise ValueError('Invalid identity flag: ' + str(value))


def make_evidence(compounds, predictions, audit, model, provenance):
    """Keyed many-to-one mapping, with exact frozen identity status validation."""
    compounds = unique(compounds, 'inchikey')
    predictions = unique(predictions, 'qsar_inchikey')
    audit = unique(audit, 'qsar_inchikey')
    if predictions.keys() != audit.keys():
        raise ValueError('Prediction and audited QSAR identities differ')
    output, counts = {}, Counter()
    for key, compound in compounds.items():
        qsar_key = compound['qsar_inchikey'] or None
        associated = qsar_key in predictions
        identity = audit.get(qsar_key)
        verified = truth(identity['identity_verified']) if identity else False
        identity_status = identity['identity_status'] if identity else 'no_report_association'
        if (truth(compound['qsar_identity_verified']) != verified or
                compound['qsar_identity_status'] != identity_status):
            raise ValueError('Full identity and frozen QSAR audit disagree: ' + key)
        if identity:
            if str(compound['vega_row_no']) != identity['vega_row_no']:
                raise ValueError('Frozen identity association disagrees: ' + key)
            if verified and identity['report_inchikey'] != qsar_key:
                raise ValueError('Verified report key mismatch: ' + key)
        raw = {field: predictions[qsar_key][MODEL_NAME + ' | ' + field] if associated else None
               for field in RAW_FIELDS.values()}
        assessment, prediction = raw['Assessment'], raw['Predicted RB activity']
        adi_raw = raw['ADI']
        adi = None if adi_raw is None or adi_raw in MISSING else float(adi_raw)
        if adi is not None and (not math.isfinite(adi) or not 0 <= adi <= 1):
            raise ValueError('Invalid raw Ready Biodegradability ADI: ' + str(adi_raw))
        reliability = re.search(r'\((LOW|MODERATE|GOOD) reliability\)', assessment or '')
        reliability = reliability.group(1) if reliability else None
        if not associated: prediction_status = 'missing'
        elif prediction in MISSING: prediction_status = 'model_error'
        elif prediction == 'Not classifiable': prediction_status = 'not_classifiable'
        else: prediction_status = 'predicted'
        status = 'identity_review_required' if associated and not verified else prediction_status
        evidence = {'format': 'plastprior-ready-biodegradability-v1', 'role': 'supplementary_display_only',
                    'used_in_scoring': False, 'status': status, 'prediction_status': prediction_status,
                    'prediction': None if prediction is None or prediction in MISSING else prediction,
                    'assessment': assessment, 'adi': adi, 'reliability': reliability,
                    'assessment_basis': 'experimental_value' if '(EXPERIMENTAL value)' in (assessment or '') else None,
                    'raw': raw, 'model': model,
                    'identity': {'inchikey': key, 'qsar_inchikey': qsar_key, 'verified': verified,
                                 'status': identity_status,
                                 'reason': identity['reason'] if identity else 'no_report_association',
                                 'vega_row_no': int(identity['vega_row_no']) if identity else None},
                    'source': provenance}
        flat = {PREFIX + suffix: raw[field] for suffix, field in RAW_FIELDS.items()}
        flat.update({PREFIX + k: v for k, v in {'ADI': adi, 'reliability': reliability, 'status': status,
                     'identity_verified': verified, 'identity_status': identity_status,
                     'qsar_inchikey': qsar_key, 'model_name': model['name'], 'model_version': model['version']}.items()})
        old = json.loads(compound['Persistence_evidence'])
        old[EVIDENCE_KEY] = evidence
        flat['Persistence_evidence'] = json.dumps(old, ensure_ascii=False, separators=(',', ':'))
        output[key] = flat
        counts['compounds'] += 1
        counts['associated_compounds' if associated else 'no_report_association'] += 1
        counts['status_' + status] += 1
        counts['prediction_status_' + prediction_status] += 1
        if associated:
            counts['verified_associations' if verified else 'review_associations'] += 1
            counts['adi_missing' if adi is None else 'adi_available'] += 1
    if set(predictions) - {r['qsar_inchikey'] for r in compounds.values()}:
        raise ValueError('Unmapped raw prediction identities')
    counts['raw_prediction_rows'] = len(predictions)
    counts['raw_missing_predictions'] = sum(r[MODEL_NAME+' | Predicted RB activity'] in MISSING for r in predictions.values())
    counts['raw_adi_missing'] = sum(r[MODEL_NAME+' | ADI'] in MISSING for r in predictions.values())
    return output, dict(counts)


def load_evidence(db):
    manifest = json.loads(b''.join(archived_bytes(db, 'stage3/qsar_manifest.json')))
    names = ['qsar_predictions.csv', 'qsar_identity_audit.csv', 'qsar_model_summary.csv',
             'qsar_screening.csv', 'vega_input_row_manifest.csv']
    source_hashes = {}
    data = {}
    for name in names:
        path = 'stage3/' + name
        record = db.execute('SELECT c.sha256,a.record_count,a.retained_count FROM artifacts a JOIN artifact_contents c ON a.content_id=c.id WHERE a.path=?', (path,)).fetchone()
        if not record or record[0] != manifest['output_sha256'][name] or record[1] != record[2]:
            raise ValueError('Incomplete or mismatched frozen QSAR artifact: ' + path)
        data[name] = list(read_artifact_records(db, path))
        if len(data[name]) != record[1]: raise ValueError('QSAR artifact row count mismatch: ' + path)
        source_hashes[path] = record[0]
    summaries = [r for r in data['qsar_model_summary.csv'] if r['model_name'] == MODEL_NAME]
    if len(summaries) != 1: raise ValueError('Expected one Ready Biodegradability model')
    summary = summaries[0]
    declaration = next(m for m in json.loads(Path(__file__).with_name('qsar_models.json').read_text())['models'] if m['name'] == MODEL_NAME)
    for a,b in [('source_file','filename'),('source_sha256','sha256'),('model_metadata','model_metadata'),('calculation_metadata','calculation_metadata')]:
        if summary[a] != declaration[b]: raise ValueError('Model metadata mismatch: ' + a)
    if not any(i['filename'] == summary['source_file'] and i['sha256'] == summary['source_sha256'] for i in manifest['inputs']):
        raise ValueError('Model is not bound to frozen QSAR manifest')
    model = {'id': summary['model_id'], 'name': MODEL_NAME,
             'version': re.search(r'\(version ([^)]+)\)',summary['model_metadata']).group(1),
             'calculation_core_version': re.search(r'version\s*:\s*([^)]+)',summary['calculation_metadata']).group(1),
             'model_metadata':summary['model_metadata'], 'calculation_metadata': summary['calculation_metadata'],
             'source_file':summary['source_file'], 'source_sha256':summary['source_sha256']}
    cursor = db.execute('SELECT inchikey,qsar_inchikey,qsar_identity_verified,qsar_identity_status,vega_row_no,Persistence_evidence FROM compounds')
    compounds = [dict(zip([d[0] for d in cursor.description], r)) for r in cursor]
    screening = unique(data['qsar_screening.csv'], 'inchikey')
    batch = unique(data['vega_input_row_manifest.csv'], 'Qsar_inchikey')
    audits = unique(data['qsar_identity_audit.csv'], 'qsar_inchikey')
    if screening.keys() != {r['inchikey'] for r in compounds} or batch.keys() != audits.keys():
        raise ValueError('Frozen screening/batch identity sets differ')
    for r in compounds:
        if r['qsar_inchikey'] != screening[r['inchikey']]['qsar_inchikey']:
            raise ValueError('Frozen full-key screening mapping mismatch')
    for key, a in audits.items():
        b = batch[key]
        if a['vega_row_no'] != b['vega_row_no'] or a['input_smiles'] != b['Smile_std'] or a['input_representative_inchikey'] != b['Inchikey_std']:
            raise ValueError('Frozen row-manifest identity mismatch')
    provenance = {'archive': 'PlastPrior_results.sqlite', 'artifact': 'stage3/qsar_predictions.csv',
                  'artifact_sha256':source_hashes['stage3/qsar_predictions.csv'],
                  'identity_artifact':'stage3/qsar_identity_audit.csv',
                  'identity_artifact_sha256':source_hashes['stage3/qsar_identity_audit.csv']}
    output, counts = make_evidence(compounds, data['qsar_predictions.csv'], data['qsar_identity_audit.csv'], model, provenance)
    return output, {'model':model, 'counts':counts, 'source_artifacts':source_hashes,
                    'json_path':'Persistence_evidence.ready_biodegradability',
                    'fields': FIELDS, 'used_in_scoring':False}


def dictionary():
    specs = {}
    for field in FIELDS:
        suffix = field[len(PREFIX):]
        specs[field] = {'field': field, 'definition': 'Display-only Ready Biodegradability; never used in scoring. '+
                        ('Exact source text; missing tokens preserved.' if suffix in RAW_FIELDS else
                         'Parsed supplemental evidence; missing numeric/reliability values are null (blank in CSV).'),
                        'source_field': RAW_FIELDS.get(suffix, suffix),
                        'json_path': 'Persistence_evidence.ready_biodegradability'}
    specs['Persistence_evidence.ready_biodegradability'] = {
        'field':'Persistence_evidence.ready_biodegradability', 'definition':
        'Independent supplementary evidence object; existing Persistence candidates and selection unchanged. '
        'raw preserves all eight original fields. adi is numeric or null; reliability is parsed only from explicit '
        'LOW/MODERATE/GOOD reliability text in Assessment. EXPERIMENTAL value is assessment_basis, not reliability. '
        'status distinguishes missing/model_error/not_classifiable/predicted/identity_review_required. '
        'Inspect identity.verified before presenting a prediction as associated with this compound.'}
    return specs
