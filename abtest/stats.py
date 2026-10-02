"""A/B test statistics for conversion-rate experiments. Standard library only."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from statistics import NormalDist

_N = NormalDist()


@dataclass(frozen=True)
class ZTestResult:
    rate_a: float
    rate_b: float
    abs_lift: float          # rate_b - rate_a
    rel_lift: float | None   # abs_lift / rate_a, None when the control rate is 0
    z: float
    p_value: float           # two-sided
    ci_low: float            # confidence interval for the absolute difference
    ci_high: float
    significant: bool


def two_proportion_ztest(conv_a: int, n_a: int, conv_b: int, n_b: int, alpha: float = 0.05) -> ZTestResult:
    """Two-sided z-test for a difference in conversion rates (B minus A).

    The test statistic uses the pooled rate, because under the null both groups share one rate.
    The confidence interval uses the unpooled standard error, because it describes the observed difference.
    """
    if not (0 <= conv_a <= n_a and 0 <= conv_b <= n_b and n_a > 0 and n_b > 0):
        raise ValueError("conversions must be between 0 and the group size, and groups must be non-empty")
    if not 0 < alpha < 1:
        raise ValueError("alpha must be between 0 and 1")

    pa, pb = conv_a / n_a, conv_b / n_b
    diff = pb - pa
    pooled = (conv_a + conv_b) / (n_a + n_b)
    se_pooled = math.sqrt(pooled * (1 - pooled) * (1 / n_a + 1 / n_b))
    if se_pooled == 0:  # nobody (or everybody) converted: no evidence either way
        z, p = 0.0, 1.0
    else:
        z = diff / se_pooled
        p = 2 * (1 - _N.cdf(abs(z)))

    se = math.sqrt(pa * (1 - pa) / n_a + pb * (1 - pb) / n_b)
    crit = _N.inv_cdf(1 - alpha / 2)
    return ZTestResult(
        rate_a=pa,
        rate_b=pb,
        abs_lift=diff,
        rel_lift=None if pa == 0 else diff / pa,
        z=z,
        p_value=p,
        ci_low=diff - crit * se,
        ci_high=diff + crit * se,
        significant=p < alpha,
    )


def sample_size_per_group(baseline: float, mde_abs: float, alpha: float = 0.05, power: float = 0.8) -> int:
    """Visitors needed in each group to detect an absolute lift of `mde_abs` over `baseline`
    with a two-sided test at the given significance level and power."""
    p1, p2 = baseline, baseline + mde_abs
    if not (0 < p1 < 1 and 0 < p2 < 1):
        raise ValueError("baseline and baseline + mde must both be between 0 and 1")
    if mde_abs == 0:
        raise ValueError("the minimum detectable effect cannot be zero")
    z_alpha = _N.inv_cdf(1 - alpha / 2)
    z_beta = _N.inv_cdf(power)
    p_bar = (p1 + p2) / 2
    numerator = (z_alpha * math.sqrt(2 * p_bar * (1 - p_bar)) + z_beta * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
    return math.ceil(numerator / mde_abs**2)


def sample_ratio_mismatch(n_a: int, n_b: int, expected_a: float = 0.5) -> float:
    """p-value for 'the traffic split is what we designed'. A very small value (below 0.001 is the
    usual alarm) means assignment or logging is broken, and the experiment result cannot be trusted."""
    n = n_a + n_b
    z = (n_a - n * expected_a) / math.sqrt(n * expected_a * (1 - expected_a))
    return 2 * (1 - _N.cdf(abs(z)))


def peeking_false_positive_rate(
    trials: int = 2000, looks: int = 10, per_look: int = 200, rate: float = 0.10, alpha: float = 0.05, seed: int = 1
) -> float:
    """Simulate A/A tests (no real difference) and stop at the first look that is 'significant'.
    With one look this is close to alpha. With many looks it is far higher."""
    rng = random.Random(seed)
    hits = 0
    for _ in range(trials):
        ca = cb = na = nb = 0
        for _ in range(looks):
            ca += rng.binomialvariate(per_look, rate)
            cb += rng.binomialvariate(per_look, rate)
            na += per_look
            nb += per_look
            if two_proportion_ztest(ca, na, cb, nb, alpha).significant:
                hits += 1
                break
    return hits / trials
