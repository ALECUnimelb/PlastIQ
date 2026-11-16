"""Manage fixed figure destinations. Approve only after the user accepts a review."""
from pathlib import Path
import argparse
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent/'_shared'))
from managed import MANAGED,approve,refresh_index
from publication import entries
from Supplementary.SILevel1Evidence.run_plot import approve as approve_si, refresh_index as refresh_si_index

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='action',required=True)
    sub.add_parser('index')
    public={row['name']:row['id'] for row in entries()}
    sub.add_parser('approve').add_argument('figure',choices=list(public)+['SILevel1Evidence'],help='Current publication name, not the historical module ID')
    args=parser.parse_args()
    if args.action=='approve':
        if args.figure=='SILevel1Evidence': approve_si()
        else: approve(public[args.figure])
    else:
        refresh_index()
        refresh_si_index()
