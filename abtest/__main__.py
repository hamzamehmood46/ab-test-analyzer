"""python -m abtest CONV_A N_A CONV_B N_B   e.g.   python -m abtest 200 2000 240 2000"""
import sys

from .stats import sample_ratio_mismatch, two_proportion_ztest


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(__doc__)
        return 2
    ca, na, cb, nb = (int(x) for x in argv)
    r = two_proportion_ztest(ca, na, cb, nb)
    rel = "n/a" if r.rel_lift is None else f"{r.rel_lift:+.1%}"
    print(f"A: {r.rate_a:.2%}   B: {r.rate_b:.2%}   lift: {r.abs_lift:+.2%} points ({rel})")
    print(f"z = {r.z:.3f}   p = {r.p_value:.4f}   95% CI for the difference: [{r.ci_low:+.2%}, {r.ci_high:+.2%}]")
    print("Significant at 95%." if r.significant else "Not significant at 95%.")
    srm = sample_ratio_mismatch(na, nb)
    if srm < 0.001:
        print(f"WARNING: sample ratio mismatch (p = {srm:.2g}). Check assignment and logging before trusting this result.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
