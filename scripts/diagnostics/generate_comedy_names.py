"""Generate deterministic comedy-name samples without touching the live application."""
import argparse
from collections import Counter
from copy import deepcopy

from newsmuncher.services.comedy_names import ComedyNameGenerator, normalized


def parser():
    command = argparse.ArgumentParser(description=__doc__)
    command.add_argument("--seed", default="newsmuncher-phase-1")
    command.add_argument("--cheeky", type=int, default=100)
    command.add_argument("--absurd", type=int, default=50)
    command.add_argument("--phonetic", type=int, default=50)
    command.add_argument("--audit", type=int, default=5000,
                         help="size of the additional mixed 70/30 quality audit")
    return command


def main(argv=None):
    args = parser().parse_args(argv)
    generator = ComedyNameGenerator(seed=args.seed)
    groups = []
    for heading, count, style in (
        ("CHEEKY", args.cheeky, "cheeky"),
        ("ABSURD", args.absurd, "absurd"),
        ("PHONETIC", args.phonetic, "phonetic"),
    ):
        names = generator.generate(count, style)
        groups.append((heading, names, deepcopy(generator.last_diagnostics)))
    for heading, names, diagnostics in groups:
        print(f"## {heading} ({len(names)})")
        for index, candidate in enumerate(names, 1):
            detail = ""
            if candidate.meaning:
                detail = f" — {candidate.meaning} ({candidate.technique})"
            print(f"{index:03}. [{candidate.category}/{candidate.recipe}] {candidate.name}{detail}")
        if heading == "PHONETIC":
            print(f"Candidates attempted: {diagnostics.proposed}")
            print(f"Candidates rejected: {diagnostics.rejected_total}")
            print(f"Constructed from components: {sum(name.generated for name in names)}")
        print()

    audit = ComedyNameGenerator(seed=f"{args.seed}:audit")
    names = audit.generate(args.audit)
    report = audit.last_diagnostics
    fingerprints = [normalized(item.name) for item in names]
    print(f"## MIXED QUALITY AUDIT ({len(names)})")
    print(f"Unique names: {len(set(fingerprints))}")
    print(f"Exact duplicates: {len(fingerprints) - len(set(fingerprints))}")
    print(f"Category distribution: {dict(sorted(Counter(n.category for n in names).items()))}")
    print(f"Candidates proposed: {report.proposed}")
    print(f"Rejected by filters/variety controls: {report.rejected_total}")
    quality_reasons = {key: value for key, value in report.rejected.items()
                       if key not in {"exact_duplicate", "surname_overuse", "first_name_overuse"}}
    print(f"Rejected specifically by quality/safety filters: {sum(quality_reasons.values())}")
    print(f"Rejected specifically by duplicate/variety controls: "
          f"{report.rejected_total - sum(quality_reasons.values())}")
    print(f"Rejection reasons: {dict(report.rejected.most_common())}")
    print(f"Template distribution: {dict(report.templates.most_common())}")
    print(f"Most reused first components: {report.first_components.most_common(10)}")
    print(f"Most reused surname components: {report.surname_components.most_common(10)}")
    print(f"Category exhausted: {'yes' if report.exhausted else 'no'}")


if __name__ == "__main__":
    main()
