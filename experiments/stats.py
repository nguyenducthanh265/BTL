"""Statistics for win rates."""
from math import sqrt

Z_95 = 1.96


def wilson_interval(successes, trials, z=Z_95):
    """95% Wilson score interval, reliable near 0 and 1 and with few games."""
    if trials == 0:
        return (0.0, 1.0)
    p = successes / trials
    denominator = 1 + z * z / trials
    centre = (p + z * z / (2 * trials)) / denominator
    margin = z * sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / denominator
    return (max(0.0, centre - margin), min(1.0, centre + margin))
