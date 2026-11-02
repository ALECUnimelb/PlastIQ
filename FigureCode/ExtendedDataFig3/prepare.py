"""Prepare current GIC figure tables; official scores and ranking are read-only."""
from pathlib import Path
from fractions import Fraction
from decimal import Decimal, ROUND_HALF_UP, localcontext
import argparse
import hashlib
import json
import sys
import numpy as np
import pandas as pd

ROOT = Path('/Users/ruiwang/Projects/APPs/PlastPrior')
MODULE = ROOT / 'FigureCode/ExtendedDataFig3'
sys.path.insert(0, str(ROOT / 'FigureCode/_shared'))
from managed import verify_sources, sha, write_json

LABELS = {
 'Persistence_score': 'Persistence', 'Bioaccumulation_score': 'Bioaccumulation',
 'Mobility_score': 'Mobility', 'Toxicity_score': 'Toxicity',
 'Exposure_food_contact_score': 'Food contact',
 'Exposure_human_biomonitoring_score': 'Human biomonitoring',
 'Exposure_inventory_score': 'Inventory', 'Exposure_production_score': 'Production',
 'Exposure_patent_score': 'Patents', 'Exposure_literature_score': 'Literature'}
STATUS = ['prohibited_or_phaseout', 'restricted_or_authorisation_required',
 'candidate_or_high_concern', 'monitoring_reporting_or_hazard_classification',
 'inventory_registration_or_use_only', 'not_listed']
PROTECTED = ['PlastPrior_results.csv', 'PlastPrior_results.sqlite', 'PlastPrior_dashboard.sqlite']

