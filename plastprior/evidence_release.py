"""Refresh display evidence, prepare/check figures, and publish one coordinated set.

Run from the canonical root: python -m plastprior.evidence_release
This entry point deliberately never invokes scoring or VEGA. For new scored
scenarios, use scenario_export in staging, prepare matching figures, then call
finalize_delivery before publishing the complete directory.
"""
from .result_names import NAMES, LEGACY_NAMES, ROLES, result_files, result_file, canonicalise_names
from contextlib import closing
from datetime import datetime, timezone
import csv
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile

from .figure_evidence import digest, package_fig4, read_rows
from .ready_biodegradability import FIELDS, dictionary, load_evidence
from .result_storage import replace_directory, update_lock
from .sankey_evidence import package_sankey, validate_publication_figures
from .scenario_export import cell, quote

ROOT = Path(__file__).resolve().parents[1]
NUMERICAL = ('Fig2','Fig3','Fig4','Fig5','ExtendedDataFig1','ExtendedDataFig2','ExtendedDataFig3')


def write_json(path, value):
    path = Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def files(folder):
    return {str(p.relative_to(folder)):digest(p) for p in sorted(Path(folder).rglob('*')) if p.is_file() and p.name != '.DS_Store'}


def load_module(name, path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def enrich_current(stage):
    """Modify only an unpublished independent copy, retaining baseline tables."""
    stage = Path(stage)
    canonicalise_names(stage)
    analysis = stage/NAMES[1]
    with closing(sqlite3.connect(analysis)) as db:
        additions, report = load_evidence(db)
    rows = read_rows(stage/NAMES[0])
    if len(rows) != len(additions) or {r['inchikey'] for r in rows} != set(additions):
        raise ValueError('CSV/full compound identity mismatch')
    fields = list(dict.fromkeys([*rows[0], *FIELDS, 'Persistence_evidence']))
    updated = [dict(r,**additions[r['inchikey']]) for r in rows]
    with (stage/NAMES[0]).open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n');writer.writeheader()
        writer.writerows({k:cell(r.get(k)) for k in fields} for r in updated)
    current_hash = digest(stage/NAMES[0])
    extra = [*FIELDS,'Persistence_evidence']
    for filename,table,key in [(NAMES[1],'scenario_results','inchikey'),(NAMES[2],'compound_audit','inchikey_std')]:
        with closing(sqlite3.connect(stage/filename)) as db, db:
            old = [r[1] for r in db.execute('PRAGMA table_info('+table+')')]
            for field in extra:
                if field not in old: db.execute('ALTER TABLE '+table+' ADD COLUMN '+quote(field)+' TEXT')
            db.executemany('UPDATE '+table+' SET '+','.join(quote(f)+'=?' for f in extra)+' WHERE '+key+'=?',
                           [[cell(additions[k][f]) for f in extra]+[k] for k in additions])
            if table == 'scenario_results':
                current = [r[1] for r in db.execute('PRAGMA table_info(current_compounds)')]
                # Retain the exact old view, overriding only display evidence.
                sql = db.execute("SELECT sql FROM sqlite_master WHERE name='current_compounds'").fetchone()[0]
                select_sql = sql[sql.upper().index(' AS SELECT ')+4:]
                db.execute('DROP VIEW current_compounds')
                columns = [*current,*[f for f in extra if f not in current]]
                expressions = [('s.' if f in extra else 'c.')+quote(f)+' AS '+quote(f) for f in columns]
                db.execute('CREATE VIEW current_compounds AS SELECT '+','.join(expressions)+
                           ' FROM ('+select_sql+') c JOIN scenario_results s USING(inchikey)')
                db.execute('INSERT OR REPLACE INTO scenario_metadata VALUES (?,?)',('csv_sha256',json.dumps(current_hash)))
                db.execute('INSERT OR REPLACE INTO scenario_metadata VALUES (?,?)',('supplemental_evidence',json.dumps(report)))
            else:
                db.executemany('INSERT OR REPLACE INTO metadata VALUES (?,?)',[
                    ('csv_sha256',current_hash),('ready_biodegradability',json.dumps(report)),
                    ('delivery_status','pending_matching_figure_preparation_and_packaging')])
                provenance = json.loads(dict(db.execute('SELECT key,value FROM metadata'))['scenario_provenance'])
                provenance.update(csv_sha256=current_hash,supplemental_evidence=report)
                db.execute('UPDATE metadata SET value=? WHERE key=?',(json.dumps(provenance),'scenario_provenance'))
                db.executemany('INSERT OR REPLACE INTO data_dictionary VALUES (?,?)',[(k,json.dumps(v)) for k,v in dictionary().items()])
    manifest_path = stage/'figure_data/_metadata/scenario_manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest.update(csv_sha256=current_hash,supplemental_evidence=report,
                    delivery_status='pending_matching_figure_preparation_and_packaging')
    manifest['output_sha256'] = {n:digest(stage/n) for n in NAMES}
    write_json(manifest_path,manifest)
    return report


