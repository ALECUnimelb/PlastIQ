"""Verified Fig. 4 evidence for browser exports; never infer or rescore annotations."""
from collections import Counter
from contextlib import closing
import csv
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read_rows(path):
    with path.open(newline='', encoding='utf-8') as stream:
        return list(csv.DictReader(stream))


def prepare(result, publication=None):
    result = Path(result)
    publication = Path(publication) if publication is not None else result / 'PlastPrior_results.csv'
    csv_hash = digest(publication)
    manifest_path = result / 'figure_data/_metadata/Fig4/preparation.json'
    if not manifest_path.exists():
        manifest_path = manifest_path.with_name('manifest.json')
    manifest = json.loads(manifest_path.read_text())
    if manifest['source']['files']['publication']['sha256'] != csv_hash:
        raise ValueError('Fig. 4 belongs to a different publication CSV.')
    source = result / 'figure_data/Fig4'
    required_files = {'compound_membership.csv', 'use_counts.csv', 'structure_counts.csv', 'reg_counts.csv'}
    if not required_files <= manifest['source_data'].keys():
        raise ValueError('Incomplete Fig. 4 source checksums.')
    hashes = {}
    for filename, expected in manifest['source_data'].items():
        path = (source / filename).resolve()
        if not path.is_relative_to(source.resolve()) or digest(path) != expected:
            raise ValueError('Fig. 4 source checksum mismatch: ' + filename)
        hashes[filename] = expected
    members = read_rows(source / 'compound_membership.csv')
    publication_rows = read_rows(publication)
    all_ids = [r['inchikey'] for r in publication_rows]
    cohort = {r['inchikey']: r for r in publication_rows if float(r['Hazard_score']) >= 12 and float(r['Exposure_score']) >= 12}
    if len(set(all_ids)) != len(all_ids) or len(members) != len(cohort) or {r['inchikey'] for r in members} != set(cohort):
        raise ValueError('Fig. 4 membership differs from the publication baseline Level 1 cohort.')
    for member in members:
        for field in ['Name', 'CAS', 'SMILES', 'Hazard_score', 'Exposure_score', 'Priority_score', 'Priority_rank', 'Top_n_selected', 'GIC_regulatory_status']:
            left, right = member[field], cohort[member['inchikey']][field]
            if field == 'Top_n_selected':
                left, right = left.lower(), right.lower()
            if left != right:
                raise ValueError('Fig. 4 member differs from publication: ' + field)
        if member['Figure_priority_level'] != '1':
            raise ValueError('Invalid figure level.')
    payload = {'members': members}
    for key, field in [('use', 'primary_use'), ('structure', 'structure_group'), ('reg', 'GIC_regulatory_status')]:
        rows = read_rows(source / (key + '_counts.csv'))
        counts = Counter(m[field] for m in members)
        if len(rows) != len(counts) or len({r['category'] for r in rows}) != len(counts) or set(counts) != {r['category'] for r in rows}:
            raise ValueError('Unexpected Fig. 4 categories: ' + key)
        if any(not r['label'] or int(r['n']) != counts[r['category']] for r in rows):
            raise ValueError('Fig. 4 counts differ from member annotations: ' + key)
        payload[key] = rows
    payload['provenance'] = {'figure': 'Fig4', 'scope': 'article_baseline_level1', 'population': len(publication_rows),
                             'csv_sha256': csv_hash, 'source_hashes': hashes}
    return payload


