import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { zTest, sampleSizePerGroup, sampleRatioMismatch, normCdf, normInv, peekingFalsePositiveRate } from "./stats.js";

const here = dirname(fileURLToPath(import.meta.url));
const cases = JSON.parse(readFileSync(join(here, "..", "tests", "cases.json"), "utf8"));
const near = (actual, expected, delta, msg) => assert.ok(Math.abs(actual - expected) <= delta, `${msg}: ${actual} vs ${expected}`);

for (const c of cases.ztest) {
  test(`z-test: ${c.name}`, () => {
    const r = zTest(...c.args);
    near(r.z, c.z, 1e-3, "z");
    near(r.p, c.p, 5e-4, "p");
    near(r.ciLow, c.ci_low, 5e-4, "ciLow");
    near(r.ciHigh, c.ci_high, 5e-4, "ciHigh");
    assert.equal(r.significant, c.significant);
  });
}

for (const c of cases.sample_size) {
  test(`sample size: ${c.name}`, () => near(sampleSizePerGroup(c.baseline, c.mde), c.expect, c.tolerance, "n"));
}

for (const c of cases.srm) {
  test(`sample ratio mismatch: ${c.name}`, () => near(sampleRatioMismatch(...c.args), c.p, 5e-4, "p"));
}

test("normal distribution helpers agree with known values", () => {
  near(normCdf(0), 0.5, 1e-7, "cdf(0)");
  near(normCdf(1.959964), 0.975, 1e-6, "cdf(1.96)");
  near(normInv(0.975), 1.959964, 1e-5, "inv(0.975)");
  near(normInv(0.8), 0.841621, 1e-5, "inv(0.8)");
});

test("identical groups give p = 1 and no division by zero", () => {
  assert.equal(zTest(50, 500, 50, 500).p, 1);
  assert.equal(zTest(0, 100, 0, 100).p, 1);
  assert.equal(zTest(0, 100, 0, 100).relLift, null);
});

test("invalid input is rejected", () => {
  assert.throws(() => zTest(11, 10, 1, 10), RangeError);
  assert.throws(() => zTest(1, 0, 1, 10), RangeError);
  assert.throws(() => zTest(NaN, 10, 1, 10), RangeError);
  assert.throws(() => sampleSizePerGroup(0.1, 0), RangeError);
});

test("peeking inflates false positives; a single look stays near 5%", () => {
  const single = peekingFalsePositiveRate({ trials: 3000, looks: 1, perLook: 1000, seed: 11 });
  const peeking = peekingFalsePositiveRate({ trials: 1500, looks: 10, perLook: 200, seed: 11 });
  assert.ok(single > 0.035 && single < 0.065, `single look: ${single}`);
  assert.ok(peeking > 0.12, `ten looks: ${peeking}`);
});

test("the simulation is reproducible from its seed", () => {
  assert.equal(peekingFalsePositiveRate({ trials: 200, seed: 4 }), peekingFalsePositiveRate({ trials: 200, seed: 4 }));
});