def round_ratio(num, den):
    return ((2 * num + den) // (2 * den)).astype(np.int64)

def capture(score, target, budget_pct):
    """Fractional allocation within the boundary tie, independent of GIC status."""
    n = len(score)
    quota = n * float(budget_pct) / 100
    if quota == 0:
        return dict(expected_hits=0., capture_pct=0., precision_pct=0., enrichment=np.nan,
                    quota=0., boundary_score=np.nan, boundary_n=0, boundary_fraction=0.)
    levels, inv, size = np.unique(score, return_inverse=True, return_counts=True)
    hits = np.bincount(inv, weights=target.astype(int), minlength=len(levels))
    levels, size, hits = levels[::-1], size[::-1], hits[::-1]
    before = np.r_[0, np.cumsum(size)[:-1]]
    take = np.clip(quota - before, 0, size)
    weights = take / size
    expected = float(np.dot(weights, hits))
    boundary = int(np.flatnonzero(take > 0)[-1])
    assert abs(float(take.sum()) - quota) < 1e-8
    return dict(expected_hits=expected, capture_pct=100*expected/target.sum(),
                precision_pct=100*expected/quota, enrichment=(expected/target.sum())/(quota/n),
                quota=quota, boundary_score=int(levels[boundary]), boundary_n=int(size[boundary]),
                boundary_fraction=float(weights[boundary]))

def main(stage):
    stage.mkdir(parents=True, exist_ok=True)
    tables = stage/'source_data'; tables.mkdir(exist_ok=True)
    profile = verify_sources()
    protected = {f: sha(ROOT/'result'/f) for f in PROTECTED}
    policy = json.loads((ROOT/'plastprior/scenario_policy.json').read_text())
    five = json.loads((ROOT/'FigureCode/_shared/five_level_policy.json').read_text())
    data = pd.read_csv(ROOT/'result/PlastPrior_results.csv', keep_default_na=True)
    assert len(data) == 15125 and data.inchikey.is_unique
    assert set(data.GIC_regulatory_status) <= set(STATUS)
    hc = ['Persistence_score','Bioaccumulation_score','Mobility_score','Toxicity_score']
    ec = ['Exposure_food_contact_score','Exposure_human_biomonitoring_score',
          'Exposure_inventory_score','Exposure_production_score','Exposure_patent_score','Exposure_literature_score']
    cols = hc+ec
    weights = {**policy['hazard_weights'], **policy['exposure_weights']}
    w = np.array([weights[c] for c in cols], dtype=np.int64)
    maxima = np.array([1 if c in ec[:2] else 2 for c in cols], dtype=np.int64)
    raw = data[cols].fillna(0).to_numpy(float)
    assert np.all(raw >= 0) and np.all(raw <= maxima)
    assert np.all(raw*4 == np.rint(raw*4))
    quarters = (raw*4).astype(np.int64)
    unique, unique_inverse = np.unique(quarters, axis=0, return_inverse=True)
    matrix = np.array(five['level_matrix_L_M_H_vH'])
    def level(h,e):
        return matrix[np.searchsorted(five['cutpoints'],h,side='right'),
                      np.searchsorted(five['cutpoints'],e,side='right')]
    scenarios = []
    def add(sid, label, family, component='', multiplier=None, changes=None, normalize=True, rank_mode='total'):
        vals = [Fraction((changes or {}).get(c,int(w[i]))) for i,c in enumerate(cols)]
        denom = int(np.lcm.reduce([x.denominator for x in vals]))
        ints = np.array([int(x*denom) for x in vals], dtype=np.int64)
        hden = 4*int(np.dot(ints[:4],maxima[:4])) if normalize else 4*denom
        eden = 4*int(np.dot(ints[4:],maxima[4:])) if normalize else 4*denom
        mult = 16 if normalize else 1
        hnum, enum = mult*(quarters[:,:4]@ints[:4]), mult*(quarters[:,4:]@ints[4:])
        h,e = round_ratio(hnum,hden), round_ratio(enum,eden)
        lev = level(h,e)
        score = h if rank_mode=='hazard' else e if rank_mode=='exposure' else h+e
        # Separate Decimal arithmetic verifies every unique vector, covering every observation.
        with localcontext() as ctx:
            ctx.prec = 40
            dh, de = [], []
            for row in unique:
                hs = sum(Decimal(int(row[i]))/4*Decimal(int(ints[i]))/Decimal(denom) for i in range(4))
                es = sum(Decimal(int(row[i]))/4*Decimal(int(ints[i]))/Decimal(denom) for i in range(4,10))
                if normalize:
                    hs = hs * Decimal(16*denom) / Decimal(int(np.dot(ints[:4],maxima[:4])))
                    es = es * Decimal(16*denom) / Decimal(int(np.dot(ints[4:],maxima[4:])))
                dh.append(int(hs.quantize(Decimal(1),rounding=ROUND_HALF_UP)))
                de.append(int(es.quantize(Decimal(1),rounding=ROUND_HALF_UP)))
        assert np.array_equal(h, np.array(dh)[unique_inverse]), sid
        assert np.array_equal(e, np.array(de)[unique_inverse]), sid
        scenarios.append(dict(id=sid,label=label,family=family,component=component,multiplier=multiplier,
                              normalize=normalize,rank_mode=rank_mode,weights=[str(x) for x in vals],
                              h=h,e=e,level=lev,score=score))
    add('baseline','Integrated','reference')
    assert np.array_equal(scenarios[0]['h'],data.Hazard_score)
    assert np.array_equal(scenarios[0]['e'],data.Exposure_score)
    assert np.array_equal(scenarios[0]['score'],data.Priority_score)
    assert np.bincount(scenarios[0]['level'],minlength=6)[1:].tolist()==five['expected_counts']
    add('hazard_only','Hazard only','reference',rank_mode='hazard')
    add('exposure_only','Exposure only','reference',rank_mode='exposure')
    add('no_inventory','Integrated, no inventory','reference',changes={'Exposure_inventory_score':0})
    for c in cols:
        for mult in [Fraction(4,5),Fraction(6,5)]:
            add(c+'_'+str(mult.numerator), LABELS[c]+(' -20%' if mult<1 else ' +20%'),
                'one_at_a_time',c,float(mult),{c:weights[c]*mult})
    targets = {'Prohibition / restriction': data.GIC_regulatory_status.isin(STATUS[:2]).to_numpy(),
               'Including candidate / concern': data.GIC_regulatory_status.isin(STATUS[:3]).to_numpy()}
    baselev = scenarios[0]['level']
    metrics,composition,levels,configs,ties = [],[],[],[],[]
    for s in scenarios:
        configs.append({k:v for k,v in s.items() if k not in ['h','e','level','score']})
        for endpoint,target in targets.items():
            for budget in [1,5,10]:
                metrics.append(dict(scenario=s['id'],label=s['label'],family=s['family'],
                   component=s['component'],multiplier=s['multiplier'],endpoint=endpoint,budget_pct=budget,
                   target_total=int(target.sum()),**capture(s['score'],target,budget)))
            if s['rank_mode']=='total':
                for l in range(1,6):
                    idx=s['level']==l
                    levels.append(dict(scenario=s['id'],endpoint=endpoint,level=l,n=int(idx.sum()),
                      target_n=int(np.sum(idx&target)),target_pct=100*target[idx].mean() if idx.any() else np.nan,
                      capture_pct=100*np.sum(idx&target)/target.sum()))
        if s['family']=='reference':
            for score in sorted(set(s['score']),reverse=True):
                idx=s['score']==score
                ties.append(dict(scenario=s['id'],score=int(score),n=int(idx.sum()),
                                 prohibited_restricted_n=int(targets['Prohibition / restriction'][idx].sum())))
        if s['id']=='baseline':
            for l in range(1,6):
                idx=baselev==l
                for status in STATUS:
                    count=int(np.sum(idx&(data.GIC_regulatory_status.to_numpy()==status)))
                    composition.append(dict(level=l,status=status,n=count,level_n=int(idx.sum()),pct=100*count/idx.sum()))
    metrics=pd.DataFrame(metrics)
    baseline=metrics[metrics.scenario=='baseline'][['endpoint','budget_pct','capture_pct']].rename(columns={'capture_pct':'baseline_capture_pct'})
    metrics=metrics.merge(baseline,on=['endpoint','budget_pct'],validate='many_to_one')
    metrics['delta_capture_pp']=metrics.capture_pct-metrics.baseline_capture_pct
    metrics.to_csv(tables/'capture_metrics.csv',index=False)
    pd.DataFrame(composition).to_csv(tables/'level_gic_composition.csv',index=False)
    pd.DataFrame(levels).to_csv(tables/'level_gic_metrics.csv',index=False)
    pd.DataFrame(ties).to_csv(tables/'score_tie_groups.csv',index=False)
    audit=data[['inchikey','Name','CAS','GIC_regulatory_status',*cols]].copy()
    audit['figure_level']=baselev
    audit['baseline_h']=scenarios[0]['h'];audit['baseline_e']=scenarios[0]['e']
    audit['baseline_total']=scenarios[0]['score']
    audit['hazard_available']=data[hc].notna().sum(axis=1)
    audit['exposure_available']=data[ec].notna().sum(axis=1)
    audit.to_csv(tables/'compound_audit.csv',index=False)
    # Independent direct compound allocation validates every headline capture statistic.
    for s in scenarios:
        for budget in [1,5,10]:
            quota=len(data)*budget/100
            cutoff=sorted(s['score'],reverse=True)[int(np.ceil(quota))-1]
            above=s['score']>cutoff; tied=s['score']==cutoff
            alpha=(quota-above.sum())/tied.sum()
            for endpoint,target in targets.items():
                hit=float(target[above].sum()+alpha*target[tied].sum())
                recorded=metrics[(metrics.scenario==s['id'])&(metrics.endpoint==endpoint)&(metrics.budget_pct==budget)].iloc[0]
                assert abs(hit-recorded.expected_hits)<1e-8
                assert abs(capture(s['score'],target,100)['capture_pct']-100)<1e-8
    assert all(sha(ROOT/'result'/f)==h for f,h in protected.items())
    config=dict(population=len(data),endpoints={k:int(v.sum()) for k,v in targets.items()},
      source=profile,protected_hashes=protected,policy=policy,five_level_policy=five,
      components=cols,component_labels=LABELS,scenarios=configs,
      primary_endpoint='Prohibition / restriction',primary_budget_pct=5,
      budgets=[1,5,10],primary_scale='Each perturbed domain rescaled to theoretical maximum 16 before half-up rounding',
      interpretation='Descriptive association with frozen GIC annotations; not external validation, causal regulation effect, or weight optimization.',
      ties='Equal fractional selection of all compounds in the boundary score tie; expected counts are fractional and do not describe a unique selected list.',
      missingness='Missing scores contribute zero only to sums; raw missingness retained. No compounds excluded.',
      endpoint_definition='Primary: prohibited_or_phaseout OR restricted_or_authorisation_required; secondary additionally includes candidate_or_high_concern.',
      design='Fixed 1/5/10% budgets, +/-20% one-at-a-time weights, and four ranking references. Displayed screening budget: 5%. No optimization against GIC.',
      qa=dict(scenarios=len(scenarios),records_per_scenario=len(data),decimal_score_checks=len(scenarios)*len(data)*2,
              baseline_exact=True,baseline_five_level_counts=five['expected_counts'],excluded_compounds=0,
              independent_capture_checks=len(scenarios)*3*2,source_unchanged=True))
    write_json(stage/'caption_facts.json',config)
    write_json(tables/'scenario_definitions.json',configs)
    print(json.dumps({'stage':str(stage),'endpoints':config['endpoints'],'qa':config['qa']}))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',type=Path)
    main(parser.parse_args().stage.resolve())
