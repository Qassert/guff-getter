from newsmuncher.services.comedy_expressions import ComedyExpressionGenerator


def test_slang_and_places_are_deterministic_typed_safe_review_material():
    for family in ("slang", "places"):
        first = ComedyExpressionGenerator("fixed").generate(family, 100)
        again = ComedyExpressionGenerator("fixed").generate(family, 100)
        assert first == again
        assert len({x.phrase.casefold() for x in first}) == 100
        assert all(x.family == family and x.approval_status == "machine_checked" for x in first)
        assert all(len(x.phrase.split()) <= 14 for x in first)


def test_phase4f_adds_structural_expression_variety_without_exhaustion():
    for family in ("slang", "places"):
        old, improved = [], []
        for number in range(30):
            seed = f"phase4f-expression:{number}"
            old.extend(x.phrase for x in ComedyExpressionGenerator(seed, "phase4e").generate(family, 10))
            improved.extend(x.phrase for x in ComedyExpressionGenerator(seed, "phase4f").generate(family, 10))
        assert len(set(improved)) > len(set(old))
        assert len({x.template for number in range(5) for x in
                    ComedyExpressionGenerator(f"phase4f-template:{number}", "phase4f").generate(family, 10)}) > 5
