import threading
import unittest

from scripts.diagnostics.evaluate_rolling_noun_exclusion import (
    RollingNounLedger, blocked_matches, extract_distinctive_nouns,
    filter_and_refill, identity_entries,
)


def record(final="The gravy boat arrested a badger", source="Council meets"):
    return {
        "source": {"headline": source, "description": "", "article_text": ""},
        "final": {"headline": final, "article_text": ""},
        "ingredients": {"offered": {
            "generated_concepts": [{"base": "gravy boat"}, {"base": "badger"}],
            "generated_descriptors": [], "raw_hybrid_ingredients": [],
            "generated_names": [], "legacy_banks": {},
        }},
    }


class RollingNounExclusionTests(unittest.TestCase):
    def test_compound_blocks_distinctive_component_not_generic_head(self):
        self.assertEqual(identity_entries("gravy boat"),
                         {"phrase:gravy boat", "noun:gravy"})

    def test_extracts_only_exact_final_offers(self):
        self.assertEqual(extract_distinctive_nouns(record()),
                         {"phrase:gravy boat", "noun:gravy", "noun:badger"})

    def test_source_required_word_is_protected(self):
        self.assertNotIn("noun:gravy", extract_distinctive_nouns(
            record(source="Gravy production rises")))
        self.assertEqual(blocked_matches("gravy tribunal", {"noun:gravy"}, "gravy report"), [])

    def test_filter_refills_vacancy(self):
        candidates = [{"text": x} for x in ("gravy pump", "otter", "sextant")]
        selected, rejected = filter_and_refill(candidates, {"noun:gravy"}, 2)
        self.assertEqual([x["text"] for x in selected], ["otter", "sextant"])
        self.assertEqual(rejected, ["gravy pump"])

    def test_fifo_releases_oldest_unique_entry(self):
        ledger = RollingNounLedger(2)
        ledger.complete("pet-a", "one", {"noun:gravy", "noun:otter"})
        ledger.complete("pet-a", "two", {"noun:sextant"})
        self.assertEqual(set(ledger.entries("pet-a")), {"noun:otter", "noun:sextant"})

    def test_pet_isolation_and_failed_reservation_release(self):
        ledger = RollingNounLedger()
        candidates = [{"text": "gravy pump"}, {"text": "otter"}]
        first, _ = ledger.reserve("pet-a", "run-a", candidates, 1)
        other, _ = ledger.reserve("pet-b", "run-b", candidates, 1)
        self.assertEqual(first, other)
        ledger.fail("run-a")
        retry, _ = ledger.reserve("pet-a", "run-c", candidates, 1)
        self.assertEqual(retry[0]["text"], "gravy pump")

    def test_concurrent_reservations_do_not_overlap_within_pet(self):
        ledger = RollingNounLedger()
        candidates = [{"text": x} for x in ("gravy", "otter", "sextant")]
        results = []
        def choose(run):
            results.append(ledger.reserve("pet", run, candidates, 1)[0][0]["text"])
        threads = [threading.Thread(target=choose, args=(str(i),)) for i in range(2)]
        [thread.start() for thread in threads]
        [thread.join() for thread in threads]
        self.assertEqual(len(set(results)), 2)

    def test_model_invented_reuse_is_detected_by_exact_scan(self):
        self.assertEqual(blocked_matches(
            "The model invented a municipal gravy cannon.", {"noun:gravy"}),
            ["noun:gravy"])


if __name__ == "__main__":
    unittest.main()
