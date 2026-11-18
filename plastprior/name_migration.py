"""Byte-preserving migration of the current delivery to PlastIQ filenames.

This is storage maintenance, not an export, evidence refresh or figure build.
Call only after readers have stopped, with the pre-change code fingerprint map.
"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import tempfile

from .result_names import CURRENT, LEGACY, NAMES, result_files, canonicalise_names
from .result_storage import replace_directory, sha, update_lock

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = 'figure_data/_metadata/manifest.json'
SCENARIO = 'figure_data/_metadata/scenario_manifest.json'
REPORT = 'figure_data/_metadata/brand_rename.json'
SOURCE_LOCK = 'FigureCode/managed_sources.json'


def inventory(directory):
    return {str(p.relative_to(directory)): sha(p)
            for p in sorted(Path(directory).rglob('*')) if p.is_file()}


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()


def detached_write(path, content):
    """Replace the directory entry, never write through a staging hard link."""
    path = Path(path)
    temporary = path.with_name('.' + path.name + '.rename-tmp')
    try:
        temporary.write_bytes(content)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def migrate(*, code_before, root=ROOT, expected_before=None, validate=None):
    root = Path(root).resolve()
    result = root / 'result'
    if validate is None:
        from .evidence_release import validate_delivery
        validate = validate_delivery
    with update_lock(result):
        paths = result_files(result)
        if all(p.name == CURRENT[role] for role, p in paths.items()):
            raise ValueError('Current delivery already uses PlastIQ filenames; no migration needed.')
        before = inventory(result)
        if expected_before is not None and before != expected_before:
            raise ValueError('Result files changed since the reviewed migration baseline.')
        lock_path = root / SOURCE_LOCK
        old_lock = lock_path.read_bytes()
        profile = json.loads(old_lock)
        for role, spec in profile['files'].items():
            if spec['path'] != 'result/' + LEGACY[role] or spec['sha256'] != before[LEGACY[role]]:
                raise ValueError('Current source lock does not match the migration input: ' + role)
            spec['path'] = 'result/' + CURRENT[role]
        new_lock = encoded(profile)
        aliases = dict(zip(LEGACY.values(), NAMES))
        mappings = [['result/' + old, 'result/' + new] for old, new in aliases.items()]
        if 'PlastPrior.ipynb' in code_before and (root/'PlastIQ.ipynb').exists():
            mappings.append(['PlastPrior.ipynb', 'PlastIQ.ipynb'])
        code_paths = dict(mappings)
        transitions = {}
        for name, old_hash in code_before.items():
            target = root / code_paths.get(name, name)
            if not target.is_file():
                continue
            new_hash = sha(target)
            if name == SOURCE_LOCK:
                import hashlib
                new_hash = hashlib.sha256(new_lock).hexdigest()
            if new_hash != old_hash:
                transitions[name] = {'before_sha256': old_hash, 'after_sha256': new_hash}
        with tempfile.TemporaryDirectory(prefix='.result-name-', dir=root) as temporary:
            stage = Path(temporary) / 'result'
            # Untouched files can share read-only inodes; all metadata writes detach.
            shutil.copytree(result, stage, copy_function=os.link)
            canonicalise_names(stage)
            scenario = json.loads((stage/SCENARIO).read_text())
            expected_output = {old: before[old] for old in LEGACY.values()}
            if scenario['output_sha256'] != expected_output:
                raise ValueError('Scenario manifest output hashes do not match the current files.')
            scenario['output_sha256'] = {aliases[n]: h for n, h in expected_output.items()}
            detached_write(stage/SCENARIO, encoded(scenario))
            receipt = json.loads((stage/RECEIPT).read_text())
            receipt['brand_rename'] = {
                'paths': mappings, 'code_transitions': transitions,
                'added_code': {name: sha(root/name) for name in ['plastprior/result_names.py']
                               if (root/name).is_file() and name not in code_before},
                'metadata_transitions': {'result/' + SCENARIO: {
                    'before_sha256': before[SCENARIO], 'after_sha256': sha(stage/SCENARIO),
                    'change': 'Output filename keys only; original source names and hashes retained.'}},
                'report': 'result/' + REPORT,
            }
            detached_write(stage/RECEIPT, encoded(receipt))
            # Check the actual figure path resolver before installation. Legacy
            # imported assets with an already different dataset stay unresolved.
            import sys
            sys.path.insert(0, str(ROOT/'FigureCode/_shared'))
            from result_paths import relocated
            old_profile = json.loads(old_lock)
            for prepared in (stage/'figure_data/_metadata').glob('*/preparation.json'):
                source = json.loads(prepared.read_text())['source']['files']
                if source == old_profile['files'] and relocated(source, record=receipt) != profile['files']:
                    raise ValueError('Figure path migration failed before install: ' + prepared.parent.name)
            # Exact byte checks include all tables, R payloads, dependencies,
            # imported images, manual PPT edits and unrelated user attachments.
            expected = {aliases.get(n, n): h for n, h in before.items()}
            for name in (RECEIPT, SCENARIO):
                expected[name] = sha(stage/name)
            if inventory(stage) != expected:
                raise ValueError('Filename migration changed a protected file or its inventory.')
            verification = validate(stage)
            report = {
                'format': 'plastiq-name-migration-v1',
                'created_at': datetime.now(timezone.utc).isoformat(),
                'paths': mappings,
                'current_files': {n: sha(stage/n) for n in NAMES},
                'preserved_files': {n: h for n, h in expected.items() if n not in (RECEIPT, SCENARIO)},
                'metadata_only_changes': [RECEIPT, SCENARIO],
                'scoring_execution': 'not invoked', 'figure_preparation': 'not invoked',
                'rendering': 'not invoked', 'validation': verification,
                'existing_limitations': [
                    'Imported manuscript assets retain their original reference CSV hash and review status.',
                    'The prior full figure check stops on the imported Fig1 reference CSV mismatch.'
                ],
            }
            detached_write(stage/REPORT, encoded(report))
            expected[REPORT] = sha(stage/REPORT)
            if inventory(result) != before or lock_path.read_bytes() != old_lock:
                raise ValueError('Live inputs changed during migration staging.')

            def finish():
                detached_write(lock_path, new_lock)
                if inventory(result) != expected:
                    raise ValueError('Installed result differs from the validated migration.')
                validate(result)

            try:
                replace_directory(stage, result, validate=finish)
            except BaseException:
                if lock_path.read_bytes() != old_lock:
                    detached_write(lock_path, old_lock)
                raise
            return report
