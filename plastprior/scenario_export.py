"""Versioned rescore of a frozen export, retaining all original evidence tables.

Run: python -m plastprior.scenario_export --source result/figure_data/_dependencies/baseline --output result
The source and its embedded stage archives are never rewritten. In the new full
archive, current_compounds is the authoritative current view; compounds and
embedded stage artifacts retain their baseline meaning for audit reconstruction.
"""
from .result_names import NAMES, ROLES, result_files, result_file
import argparse
from collections import Counter
from contextlib import closing
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile

from .scoring_scenarios import default_policy, score_population, score_record, three_level_policy, three_level_exposure_policy


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def cell(value):
    return '' if value is None else str(value)


def quote(value):
    return '"' + value.replace('"', '""') + '"'


def export_scenario(source, output, policy=None):
    source, output = Path(source).resolve(), Path(output).absolute()
    policy = default_policy() if policy is None else policy
    if output == source or output.is_relative_to(source):
        raise ValueError('Output must not replace the evidence baseline or a directory inside it.')
    names = NAMES
    inputs = result_files(source)
    source_paths = dict(zip(names, (inputs[role] for role in ROLES)))
    hashes = {path.name: sha(path) for path in source_paths.values()}
    with (source_paths[names[0]]).open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        original_fields = reader.fieldnames
        baseline = list(reader)
    with closing(sqlite3.connect((source_paths[names[2]]).as_uri() + '?mode=ro', uri=True)) as db:
        meta = dict(db.execute('select key,value from metadata'))
        if meta['csv_sha256'] != hashes[source_paths[names[0]].name]:
            raise ValueError('Source CSV and Dashboard database are not paired.')
    if 'exposure_score_policy' in policy:
        # The public CSV omits qualitative market presence; recover the selected
        # raw input from the paired immutable archive, not from a previous score.
        with closing(sqlite3.connect((source_paths[names[1]]).as_uri() + '?mode=ro', uri=True)) as db:
            presence = dict(db.execute('SELECT inchikey, Exposure_scale_market_presence FROM compounds'))
        if set(presence) != {r['inchikey'] for r in baseline}:
            raise ValueError('Selected exposure inputs and CSV identities differ.')
        for row in baseline:
            row['Exposure_scale_market_presence'] = presence[row['inchikey']]
        original_fields = list(dict.fromkeys([*original_fields, 'Exposure_scale_market_presence']))
    # Enrichment is separate from scoring and uses the immutable archived key mapping.
    from .ready_biodegradability import load_evidence, FIELDS, dictionary
    supplemental, supplemental_report = {}, None
    with closing(sqlite3.connect((source_paths[names[1]]).as_uri() + '?mode=ro', uri=True)) as db:
        if db.execute("SELECT 1 FROM sqlite_master WHERE name='artifacts'").fetchone():
            supplemental, supplemental_report = load_evidence(db)
    if supplemental:
        if set(supplemental) != {r['inchikey'] for r in baseline}:
            raise ValueError('Supplemental evidence and baseline identities differ')
        for row in baseline:
            row.update(supplemental[row['inchikey']])
        original_fields = list(dict.fromkeys([*original_fields, *FIELDS, 'Persistence_evidence']))
    evidence_fields = [*FIELDS, 'Persistence_evidence'] if supplemental else []
    scored = score_population(baseline, policy)
    derived_fields = [*score_record(baseline[0], policy), 'Priority_rank', 'Priority_tie_size', 'Top_n_selected']
    current_fields = [*derived_fields, *evidence_fields]
    fields = list(dict.fromkeys([*original_fields, *derived_fields]))
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-rounded'
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.scenario-', dir=output.parent) as temp:
        staging = Path(temp) / 'export'; staging.mkdir()
        csv_path = staging / names[0]
        with csv_path.open('w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
            writer.writeheader()
            writer.writerows({k: cell(row.get(k)) for k in fields} for row in scored)
        current_hash = sha(csv_path)
        provenance = {'run_id': run_id, 'source': str(source), 'source_sha256': hashes,
                      'base_run_id': meta['run_id'], 'policy': policy,
                      'policy_sha256': hashlib.sha256(json.dumps(policy,sort_keys=True,separators=(',', ':')).encode()).hexdigest(),
                      'implementation_sha256': {n: sha(Path(__file__).with_name(n)) for n in ['scoring_scenarios.py', 'scenario_export.py', 'hazard_score_mapping.py', 'exposure.py', 'exposure_policy.json']},
                      'csv_sha256': current_hash, 'supplemental_evidence': supplemental_report,
                      'delivery_status': 'pending_matching_figure_preparation_and_packaging',
                      'scope': 'Current scores in scenario_results/current_compounds; original compounds and stage artifacts remain immutable baseline audit. Detailed evidence retains source-native scores; apply the configured mapping when comparing with current scores.'}
        for name in names[1:]:
            shutil.copy2(source_paths[name], staging / name)
        # Preserve the original archive tables, including delta snapshots that depend on them.
        with closing(sqlite3.connect(staging / names[1])) as db, db:
            if db.execute("select 1 from sqlite_master where name='scenario_results'").fetchone():
                raise ValueError('Use the immutable original export as the scenario source.')
            db.execute('CREATE TABLE scenario_results (' + ','.join(quote(f)+' TEXT'+(' PRIMARY KEY' if f=='inchikey' else '') for f in fields)+')')
            db.executemany('INSERT INTO scenario_results VALUES ('+','.join('?' for _ in fields)+')',
                           [[cell(row.get(f)) for f in fields] for row in scored])
            original = [r[1] for r in db.execute('pragma table_info(compounds)')]
            select = ['s.'+quote(f) if f in current_fields else 'c.'+quote(f) for f in original]
            select += ['s.'+quote(f) for f in current_fields if f not in original]
            db.execute('CREATE VIEW current_compounds AS SELECT '+','.join(select)+' FROM compounds c JOIN scenario_results s USING(inchikey)')
            db.execute('CREATE TABLE scenario_metadata (key TEXT PRIMARY KEY,value_json TEXT NOT NULL)')
            db.executemany('INSERT INTO scenario_metadata VALUES (?,?)', [(k,json.dumps(v)) for k,v in provenance.items()])
        with closing(sqlite3.connect(staging / names[2])) as db, db:
            old = [r[1] for r in db.execute('pragma table_info(compound_audit)')]
            db.execute('CREATE TABLE baseline_scoring AS SELECT inchikey_std,'+','.join(quote(f) for f in derived_fields if f in old)+' FROM compound_audit')
            for field in current_fields:
                if field not in old:
                    db.execute('ALTER TABLE compound_audit ADD COLUMN '+quote(field)+' TEXT')
            statement = 'UPDATE compound_audit SET '+','.join(quote(f)+'=?' for f in current_fields)+' WHERE inchikey_std=?'
            db.executemany(statement, [[cell(row[f]) for f in current_fields]+[row['inchikey']] for row in scored])
            new_meta = {'run_id':run_id, 'csv_sha256':current_hash, 'priority_policy':policy['policy_version'],
                        'base_run_id':meta['run_id'], 'scenario_provenance':json.dumps(provenance),
                        'delivery_status':'pending_matching_figure_preparation_and_packaging',
                        'sankey_status':'Prepare and package matching ExtendedDataFig1 data before release.',
                        'readme':'H/E weighted sums rounded half up separately. Priority=sum of rounded H/E. Labels: L<4, M<8, H<12, otherwise vH. Original evidence preserved; weighted sums retained as *_score_raw.'}
            if 'hazard_score_mapping' in policy:
                new_meta['readme'] += ' PBMT source scores 0.25/0.5 map to 1 before aggregation; *_score_original retains the selected pre-mapping score. Source-native evidence is unchanged.'
                if 'exposure_score_policy' not in policy:
                    new_meta['readme'] += ' Exposure scores are unchanged.'
            if 'exposure_score_policy' in policy:
                new_meta['readme'] += ' Exposure components are recalculated directly from selected counts, quantities and qualitative market presence using exposure-three-level-rules-v1; the rules produce 0, 1 or 2 without a score mapping. Historical evidence remains in the preserved baseline.'
            db.executemany('INSERT OR REPLACE INTO metadata VALUES (?,?)', new_meta.items())
            if supplemental:
                db.execute('INSERT OR REPLACE INTO metadata VALUES (?,?)', ('ready_biodegradability',json.dumps(supplemental_report)))
                db.executemany('INSERT OR REPLACE INTO data_dictionary VALUES (?,?)',[(k,json.dumps(v)) for k,v in dictionary().items()])
            from .figure_evidence import add_fig4
            add_fig4(db, csv_path)
            for field in derived_fields:
                spec = {'field':field,'source_field':field,'definition':'Derived by '+policy['policy_version']+'; see scoring_config_json and scenario_provenance.'}
                if field.endswith('_score_original'):
                    if field.startswith('Exposure_'):
                        spec['definition'] = 'Selected exposure component score before exposure mapping. Original counts, quantities and source-native evidence remain unchanged.'
                    else:
                        spec['definition'] = 'Selected component score before PBMT mapping; not necessarily PlastChem. Source-native PlastChem scores remain in detailed evidence.'
                db.execute('INSERT OR REPLACE INTO data_dictionary VALUES (?,?)',(field,json.dumps(spec)))
        # Verify every CSV field against the current archive and every changed detail field.
        for name, table, key in [(names[1],'scenario_results','inchikey'),(names[1],'current_compounds','inchikey'),(names[2],'compound_audit','inchikey_std')]:
            with closing(sqlite3.connect(staging / name)) as db:
                if db.execute('pragma integrity_check').fetchall() != [('ok',)]:
                    raise ValueError('SQLite integrity failed: '+name)
                check_fields = fields if table == 'scenario_results' else current_fields
                for row in scored:
                    actual = db.execute('SELECT '+','.join(map(quote,check_fields))+' FROM '+table+' WHERE '+key+'=?',(row['inchikey'],)).fetchone()
                    if actual != tuple(cell(row.get(f)) for f in check_fields):
                        raise ValueError('Export mismatch: '+row['inchikey'])
        (staging/'scoring_config.json').write_text(json.dumps(policy,indent=2)+'\n', encoding='utf-8')
        summary = {**provenance, 'rows':len(scored), 'levels':dict(Counter(r['Priority_tier'] for r in scored)),
                   'top_n_selected':sum(r['Top_n_selected'] is True for r in scored),
                   'verification':'Data-only export: CSV/current fields match and SQLite integrity passed. Complete delivery still requires matched Fig4 and Sankey packaging and validation.',
                   'output_sha256':{name:sha(staging/name) for name in names}}
        # A portable chart source contains exactly the same integer domains and ranks.
        with (staging/'score_chart_data.csv').open('w', encoding='utf-8', newline='') as f:
            columns=['inchikey','Hazard_score','Exposure_score','Priority_score','Hazard_label','Exposure_label','Priority_level','Priority_rank','Top_n_selected']
            writer=csv.DictWriter(f,fieldnames=columns,lineterminator='\n');writer.writeheader()
            writer.writerows({k:cell(r[k]) for k in columns} for r in scored)
        (staging/'scenario_manifest.json').write_text(json.dumps(summary,indent=2)+'\n', encoding='utf-8')
        if {path.name:sha(path) for path in source_paths.values()} != hashes:
            raise ValueError('Source changed during scoring.')
        from .result_storage import install_package
        install_package(staging, output)
    return summary


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    policies = parser.add_mutually_exclusive_group()
    policies.add_argument('--config',type=Path,help='Scoring configuration JSON, or a Dashboard scenario configuration export.')
    policies.add_argument('--three-level-hazard',action='store_true',help='Opt in to PBMT 0.25/0.5 -> 1 mapping; preserve source evidence, exposure and domain rounding.')
    policies.add_argument('--three-level-exposure',action='store_true',help='Use PBMT three-level mapping and direct exposure 0/1/2 rules over selected raw inputs; preserve evidence and rounding.')
    args=parser.parse_args()
    policy=three_level_exposure_policy() if args.three_level_exposure else three_level_policy() if args.three_level_hazard else None
    if args.config:
        config=json.loads(args.config.read_text(encoding='utf-8'))
        if config.get('format') == 'plastprior-scenario-v1':
            if config.get('base_csv_sha256') != sha(result_file(args.source, 'publication')):
                parser.error('Scenario configuration belongs to a different source CSV.')
            policy=config['config']
        else:
            policy=config
    print(json.dumps(export_scenario(args.source,args.output,policy),indent=2))
