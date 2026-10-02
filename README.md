# A/B Test Analyzer

[![Test and deploy](https://github.com/hamzamehmood46/ab-test-analyzer/actions/workflows/pages.yml/badge.svg)](https://github.com/hamzamehmood46/ab-test-analyzer/actions/workflows/pages.yml)

**Live tool: [hamzamehmood46.github.io/ab-test-analyzer](https://hamzamehmood46.github.io/ab-test-analyzer/)**

Did the variant really win? Type in the results of an A/B test and get the answer in plain language: whether the difference is likely real, how big it could plausibly be, and whether the traffic split itself looks trustworthy. It also plans tests (how many visitors do you need?) and runs a simulation that shows why checking results early produces false wins.

Everything runs in the browser. The same statistics are implemented twice, in Python (the reference implementation, standard library only) and in JavaScript (the live page), and both are tested against the same hand-checked cases.

## What it does

| Feature | Method |
|---|---|
| Is the lift real? | Two-sided two-proportion z-test (pooled standard error for the test) |
| How big could it be? | Confidence interval for the difference (unpooled standard error) |
| How many visitors do I need? | Sample size per group from baseline, minimum detectable effect, confidence and power |
| Is the traffic split trustworthy? | Sample ratio mismatch check (alarm below p = 0.001) |
| Why not stop early? | Simulation of 1,000 A/A tests with repeated peeking |

On the peeking simulation: with ten looks at an A/A test (no real difference), about 19% of tests declare a winner at a nominal 5% significance level.

## Correctness

- `tests/cases.json` holds expected values worked out by hand from the formulas. `tests/test_stats.py` (Python) and `web/stats.test.mjs` (JavaScript) both check them, so the two implementations cannot drift apart.
- Behavioural tests: swapping groups flips the sign but not the p-value; identical groups give p = 1; zero conversions do not divide by zero; a stricter confidence level can overturn a borderline result; smaller effects and higher power need more visitors; bad input is rejected.
- Simulation tests: a single look keeps the false-positive rate near 5%, ten looks inflate it, and results are reproducible from a seed.
- Building the tests caught a real bug: the JavaScript normal-CDF approximation could return a p-value of 1.000000001. P-values are now clamped to [0, 1].

## Run it

Python 3.12+ (`random.binomialvariate`) and Node 20+ for the JavaScript tests. No dependencies.

```bash
python -m unittest discover -s tests -t .
node --test web/stats.test.mjs

python -m abtest 200 2000 240 2000     # command-line analysis
```

To use the page locally, serve the `web/` folder with any static server (browsers do not load ES modules from `file://`), for example `python -m http.server -d web`.

## Scope

This handles one control and one variant with a binary conversion metric and a fixed sample size. It does not cover multiple variants, revenue or other continuous metrics, or sequential testing methods, and the z-test is an approximation that suits large samples. With very few conversions per group, use an exact test.

## License

MIT
