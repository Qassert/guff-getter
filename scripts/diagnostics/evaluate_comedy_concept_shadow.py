"""Compare three offline comedy-concept prompt strategies without providers or DB."""
import argparse

from newsmuncher.services.concept_shadow import build_shadow_slate, slate_metrics


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", default="concept-shadow")
    parser.add_argument("--slates", type=int, default=10)
    args = parser.parse_args(argv)
    totals = {key: [] for key in "ABC"}
    for number in range(1, args.slates + 1):
        print(f"## MOCK SLATE {number}")
        for strategy in "ABC":
            slate = build_shadow_slate(f"{args.seed}:{number}", strategy)
            metrics = slate_metrics(slate)
            totals[strategy].append(metrics)
            print(f"Strategy {strategy}: concepts={len(slate.concepts)} "
                  f"categories={metrics['categories']} intensities={metrics['intensities']} "
                  f"repeated_bases={metrics['repeated_bases']} "
                  f"approx_token_delta={metrics['token_difference']:+d} "
                  f"candidate_delta={metrics['candidate_token_difference']:+d}")
            print(f"  Nouns: {', '.join(slate.nouns)}")
            print(f"  Animals/objects: {', '.join(slate.animals)}")
        print()
    print("## PROMPT GUIDANCE PREVIEW")
    sample = build_shadow_slate(f"{args.seed}:preview", "C")
    print(sample.prompt_preview)
    print("\n## RECOMMENDATION")
    print("Begin Phase 2D with Strategy C behind a disabled-by-default switch: six optional "
          "concepts preserve fourteen ordinary anchors, minimize prompt growth, and reduce the "
          "risk that several elaborate premises compete inside one rewrite. Track exact accepted "
          "phrase use and base cooldown separately from permanent CSV claims.")


if __name__ == "__main__":
    main()
