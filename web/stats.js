// The same statistics as abtest/stats.py, for the browser. No dependencies.
// Both implementations are tested against tests/cases.json.

// Complementary error function, Abramowitz & Stegun 7.1.26 (absolute error below 1.5e-7).
function erfc(x) {
  const z = Math.abs(x);
  const t = 1 / (1 + 0.3275911 * z);
  const poly = t * (0.254829592 + t * (-0.284496736 + t * (1.421413741 + t * (-1.453152027 + t * 1.061405429))));
  const r = poly * Math.exp(-z * z);
  return x >= 0 ? r : 2 - r;
}

export const normCdf = (x) => 0.5 * erfc(-x / Math.SQRT2);

// Inverse of normCdf by bisection: slow in theory, instant for the handful of calls we make.
export function normInv(p) {
  if (!(p > 0 && p < 1)) throw new RangeError("p must be between 0 and 1");
  let lo = -10, hi = 10;
  for (let i = 0; i < 80; i++) {
    const mid = (lo + hi) / 2;
    if (normCdf(mid) < p) lo = mid; else hi = mid;
  }
  return (lo + hi) / 2;
}

// The CDF approximation can be off by ~1e-7, so clamp: a probability must stay within [0, 1].
const twoSidedP = (z) => Math.min(1, Math.max(0, 2 * (1 - normCdf(Math.abs(z)))));

export function zTest(convA, nA, convB, nB, alpha = 0.05) {
  if (![convA, nA, convB, nB].every(Number.isFinite) || nA <= 0 || nB <= 0 || convA < 0 || convB < 0 || convA > nA || convB > nB) {
    throw new RangeError("conversions must be between 0 and the group size, and groups must be non-empty");
  }
  const pa = convA / nA, pb = convB / nB, diff = pb - pa;
  const pooled = (convA + convB) / (nA + nB);
  const sePooled = Math.sqrt(pooled * (1 - pooled) * (1 / nA + 1 / nB));
  const z = sePooled === 0 ? 0 : diff / sePooled;
  const p = sePooled === 0 ? 1 : twoSidedP(z);
  const se = Math.sqrt((pa * (1 - pa)) / nA + (pb * (1 - pb)) / nB);
  const crit = normInv(1 - alpha / 2);
  return {
    rateA: pa, rateB: pb, absLift: diff, relLift: pa === 0 ? null : diff / pa,
    z, p, ciLow: diff - crit * se, ciHigh: diff + crit * se, significant: p < alpha,
  };
}

export function sampleSizePerGroup(baseline, mdeAbs, alpha = 0.05, power = 0.8) {
  const p1 = baseline, p2 = baseline + mdeAbs;
  if (!(p1 > 0 && p1 < 1 && p2 > 0 && p2 < 1)) throw new RangeError("baseline and baseline + effect must both be between 0 and 1");
  if (mdeAbs === 0) throw new RangeError("the minimum detectable effect cannot be zero");
  const zA = normInv(1 - alpha / 2), zB = normInv(power), pBar = (p1 + p2) / 2;
  const num = (zA * Math.sqrt(2 * pBar * (1 - pBar)) + zB * Math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2;
  return Math.ceil(num / mdeAbs ** 2);
}

export function sampleRatioMismatch(nA, nB, expectedA = 0.5) {
  const n = nA + nB;
  const z = (nA - n * expectedA) / Math.sqrt(n * expectedA * (1 - expectedA));
  return twoSidedP(z);
}

// Small seeded generator so a simulation can be replayed exactly.
export function mulberry32(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// A/A tests (no real difference); stop at the first "significant" look.
export function peekingFalsePositiveRate({ trials = 1000, looks = 10, perLook = 200, rate = 0.1, alpha = 0.05, seed = 1 } = {}) {
  const rnd = mulberry32(seed);
  const bern = (n) => { let c = 0; for (let i = 0; i < n; i++) if (rnd() < rate) c++; return c; };
  let hits = 0;
  for (let t = 0; t < trials; t++) {
    let ca = 0, cb = 0, n = 0;
    for (let k = 0; k < looks; k++) {
      ca += bern(perLook); cb += bern(perLook); n += perLook;
      if (zTest(ca, n, cb, n, alpha).significant) { hits++; break; }
    }
  }
  return hits / trials;
}
