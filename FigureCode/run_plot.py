"""Render by current publication filename, e.g. --figure Fig3 or ExtendedDataFig6."""
from pathlib import Path
import argparse
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'FigureCode/_shared'))
from publication import entries, publish_asset

if __name__ == '__main__':
    rows = entries()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--figure', required=True, choices=[r['name'] for r in rows])
    args = parser.parse_args()
    row = next(r for r in rows if r['name'] == args.figure)
    if row.get('asset'):
        publish_asset(row['id'])
    else:
        subprocess.run([sys.executable, str(ROOT/'FigureCode'/row['id']/'run_plot.py')], cwd=ROOT, check=True)
