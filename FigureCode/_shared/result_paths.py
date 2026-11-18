"""Current result locations and verified relocation of historical provenance.

Original build manifests remain unchanged. The relocation receipt records the
old and new paths/hashes; it never implies that an existing figure was rebuilt.
"""
from functools import lru_cache
from pathlib import Path
import hashlib
import json
from publication import output_name

ROOT = Path(__file__).resolve().parents[2]
RESULT = ROOT / 'result'


@lru_cache(maxsize=1)
def receipt():
    path = RESULT / 'figure_data/_metadata/manifest.json'
    return json.loads(path.read_text()) if path.exists() else {}


def relocated(value, *, record=None):
    """Resolve historical paths through the successive verified storage maps."""
    record = receipt() if record is None else record
    if isinstance(value, dict):
        return {relocated(k, record=record): relocated(v, record=record) for k, v in value.items()}
    if isinstance(value, list):
        return [relocated(v, record=record) for v in value]
    if not isinstance(value, str):
        return value
    absolute = value.startswith(str(ROOT) + '/')
    name = value[len(str(ROOT)) + 1:] if absolute else value
    # Prefer the newest mapping when a historical receipt contains an identity
    # mapping for the same exact path. Otherwise the old self-map stops the chain.
    maps = record.get('brand_rename', {}).get('paths', []) + record.get('storage_migration', {}).get('paths', []) + record.get('layout_cleanup', {}).get('paths', []) + record.get('code_layout', {}).get('paths', [])
    for _ in range(8):
        previous = name
        for old, new in sorted(maps, key=lambda p: len(p[0]), reverse=True):
            if name == old or name.startswith(old + '/'):
                name = new + name[len(old):]
                break
        if name == previous: break
    if name == 'result/figures': name = 'result/figure_data'  # historical data_root only
    return str(ROOT/name) if absolute else name


def resolve(value):
    return ROOT / relocated(str(value))


def figure_paths(figure, state='output'):
    if state not in {'output', 'review'}: raise ValueError('Unknown figure state: '+state)
    return RESULT / 'figures', RESULT / 'figure_data' / figure


def manifest_path(figure):
    return RESULT / 'figure_data/_metadata' / figure / 'manifest.json'


def artifact_path(figure, name):
    if Path(name).suffix in {'.png','.pdf','.xlsx'}:
        return RESULT / 'figures' / output_name(figure, name)
    return manifest_path(figure).parent / name



def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify_digest(path, expected):
    path = resolve(path)
    actual = digest(path)
    if actual == expected: return
    name = str(path.relative_to(ROOT))
    edges = []
    ledgers = [receipt().get('storage_migration', {}).get('code_relocations', {}),
               receipt().get('layout_cleanup', {}).get('code_transitions', {}),
               receipt().get('code_layout', {}).get('code_transitions', {})]
    # Later figure adoptions append transitions without rewriting historical hashes.
    ledgers += [item.get('code_transitions', {}) for item in receipt().get('figure_adoptions', {}).values()]
    ledgers.append(receipt().get('publication_numbering', {}).get('code_transitions', {}))
    ledgers.append(receipt().get('evidence_release', {}).get('code_transitions', {}))
    ledgers.append(receipt().get('brand_rename', {}).get('code_transitions', {}))
    ledgers.append(receipt().get('brand_rename', {}).get('metadata_transitions', {}))
    ledger = ROOT/'audit_archive/workspace_migration_20261026/code_relocations.json'
    if ledger.exists(): ledgers.append(json.loads(ledger.read_text()))
    for ledger in ledgers:
        for original, change in ledger.items():
            if relocated(original) == name:
                edges.append((change['before_sha256'], change['after_sha256']))
    reachable = {expected}
    for _ in range(len(edges)):
        reachable.update(b for a,b in edges if a in reachable)
    assert actual in reachable, (name, 'unrecorded source change')


def verify_code(expected, actual):
    historical = set(receipt().get('code_layout', {}).get('historical_sources', []))
    assert set(expected) <= set(actual) | historical, 'Recorded build source disappeared'
    for name,value in expected.items():
        verify_digest(name,value)
        if name in actual: assert digest(resolve(name)) == actual[name]
    additions = {**receipt().get('storage_migration', {}).get('added_code', {}),
                 **receipt().get('layout_cleanup', {}).get('added_code', {}),
                 **receipt().get('code_layout', {}).get('added_code', {}),
                 **receipt().get('publication_numbering', {}).get('added_code', {}),
                 **receipt().get('brand_rename', {}).get('added_code', {})}
    additions = {relocated(k):v for k,v in additions.items()}
    for name in set(actual)-set(expected):
        assert name in additions, (name, 'unrecorded build source')
        verify_digest(name, additions[name])
