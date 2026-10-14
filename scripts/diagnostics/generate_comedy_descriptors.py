"""Print deterministic descriptor samples/audits; no network or database access."""
from collections import Counter
import argparse

from newsmuncher.services.comedy_descriptors import ComedyDescriptorGenerator


def balanced_editorial_sample(seed, count):
    """Select an equal role sample while rotating mechanisms within each role."""
    if count % 6:
        raise ValueError("Editorial sample size must be divisible by the six roles")
    pool = ComedyDescriptorGenerator(f"{seed}:sample-pool").generate(max(5000, count * 10))
    per_role = count // 6
    sample = []
    for role in sorted({item.grammatical_role for item in pool}):
        buckets = {}
        for item in (value for value in pool if value.grammatical_role == role):
            buckets.setdefault(item.comic_mechanism, []).append(item)
        chosen = []
        while len(chosen) < per_role:
            progressed = False
            for mechanism in sorted(buckets):
                if buckets[mechanism] and len(chosen) < per_role:
                    chosen.append(buckets[mechanism].pop(0)); progressed = True
            if not progressed:
                raise ValueError(f"Insufficient editorial examples for {role}")
        sample.extend(chosen)
    return sample


def balanced_extremes(items, reverse=False):
    """Return five score extremes per role so one productive form cannot dominate."""
    result = []
    for role in sorted({item.grammatical_role for item in items}):
        ranked = sorted(
            (item for item in items if item.grammatical_role == role),
            key=lambda item: (item.quality_score, item.phrase), reverse=reverse,
        )
        result.extend(ranked[:5])
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", default="phase3a-editorial")
    parser.add_argument("--sample", type=int, default=150)
    parser.add_argument("--audit", type=int, default=5000)
    args = parser.parse_args()
    sample = balanced_editorial_sample(args.seed, args.sample)
    print(f"EDITORIAL SAMPLE ({len(sample)})")
    for role in sorted({item.grammatical_role for item in sample}):
        print(f"\n[{role}]")
        for item in (value for value in sample if value.grammatical_role == role):
            warning = f" warnings={','.join(item.editorial_warnings)}" if item.editorial_warnings else ""
            print(f"- {item.phrase} | example={item.usage_example} | {item.category} | intensity={item.intensity} | "
                  f"mechanism={item.comic_mechanism} | template={item.template} | "
                  f"score={item.quality_score}{warning}")

    auditor = ComedyDescriptorGenerator(f"{args.seed}:audit")
    audit = auditor.generate(args.audit); report = auditor.last_diagnostics
    print(f"\nAUDIT ({len(audit)})")
    print("unique=", len({item.phrase.casefold() for item in audit}), "duplicates=",
          len(audit) - len({item.phrase.casefold() for item in audit}))
    for label, values in (("categories", report.categories), ("intensities", report.intensities),
                          ("roles", report.roles), ("templates", report.templates),
                          ("mechanisms", report.mechanisms), ("rejections", report.rejected)):
        print(label, dict(values))
    print("top subjects", report.subjects.most_common(20))
    print("proposed", report.proposed, "eligible", report.eligible, "emitted", report.accepted,
          "eligible-not-selected", report.unselected, "rejected", report.rejected_total,
          "exhausted", report.exhausted)
    print("\nWEAKEST 30")
    for item in balanced_extremes(audit):
        print(f"- {item.phrase} | {item.grammatical_role} | {item.comic_mechanism} | "
              f"score={item.quality_score} | warnings={','.join(item.editorial_warnings) or 'none'}")
    print("\nSTRONGEST 30")
    for item in balanced_extremes(audit, reverse=True):
        print(f"- {item.phrase} | {item.grammatical_role} | {item.comic_mechanism} | "
              f"score={item.quality_score} | warnings={','.join(item.editorial_warnings) or 'none'}")


if __name__ == "__main__":
    main()
