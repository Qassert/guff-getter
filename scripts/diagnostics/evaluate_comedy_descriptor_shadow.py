"""Evaluate descriptor replacement strategies without providers or databases."""
import argparse
from collections import Counter

from newsmuncher.services.descriptor_shadow import (
    SHADOW_DESCRIPTOR_GUIDANCE, build_shadow_slate, slate_metrics,
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", default="descriptor-shadow")
    parser.add_argument("--slates", type=int, default=10)
    args = parser.parse_args(argv)
    totals = {key: [] for key in "ABC"}
    for number in range(1, args.slates + 1):
        print(f"## REALISTIC SLATE {number}")
        for strategy in "ABC":
            slate = build_shadow_slate(f"{args.seed}:{number}", strategy)
            metrics = slate_metrics(slate); totals[strategy].append(metrics)
            print(f"Strategy {strategy}: generated={len(slate.generated)} legacy={len(slate.legacy)} "
                  f"categories={metrics['categories']} intensities={metrics['intensities']} "
                  f"roles={metrics['roles']} mechanisms={metrics['mechanisms']} "
                  f"repeated_subjects={metrics['repeated_subjects']} short={metrics['short_descriptors']} "
                  f"approx_token_delta={metrics['token_difference']:+d}")
            print(slate.descriptor_section or "- legacy CSV descriptors only")
        print()
    print("## TEN-SLATE AGGREGATE")
    for strategy in "ABC":
        print(strategy, "average_token_delta=", round(sum(x["token_difference"] for x in totals[strategy]) / len(totals[strategy])),
              "roles=", dict(sum((Counter(x["roles"]) for x in totals[strategy]), Counter())),
              "mechanisms=", dict(sum((Counter(x["mechanisms"]) for x in totals[strategy]), Counter())))
    preview = build_shadow_slate(f"{args.seed}:preview", "A")
    print("\n## MOCK DESCRIPTOR PROMPT SECTION")
    print(preview.descriptor_section)
    print("\n## OPTIONAL-USE GUIDANCE")
    print(SHADOW_DESCRIPTOR_GUIDANCE)


if __name__ == "__main__":
    main()
