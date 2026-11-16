"""Prepare the current figure data together, without rendering or rescoring."""
from pathlib import Path
import argparse
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent/'_shared'))
from preparation import CURRENT, FROZEN, prepare
from publication import entry

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    numerical=tuple(n for n in CURRENT+FROZEN if not (entry(n) or {}).get('asset'))
    parser.add_argument('--figures',nargs='+',choices=numerical,default=tuple(n for n in CURRENT if n in numerical),
                        help='Stable internal IDs, not publication numbers. Imported manuscript rasters have no numerical preparation.')
    parser.add_argument('--check',action='store_true',help='Check against current tables in temporary storage; do not publish data.')
    args=parser.parse_args()
    prepare(args.figures,check_existing=args.check,install=not args.check)
