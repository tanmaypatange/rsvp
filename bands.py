"""Statistics used by the reporter.

Every constant here traces to the RSVP doc:
- Z_95 = 1.96, the 95% level of the Wilson band (Confidence Bands page).
- Cell class cut points 30% and 70% (Run Spread page; they follow
  Kumar, 2026).
- Rotation cut points 10% and 90% (Run Spread page; an RSVP decision).
"""

import math
from decimal import Decimal, ROUND_HALF_UP
from itertools import combinations

Z_95 = 1.96

CELL_RARELY_BELOW = 0.30
CELL_FLIPPING_MAX = 0.70

ROTATION_LOW = 0.10
ROTATION_HIGH = 0.90


def wilson(k, n, z=Z_95):
    """95% Wilson interval for k successes in n trials, as (low, high) in 0..1."""
    if n <= 0:
        raise ValueError("a band needs at least one valid run")
    if k < 0 or k > n:
        raise ValueError("successes must be between 0 and the number of runs")
    p = k / n
    z2 = z * z
    denom = 1 + z2 / n
    centre = (p + z2 / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / denom
    low = max(0.0, centre - half)
    high = min(1.0, centre + half)
    if k == 0:
        low = 0.0
    if k == n:
        high = 1.0
    return low, high


def pct(x, places=0):
    """Round a 0..1 value to a percent, half up (so 0.5 rounds to 1)."""
    q = Decimal(1) if places == 0 else Decimal(1).scaleb(-places)
    value = (Decimal(repr(x)) * 100).quantize(q, rounding=ROUND_HALF_UP)
    return int(value) if places == 0 else float(value)


def band_pct(k, n):
    low, high = wilson(k, n)
    return pct(low), pct(high)


def band_width_points(k, n):
    low, high = band_pct(k, n)
    return high - low


def bands_overlap(a, b):
    """a and b are (k, n). True when the two rounded Wilson bands overlap."""
    la, ha = band_pct(*a)
    lb, hb = band_pct(*b)
    return not (ha < lb or hb < la)


def jaccard(a, b):
    a, b = set(a), set(b)
    union = a | b
    if not union:
        return None
    return len(a & b) / len(union)


def mean_pairwise_jaccard(sets):
    """Mean Jaccard over every pair. Pairs where both sets are empty are skipped."""
    values = [j for j in (jaccard(x, y) for x, y in combinations(sets, 2)) if j is not None]
    if not values:
        return None
    return sum(values) / len(values)


def cell_class(k, n):
    if n <= 0:
        return None
    if k == 0:
        return "never"
    if k == n:
        return "always"
    rate = k / n
    if rate < CELL_RARELY_BELOW:
        return "rarely"
    if rate <= CELL_FLIPPING_MAX:
        return "flipping"
    return "mostly"


CELL_CLASSES = ("never", "rarely", "flipping", "mostly", "always")


def rotates(appearances, n):
    """A brand rotates in a cell if it appears in more than 10% and fewer than 90% of valid runs."""
    if n <= 0:
        return False
    share = appearances / n
    return ROTATION_LOW < share < ROTATION_HIGH