def compare_current(before, after):
    """Exact comparisons, not numerical tolerances, over the whole population."""
    left,right=read_rows(result_file(before, 'publication')),read_rows(result_file(after, 'publication'))
    if [r['inchikey'] for r in left] != [r['inchikey'] for r in right] or len(left)!=15125 or len({r['inchikey'] for r in right})!=15125:
        raise ValueError('Full compound identities/order changed')
    original_fields = [f for f in left[0] if f not in FIELDS and f!='Persistence_evidence']
    for a,b in zip(left,right):
        for f in original_fields:
            if a[f] != b[f]: raise ValueError('Existing CSV field changed: '+a['inchikey']+' '+f)
    checks = {}
    for filename,table,key in [(NAMES[1],'current_compounds','inchikey'),(NAMES[2],'compound_audit','inchikey_std')]:
        with closing(sqlite3.connect((result_file(before, ROLES[NAMES.index(filename)])).as_uri()+'?mode=ro',uri=True)) as a, closing(sqlite3.connect((result_file(after, ROLES[NAMES.index(filename)])).as_uri()+'?mode=ro',uri=True)) as b:
            cols=[r[1] for r in a.execute('PRAGMA table_info('+table+')') if r[1] not in FIELDS]
            qa='SELECT '+','.join(map(quote,cols))+' FROM '+table+' ORDER BY '+key
            count=0
            for old,new in zip(a.execute(qa),b.execute(qa),strict=True):
                count+=1
                for f,x,y in zip(cols,old,new):
                    if f=='Persistence_evidence':
                        x,y=json.loads(x),json.loads(y)
                        x.pop('ready_biodegradability',None);y.pop('ready_biodegradability',None)
                    if x!=y: raise ValueError('Existing database field changed: '+table+' '+f)
            if count !=15125: raise ValueError('Database population changed')
            checks[table]={'rows':count,'existing_fields_unchanged':len(cols)}
    return {'population':len(left),'original_csv_fields_unchanged':len(original_fields),
            'all_original_csv_cells_identical':True,'identities_and_order_identical':True,
            'scores_weights_ranks_levels_top_n_identical':True,'database_checks':checks,
            'top_n_count':sum(r['Top_n_selected'].lower()=='true' for r in right)}


