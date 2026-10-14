"""Offline tests for invented rewrite-name slates and accepted-use cooldowns."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from pymongo.errors import DuplicateKeyError

from newsmuncher.services.comedy_names import ComedyNameGenerator, legacy_names, normalized
from newsmuncher.services.name_selection import (
    INVENTED_NAME_GUIDANCE, InventedNameRegistry, NameSelectionConfig,
    NameSelectionExhausted,
)


class MemoryCollection:
    def __init__(self):
        self.docs = {}
        self.lock = Lock()
        self.operations = {"find": 0, "update_one": 0, "update_many": 0}

    @staticmethod
    def _eligible(doc, query):
        if doc is None:
            return True
        if "$and" not in query:
            return ("offered_by" not in query or
                    doc.get("offered_by") == query["offered_by"])
        clauses = query.get("$and", [])
        cooldown_clause = next((clause for clause in clauses
                                if "last_used_at" in clause["$or"][-1]), None)
        offer_clause = next(clause for clause in clauses
                            if "offered_by" in clause["$or"][0])
        now = offer_clause["$or"][2]["offer_until"]["$lte"]
        selection_key = offer_clause["$or"][0]["offered_by"]
        recent_ok = True
        if cooldown_clause:
            cooldown = cooldown_clause["$or"][1]["last_used_at"]["$lte"]
            recent_ok = "last_used_at" not in doc or doc["last_used_at"] <= cooldown
        offer_ok = (doc.get("offered_by") == selection_key or
                    "offer_until" not in doc or doc["offer_until"] <= now)
        return recent_ok and offer_ok

    @staticmethod
    def _apply(doc, update, inserted=False):
        if inserted:
            doc.update(deepcopy(update.get("$setOnInsert", {})))
        doc.update(deepcopy(update.get("$set", {})))
        for key, value in update.get("$inc", {}).items():
            doc[key] = doc.get(key, 0) + value
        for key in update.get("$unset", {}):
            doc.pop(key, None)

    def update_one(self, query, update, upsert=False):
        with self.lock:
            self.operations["update_one"] += 1
            key = query["_id"]
            doc = self.docs.get(key)
            if not self._eligible(doc, query):
                if upsert:
                    raise DuplicateKeyError("leased or cooling down")
                return SimpleNamespace(matched_count=0, upserted_id=None)
            inserted = doc is None
            doc = self.docs.setdefault(key, {"_id": key})
            self._apply(doc, update, inserted)
            return SimpleNamespace(matched_count=0 if inserted else 1,
                                   upserted_id=key if inserted else None)

    def update_many(self, query, update):
        with self.lock:
            self.operations["update_many"] += 1
            count = 0
            for key, doc in self.docs.items():
                ids = query.get("_id", {}).get("$in")
                if ids is not None and key not in ids:
                    continue
                if "offered_by" in query and doc.get("offered_by") != query["offered_by"]:
                    continue
                self._apply(doc, update)
                count += 1
            return SimpleNamespace(modified_count=count)

    def find(self, query, projection=None):
        self.operations["find"] += 1
        ids = set(query.get("_id", {}).get("$in", self.docs))
        with self.lock:
            return [deepcopy(doc) for key, doc in self.docs.items() if key in ids]


def registry(collection=None, **config):
    return InventedNameRegistry(
        collection or MemoryCollection(),
        NameSelectionConfig(**config),
        now=lambda: datetime(2026, 10, 9, tzinfo=timezone.utc),
    )


def categories(collection, names):
    return [collection.docs[normalized(name)]["category"] for name in names]


def test_default_slate_is_exactly_seven_cheeky_three_absurd_and_no_phonetic_or_legacy():
    collection = MemoryCollection()
    names = registry(collection).offer("pet:session")
    assert len(names) == len(set(names)) == 10
    assert categories(collection, names).count("cheeky") == 7
    assert categories(collection, names).count("absurd") == 3
    assert not ({normalized(name) for name in names} & legacy_names())
    phonetic = {normalized(item.name) for item in ComedyNameGenerator(seed=1)._phonetic_candidates()}
    assert not ({normalized(name) for name in names} & phonetic)


def test_weights_are_configurable_without_changing_slate_size():
    collection = MemoryCollection()
    names = registry(collection, cheeky_weight=.4, absurd_weight=.6).offer("pet:weighted")
    assert categories(collection, names).count("cheeky") == 4
    assert categories(collection, names).count("absurd") == 6


def test_same_session_retry_gets_same_slate_and_release_does_not_consume_names():
    collection = MemoryCollection()
    service = registry(collection)
    first = service.offer("pet:retry")
    assert service.offer("pet:retry") == first
    service.release("pet:retry")
    assert service.offer("pet:retry") == first
    assert all("last_used_at" not in collection.docs[normalized(name)] for name in first)


def test_only_names_in_an_accepted_rewrite_enter_cooldown():
    collection = MemoryCollection()
    service = registry(collection)
    names = service.offer("pet:first")
    used = service.accept("pet:first", "rewrite-1", names, names[0], f"{names[1]} arrived.")
    assert used == names[:2]
    assert all("last_used_at" in collection.docs[normalized(name)] for name in names[:2])
    assert all("last_used_at" not in collection.docs[normalized(name)] for name in names[2:])
    next_names = service.offer("pet:second")
    assert not set(names[:2]) & set(next_names)


def test_semantic_name_family_is_recorded_without_becoming_a_hard_cooldown():
    collection = MemoryCollection()
    service = registry(collection, vocabulary_mode="evaluation",
                       semantic_memory_mode="evaluation")
    names = service.offer("semantic:first")
    service.accept("semantic:first", "rewrite", names, names[0], "")
    family_docs = [doc for key, doc in collection.docs.items()
                   if key.startswith("semantic:name:")]
    assert family_docs and family_docs[0]["last_rewrite_id"] == "rewrite"
    assert len(service.offer("semantic:second")) == 10


def test_concurrent_sessions_receive_disjoint_leased_slates():
    collection = MemoryCollection()
    service = registry(collection)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = list(pool.map(service.offer, ("pet:a", "pet:b")))
    assert not set(first) & set(second)


def test_twenty_five_fresh_rewrites_do_not_exhaust_after_reported_five_munge_point():
    collection = MemoryCollection()
    service = registry(collection)
    all_names = []
    for attempt in range(25):
        names = service.offer(f"pet:rewrite-{attempt}")
        assert len(names) == 10
        # Model an unusually demanding rewrite that uses every offered name.
        service.accept(f"pet:rewrite-{attempt}", f"rewrite-{attempt}", names,
                       names[0], " ".join(names[1:]))
        all_names.extend(names)
    assert len(set(all_names)) == 250
    assert collection.operations["find"] == 25
    # Ten final lease writes plus ten accepted-use updates per rewrite; candidate
    # filtering itself performs no per-candidate write storm.
    assert collection.operations["update_one"] <= 25 * 20


def test_reported_five_munge_failure_is_reproduced_by_reusing_one_narrow_attempt_pool():
    """Models the old draft-session seed with its usable queue already narrowed.

    Thirty-five cheeky and fifteen absurd candidates provide exactly five 7/3
    slates. Reusing that identity then exhausts despite other seeds having a
    fresh combinatorial space, which is the production failure mechanism.
    """
    collection = MemoryCollection()
    service = registry(collection, candidates_per_style=35)
    for attempt in range(5):
        names = service.offer("pet:durable-draft-session")
        service.accept("pet:durable-draft-session", f"rewrite-{attempt}", names,
                       names[0], " ".join(names[1:]))
    with pytest.raises(NameSelectionExhausted):
        service.offer("pet:durable-draft-session")
    assert len(registry(collection, candidates_per_style=35).offer(
        "pet:fresh-rewrite-uuid"
    )) == 10


def test_same_source_fresh_rewrite_ids_get_fresh_slates_but_retry_is_stable():
    collection = MemoryCollection()
    service = registry(collection)
    first = service.offer("same-pet:rewrite-one")
    assert service.offer("same-pet:rewrite-one") == first
    second = service.offer("same-pet:rewrite-two")
    assert not set(first) & set(second)


def test_name_normalization_prevents_case_punctuation_collision():
    collection = MemoryCollection()
    service = registry(collection)
    names = service.offer("pet:normalization")
    key = normalized(names[0])
    assert key == normalized(names[0].upper().replace(" ", "---"))
    assert collection.docs[key]["display_name"] == names[0]


def test_typed_exhaustion_releases_partial_leases():
    collection = MemoryCollection()
    service = registry(collection, candidates_per_style=10)
    first = service.offer("pet:first")
    service.accept("pet:first", "rewrite-first", first, first[0], " ".join(first[1:]))
    with pytest.raises(NameSelectionExhausted):
        service.offer("pet:first")
    assert not any(doc.get("offered_by") == "pet:first" for doc in collection.docs.values())


def test_configuration_defaults_to_invented_and_legacy_switch_remains_available(monkeypatch):
    monkeypatch.delenv("NEWSMUNCHER_NAME_MODE", raising=False)
    monkeypatch.delenv("NEWSMUNCHER_EXPANDED_NAMES", raising=False)
    assert NameSelectionConfig.from_environment().mode == "invented"
    assert NameSelectionConfig.from_environment().vocabulary_mode == "off"
    monkeypatch.setenv("NEWSMUNCHER_EXPANDED_NAMES", "evaluation")
    assert NameSelectionConfig.from_environment().vocabulary_mode == "evaluation"
    monkeypatch.setenv("NEWSMUNCHER_NAME_MODE", "legacy")
    assert NameSelectionConfig.from_environment().mode == "legacy"


def test_prompt_guidance_is_specific_without_forcing_all_ten_names():
    assert "supplied invented names" in INVENTED_NAME_GUIDANCE
    assert "Do not introduce real celebrities" in INVENTED_NAME_GUIDANCE
    assert "do not force every supplied name" in INVENTED_NAME_GUIDANCE


def test_rewrite_route_uses_existing_provider_calls_and_releases_failed_offer():
    from test_image_generation import ImageTests

    fixture = ImageTests()
    fixture.setUp()
    try:
        routes = fixture.previews()
        names = ComedyNameGenerator(seed="route").generate(10)
        names = [item.name for item in names]
        offered = SimpleNamespace(
            offer=MagicMock(return_value=names),
            accept=MagicMock(return_value=[]),
            release=MagicMock(),
        )
        routes.NameSelectionConfig.from_environment.return_value = SimpleNamespace(
            mode="invented", slate_size=10,
        )
        routes.InventedNameRegistry = MagicMock(return_value=offered)
        routes.invented_name_collection = MagicMock(return_value=object())
        routes.prepare_prompt.return_value = {
            "full_prompt": "invented prompt", "preprocessing": None,
            "contenders": {"names": names},
        }
        routes.send_prompt.return_value = {"title": "Pass one", "extract": "Pass one body"}
        routes.format_shizzalise_result.return_value = dict(fixture.result)
        routes.copy_edit_pass.return_value = None

        result = routes.shizzalise_data(
            routes.ShizzRequest(title="source", description="", extract="source"),
            "alice", "alice",
        )
        assert result["crazyReplacement1Title"] == fixture.result["crazyReplacement1Title"]
        routes.send_prompt.assert_called_once()
        routes.copy_edit_pass.assert_called_once()
        offered.accept.assert_called_once()
        offered.release.assert_not_called()
        assert routes.prepare_prompt.call_args.kwargs["names_override"] == names

        routes.send_prompt.reset_mock()
        routes.copy_edit_pass.reset_mock()
        offered.accept.reset_mock()
        routes.send_prompt.return_value = None
        try:
            routes.shizzalise_data(
                routes.ShizzRequest(title="source", description="", extract="source",
                                    draft_session="failure"),
                "alice", "alice",
            )
        except routes.HTTPException as exc:
            assert exc.status_code == 500
        else:
            raise AssertionError("Expected failed mocked rewrite")
        routes.send_prompt.assert_called_once()
        routes.copy_edit_pass.assert_not_called()
        offered.accept.assert_not_called()
        released_key = offered.release.call_args.args[0]
        assert released_key.startswith("alice:")
        assert released_key != "alice:failure"
    finally:
        fixture.tearDown()
        fixture.doCleanups()


def test_name_exhaustion_returns_409_before_provider_call():
    from test_image_generation import ImageTests

    fixture = ImageTests()
    fixture.setUp()
    try:
        routes = fixture.previews()
        offered = SimpleNamespace(
            offer=MagicMock(side_effect=NameSelectionExhausted(
                "Not enough invented names are currently available. Please try MUNGE IT again."
            )),
            release=MagicMock(),
        )
        routes.NameSelectionConfig.from_environment.return_value = SimpleNamespace(
            mode="invented", slate_size=10,
        )
        routes.InventedNameRegistry = MagicMock(return_value=offered)
        routes.invented_name_collection = MagicMock(return_value=object())
        with pytest.raises(routes.HTTPException) as failure:
            routes.shizzalise_data(
                routes.ShizzRequest(title="source", description="", extract="source"),
                "alice", "alice",
            )
        assert failure.value.status_code == 409
        assert "invented names" in failure.value.detail
        routes.send_prompt.assert_not_called()
        offered.release.assert_called_once()
    finally:
        fixture.tearDown()
        fixture.doCleanups()


def test_legacy_route_keeps_original_prompt_name_path_and_skips_registry():
    from test_image_generation import ImageTests

    fixture = ImageTests()
    fixture.setUp()
    try:
        routes = fixture.previews()
        routes.NameSelectionConfig.from_environment.return_value = SimpleNamespace(
            mode="legacy", slate_size=10,
        )
        routes.InventedNameRegistry = MagicMock()
        routes.prepare_prompt.return_value = {
            "full_prompt": "legacy prompt", "preprocessing": None, "contenders": {},
        }
        routes.send_prompt.return_value = {"title": "Pass one", "extract": "Pass one body"}
        routes.format_shizzalise_result.return_value = dict(fixture.result)
        routes.copy_edit_pass.return_value = None
        routes.shizzalise_data(
            routes.ShizzRequest(title="source", description="", extract="source"),
            "alice", "alice",
        )
        routes.InventedNameRegistry.assert_not_called()
        assert routes.prepare_prompt.call_args.kwargs["names_override"] is None
        assert routes.prepare_prompt.call_args.kwargs["name_guidance"] == ""
    finally:
        fixture.tearDown()
        fixture.doCleanups()
