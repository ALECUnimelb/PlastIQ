"""Three-level policy at the scoring boundary; source-native evidence is immutable."""
from copy import deepcopy
from decimal import Decimal
import json
import unittest

import pandas as pd

from plastprior.hazard import (
    PERSISTENCE_VEGA_COLUMNS, _compute_vega_p,
    _lrtp_ratio_to_mobility_score, _opera_logkoc_to_mobility_score,
)
from plastprior.hazard_bt import _fish_lc50_to_score_mg_l, _logbcf_to_bioaccum_score
from plastprior.hazard_score_mapping import three_level_hazard_score
from plastprior.scoring_scenarios import (
    COMPONENT_MAXIMA, EXPOSURE_WEIGHTS, HAZARD_WEIGHTS, default_policy,
    score_population, three_level_policy, validate_policy,
)


class ThreeLevelTests(unittest.TestCase):
    def record(self, **values):
        return {**dict.fromkeys(COMPONENT_MAXIMA, 0), 'inchikey': 'A', **values}

    def test_source_mapping_missing_and_invalid_values(self):
        for source, expected in [(0, 0), ('.25', 1), ('0.50', 1), (1, 1), (2, 2),
                                 (None, None), ('', None), ('  ', None)]:
            with self.subTest(source=source):
                self.assertEqual(three_level_hazard_score(source), expected)
        for source in [-1, .75, 1.5, 3, True, False, 'bad', float('nan'), float('inf')]:
            with self.subTest(source=source), self.assertRaises(ValueError):
                three_level_hazard_score(source)

    def test_physical_prediction_boundaries_and_unchanged_source_scores(self):
        cases = [
            (_logbcf_to_bioaccum_score, [(1.999, 0), (2, 1), (2.999, 1), (3, 1), (3.6999, 1), (3.7, 2)]),
            (_opera_logkoc_to_mobility_score, [(1.999, 2), (2, 1), (2.999, 1), (3, 1), (3.999, 1), (4, 0)]),
            (_lrtp_ratio_to_mobility_score, [(0, 0), (.2499, 0), (.25, 1), (.4999, 1), (.5, 1), (.9999, 1), (1, 2)]),
            (_fish_lc50_to_score_mg_l, [(1, 2), (1.0001, 1), (10, 1), (10.0001, 1), (100, 1), (100.0001, 0)]),
        ]
        for function, boundaries in cases:
            for value, expected in boundaries:
                with self.subTest(function=function.__name__, value=value):
                    self.assertEqual(three_level_hazard_score(function(value)), expected)
        # Historical reconstruction still has its original intermediate scores.
        self.assertEqual(_logbcf_to_bioaccum_score(2), .5)
        self.assertEqual(_lrtp_ratio_to_mobility_score(.25), .5)

    def test_persistence_and_adi_gate(self):
        assessment, adi = PERSISTENCE_VEGA_COLUMNS['water']
        for label, expected in [('nP', 0), ('nP/P', 1), ('P/vP', 1), ('vP', 2)]:
            score, _ = _compute_vega_p(pd.Series({assessment: label, adi: .5}))
            self.assertEqual(three_level_hazard_score(score), expected)
        for value in [.4999, None]:
            score, _ = _compute_vega_p(pd.Series({assessment: 'vP', adi: value}))
            self.assertIsNone(three_level_hazard_score(score))

    def test_original_evidence_selection_and_exposure_unchanged(self):
        evidence = json.dumps({'curated_db': {'selected': {'score': .25}},
                               'final_selection': {'selected': {'score': 0}}})
        row = self.record(Persistence_score=0, Toxicity_score='.25', Mobility_score='.5',
                          Bioaccumulation_score=2, Aquatic_M_score='.5', LRTP_M_score=0,
                          Persistence_evidence=evidence, Persistence_score_basis='independent',
                          Exposure_patent_score='.5')
        original = deepcopy(row)
        result = score_population([row], three_level_policy())[0]
        self.assertEqual(row, original)
        self.assertEqual(result['Persistence_evidence'], evidence)
        self.assertEqual(result['Persistence_score_basis'], 'independent')
        self.assertEqual(result['Persistence_score'], 0)  # Curated positive cannot override independent zero.
        self.assertEqual(result['Toxicity_score_original'], '.25')
        self.assertEqual(result['Toxicity_score'], 1)
        self.assertEqual(result['Aquatic_M_score'], 1)
        self.assertEqual(result['Aquatic_M_score_original'], '.5')
        self.assertEqual(result['LRTP_M_score'], 0)
        self.assertEqual(result['Hazard_score'], 8)
        for field in EXPOSURE_WEIGHTS:
            self.assertEqual(result[field], original[field])
        self.assertEqual(result['Exposure_score'], 1)
        self.assertEqual(score_population([result], three_level_policy())[0], result)

    def test_mapping_precedes_weighting_and_preserves_rounding(self):
        row = self.record(Persistence_score='.25', Exposure_production_score='.5')
        result = score_population([row], three_level_policy())[0]
        self.assertEqual(Decimal(result['Hazard_score_raw']), 2)
        self.assertEqual(Decimal(result['Exposure_score_raw']), Decimal('.5'))
        self.assertEqual((result['Hazard_score'], result['Exposure_score'], result['Priority_score']), (2, 1, 3))
        contributions = json.loads(result['Hazard_weighted_contributions'])
        self.assertEqual(Decimal(contributions['Persistence_score']), 2)
        policy = three_level_policy()
        policy['hazard_weights']['Persistence_score'] = '0.5'
        weighted = score_population([row], policy)[0]
        self.assertEqual(Decimal(weighted['Hazard_score_raw']), Decimal('.5'))
        self.assertEqual(weighted['Hazard_score'], 1)

    def test_missing_stays_missing_and_unranked(self):
        row = self.record(**dict.fromkeys(COMPONENT_MAXIMA, None))
        result = score_population([row], three_level_policy())[0]
        for field in HAZARD_WEIGHTS:
            self.assertIsNone(result[field])
            self.assertIsNone(result[field + '_original'])
        self.assertIsNone(result['Priority_rank'])
        self.assertIsNone(result['Priority_level'])

    def test_mapped_ties_change_ranking_and_top_n_consistently(self):
        rows = [self.record(inchikey=key, Persistence_score=value)
                for key, value in [('A', '.25'), ('B', '.5'), ('C', 1), ('D', 0)]]
        result = score_population(rows, {**three_level_policy(), 'top_n': 1})
        self.assertEqual([r['Priority_rank'] for r in result], [1, 1, 1, 4])
        self.assertEqual([r['Top_n_selected'] for r in result], [True, True, True, False])

    def test_explicit_policy_and_original_consistency(self):
        row = self.record(Persistence_score='.25')
        before = default_policy()
        new = three_level_policy()
        validate_policy(new)
        self.assertEqual(default_policy(), before)
        self.assertNotIn('hazard_score_mapping', before)
        self.assertEqual(score_population([row], before)[0]['Hazard_score'], 1)
        mapped = score_population([row], new)[0]
        with self.assertRaisesRegex(ValueError, 'legacy policy'):
            score_population([mapped], before)
        with self.assertRaisesRegex(ValueError, 'disagrees with original'):
            score_population([{**mapped, 'Persistence_score': 0}], new)
        with self.assertRaisesRegex(ValueError, 'disagrees with original'):
            score_population([{**mapped, 'Persistence_score': '.5'}], new)
        with self.assertRaises(ValueError):
            validate_policy({**new, 'hazard_score_mapping': 'unknown'})
        with self.assertRaises(ValueError):
            validate_policy({**new, 'policy_version': before['policy_version']})
        with self.assertRaises(ValueError):
            validate_policy({k: v for k, v in new.items() if k != 'hazard_score_mapping'})


if __name__ == '__main__':
    unittest.main()
