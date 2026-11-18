"""Package prepared source-flow evidence; reject stale or incomplete deliveries."""
from .result_names import result_file
from collections import Counter
from contextlib import closing
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import tempfile
from .figure_evidence import digest, read_rows, prepare as prepare_fig4

FIGURE_ID = 'ExtendedDataFig1a'
FORMAT = 'plastprior-sankey-v1'


def prepare(result):
    result = Path(result)
    csv_hash = digest(result_file(result, 'publication'))
    analysis_hash = digest(result_file(result, 'analysis'))
    folder = result/'figure_data/ExtendedDataFig1'
    meta = result/'figure_data/_metadata/ExtendedDataFig1/preparation.json'
    if not meta.exists(): meta = meta.with_name('manifest.json')
    manifest = json.loads(meta.read_text())
    for name, actual in [('publication',csv_hash), ('analysis',analysis_hash)]:
        if manifest['source']['files'][name]['sha256'] != actual:
            raise ValueError('Sankey source mismatch: ' + name)
    files = dict(nodes='layout/plotted_nodes.csv',edges='layout/plotted_edges.csv',
                 connectors='layout/connector_segments.csv',summary='flow/summary.csv')
    hashes, payload = {}, {}
    def checked(relative):
        path = folder/relative
        actual = digest(path)
        if actual != manifest['source_data'].get(relative):
            raise ValueError('Sankey prepared checksum mismatch: ' + relative)
        hashes[relative] = actual
        return read_rows(path)
    for key, relative in files.items(): payload[key] = checked(relative)
    for key, fields in [('nodes',['node_id','node_value','layer']),
                        ('edges',['source_id','target_id','value','stage','unit'])]:
        rows = checked('flow/'+key+'.csv')
        project = lambda rs: sorted(tuple(r[f] for f in fields) for r in rs)
        if project(rows) != project(payload[key]): raise ValueError('Sankey layout/flow mismatch: '+key)
    nodes = {n['node_id']:n for n in payload['nodes']}
    if len(nodes) != len(payload['nodes']): raise ValueError('Duplicate Sankey node')
    incoming,outgoing = Counter(),Counter()
    seen = set()
    for e in payload['edges']:
        a,b,n = e['source_id'],e['target_id'],int(e['value'])
        if a not in nodes or b not in nodes or n < 0 or (a,b) in seen:
            raise ValueError('Invalid/duplicate Sankey edge')
        seen.add((a,b));outgoing[a] += n;incoming[b] += n
        if int(nodes[b]['layer']) != int(nodes[a]['layer']) + 1: raise ValueError('Invalid Sankey layer direction')
        for prefix, key in [('source',a),('target',b)]:
            lo,hi = float(e[prefix+'_flow_ymin']),float(e[prefix+'_flow_ymax'])
            if not all(math.isfinite(v) for v in (lo,hi)) or lo > hi or lo < float(nodes[key]['ymin'])-1e-9 or hi > float(nodes[key]['ymax'])+1e-9:
                raise ValueError('Sankey ribbon outside node')
    for key,n in nodes.items():
        if max(incoming[key],outgoing[key]) != int(n['node_value']): raise ValueError('Sankey node totals differ: '+key)
        if incoming[key] and outgoing[key] and incoming[key] != outgoing[key]: raise ValueError('Sankey flow not conserved: '+key)
        if not all(math.isfinite(float(n[f])) for f in ['x','ymin','ymax','label_x','label_y']): raise ValueError('Invalid node geometry')
    segments = set()
    for c in payload['connectors']:
        segment = (c['connector_id'],c['segment_index'])
        if c['connector_id'] not in nodes or segment in segments: raise ValueError('Invalid/duplicate connector')
        segments.add(segment)
        if not all(math.isfinite(float(c[f])) for f in ['x','y','xend','yend']): raise ValueError('Invalid connector geometry')
    summary = {r['metric']:int(r['value']) for r in payload['summary']}
    if len(summary) != len(payload['summary']): raise ValueError('Duplicate summary metric')
    with closing(sqlite3.connect((result_file(result, 'analysis')).resolve().as_uri()+'?mode=ro',uri=True)) as db:
        records = db.execute('SELECT count(*) FROM source_records').fetchone()[0]
        resolved = db.execute('SELECT count(DISTINCT record_id) FROM compound_memberships').fetchone()[0]
        compounds = db.execute('SELECT count(*) FROM current_compounds').fetchone()[0]
        eligible = db.execute("SELECT count(*) FROM current_compounds WHERE lower(keep_for_vega) IN ('true','1')").fetchone()[0]
    expected = dict(source_records=records,resolved_records=resolved,unresolved_records=records-resolved,
                    unique_compounds=compounds,collapsed_duplicate_records=resolved-compounds,
                    qsar_eligible_compounds=eligible,qsar_ineligible_compounds=compounds-eligible)
    if summary != expected: raise ValueError('Sankey summary disagrees with analysis archive')
    rows = read_rows(result_file(result, 'publication'))
    if len(rows) != compounds or len({r['inchikey'] for r in rows}) != compounds: raise ValueError('CSV identity count mismatch')
    for layer, expected_total in [(1,records),(2,records),(3,records),(4,records),(5,resolved),(6,compounds)]:
        if sum(int(n['node_value']) for n in nodes.values() if int(n['layer'])==layer) != expected_total:
            raise ValueError('Sankey layer total differs from archive: '+str(layer))
    for key,value in [('dedup:unique_compounds',compounds),('resolution:resolved_records',resolved),('qsar:eligible',eligible)]:
        if key not in nodes or int(nodes[key]['node_value'])!=value:
            raise ValueError('Sankey summary/node mismatch: '+key)
    payload['provenance'] = dict(figure='ExtendedDataFig1',scope='full_import',source_hashes=hashes,
                                 csv_sha256=csv_hash,analysis_sha256=analysis_hash,
                                 figure_run_id=manifest['source']['run_id'])
    return payload


