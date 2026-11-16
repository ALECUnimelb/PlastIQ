"""Current PBMT score mapping; source evidence and prediction thresholds stay intact."""
from decimal import Decimal, InvalidOperation


MAPPING_VERSION = 'pbmt-three-level-v1'
SCORE_MAP = {Decimal('0'): 0, Decimal('0.25'): 1, Decimal('0.5'): 1,
             Decimal('1'): 1, Decimal('2'): 2}


def three_level_hazard_score(value):
    """Map an eligible source score, never a physical prediction or ADI value.

    Missing evidence stays missing. Unknown scores fail instead of being rounded
    or silently treated as zero. The caller retains source-selection eligibility.
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, bool):
        raise ValueError('Boolean values are not PBMT scores.')
    try:
        numeric = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError('Invalid PBMT source score.') from exc
    if not numeric.is_finite() or numeric not in SCORE_MAP:
        raise ValueError('PBMT source score must be 0, 0.25, 0.5, 1, 2 or missing.')
    return SCORE_MAP[numeric]


def mapped_hazard_fields(record, fields):
    """Return current scores plus original selected scores without mutating input.

    *_original is the selected pre-mapping component, not necessarily PlastChem.
    Source-native PlastChem values remain in the untouched detailed evidence.
    Re-scoring a mapped record preserves its first original value and rejects
    contradictions between that value and its recorded current component.
    """
    output = {}
    for field in fields:
        if field not in record:
            raise ValueError('Missing base score column: ' + field)
        original_field = field + '_original'
        original = record.get(original_field, record[field])
        mapped = three_level_hazard_score(original)
        if original_field in record:
            current = record[field]
            current_mapped = three_level_hazard_score(current)
            if current_mapped != mapped or (mapped is not None and Decimal(str(current)) != mapped):
                raise ValueError('Mapped PBMT score disagrees with original: ' + field)
        output[field] = mapped
        output[original_field] = original
    return output
