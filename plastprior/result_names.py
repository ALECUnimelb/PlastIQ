"""PlastIQ delivery filenames, with read compatibility for complete legacy sets.

Names are presentation, not schema or dataset identity. Never select individual
files from different naming generations in the same input directory.
"""
from pathlib import Path

ROLES = ('publication', 'analysis', 'dashboard')
NAMES = ('PlastIQ_results.csv', 'PlastIQ_results.sqlite', 'PlastIQ_dashboard.sqlite')
LEGACY_NAMES = ('PlastPrior_results.csv', 'PlastPrior_results.sqlite', 'PlastPrior_dashboard.sqlite')
CURRENT = dict(zip(ROLES, NAMES))
LEGACY = dict(zip(ROLES, LEGACY_NAMES))
DICTIONARY_NAME = 'PlastIQ_data_dictionary.csv'


def result_files(directory, required=ROLES):
    """Resolve one input generation, checking required files before opening SQLite.

``required=()`` supports inspecting partial staged packages; public consumers
request all three files or their actual required role(s).
"""
    directory = Path(directory)
    new = any((directory / n).exists() for n in NAMES)
    old = any((directory / n).exists() for n in LEGACY_NAMES)
    if new and old:
        raise ValueError('Mixed PlastIQ/PlastPrior result filenames: ' + str(directory))
    mapping = LEGACY if old else CURRENT
    paths = {role: directory / name for role, name in mapping.items()}
    for role in required:
        if not paths[role].is_file():
            raise FileNotFoundError('Missing paired result file: ' + str(paths[role]))
    return paths


def result_file(directory, role):
    return result_files(directory, required=(role,))[role]


def canonicalise_names(directory):
    """Rename only unpublished staged files; never rewrite their contents."""
    directory = Path(directory)
    paths = result_files(directory, required=())
    for role, path in paths.items():
        target = directory / CURRENT[role]
        if path.exists() and path != target:
            path.rename(target)
    old = directory / 'PlastPrior_data_dictionary.csv'
    target = directory / DICTIONARY_NAME
    if old.exists():
        if target.exists():
            raise ValueError('Duplicate data dictionaries: ' + str(directory))
        old.rename(target)