def check_dashboard(db, payload):
    meta = dict(db.execute('SELECT key,value FROM metadata'))
    summary = {r['metric']:int(r['value']) for r in payload['summary']}
    if meta['csv_sha256'] != payload['provenance']['csv_sha256'] or int(meta['row_count']) != summary['unique_compounds']:
        raise ValueError('Dashboard/Sankey pairing mismatch')
    counts = db.execute('SELECT count(*),count(distinct inchikey_std),sum(cast(n_records AS INTEGER)) FROM compound_audit').fetchone()
    eligible = db.execute("SELECT count(*) FROM compound_audit WHERE lower(keep_for_vega) IN ('true','1')").fetchone()[0]
    if counts != (summary['unique_compounds'],summary['unique_compounds'],summary['resolved_records']) or eligible != summary['qsar_eligible_compounds']:
        raise ValueError('Dashboard/Sankey population mismatch')


def package_sankey(result):
    result = Path(result)
    payload = prepare(result)
    encoded = json.dumps(payload,ensure_ascii=False,separators=(',',':'))
    checksum = hashlib.sha256(encoded.encode()).hexdigest()
    target = result_file(result, 'dashboard')
    # Backup detaches hardlinks, so preparation never mutates the live database.
    with tempfile.TemporaryDirectory(prefix='.sankey-',dir=result.parent) as tmp:
        candidate = Path(tmp)/target.name
        with closing(sqlite3.connect(target.resolve().as_uri()+'?mode=ro',uri=True)) as old, closing(sqlite3.connect(candidate)) as db:
            old.backup(db);check_dashboard(db,payload)
            db.execute('CREATE TABLE IF NOT EXISTS publication_figures (figure_id TEXT PRIMARY KEY, format TEXT NOT NULL, csv_sha256 TEXT NOT NULL, payload_sha256 TEXT NOT NULL, payload_json TEXT NOT NULL)')
            db.execute('INSERT OR REPLACE INTO publication_figures VALUES (?,?,?,?,?)',
                       (FIGURE_ID,FORMAT,payload['provenance']['csv_sha256'],checksum,encoded))
            db.execute('INSERT OR REPLACE INTO metadata VALUES (?,?)',('sankey_status','ready'))
            db.commit()
            if db.execute('PRAGMA integrity_check').fetchall() != [('ok',)]: raise ValueError('Sankey database integrity failed')
        candidate.replace(target)
    return {'nodes':len(payload['nodes']),'edges':len(payload['edges']),
            'summary':{r['metric']:int(r['value']) for r in payload['summary']},'payload_sha256':checksum}


def validate_publication_figures(result):
    result = Path(result)
    expected = {FIGURE_ID:(FORMAT,prepare(result)), 'Fig4':('plastprior-level1-composition-v1',prepare_fig4(result))}
    with closing(sqlite3.connect((result_file(result, 'dashboard')).resolve().as_uri()+'?mode=ro',uri=True)) as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE name='publication_figures'").fetchone():
            raise ValueError('Incomplete delivery: publication_figures missing')
        for key,(format_,payload) in expected.items():
            row = db.execute('SELECT format,csv_sha256,payload_sha256,payload_json FROM publication_figures WHERE figure_id=?',(key,)).fetchone()
            if row is None: raise ValueError('Incomplete delivery: missing '+key)
            if row[0] != format_ or row[1] != payload['provenance']['csv_sha256'] or row[2] != hashlib.sha256(row[3].encode()).hexdigest() or json.loads(row[3]) != payload:
                raise ValueError('Invalid publication figure payload: '+key)
        check_dashboard(db,expected[FIGURE_ID][1])
    return {'required_figures':list(expected),'valid':True}