def verify_immutable_tables(before, after):
    """Compare all retained original analysis tables, including raw archive blobs."""
    with closing(sqlite3.connect((result_file(before, 'analysis')).as_uri()+'?mode=ro',uri=True)) as old, closing(sqlite3.connect((result_file(after, 'analysis')).as_uri()+'?mode=ro',uri=True)) as new:
        tables=[r[0] for r in old.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT IN ('scenario_results','scenario_metadata')")]
        for table in tables:
            a,b=old.execute('SELECT * FROM '+quote(table)),new.execute('SELECT * FROM '+quote(table))
            while True:
                x,y=a.fetchmany(128),b.fetchmany(128)
                if x!=y: raise ValueError('Immutable archive changed: '+table)
                if not x: break
    return {'unchanged_tables':tables}


def refresh_figure_data(stage, temp, profile):
    """Re-prepare every current numerical figure; reject any scientific change.

Retain render bytes only after their freshly computed tables and R payloads
compare equal. Reuse audited geometry only when its scientific flow is equal.
"""
    sys.path.insert(0,str(ROOT/'FigureCode/_shared'))
    from preparation import equivalent
    from managed import code_hashes
    candidate_profile=json.loads(json.dumps(profile))
    for spec in candidate_profile['files'].values():
        spec['path']=str((stage/Path(spec['path']).name).relative_to(ROOT))
    lock=temp/'source_lock.json';write_json(lock,candidate_profile)
    env=dict(os.environ,PLASTPRIOR_SOURCE_LOCK=str(lock),PLASTPRIOR_FIGURE_PHASE='prepare',
             PLASTPRIOR_CLASSIFICATION_STAGE=str(stage/'figure_data/Level1Identity'))
    reports={}
    # Regenerate the retained structural identity evidence against the candidate.
    identity=temp/'identity';identity.mkdir()
    identity_env=dict(env,PLASTPRIOR_CLASSIFICATION_STAGE=str(identity),
                      PLASTPRIOR_PUBLICATION=str(stage/NAMES[0]))
    subprocess.run([str(ROOT/'.venv/bin/python'),str(ROOT/'FigureCode/Supplementary/Level1Identity/prepare.py')],
                   cwd=ROOT,env=identity_env,check=True)
    old_identity=stage/'figure_data/Level1Identity'
    if not equivalent(identity/'compound_identity.csv',old_identity/'compound_identity.csv'):
        raise ValueError('Retained identity/classification rows changed')
    classification=json.loads((identity/'classification.json').read_text())
    previous=json.loads((old_identity/'classification.json').read_text())
    if {k:v for k,v in classification.items() if k!='source_hashes'} != {k:v for k,v in previous.items() if k!='source_hashes'}:
        raise ValueError('Structural classification changed')
    classification['source_hashes']={k.replace(str(stage.relative_to(ROOT)),'result'):v for k,v in classification['source_hashes'].items()}
    write_json(old_identity/'classification.json',classification)
    for name in ['Level1Identity','Level1IdentityTree']:
        path=stage/'figure_data/_metadata'/name/'manifest.json'
        record=json.loads(path.read_text())
        record['evidence_refresh']={'previous_source_hashes':record['classification']['source_hashes'],
                                    'verification':'Fresh structural classification and identity rows identical; sources refreshed.'}
        record['classification']=classification
        write_json(path,record)
    reports['Level1Identity']={'identities_regenerated':classification['exact_regenerated_inchikey_matches'],
                               'classification_unchanged':True}
    for name in NUMERICAL:
        print('Preparing '+name,flush=True)
        module=ROOT/'FigureCode'/name
        work=temp/('prepare-'+name);work.mkdir()
        if name=='ExtendedDataFig1':
            subprocess.run([sys.executable,str(module/'prepare_data.py'),str(work)],cwd=ROOT,env=env,check=True)
        subprocess.run(['Rscript',str(module/'prepare.R'),str(work)],cwd=ROOT,env=env,check=True)
        current=stage/'figure_data'/name; generated=work/'source_data'
        matched=[]
        for p in generated.rglob('*'):
            if not p.is_file(): continue
            rel=p.relative_to(generated);old=current/rel
            if not old.exists(): raise ValueError('Unexpected new figure input: '+name+'/'+str(rel))
            if p.name=='plot_data.rds':
                comparison = 'a<-commandArgs(TRUE);x<-readRDS(a[1]);y<-readRDS(a[2]);'
                if name=='ExtendedDataFig3':
                    # This payload embeds provenance alongside numerical arrays.
                    comparison += 'x$config$source<-NULL;y$config$source<-NULL;x$config$protected_hashes<-NULL;y$config$protected_hashes<-NULL;'
                comparison += 'if(!identical(x,y)){print(all.equal(x,y,tolerance=0));stop("R numerical payload changed")}'
                subprocess.run(['Rscript','-e',comparison,str(old),str(p)],cwd=ROOT,check=True)
            elif p.name=='classification.json':
                x,y=json.loads(old.read_text()),json.loads(p.read_text())
                if {k:v for k,v in x.items() if k!='source_hashes'} != {k:v for k,v in y.items() if k!='source_hashes'}:
                    raise ValueError('Figure structural classification changed')
            elif not equivalent(old,p): raise ValueError('Evidence-only refresh changed figure inputs: '+name+'/'+str(rel))
            matched.append(str(rel))
            # Preserve exact historical serialization except provenance embedded in ED3.
            if p.name!='classification.json' and not (name=='ExtendedDataFig3' and p.name=='plot_data.rds'):
                shutil.copy2(old,p)
        for p in generated.rglob('*'):
            if p.is_file(): shutil.copy2(p,current/p.relative_to(generated))
        data_hashes=files(current)
        for kind in ['manifest.json','preparation.json']:
            path=stage/'figure_data/_metadata'/name/kind
            record=json.loads(path.read_text())
            record['evidence_refresh']={'previous_source':record['source'],
                                        'verification':'Fresh numerical tables and R payload identical; existing render/geometry retained.',
                                        'regenerated_inputs':matched}
            record['source']=profile
            record['source_data']=data_hashes
            if name=='ExtendedDataFig3':
                record['facts']=json.loads((work/'caption_facts.json').read_text())
                record['facts']['source']=profile
            if kind=='preparation.json':
                record['code']=code_hashes(module)
                record['changed_tables']=[]
            write_json(path,record)
        reports[name]={'regenerated_equal_inputs':matched,'images_unchanged':True}
    # SI evidence is regenerated independently using the staged CSV/configuration.
    si=load_module('ready_release_si',ROOT/'FigureCode/Supplementary/SILevel1Evidence/prepare.py')
    payload=si.make_payload(run_dir=stage)
    old=json.loads((stage/'figure_data/SILevel1Evidence/si_payload.json').read_text())
    if [r['inchikey'] for r in payload['rows']] != [r['inchikey'] for r in old['rows']]:
        raise ValueError('SI identities/order changed')
    for previous,current in zip(old['rows'],payload['rows']):
        for field,value in previous.items():
            if field not in FIELDS and field!='Persistence_evidence' and current[field]!=value:
                raise ValueError('SI existing scientific value changed: '+field)
        if set(current)-set(previous)-set(FIELDS)-{'Persistence_evidence'}:
            raise ValueError('Unexpected added SI evidence field')
    for key in ['components','score_palette','regulatory_legend']:
        if payload[key]!=old[key]: raise ValueError('SI evidence content changed: '+key)
    payload['changes']=old['changes']
    payload['metadata']['sources']={k.replace(str(stage.relative_to(ROOT)),'result'):v for k,v in payload['metadata']['sources'].items()}
    si.write_payload(payload,stage/'figure_data/SILevel1Evidence')
    for kind in ['manifest.json','preparation.json']:
        path=stage/'figure_data/_metadata/SILevel1Evidence'/kind
        if not path.exists():continue
        record=json.loads(path.read_text());record['evidence_refresh']={'previous_source':record.get('source'),
            'verification':'Recomputed existing SI scientific fields, components and palettes identical; supplemental fields and source provenance added.'}
        record['source']=profile;record['source_data']=files(stage/'figure_data/SILevel1Evidence')
        write_json(path,record)
    reports['SILevel1Evidence']={'rows':len(payload['rows']),'scientific_content_unchanged':True}
    return reports


def validate_delivery(result):
    """Fail closed if either required publication payload or compound evidence is lost."""
    result=Path(result)
    names = tuple(p.name for p in result_files(result).values())
    figures=validate_publication_figures(result)
    rows=read_rows(result/names[0]);keys=[r['inchikey'] for r in rows]
    if len(keys)!=15125 or len(set(keys))!=15125:raise ValueError('Expected 15125 unique compounds')
    csv_hash=digest(result/names[0])
    with closing(sqlite3.connect((result/names[1]).resolve().as_uri()+'?mode=ro',uri=True)) as db:
        additions,report=load_evidence(db)
        metadata={k:json.loads(v) for k,v in db.execute('SELECT * FROM scenario_metadata')}
        if metadata['csv_sha256']!=csv_hash:raise ValueError('Analysis CSV pairing mismatch')
    required=[*FIELDS,'Persistence_evidence']
    for row in rows:
        if any(row[f]!=cell(additions[row['inchikey']][f]) for f in required):
            raise ValueError('Ready Biodegradability raw/export mismatch: '+row['inchikey'])
    tables=[(names[1],'scenario_results','inchikey',list(rows[0])),
            (names[1],'current_compounds','inchikey',required),
            (names[2],'compound_audit','inchikey_std',required)]
    checked_integrity=set()
    for filename,table,key,fields in tables:
        with closing(sqlite3.connect((result/filename).resolve().as_uri()+'?mode=ro',uri=True)) as db:
            if filename not in checked_integrity:
                if db.execute('PRAGMA integrity_check').fetchall()!=[('ok',)] or db.execute('PRAGMA foreign_key_check').fetchall():
                    raise ValueError('Database integrity failed: '+filename)
                checked_integrity.add(filename)
            actual=dict((r[0],r[1:]) for r in db.execute('SELECT '+key+','+','.join(map(quote,fields))+' FROM '+table))
            if set(actual)!=set(keys):raise ValueError('Database identity set differs: '+table)
            for row in rows:
                if actual[row['inchikey']]!=tuple(row[f] for f in fields):raise ValueError('CSV/SQLite mismatch: '+table+' '+row['inchikey'])
    samples={}
    for row in rows:
        e=json.loads(row['Persistence_evidence'])['ready_biodegradability']
        categories=[e['status']]
        if e['adi']==0:categories.append('actual_zero_adi')
        if e['assessment_basis']=='experimental_value':categories.append('experimental_assessment')
        for category in categories:
            if category not in samples:
                samples[category]={'inchikey':row['inchikey'],'qsar_inchikey':e['identity']['qsar_inchikey'],
                                   'prediction_raw':e['raw']['Predicted RB activity'],
                                   'assessment_raw':e['raw']['Assessment'],'adi_raw':e['raw']['ADI'],
                                   'adi':e['adi'],'identity_verified':e['identity']['verified'],'raw_export_equal':True}
    return {'publication_figures':figures,'ready_biodegradability':report,'sample_checks':samples,
            'raw_to_export_checked_compounds':len(rows),'csv_sqlite_pairing':'passed','sqlite_integrity':'passed'}


def finalize_delivery(stage):
    """Required final step after matching numerical preparation, before publication."""
    stage=Path(stage)
    fig4=package_fig4(stage)
    sankey=package_sankey(stage)
    verification=validate_delivery(stage)
    with closing(sqlite3.connect(stage/NAMES[2])) as db,db:
        db.execute('INSERT OR REPLACE INTO metadata VALUES (?,?)',('delivery_status','complete'))
    manifest_path=stage/'figure_data/_metadata/scenario_manifest.json'
    manifest=json.loads(manifest_path.read_text())
    manifest.update(delivery_status='complete',verification='CSV/SQLite, raw QSAR identity evidence, Fig4 and Sankey validated.',
                    output_sha256={n:digest(stage/n) for n in NAMES})
    write_json(manifest_path,manifest)
    return {'fig4':fig4,'sankey':sankey,'validation':verification}


def release():
    result=ROOT/'result'
    lock_path=ROOT/'FigureCode/managed_sources.json'
    si_pin=ROOT/'FigureCode/Supplementary/SILevel1Evidence/source.json'
    with update_lock(result), tempfile.TemporaryDirectory(prefix='.evidence-release-',dir=ROOT) as temporary:
        temp=Path(temporary);stage=temp/'result'
        # Independent copies: no writable inode shared with the current results.
        print('Snapshotting current complete result set',flush=True)
        original_hashes=files(result)
        source_lock_bytes=lock_path.read_bytes();si_pin_bytes=si_pin.read_bytes()
        profile=json.loads(source_lock_bytes)
        for item in profile['files'].values():
            if digest(ROOT/item['path'])!=item['sha256']:raise ValueError('Current source lock is stale')
        shutil.copytree(result,stage)
        canonicalise_names(stage)
        for role, spec in profile['files'].items():
            spec['path'] = 'result/' + dict(zip(ROLES, NAMES))[role]
        before_core={p.name:digest(p) for p in result_files(result).values()}
        report={'format':'plastprior-evidence-release-v1','created_at':datetime.now(timezone.utc).isoformat(),
                'implementation_sha256':{n:digest(ROOT/'plastprior'/n) for n in ['evidence_release.py','ready_biodegradability.py','sankey_evidence.py','scenario_export.py']},
                'before_sha256':before_core,'scoring_execution':'not invoked','vega_execution':'not invoked'}
        report['ready_biodegradability']=enrich_current(stage)
        report['invariance']=compare_current(result,stage)
        prior_report=result/'figure_data/_metadata/evidence_release.json'
        if prior_report.exists():
            prior=json.loads(prior_report.read_text())
            report['original_before_sha256']=prior.get('original_before_sha256',prior['before_sha256'])
            report['prior_invariance']=prior['invariance']
        for name,spec in profile['files'].items():spec['sha256']=digest(stage/Path(spec['path']).name)
        report['figure_preparation']=refresh_figure_data(stage,temp,profile)
        print('Verifying immutable original archive tables',flush=True)
        report['immutable_archive']=verify_immutable_tables(result,stage)
        print('Packaging and validating publication evidence',flush=True)
        report['delivery']=finalize_delivery(stage)
        # ED3 embeds file provenance inside its R payload. Refresh only those
        # two metadata members after Dashboard packaging fixes its final hash.
        ed3_meta=stage/'figure_data/_metadata/ExtendedDataFig3'
        final_hashes={n:digest(stage/n) for n in NAMES}
        facts=json.loads((ed3_meta/'preparation.json').read_text())['facts']
        facts['source']=profile;facts['protected_hashes']=final_hashes
        facts_path=temp/'ed3-final-facts.json';write_json(facts_path,facts)
        subprocess.run(['Rscript','-e',
            'a<-commandArgs(TRUE);x<-readRDS(a[1]);f<-jsonlite::fromJSON(a[2],simplifyVector=FALSE);x$config$source<-f$source;x$config$protected_hashes<-f$protected_hashes;saveRDS(x,a[1],version=3)',
            str(stage/'figure_data/ExtendedDataFig3/plot_data.rds'),str(facts_path)],cwd=ROOT,check=True)
        for kind in ['manifest.json','preparation.json']:
            path=ed3_meta/kind;record=json.loads(path.read_text())
            record['facts']=facts;record['source_data']=files(stage/'figure_data/ExtendedDataFig3')
            write_json(path,record)
        # SI source manifests are finalized after Dashboard packaging. Update the
        # embedded fingerprint and its table manifests without changing display cells.
        si_path=stage/'figure_data/SILevel1Evidence/si_payload.json'
        si_payload=json.loads(si_path.read_text())
        si_payload['metadata']['sources']['result/figure_data/_metadata/scenario_manifest.json']=digest(stage/'figure_data/_metadata/scenario_manifest.json')
        write_json(si_path,si_payload)
        for kind in ['manifest.json','preparation.json']:
            path=stage/'figure_data/_metadata/SILevel1Evidence'/kind
            if path.exists():
                record=json.loads(path.read_text());record['source_data']=files(stage/'figure_data/SILevel1Evidence')
                write_json(path,record)
        # These current-data checks are rerun here; historical and imported-asset
        # references retain their old provenance and existing review status.
        from collections import Counter
        csv_rows=read_rows(stage/NAMES[0]);level_counts=Counter(r['Priority_level'] for r in csv_rows)
        for filename in ['verification.json','five_level_validation.json','publication_consistency.json','dashboard_parity_validation.json']:
            path=stage/'figure_data/_metadata'/filename
            record=json.loads(path.read_text())
            record['evidence_refresh']={'previous_csv_sha256':record.get('csv_sha256'),
                                        'report':'result/figure_data/_metadata/evidence_release.json'}
            record['csv_sha256']=profile['files']['publication']['sha256']
            if 'level_counts' in record:
                if record['level_counts'] != [level_counts[str(i)] for i in range(1,6)]:raise ValueError('Level counts changed')
            write_json(path,record)
        for path in (stage/'figure_data/_metadata').glob('*/publication_asset.json'):
            record=json.loads(path.read_text())
            if 'current_csv_sha256' in record:
                record['current_csv_sha256']=profile['files']['publication']['sha256']
                # reference_csv_sha256 remains the imported asset's actual source.
                write_json(path,record)
        # Verify preservation of dependencies, all rendered images and manually edited PPT.
        preserved=[p for p in original_hashes if p.startswith(('figure_data/_dependencies/','figures/')) or p.lower().endswith('.pptx')]
        for p in preserved:
            if digest(stage/p)!=original_hashes[p]:raise ValueError('Protected file changed: '+p)
        report['preserved_files']={p:original_hashes[p] for p in preserved}
        # Preserve pre-existing user attachments without reorganizing unrelated files.
        for p in original_hashes:
            if '/' not in p and p not in (*NAMES, *LEGACY_NAMES) and not p.lower().endswith('.pptx'):
                if digest(stage/p)!=original_hashes[p]:raise ValueError('Root attachment was not preserved: '+p)
        report['after_sha256']={n:digest(stage/n) for n in NAMES}
        report['all_figure_images_and_ppt_byte_identical']=True
        write_json(stage/'figure_data/_metadata/evidence_release.json',report)
        # Preserve historical render/code hashes with explicit transitions, not fake rebuilds.
        receipt_path=stage/'figure_data/_metadata/manifest.json'
        receipt=json.loads(receipt_path.read_text());transitions={}
        for name in NUMERICAL:
            previous=json.loads((result/'figure_data/_metadata'/name/'manifest.json').read_text())
            for path,old in previous.get('code',{}).items():
                if (ROOT/path).exists() and digest(ROOT/path)!=old:
                    transitions[path]={'before_sha256':old,'after_sha256':digest(ROOT/path)}
        receipt['evidence_release']={'code_transitions':transitions,'report':'result/figure_data/_metadata/evidence_release.json'}
        write_json(receipt_path,receipt)
        new_pin=json.loads(si_pin_bytes);new_pin['csv_sha256']=profile['files']['publication']['sha256']
        if files(result)!=original_hashes or lock_path.read_bytes()!=source_lock_bytes or si_pin.read_bytes()!=si_pin_bytes:
            raise ValueError('Current inputs changed during staging; aborting publication')
        def finish():
            write_json(lock_path,profile);write_json(si_pin,new_pin)
            if {n:digest(result/n) for n in NAMES} != report['after_sha256']:
                raise ValueError('Installed files differ from the validated candidate')
            validate_publication_figures(result)
        print('Publishing validated complete directory',flush=True)
        try:
            replace_directory(stage,result,validate=finish)
        except BaseException:
            lock_path.write_bytes(source_lock_bytes);si_pin.write_bytes(si_pin_bytes)
            raise
        print(json.dumps({'report':str(result/'figure_data/_metadata/evidence_release.json'),
                          'invariance':report['invariance'],'sankey':report['delivery']['sankey'],
                          'ready_biodegradability':report['ready_biodegradability']['counts']},indent=2),flush=True)
    return report


if __name__=='__main__':
    release()
