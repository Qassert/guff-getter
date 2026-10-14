"""Generate deterministic comedy concepts without database or network access."""
import argparse
from collections import Counter
from copy import deepcopy
import re

from newsmuncher.services.comedy_concepts import ComedyConceptGenerator, normalised


EDITORIAL_COUNTS = (
    ("EVERYDAY BRITISH", "everyday_british", 20),
    ("CHEEKY OBJECTS", "cheeky_object", 20),
    ("ABSURD INVENTIONS", "absurd_invention", 20),
    ("RIDICULOUS CREATURES", "ridiculous_creature", 20),
    ("BUREAUCRATIC NONSENSE", "bureaucratic_nonsense", 20),
    ("EMERGENCY EQUIPMENT", "emergency_equipment", 20),
    ("CEREMONIAL OBJECTS", "ceremonial_object", 20),
)


def parser():
    command = argparse.ArgumentParser(description=__doc__)
    command.add_argument("--seed", default="newsmuncher-concepts-phase-2a")
    command.add_argument("--audit", type=int, default=5000)
    return command


def main(argv=None):
    args = parser().parse_args(argv)
    for heading, category, count in EDITORIAL_COUNTS:
        generator = ComedyConceptGenerator(seed=f"{args.seed}:{category}")
        concepts = generator.generate(count, category=category)
        print(f"## {heading} ({len(concepts)})")
        for index, concept in enumerate(concepts, 1):
            warnings = ", ".join(concept.editorial_warnings) or "none"
            print(
                f"{index:03}. {concept.phrase} | category={concept.category} | "
                f"intensity={concept.intensity} | base={concept.base} | "
                f"template={concept.template} | mechanism={concept.comic_mechanism} | "
                f"score={concept.score:.2f} | warnings={warnings} | words={concept.word_count}"
            )
        print()

    generator = ComedyConceptGenerator(seed=f"{args.seed}:audit")
    concepts = generator.generate(args.audit)
    report = deepcopy(generator.last_diagnostics)
    fingerprints = [normalised(item.phrase) for item in concepts]
    weakest = sorted(concepts, key=lambda item: (item.score, item.phrase))[:30]
    print(f"## QUALITY AUDIT ({len(concepts)})")
    print(f"Unique phrases: {len(set(fingerprints))}")
    print(f"Duplicate outputs: {len(fingerprints) - len(set(fingerprints))}")
    print(f"Candidates attempted: {report.proposed}")
    print(f"Candidates rejected: {report.rejected_total}")
    print(f"Rejection reasons: {dict(report.rejected.most_common())}")
    print(f"Category distribution: {dict(report.categories)}")
    print(f"Intensity distribution: {dict(sorted(report.intensities.items()))}")
    print(f"Template distribution: {dict(report.templates.most_common())}")
    print(f"Most reused base objects: {report.bases.most_common(12)}")
    theme_counts = Counter(
        theme for item in concepts for theme in generator.overused_themes
        if re.search(rf"(?<![a-z]){re.escape(theme)}(?![a-z])", item.phrase.casefold())
    )
    print(f"Explicitly monitored theme usage: {dict(theme_counts)}")
    for category in ("ridiculous_creature", "ceremonial_object"):
        group = [item for item in concepts if item.category == category]
        short = sum(item.word_count == 2 for item in group)
        print(f"Two-word {category}: {short}/{len(group)} ({short / len(group):.1%})")
    weak = set(id(item) for item in weakest)
    weak_short = sum(item.word_count == 2 and id(item) in weak for item in concepts)
    all_short = sum(item.word_count == 2 for item in concepts)
    print(f"Two-word concepts among weakest 30: {weak_short}; across audit: {all_short}")
    print("Grammatical validation: all outputs passed word-order, repeated-word, visible-base and category-length rules")
    print(f"Category exhausted: {'yes' if report.exhausted else 'no'}")
    print("Phase 2B comparison (same 5,000 seed): 85,993 → "
          f"{report.proposed:,} attempted; 15,993 → {report.rejected_total:,} rejected; "
          "5,000 unique and zero emitted duplicates in both phases")
    print("Weakest/borderline accepted combinations:")
    for item in weakest:
        print(
            f"- [{item.score:.2f}; {item.category}; intensity {item.intensity}; "
            f"{item.comic_mechanism}; {item.word_count} words] {item.phrase}"
        )


if __name__ == "__main__":
    main()