def add_fig4(db, publication, source=None, *, required=False):
    """Attach matching prepared evidence to an unpublished database connection.

    New datasets without matching prepared annotations remain valid exports, but
    explicitly record why Fig. 4 is unavailable. Never reuse a stale cohort.
    """
    source = Path(source) if source is not None else Path(__file__).resolve().parents[1] / 'result'
    manifest = source / 'figure_data/_metadata/Fig4/preparation.json'
    if not manifest.exists():
        manifest = manifest.with_name('manifest.json')
    reason = None
    if not manifest.exists():
        reason = 'Fig. 4 annotations have not been prepared.'
    elif json.loads(manifest.read_text())['source']['files']['publication']['sha256'] != digest(Path(publication)):
        reason = 'Prepare Fig. 4 annotations for this publication CSV before packaging.'
    if reason:
        if required:
            raise ValueError(reason)
        if db.execute("SELECT 1 FROM sqlite_master WHERE name='publication_figures'").fetchone():
            db.execute("DELETE FROM publication_figures WHERE figure_id='Fig4'")
        db.execute('INSERT OR REPLACE INTO metadata VALUES (?,?)', ('fig4_status', reason))
        return {'status': 'unavailable', 'reason': reason}
    payload = prepare(source, publication)
    metadata = dict(db.execute('SELECT key,value FROM metadata'))
    if metadata['csv_sha256'] != payload['provenance']['csv_sha256'] or int(metadata['row_count']) != payload['provenance']['population']:
        raise ValueError('Dashboard and Fig. 4 CSV do not match.')
    encoded = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
    db.execute('CREATE TABLE IF NOT EXISTS publication_figures (figure_id TEXT PRIMARY KEY, format TEXT NOT NULL, csv_sha256 TEXT NOT NULL, payload_sha256 TEXT NOT NULL, payload_json TEXT NOT NULL)')
    db.execute('INSERT OR REPLACE INTO publication_figures VALUES (?,?,?,?,?)',
               ('Fig4', 'plastprior-level1-composition-v1', metadata['csv_sha256'], hashlib.sha256(encoded.encode()).hexdigest(), encoded))
    db.execute('INSERT OR REPLACE INTO metadata VALUES (?,?)', ('fig4_status', 'ready'))
    return {'status': 'ready', 'members': len(payload['members'])}


def package_fig4(result):
    """Modify only a staging directory. Break hardlinks before changing SQLite."""
    result = Path(result)
    target = result / 'PlastPrior_dashboard.sqlite'
    with tempfile.TemporaryDirectory(prefix='.fig4-', dir=result.parent) as temporary:
        candidate = Path(temporary) / target.name
        with closing(sqlite3.connect(target.resolve().as_uri() + '?mode=ro', uri=True)) as old:
            with closing(sqlite3.connect(candidate)) as db:
                old.backup(db)
                report = add_fig4(db, result / 'PlastPrior_results.csv', result, required=True)
                db.commit()
                for (table,) in old.execute("SELECT name FROM sqlite_master WHERE type='table'"):
                    quoted = '"' + table.replace('"', '""') + '"'
                    condition = " WHERE figure_id != 'Fig4' ORDER BY figure_id" if table == 'publication_figures' else (" WHERE key != 'fig4_status' ORDER BY key" if table == 'metadata' else '')
                    left = old.execute('SELECT * FROM ' + quoted + condition)
                    right = db.execute('SELECT * FROM ' + quoted + condition)
                    while True:
                        a, b = left.fetchmany(256), right.fetchmany(256)
                        if a != b:
                            raise ValueError('Existing data changed: ' + table)
                        if not a:
                            break
                if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise ValueError('Fig. 4 database integrity failed.')
        candidate.replace(target)
    return report


def refresh_fig4(result):
    """Publish existing prepared annotations by coordinated result replacement."""
    from .result_storage import update_lock, replace_directory, validate_destination
    import os
    result = validate_destination(result)
    with update_lock(result), tempfile.TemporaryDirectory(prefix='.fig4-package-', dir=result.parent) as temporary:
        stage = Path(temporary) / 'result'
        shutil.copytree(result, stage, copy_function=os.link)
        report = package_fig4(stage)
        replace_directory(stage, result)
    return report


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('result', type=Path)
    args = parser.parse_args()
    print(json.dumps(refresh_fig4(args.result), indent=2))
