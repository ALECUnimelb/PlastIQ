"""One publication order; stable IDs continue to identify code and evidence."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]


def entries():
    rows = json.loads((ROOT/'FigureCode/publication_order.json').read_text())['figures']
    for key in ('id', 'name', 'label'):
        if len({r[key] for r in rows}) != len(rows):
            raise ValueError('Duplicate publication '+key)
    return rows


def entry(figure):
    return next((row for row in entries() if row['id'] == figure), None)


def output_name(figure, filename):
    """Map build filenames once, never recursively through another figure ID."""
    row = entry(figure)
    path = Path(filename)
    if row and path.stem == figure and path.suffix in {'.png', '.pdf'}:
        return row['name']+path.suffix
    return filename


def asset_path(figure, result=None):
    return (result or ROOT/'result')/'figure_data/_metadata'/figure/'publication_asset.json'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify_asset(figure, result=None):
    result = result or ROOT/'result'
    row = entry(figure)
    assert row and row.get('asset'), figure
    record = json.loads(asset_path(figure, result).read_text())
    assert record['figure'] == figure
    assert record['status'] in {'review', 'approved'}
    assert set(record['outputs']) == {figure+'.png'}, (figure, 'unexpected raster exports')
    assert sha(result/'PlastPrior_results.csv') == record['reference_csv_sha256'], (figure, 'dataset changed; review imported figure')
    source = result/record['source_asset']
    assert sha(source) == record['source_sha256'], (figure, 'changed imported source')
    for name, digest in record['outputs'].items():
        assert sha(result/'figures'/output_name(figure, name)) == digest, (figure, name)
    # Retained numerical evidence is not reinterpreted as the source of the raster.
    for name, digest in record.get('retained_data', {}).items():
        assert sha(result/'figure_data'/figure/name) == digest, (figure, 'changed evidence', name)
    for name, digest in record.get('retained_metadata', {}).items():
        assert sha(result/'figure_data/_metadata'/figure/name) == digest, (figure, 'changed historical metadata', name)
    return record


def publish_asset(figure):
    """Restore the imported manuscript image, without rescoring or recapturing."""
    import os
    import shutil
    import sys
    import tempfile
    from PIL import Image
    sys.path.insert(0, str(ROOT))
    from plastprior.result_storage import update_lock, replace_directory
    result = ROOT/'result'
    record = json.loads(asset_path(figure).read_text())
    source = result/record['source_asset']
    if sha(source) != record['source_sha256']:
        raise ValueError('Imported source changed: '+figure)
    with update_lock(result), tempfile.TemporaryDirectory(prefix='.publication-asset-', dir=ROOT) as temp:
        stage = Path(temp)/'result'
        shutil.copytree(result, stage, copy_function=os.link)
        target = stage/'figures'/output_name(figure, figure+'.png')
        target.unlink(missing_ok=True)
        if source.suffix.lower() == '.png':
            shutil.copy2(source, target)
        else:
            with Image.open(source) as im:
                im.convert('RGB').save(target)
        assert sha(target) == record['outputs'][figure+'.png'], 'Raster conversion changed'
        verify_asset(figure, stage)
        replace_directory(stage, result)
    print(f'{entry(figure)["label"]}: {target.name} (imported manuscript asset)')
