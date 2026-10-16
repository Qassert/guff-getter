from newsmuncher.utils.source_preprocessing import log_overlap
from newsmuncher.config import (PROJECT_ROOT, TEMP_FILE, TEMP_SHIZZ_FILE,
    GENERATED_NARRATION_DIR, first_pass_prompt_file, comedy_editor_enabled,
    comedy_editor_model)
from fastapi import APIRouter, HTTPException, Request, Cookie
from pydantic import BaseModel, Field
from openai import BadRequestError
import json
import requests
import subprocess
import sys
import os
import re
from typing import Literal
from time import monotonic
from collections import Counter
from datetime import datetime, timezone
from uuid import uuid4, UUID
from bson import ObjectId
from newsmuncher.utils.clean_data import (prepare_prompt, send_prompt,
    format_shizzalise_result, copy_edit_pass, comedy_editor_pass,
    comedy_editor_word_target, claim_used_words,
    RewriteProviderQuotaExhausted)
from newsmuncher.utils.file_handler import load_prompt
from newsmuncher.services.word_shuffle import WordClaimConflict
from newsmuncher.services.rewrite_title import final_title
from newsmuncher.services.name_selection import (
    INVENTED_NAME_GUIDANCE, InventedNameRegistry, NameSelectionConfig,
    NameSelectionExhausted,
)
from newsmuncher.services.concept_selection import (
    CONCEPT_GUIDANCE, ConceptRegistry, ConceptSelectionConfig, ConceptSelectionExhausted,
)
from newsmuncher.services.descriptor_selection import (
    DESCRIPTOR_GUIDANCE, DescriptorRegistry, DescriptorSelectionConfig,
    DescriptorSelectionExhausted, prompt_descriptor,
)
from newsmuncher.services.final_joke_memory import (
    FinalJokeMemory, FinalJokeMemoryConfig,
)
from newsmuncher.services.comedy_audit import (
    ComedyAuditConfig, ComedyAuditLogger, build_audit_record,
)
from newsmuncher.services.topic_memory import (
    TopicMemory, TopicMemoryConfig, build_topic_event,
)
from newsmuncher.services.comedy_variants import ComedyVariantConfig, build_variant
from newsmuncher.services.lexical_exposure import (
    LexicalExposureConfig, LexicalExposureMemory, build_lexical_event, text_penalty,
)
from newsmuncher.services.thematic_diversity import (
    ThematicDiversityConfig, ThematicDiversityMemory, thematic_event,
)
from newsmuncher.services.thematic_ingredients import (
    ThemeIngredientConfig, ThemeIngredientMemory, ThemeSparkConfig,
    ThematicIngredientBuilder, partition_theme_sparks, theme_ingredient_event,
)
from newsmuncher.services.repetition_replacement import (
    PhraseReplacementConfig, RepetitionReplacementConfig, build_repetition_replacement,
    finish_repetition_diagnostic,
)
from newsmuncher.services.noun_exclusion import (
    NounExclusionConfig, NounExclusionMemory, blocked_entries,
    NounExclusionExhausted, attribute_violations, discover_recent_identities,
    discover_used_constructions, extract_final_entries, identity_entries,
    ingredient_texts, protected_words,
)
from newsmuncher.services.munge_engines import (
    MungeEngine, engine_plan, project_modern_variant,
)


from newsmuncher.services.image_generation import store, choose_image_style, get_provider, build_image_prompt, IMAGE_FIELDS, recover_image, IMAGE_MODEL, IMAGE_QUALITY, IMAGE_SIZE, image_path, DefinitiveImageFailure

router = APIRouter()

ENTRIES_API_BASE_URL = os.getenv("ENTRIES_API_BASE_URL", "http://127.0.0.1:8000")


def safe_provider_failure(exc):
    """Small diagnostic subset only; never persist request/auth/full response data."""
    body = getattr(exc, 'body', None)
    error = body.get('error', body) if isinstance(body, dict) else {}
    def text(value, limit):
        if not isinstance(value, str):
            return None
        return ' '.join(value.split())[:limit]
    return {
        'failure_category': type(exc).__name__,
        'failure_http_status': getattr(exc, 'status_code', None),
        'failure_code': text(error.get('code') if isinstance(error, dict) else None, 80),
        'failure_param': text(error.get('param') if isinstance(error, dict) else None, 80),
        'failure_message': text(error.get('message') if isinstance(error, dict) else None, 240)
                           or 'Provider rejected the image request.',
    }

def entries_collection():
    from newsmuncher.api.entries import collection
    return collection


def invented_name_collection():
    from newsmuncher.api.entries import db
    return db["invented_name_usage"]

def generated_concept_collection():
    from newsmuncher.api.entries import db
    return db["generated_concept_usage"]

def generated_descriptor_collection():
    from newsmuncher.api.entries import db
    return db["generated_descriptor_usage"]

def final_joke_memory_collection():
    from newsmuncher.api.entries import db
    return db["final_joke_memory"]

def comedy_topic_memory_collection():
    from newsmuncher.api.entries import db
    return db["comedy_topic_memory"]

def comedy_lexical_exposure_collection():
    from newsmuncher.api.entries import db
    return db["comedy_lexical_exposure"]

def comedy_thematic_diversity_collection():
    from newsmuncher.api.entries import db
    return db["comedy_thematic_diversity"]

def comedy_theme_ingredient_collection():
    from newsmuncher.api.entries import db
    return db["comedy_theme_ingredients"]

def comedy_noun_exclusion_collection():
    from newsmuncher.api.entries import db
    return db["comedy_noun_exclusion"]


# ✅ 1. TEMP GET
@router.get("/temp_data")
def get_temp_data():
    if not os.path.exists(TEMP_FILE):
        raise HTTPException(status_code=404, detail="No temporary data available.")
    with open(TEMP_FILE, "r") as file:
        return json.load(file)

class NominationResponse(BaseModel):
    crazyReplacement1Title: str
    crazyReplacement1Extract: str


# ✅ 2. FINAL BANKING
@router.post("/confirm_data")
def confirm_temp_data(request: Request, rewrite_id: str | None = None, payload: NominationResponse | None = None):
    if rewrite_id:
        return bank_image_rewrite(request, rewrite_id, payload)
    owner = request.cookies.get('active_pet')
    if not owner:
        raise HTTPException(status_code=401, detail='No active pet selected.')
    # Compatibility for a pre-upgrade JSON preview: assign its stable identity
    # before any persistence call, then use the same nomination lifecycle.
    with store.transaction() as db:
        if not os.path.exists(TEMP_SHIZZ_FILE):
            raise HTTPException(status_code=404, detail='No temporary shizzalised data available.')
        with open(TEMP_SHIZZ_FILE) as file:
            data = json.load(file)
        rewrite_id = data.get('rewrite_id') or str(uuid4())
        row = db.execute('SELECT state FROM rewrites WHERE id=?', (rewrite_id,)).fetchone()
        if row:
            read_image_rewrite(db, rewrite_id, owner)
        else:
            data['rewrite_id'] = rewrite_id
            store.save(db, rewrite_id, dict(result=data, owner=owner, entry_id=None))
        with open(TEMP_SHIZZ_FILE, 'w') as file:
            json.dump(data, file)
    return bank_image_rewrite(request, rewrite_id, payload)

# ✅ 3. SCRIPT TRIGGER
@router.get("/run_script/{script_name}")
def run_script(script_name: str):
    script_mapping = {
        "fetch_dating_from_api": [sys.executable, "-m", "newsmuncher.jobs.fetch_historical_funny", "dating"],
        "fetch_historicalFunny_from_api": [sys.executable, "-m", "newsmuncher.jobs.fetch_historical_funny"],
        "fetch_wikipedia_into_api": [sys.executable, "-m", "newsmuncher.jobs.fetch_wikipedia"],
        "fetch_poem_into_api": [sys.executable, "-m", "newsmuncher.jobs.fetch_poem"],
        "fetch_people_into_api": [sys.executable, "-m", "newsmuncher.jobs.fetch_people"],
        "process_data": [sys.executable, "-m", "newsmuncher.jobs.process_data"]
    }

    if script_name in script_mapping:
        result = subprocess.run(script_mapping[script_name], cwd=PROJECT_ROOT)
        if result.returncode == 0:
            return {"message": f"Script {script_name} executed successfully."}
        else:
            raise HTTPException(status_code=500, detail=f"Script {script_name} failed.")
    
    raise HTTPException(status_code=400, detail="Invalid script name.")

# ✅ 4. SHIZZALISE ENTRY TO TEMP + CALL OPENAI
class ShizzRequest(BaseModel):
    title: str
    description: str
    extract: str
    generate_images: bool = False
    draft_session: str = Field(default="legacy", min_length=1, max_length=100)
    engine: Literal["classic", "current", "experimental"] = "current"

@router.post("/shizzalise_data")
def shizzalise_data(payload: ShizzRequest, creationUser: str = Cookie(None), active_pet: str = Cookie(None)):
    request_started = monotonic()
    timings = {}
    def elapsed(stage, started):
        timings[stage] = round((monotonic() - started) * 1000, 2)
    def log_timings(status):
        timings["total_request_ms"] = round((monotonic() - request_started) * 1000, 2)
        timings["status"] = status
        print("[munge-timing] " + json.dumps(timings, sort_keys=True))

    if not active_pet:
        raise HTTPException(status_code=401, detail="No active pet selected.")
    plan = engine_plan(payload.engine)
    source = payload.model_dump(exclude={'generate_images', 'draft_session', 'engine'})
    rewrite_id = store.begin_draft({**source, 'creationUser': creationUser}, active_pet, payload.draft_session)
    with open(TEMP_FILE, "w") as f:
        json.dump({**source, "creationUser": creationUser}, f)

    if plan.classic_csv:
        try:
            from newsmuncher.services.classic_munge import prepare_classic_prompt
            prompt_template = prepare_classic_prompt(source)
            initial_response = send_prompt(prompt_template["full_prompt"])
            if not initial_response:
                raise HTTPException(status_code=500, detail="OpenAI generation failed.")
            result = format_shizzalise_result(initial_response)
            if not result:
                raise HTTPException(status_code=500, detail="Generated title or extract is invalid.")
            polished = copy_edit_pass(result)
            if polished:
                result = polished
            full_result = {
                **source, **result, "creationUser": creationUser,
                "contenders": prompt_template["contenders"],
                "munge_engine": MungeEngine.CLASSIC.value,
            }
            full_result = store.complete_draft(
                rewrite_id, active_pet, full_result,
                before_save=lambda: claim_used_words(prompt_template["contenders"], result),
            )
            if full_result is None:
                raise HTTPException(status_code=409, detail="Draft superseded by a newer rewrite.")
            log_timings("complete")
            return full_result
        except RewriteProviderQuotaExhausted as exc:
            log_timings("rewrite_error")
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    name_config = NameSelectionConfig.from_environment()
    # A rewrite UUID identifies one attempt. New MUNGEs from the same browser
    # draft receive fresh deterministic candidates; a genuine registry retry
    # with this identity retains its slate.
    name_selection_key = f"{active_pet}:{rewrite_id}"
    # A browser session is a durable draft slot, not a rewrite attempt.  Use the
    # newly allocated rewrite identity so a second MUNGE from the same source gets
    # a fresh deterministic concept slate. Retrying that attempt with its key is
    # still stable at the registry layer.
    concept_selection_key = f"{active_pet}:{rewrite_id}"
    name_registry = None
    invented_names = None
    concept_config = ConceptSelectionConfig.from_environment()
    concept_registry = None
    offered_concepts = None
    concept_overrides = None
    descriptor_config = DescriptorSelectionConfig.from_environment()
    descriptor_registry = None
    offered_descriptors = None
    leased_descriptors = None
    descriptor_overrides = None
    descriptor_selection_key = f"{active_pet}:{rewrite_id}"
    final_joke_config = FinalJokeMemoryConfig.from_environment()
    final_joke_memory = None
    final_joke_guidance = ""
    topic_memory = None
    topic_guidance = ""
    topic_config = TopicMemoryConfig.from_environment()
    lexical_config = LexicalExposureConfig.from_environment()
    lexical_memory = None
    lexical_penalties = None
    lexical_guidance = ""
    lexical_snapshot = {}
    thematic_config = ThematicDiversityConfig.from_environment()
    thematic_memory = None
    thematic_domains = []
    thematic_guidance = ""
    thematic_snapshot = {}
    theme_ingredient_config = ThemeIngredientConfig.from_environment()
    theme_spark_config = ThemeSparkConfig.from_environment()
    theme_ingredient_memory = None
    theme_ingredient_builder = None
    theme_ingredient_snapshot = {}
    theme_sparks = []
    repetition_config = RepetitionReplacementConfig.from_environment()
    phrase_replacement_config = PhraseReplacementConfig.from_environment()
    repetition_plan = None
    repetition_snapshot = {"enabled": repetition_config.enabled}
    audit_logger = None
    variant_config = ComedyVariantConfig.from_environment()
    variant_plan = None
    noun_exclusion_config = NounExclusionConfig.from_environment()
    noun_exclusion_memory = None
    noun_exclusions = set()
    automatic_identity_penalties = Counter()
    automatic_identity_guidance = ""
    noun_exclusion_snapshot = {"enabled": noun_exclusion_config.enabled}
    source_text = "\n".join(str(source.get(key, ""))
                            for key in ("title", "description", "extract"))
    try:
        audit_config = ComedyAuditConfig.from_environment()
        if audit_config.enabled:
            audit_logger = ComedyAuditLogger(audit_config)
    except Exception as audit_exc:
        print("[comedy-audit] disabled after configuration failure: "
              f"{type(audit_exc).__name__}")
    try:
        if noun_exclusion_config.enabled:
            noun_exclusion_memory = NounExclusionMemory(
                comedy_noun_exclusion_collection(), active_pet, noun_exclusion_config)
            noun_exclusion_memory.load()
            noun_exclusions = noun_exclusion_memory.exclusions(rewrite_id)
            automatic_identity_penalties = noun_exclusion_memory.identity_penalties(
                source_text)
            automatic_identity_guidance = noun_exclusion_memory.avoidance_guidance(
                source_text)
            if not isinstance(automatic_identity_penalties, dict):
                automatic_identity_penalties = Counter()
            if not isinstance(automatic_identity_guidance, str):
                automatic_identity_guidance = ""
            noun_exclusion_snapshot["excluded_before"] = len(noun_exclusions)
            noun_exclusion_snapshot["automatic_repetition"] = {
                "recent_events": len(noun_exclusion_memory.recent_identity_events),
                "recent_identity_history": noun_exclusion_memory.recent_identity_events,
                "applied_penalties": dict(automatic_identity_penalties),
                "guidance": automatic_identity_guidance,
            }
        if thematic_config.enabled or theme_ingredient_config.enabled:
            try:
                domain_config = (thematic_config if thematic_config.enabled else
                                 ThematicDiversityConfig("evaluation"))
                domain_scope = (active_pet if thematic_config.enabled else
                                f"{active_pet}:theme-ingredients")
                thematic_memory = ThematicDiversityMemory(
                    comedy_thematic_diversity_collection(), domain_scope, domain_config)
                thematic_memory.load()
                thematic_domains = thematic_memory.select(rewrite_id)
                if thematic_config.enabled:
                    thematic_guidance = thematic_memory.guidance(thematic_domains)
                thematic_snapshot = {
                    "recent_events": len(thematic_memory.events),
                    "selected_domains": thematic_domains,
                    "selection_penalties": thematic_memory.last_metrics.get(
                        "selected_penalties", {}),
                }
                timings["thematic_diversity"] = thematic_memory.last_metrics
            except Exception as thematic_exc:
                print("[comedy-themes] memory unavailable; continuing without guidance: "
                      f"{type(thematic_exc).__name__}")
                thematic_memory = None
        if lexical_config.enabled:
            try:
                lexical_memory = LexicalExposureMemory(
                    comedy_lexical_exposure_collection(), active_pet, lexical_config)
                lexical_memory.load()
                source_text_for_lexical = "\n".join(
                    str(source.get(key, "")) for key in ("title", "description", "extract"))
                lexical_penalties = lexical_memory.penalties(source_text_for_lexical)
                lexical_guidance = lexical_memory.guidance(source_text_for_lexical)
                lexical_snapshot = {
                    "recent_events": len(lexical_memory.events),
                    "penalties": dict(lexical_penalties.most_common(80)),
                }
                timings["lexical_exposure"] = lexical_memory.last_metrics
            except Exception as lexical_exc:
                print("[comedy-lexical] memory unavailable; continuing without lexical ranking: "
                      f"{type(lexical_exc).__name__}")
                lexical_memory = None
                lexical_penalties = None
        if automatic_identity_penalties:
            lexical_penalties = Counter(lexical_penalties or {})
            lexical_penalties.update(automatic_identity_penalties)
        if theme_ingredient_config.enabled and thematic_domains:
            try:
                theme_ingredient_memory = ThemeIngredientMemory(
                    comedy_theme_ingredient_collection(), active_pet,
                    theme_ingredient_config)
                theme_ingredient_memory.load()
                ingredient_penalties = theme_ingredient_memory.penalties()
                theme_ingredient_builder = ThematicIngredientBuilder(
                    thematic_domains, rewrite_id, theme_ingredient_config,
                    ingredient_penalties, lexical_penalties,
                    noun_exclusions, source_text)
                theme_ingredient_snapshot = {
                    "recent_events": len(theme_ingredient_memory.events),
                    "selection_penalties": dict(ingredient_penalties),
                }
                timings["theme_ingredient_memory"] = (
                    theme_ingredient_memory.last_metrics)
            except Exception as theme_ingredient_exc:
                print("[theme-ingredients] memory unavailable; continuing without "
                      "thematic ingredients: "
                      f"{type(theme_ingredient_exc).__name__}")
                theme_ingredient_memory = None
                theme_ingredient_builder = None
        if topic_config.enabled:
            try:
                topic_memory = TopicMemory(comedy_topic_memory_collection(), topic_config)
                topic_memory.load()
                topic_guidance = topic_memory.guidance()
                timings["topic_memory"] = topic_memory.last_metrics
            except Exception as topic_exc:
                print("[comedy-topics] memory unavailable; continuing without topic ranking: "
                      f"{type(topic_exc).__name__}")
                topic_memory = None
        if name_config.mode == "invented":
            name_registry = InventedNameRegistry(invented_name_collection(), name_config)
            stage = monotonic()
            invented_names = name_registry.offer(
                name_selection_key,
                topic_memory.recent_name_families() if topic_memory else None,
                noun_exclusions=noun_exclusions,
                source_text=source_text,
            )
            elapsed("invented_name_selection_ms", stage)
            timings["invented_name_selection"] = getattr(name_registry, "last_metrics", {})
        if concept_config.mode == "generated":
            concept_registry = ConceptRegistry(generated_concept_collection(), concept_config)
            concept_recent = None
            if topic_memory:
                concept_recent = sum((topic_memory.penalties(field, prefix) for field, prefix in (
                    ("concept_phrases", "phrase:"), ("concept_premises", "premise:"),
                    ("concept_bases", "base:"))), Counter())
            offered_concepts = concept_registry.offer(
                concept_selection_key, concept_recent, lexical_penalties,
                noun_exclusions, source_text)
            timings["concept_selection"] = getattr(concept_registry, "last_metrics", {})
            variant_plan = build_variant(
                variant_config.label, offered_concepts, concept_selection_key,
                getattr(concept_config, "vocabulary_mode", "off"),
                lexical_penalties=lexical_penalties,
                noun_exclusions=noun_exclusions,
                source_text=source_text,
            )
            if theme_ingredient_builder:
                variant_plan = theme_ingredient_builder.apply_concepts(variant_plan)
            variant_plan, animal_exposure = project_modern_variant(variant_plan)
            timings["animal_concept_exposure"] = animal_exposure
            timings["comedy_variant"] = variant_plan["counts"]
        if descriptor_config.mode == "generated":
            descriptor_registry = DescriptorRegistry(generated_descriptor_collection(), descriptor_config)
            # Prefer descriptor mechanisms that are not already dominating the
            # twenty-concept slate. This is a soft ordering preference: grammar
            # and exact category/intensity quotas remain hard requirements.
            theme_counts = Counter(item["semantic_theme"] for item in (offered_concepts or []))
            concept_themes = [theme for theme, count in theme_counts.items() if count >= 3]
            descriptor_recent = None
            if topic_memory:
                descriptor_recent = sum((topic_memory.penalties(field, prefix) for field, prefix in (
                    ("descriptor_phrases", "offered:"),
                    ("descriptor_premises", "offered-premise:"))), Counter())
            offered_descriptors = descriptor_registry.offer(
                descriptor_selection_key, avoid_themes=concept_themes,
                recent_offers=descriptor_recent,
                lexical_penalties=lexical_penalties,
                noun_exclusions=noun_exclusions,
                source_text=source_text,
            )
            leased_descriptors = offered_descriptors
            if theme_ingredient_builder:
                offered_descriptors, _ = theme_ingredient_builder.apply_descriptors(
                    offered_descriptors)
            timings["descriptor_selection"] = getattr(descriptor_registry, "last_metrics", {})
            descriptor_overrides = [prompt_descriptor(item) for item in offered_descriptors]
        if variant_plan:
            spark_enabled = bool(theme_ingredient_builder and theme_spark_config.enabled)
            concept_overrides, _, theme_sparks = partition_theme_sparks(
                variant_plan["prompt"], offered_descriptors, spark_enabled)
            if offered_descriptors is not None:
                if spark_enabled:
                    spark_descriptor_prompts = {
                        item["phrase"]: prompt_descriptor(item) for item in offered_descriptors
                        if item.get("source") == "thematic_seed_catalogue"
                    }
                    for spark in theme_sparks:
                        if spark["kind"] == "descriptor":
                            spark["text"] = spark_descriptor_prompts[spark["text"]]
                descriptor_overrides = [prompt_descriptor(item) for item in offered_descriptors
                                        if not (spark_enabled and item.get("source") ==
                                                "thematic_seed_catalogue")]
            if theme_ingredient_builder:
                theme_ingredient_snapshot.update({
                    "theme_sparks_enabled": spark_enabled,
                    "prompt_placement": ("adjacent_before_source" if spark_enabled
                                         else "ordinary_ingredient_banks"),
                    "selected": theme_ingredient_builder.selected,
                    "selection_metrics": theme_ingredient_builder.last_metrics,
                })
        if final_joke_config.enabled:
            try:
                final_joke_memory = FinalJokeMemory(
                    final_joke_memory_collection(), final_joke_config)
                stage = monotonic()
                final_joke_guidance = final_joke_memory.guidance()
                elapsed("final_joke_memory_read_ms", stage)
                timings["final_joke_memory"] = final_joke_memory.last_metrics
            except Exception as memory_exc:
                # Variety memory is advisory. Missing or unavailable history
                # must never block a rewrite or trigger another provider call.
                print("[final-jokes] memory unavailable; continuing without guidance: "
                      f"{type(memory_exc).__name__}")
                final_joke_memory = None
    except Exception as exc:
        if name_registry:
            name_registry.release(name_selection_key)
        if concept_registry:
            concept_registry.release(concept_selection_key)
        if descriptor_registry:
            descriptor_registry.release(descriptor_selection_key)
        if noun_exclusion_memory:
            noun_exclusion_memory.release(rewrite_id)
        if isinstance(exc, (NameSelectionExhausted, ConceptSelectionExhausted,
                            DescriptorSelectionExhausted, NounExclusionExhausted)):
            if noun_exclusion_config.enabled:
                print("[selection-diagnostic] " + json.dumps({
                    "status": "selection_exhausted",
                    "exception": type(exc).__name__,
                    "rewrite_id": str(rewrite_id),
                    "noun_exclusions": len(noun_exclusions),
                    "noun_reservations": len(
                        getattr(noun_exclusion_memory, "reservations", ()) or ()),
                    "name": getattr(name_registry, "last_metrics", None),
                    "concept": getattr(concept_registry, "last_metrics", None),
                    "descriptor": getattr(descriptor_registry, "last_metrics", None),
                }, sort_keys=True, default=str))
            log_timings("selection_exhausted")
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        log_timings("selection_error")
        raise

    rewrite_stage = "prompt_construction"
    try:
        stage = monotonic()
        prompt_template = prepare_prompt(
            source, name_config.slate_size, load_prompt(first_pass_prompt_file()),
            names_override=invented_names,
            name_guidance=INVENTED_NAME_GUIDANCE if invented_names is not None else "",
            concept_overrides=concept_overrides,
            concept_guidance=(CONCEPT_GUIDANCE + ("\n\n" + variant_plan["guidance"]
                              if variant_plan and variant_plan["guidance"] else ""))
                             if offered_concepts is not None else "",
            descriptor_overrides=descriptor_overrides,
            descriptor_guidance=DESCRIPTOR_GUIDANCE if offered_descriptors is not None else "",
            final_joke_guidance=final_joke_guidance,
            topic_guidance="\n\n".join(
                value for value in (topic_guidance, lexical_guidance,
                                    automatic_identity_guidance, thematic_guidance) if value),
            theme_sparks=theme_sparks,
            diagnostics=timings,
            noun_exclusions=noun_exclusions,
        )
        elapsed("prompt_preparation_total_ms", stage)
        if not prompt_template:
            raise HTTPException(status_code=400, detail="Prompt preparation failed.")

        if noun_exclusion_memory:
            rewrite_stage = "noun_reservation"
            reserved_entries = set()
            reserve_concepts = (variant_plan or {}).get("prompt") or offered_concepts or ()
            reserve_raw = list((variant_plan or {}).get("raw") or ())
            for text in ingredient_texts(
                    reserve_concepts, offered_descriptors or (), reserve_raw,
                    prompt_template.get("contenders", {})):
                reserved_entries.update(identity_entries(text))
            source_protected = protected_words(source_text)
            reserved_entries = {entry for entry in reserved_entries
                                if not any(word in source_protected
                                           for word in entry.split(":", 1)[1].split())}
            if not noun_exclusion_memory.reserve(rewrite_id, reserved_entries):
                conflict = noun_exclusion_memory.last_reservation_conflict
                completed_entries = set(conflict.get("completed_entries", ()))
                snapshot_conflicts = sorted(completed_entries & noun_exclusions)
                introduced_conflicts = sorted(completed_entries - noun_exclusions)
                conflict_origin = (
                    "already_excluded_at_selection"
                    if snapshot_conflicts and not introduced_conflicts else
                    "introduced_after_selection"
                    if introduced_conflicts and not snapshot_conflicts else
                    "mixed" if completed_entries else "not_completed_history"
                )
                conflict.update({
                    "origin": conflict_origin,
                    "selection_snapshot_entries": snapshot_conflicts,
                    "introduced_after_selection": introduced_conflicts,
                })
                print("[noun-reservation-diagnostic] " + json.dumps({
                    "rewrite_id": str(rewrite_id),
                    "reason": conflict.get("reason", "unknown"),
                    "origin": conflict_origin,
                    "completed_entries": conflict.get("completed_entries", ())[:12],
                    "selection_snapshot_entries": snapshot_conflicts[:12],
                    "introduced_after_selection": introduced_conflicts[:12],
                    "active_entries": conflict.get("active_entries", ())[:12],
                    "active_owner_count": conflict.get("active_owner_count", 0),
                    "requested_entries": len(reserved_entries),
                }, sort_keys=True))
                noun_exclusion_snapshot["reservation_conflict"] = conflict
                raise NounExclusionExhausted(
                    "Selected comedy ingredients became unavailable before generation "
                    f"({conflict.get('reason', 'unknown')}). Please try MUNGE IT again.")
            noun_exclusion_snapshot["reserved_ingredients"] = len(reserved_entries)

        rewrite_stage = "first_provider_call"
        stage = monotonic()
        initial_response = send_prompt(prompt_template["full_prompt"])
        elapsed("first_rewrite_provider_ms", stage)
        if not initial_response:
            raise HTTPException(status_code=500, detail="OpenAI generation failed.")

        log_overlap(prompt_template["preprocessing"], initial_response)

        result = format_shizzalise_result(initial_response)
        if not result:
            raise HTTPException(status_code=500, detail="Generated title or extract is invalid.")
        first_pass_result = dict(result)

        # Pass 2: copy-editing.  Receives only pass-1 output — never source text.
        # Falls back to the pass-1 result on any failure.
        if repetition_config.enabled:
            source_text_for_replacement = "\n".join(
                str(source.get(key, "")) for key in ("title", "description", "extract"))
            if lexical_memory is None:
                try:
                    # Phase 4T reuses the same bounded per-pet ledger without enabling
                    # Phase 4M's ingredient ranking or first-pass guidance.
                    lexical_memory = LexicalExposureMemory(
                        comedy_lexical_exposure_collection(), active_pet,
                        LexicalExposureConfig("evaluation"))
                    lexical_memory.load()
                    lexical_penalties = lexical_memory.penalties(
                        source_text_for_replacement)
                    lexical_snapshot = {
                        "recent_events": len(lexical_memory.events),
                        "penalties": dict(lexical_penalties.most_common(80)),
                    }
                except Exception as lexical_exc:
                    print("[repetition-replacement] lexical history unavailable; "
                          "continuing with ordinary copy edit: "
                          f"{type(lexical_exc).__name__}")
                    lexical_memory = None
                    lexical_penalties = None
            current_raw = list((variant_plan or {}).get("raw") or ())
            for ingredient in ((theme_ingredient_builder.selected
                                if theme_ingredient_builder else ())):
                if ingredient not in current_raw:
                    current_raw.append(ingredient)
            repetition_plan, repetition_snapshot = build_repetition_replacement(
                first_pass=first_pass_result,
                source_text=source_text_for_replacement,
                lexical_penalties=lexical_penalties or {},
                concepts=(variant_plan or {}).get("generated") or offered_concepts or (),
                descriptors=offered_descriptors or (),
                raw_ingredients=current_raw,
                thematic_ingredients=(theme_ingredient_builder.selected
                                      if theme_ingredient_builder else ()),
                names=invented_names or (),
                places=prompt_template.get("contenders", {}).get("places", ()),
                config=repetition_config,
                phrase_config=phrase_replacement_config,
            )
            repetition_snapshot["recent_exposure_signals"] = dict(
                (lexical_penalties or {}).most_common(80)
                if hasattr(lexical_penalties, "most_common") else
                list((lexical_penalties or {}).items())[:80])
        rewrite_stage = "editor_provider_call"
        stage = monotonic()
        editor_enabled = comedy_editor_enabled()
        editor_target = comedy_editor_word_target(
            first_pass_result.get("crazyReplacement1Extract", ""))
        first_pass_word_count = editor_target["first_pass_word_count"]
        comedy_editor_snapshot = {
            "enabled": editor_enabled,
            "invoked": False,
            "model": comedy_editor_model() if editor_enabled else "",
            "succeeded": False,
            "fell_back": False,
            "first_pass_word_count": first_pass_word_count,
            "target_word_count": editor_target["target_word_count"],
            "target_min_word_count": editor_target["target_min_word_count"],
            "target_max_word_count": editor_target["target_max_word_count"],
        }
        if editor_enabled:
            comedy_editor_snapshot["invoked"] = True
            polished = comedy_editor_pass(source, result, editor_target)
            comedy_editor_snapshot["succeeded"] = bool(polished)
            comedy_editor_snapshot["fell_back"] = not bool(polished)
        else:
            polished = (copy_edit_pass(result, repetition_replacement=repetition_plan)
                        if repetition_plan else copy_edit_pass(result))
        elapsed("copy_edit_provider_ms", stage)
        if polished:
            result = polished

        final_word_count = comedy_editor_word_target(
            result.get("crazyReplacement1Extract", ""))["first_pass_word_count"]
        comedy_editor_snapshot["final_word_count"] = final_word_count
        comedy_editor_snapshot["achieved_word_count"] = final_word_count
        comedy_editor_snapshot["percentage_reduction"] = (
            round((first_pass_word_count - final_word_count) * 100 / first_pass_word_count, 1)
            if first_pass_word_count else None)

        finish_repetition_diagnostic(
            repetition_snapshot, first_pass_result, result, fell_back=not bool(polished))

        result = dict(result)
        result['crazyReplacement1Title'] = final_title(
            result['crazyReplacement1Extract'],
            result['crazyReplacement1Title'],
        )

        full_result = {
            **source,
            **result,
            "creationUser": creationUser,
            "contenders": prompt_template.get("contenders", {}),
            "munge_engine": plan.engine.value,
        }

        try:
            rewrite_stage = "persistence"
            stage = monotonic()
            full_result = store.complete_draft(
                rewrite_id,
                active_pet,
                full_result,
                before_save=lambda: claim_used_words(prompt_template.get('contenders', {}), result),
            )
            elapsed("persistence_and_word_claim_ms", stage)
        except WordClaimConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        if full_result is None:
            raise HTTPException(status_code=409, detail='Draft superseded by a newer rewrite.')
    except Exception as exc:
        if name_registry:
            name_registry.release(name_selection_key)
        if concept_registry:
            concept_registry.release(concept_selection_key)
        if descriptor_registry:
            descriptor_registry.release(descriptor_selection_key)
        if noun_exclusion_memory:
            noun_exclusion_memory.release(rewrite_id)
        print("[rewrite-diagnostic] " + json.dumps({
            "status": "rewrite_error",
            "stage": rewrite_stage,
            "exception": type(exc).__name__,
            "http_status": getattr(exc, "status_code", None),
            "rewrite_id": str(rewrite_id),
            "provider_entered": rewrite_stage in {
                "first_provider_call", "editor_provider_call", "persistence"},
            "noun_reservations": len(
                getattr(noun_exclusion_memory, "reservations", ()) or ()),
        }, sort_keys=True, default=str))
        log_timings("rewrite_error")
        if isinstance(exc, RewriteProviderQuotaExhausted):
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        if isinstance(exc, NounExclusionExhausted):
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        raise

    tracking_started = monotonic()
    raw_ingredients = list((variant_plan or {}).get("raw") or ())
    for ingredient in ((theme_ingredient_builder.selected
                        if theme_ingredient_builder else ())):
        if ingredient not in raw_ingredients:
            raw_ingredients.append(ingredient)
    topic_event = None
    if topic_memory:
        topic_event = build_topic_event(
            rewrite_id, result, source, invented_names or (),
            name_registry.offered_family_map(name_selection_key) if name_registry else {},
            ((variant_plan or {}).get("generated") or offered_concepts or ()),
            offered_descriptors or (),
        )
    if final_joke_memory:
        try:
            final_joke_memory.accept(
                rewrite_id, result['crazyReplacement1Title'],
                result['crazyReplacement1Extract'], source_text,
            )
            timings["final_joke_accept"] = final_joke_memory.last_metrics
        except Exception as exc:
            print("[final-jokes] accepted rewrite saved; memory update failed: "
                  f"{type(exc).__name__}")
    if name_registry:
        try:
            name_registry.accept(
                name_selection_key, rewrite_id, invented_names,
                result['crazyReplacement1Title'], result['crazyReplacement1Extract'],
            )
        except Exception as exc:
            # A tracking outage must not discard a successfully paid-for rewrite.
            print(f"[invented-names] accepted rewrite saved; cooldown update failed: {type(exc).__name__}")
            name_registry.release(name_selection_key)
    if concept_registry:
        try:
            concept_registry.accept(
                concept_selection_key, rewrite_id,
                (variant_plan or {}).get("generated") or offered_concepts,
                result['crazyReplacement1Title'], result['crazyReplacement1Extract'], source_text,
            )
            timings["concept_accept"] = getattr(concept_registry, "last_accept_metrics", {})
        except Exception as exc:
            print(f"[concepts] accepted rewrite saved; cooldown update failed: {type(exc).__name__}")
            concept_registry.release(concept_selection_key)
    if descriptor_registry:
        try:
            descriptor_registry.accept(
                descriptor_selection_key, rewrite_id,
                leased_descriptors or offered_descriptors,
                result['crazyReplacement1Title'], result['crazyReplacement1Extract'], source_text,
            )
            timings["descriptor_accept"] = getattr(descriptor_registry, "last_accept_metrics", {})
        except Exception as exc:
            print(f"[descriptors] accepted rewrite saved; cooldown update failed: {type(exc).__name__}")
            descriptor_registry.release(descriptor_selection_key)
    elapsed("accepted_use_and_cooldown_ms", tracking_started)
    if topic_memory and topic_event:
        try:
            topic_memory.record(topic_event)
            timings["topic_memory_update"] = topic_memory.last_metrics
        except Exception as topic_exc:
            print("[comedy-topics] persisted rewrite saved; memory update failed: "
                  f"{type(topic_exc).__name__}")
    if lexical_memory:
        try:
            lexical_event = build_lexical_event(
                rewrite_id, source_text,
                first_pass_result.get('crazyReplacement1Title', ''),
                first_pass_result.get('crazyReplacement1Extract', ''),
                result['crazyReplacement1Title'], result['crazyReplacement1Extract'],
                (variant_plan or {}).get("generated") or offered_concepts or (),
                offered_descriptors or (), raw_ingredients,
            )
            lexical_memory.record(lexical_event)
            timings["lexical_exposure_update"] = lexical_memory.last_metrics
        except Exception as lexical_exc:
            print("[comedy-lexical] persisted rewrite saved; memory update failed: "
                  f"{type(lexical_exc).__name__}")
    if thematic_memory and (thematic_config.enabled or
                            (theme_ingredient_builder and
                             theme_ingredient_builder.selected)):
        try:
            theme_event = thematic_event(
                rewrite_id, thematic_domains,
                f"{result['crazyReplacement1Title']}\n{result['crazyReplacement1Extract']}",
                source_text,
            )
            thematic_memory.record(theme_event)
            thematic_snapshot["influenced_domains"] = theme_event["influenced"]
            timings["thematic_diversity_update"] = thematic_memory.last_metrics
        except Exception as thematic_exc:
            print("[comedy-themes] persisted rewrite saved; memory update failed: "
                  f"{type(thematic_exc).__name__}")
    if theme_ingredient_memory and theme_ingredient_builder:
        try:
            ingredient_event = theme_ingredient_event(
                rewrite_id, theme_ingredient_builder.selected)
            theme_ingredient_memory.record(ingredient_event)
            timings["theme_ingredient_memory_update"] = (
                theme_ingredient_memory.last_metrics)
        except Exception as theme_ingredient_exc:
            print("[theme-ingredients] persisted rewrite saved; memory update failed: "
                  f"{type(theme_ingredient_exc).__name__}")
    if noun_exclusion_memory:
        try:
            final_text = f"{result['crazyReplacement1Title']}\n{result['crazyReplacement1Extract']}"
            selected_texts = list(ingredient_texts(
                (variant_plan or {}).get("prompt") or offered_concepts or (),
                offered_descriptors or (), raw_ingredients,
                prompt_template.get("contenders", {})))
            violation_attribution = attribute_violations(
                final_text, noun_exclusions, selected_texts, source_text)
            new_entries = extract_final_entries(
                title=result['crazyReplacement1Title'],
                body=result['crazyReplacement1Extract'], source_text=source_text,
                concepts=(variant_plan or {}).get("prompt") or offered_concepts or (),
                descriptors=offered_descriptors or (), raw=raw_ingredients,
                contenders=prompt_template.get("contenders", {}),
                names=invented_names or (),
                places=prompt_template.get("contenders", {}).get("places", ()),
            )
            recent_identities = discover_recent_identities(final_text, source_text)
            recent_constructions = discover_used_constructions(
                final_text, source_text,
                (variant_plan or {}).get("prompt") or offered_concepts or (),
                offered_descriptors or ())
            noun_exclusion_memory.complete(
                rewrite_id, new_entries, recent_identities=recent_identities,
                recent_constructions=recent_constructions)
            noun_exclusion_snapshot.update({
                **violation_attribution,
                "newly_extracted": sorted(new_entries),
                "recent_identities": recent_identities,
                "recent_constructions": recent_constructions,
                "prevented_ingredient_candidates": sum(
                    int(metrics.get("noun_exclusion_rejected", 0))
                    for metrics in (
                        getattr(concept_registry, "last_metrics", {}),
                        getattr(descriptor_registry, "last_metrics", {}),
                    )) + int(timings.get("noun_exclusion_legacy_rejected", 0)) +
                    int((theme_ingredient_builder.last_metrics.get("rejected", {})
                         if theme_ingredient_builder else {}).get("noun_exclusion", 0)),
            })
        except Exception as noun_exc:
            noun_exclusion_memory.release(rewrite_id)
            print("[noun-exclusion] persisted rewrite saved; memory update failed: "
                  f"{type(noun_exc).__name__}")
    if audit_logger:
        try:
            if lexical_penalties:
                influenced = []
                for kind, items, field in (
                    ("concept", (variant_plan or {}).get("generated") or offered_concepts or (), "phrase"),
                    ("descriptor", offered_descriptors or (), "phrase"),
                    ("raw", raw_ingredients, "text"),
                ):
                    for item in items:
                        score = text_penalty(item.get(field, ""), lexical_penalties)
                        if score:
                            influenced.append({"kind": kind, "text": item.get(field, ""),
                                               "penalty": score})
                lexical_snapshot["selected_with_penalty"] = influenced
            timings["audit_snapshot_total_ms"] = round(
                (monotonic() - request_started) * 1000, 2)
            audit_logger.append(build_audit_record(
                rewrite_id=rewrite_id,
                source=source,
                result=result,
                names=invented_names,
                concepts=(variant_plan or {}).get("generated") or offered_concepts,
                descriptors=offered_descriptors,
                contenders=prompt_template.get("contenders", {}),
                timings=timings,
                raw_ingredients=raw_ingredients,
                comparison_variant=variant_config.label,
                first_pass=first_pass_result,
                lexical_context=lexical_snapshot,
                thematic_context=thematic_snapshot,
                theme_ingredient_context=theme_ingredient_snapshot,
                repetition_replacement_context=repetition_snapshot,
                noun_exclusion_context=noun_exclusion_snapshot,
                comedy_editor_context=comedy_editor_snapshot,
            ))
        except Exception as audit_exc:
            # The local audit is diagnostic and cannot invalidate persisted work.
            print("[comedy-audit] persisted rewrite was not logged: "
                  f"{type(audit_exc).__name__}")
    # New drafts live only in the session's SQLite slot. Legacy JSON is not an archive.

    log_timings("completed")
    return full_result

# ✅ 5. GET SHIZZALISED RESULT
@router.get("/get_shizz_data")
def get_shizz_data():
    if not os.path.exists(TEMP_SHIZZ_FILE):
        raise HTTPException(status_code=404, detail="No shizzalised data found.")
    with open(TEMP_SHIZZ_FILE, "r") as f:
        return json.load(f)


class ImageRequest(BaseModel):
    rewrite_id: str


def _owned_image_ids(rewrite_id, state):
    """Return only UUID image keys recorded in this server-owned rewrite state."""
    owned = {rewrite_id}
    def add(value):
        try:
            owned.add(str(UUID(str(value))))
        except (ValueError, TypeError, AttributeError):
            pass
    result = state.get('result') or {}
    url = result.get('image_url', '')
    if isinstance(url, str) and url.startswith('/generated-images/') and url.endswith('.png'):
        add(url.removeprefix('/generated-images/').removesuffix('.png'))
    for field in ('image_attempt', 'image_redo'):
        add((state.get(field) or {}).get('image_id'))
    for field in ('image_attempt_history', 'image_redo_history'):
        for attempt in state.get(field) or []:
            add((attempt or {}).get('image_id'))
    for video in [state.get('video'), *(state.get('video_history') or [])]:
        add(((video or {}).get('end_frame') or {}).get('image_id'))
    return owned


@router.delete('/creation/{rewrite_id}')
def delete_creation(rewrite_id: str, active_pet: str = Cookie(None)):
    """Delete one owner-checked rewrite and only its deterministically owned media."""
    if not active_pet:
        raise HTTPException(401, 'No active pet selected.')
    try:
        key = str(UUID(rewrite_id))
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(404, 'Creation unavailable.') from None
    if key != rewrite_id:
        raise HTTPException(404, 'Creation unavailable.')

    collection = entries_collection()
    entry = None
    with store.transaction() as db:
        state = read_image_rewrite(db, key, active_pet, allow_discarded=True)
        if state.get('deleted'):
            raise HTTPException(410, 'Creation already deleted.')
        ownership = {'rewrite_id': key, '$or': [
            {'image_owner': active_pet},
            {'image_owner': {'$exists': False}, 'creationUser': active_pet},
        ]}
        entry_id = state.get('entry_id')
        if entry_id:
            if not ObjectId.is_valid(entry_id):
                raise HTTPException(409, 'Creation identity is invalid; nothing was deleted.')
        entries = list(collection.find(ownership).limit(2))
        if len(entries) > 1:
            raise HTTPException(409, 'Creation identity is ambiguous; nothing was deleted.')
        entry = entries[0] if entries else None
        if entry and entry_id and entry['_id'] != ObjectId(entry_id):
            raise HTTPException(409, 'Creation identity does not match; nothing was deleted.')
        image_ids = _owned_image_ids(key, state)
        if entry:
            result = collection.delete_one({'_id': entry['_id'], **ownership})
            if result.deleted_count != 1:
                raise HTTPException(409, 'Creation changed while deletion was requested.')
        # A tombstone prevents late image/video workers from resurrecting this UUID.
        store.save(db, key, {'owner': active_pet, 'entry_id': None, 'discarded': True,
                             'deleted': True, 'result': {'rewrite_id': key}})
        db.execute('DELETE FROM draft_slots WHERE owner=? AND rewrite_id=?', (active_pet, key))

    failures = []
    if entry:
        try:
            from newsmuncher.services.jingles import service as jingles
            jingles.retire_deleted(collection, entry)
        except Exception:
            failures.append('jingle')
        narration = GENERATED_NARRATION_DIR / f"{entry['_id']}.mp3"
        try:
            if narration.is_file() and not narration.is_symlink():
                narration.unlink()
        except OSError:
            failures.append('narration')
    for image_id in image_ids:
        path = image_path(image_id)
        try:
            if path.is_file() and not path.is_symlink():
                path.unlink()
        except OSError:
            failures.append(f'image:{image_id}')
    try:
        from newsmuncher.services.video import service as videos
        videos.remove_local_media(key)
    except (OSError, ValueError):
        failures.append('video')
    if os.path.exists(TEMP_SHIZZ_FILE):
        try:
            with open(TEMP_SHIZZ_FILE) as file:
                current = json.load(file)
            if current.get('rewrite_id') == key:
                os.remove(TEMP_SHIZZ_FILE)
        except (OSError, ValueError, TypeError):
            failures.append('temporary state')
    if failures:
        raise HTTPException(500, 'Creation deleted, but some local media needs operator cleanup: '
                            + ', '.join(failures))
    return {'deleted': True, 'rewrite_id': key}


def read_image_rewrite(db, rewrite_id, owner, allow_discarded=False):
    try:
        state = store.read(db, rewrite_id, owner)
        if state.get('discarded') and not allow_discarded:
            raise HTTPException(status_code=410, detail='Draft discarded.')
        return state
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))


def persist_banked_image(state, metadata):
    response = requests.patch(
        f"{ENTRIES_API_BASE_URL}/entry/{state['entry_id']}/image",
        json={**metadata, 'rewrite_id': state['result']['rewrite_id']},
        cookies={'active_pet': state['owner']}, timeout=15)
    response.raise_for_status()


def sync_image_metadata(rewrite_id, owner):
    # Local success is already durable. DB synchronization must not lose the image.
    with store.transaction() as db:
        state = read_image_rewrite(db, rewrite_id, owner)
        if state['entry_id'] and not state.get('image_synced'):
            try:
                persist_banked_image(state, {key: state['result'].get(key) for key in IMAGE_FIELDS})
                state['image_synced'] = True
                store.save(db, rewrite_id, state)
            except requests.RequestException:
                # A subsequent image/status/bank request can retry metadata sync only.
                pass


@router.post('/generate_image')
def generate_image(payload: ImageRequest, active_pet: str = Cookie(None)):
    cached = None
    with store.transaction() as db:
        state = read_image_rewrite(db, payload.rewrite_id, active_pet)
        if state.get('generating'):
            raise HTTPException(status_code=409, detail='Rewrite is not ready.')
        if state['result'].get('image_url'):
            # Even partial legacy metadata must not trigger another paid image.
            defaults = dict(image_prompt=build_image_prompt(state['result']), image_model='unknown',
                            image_provider='unknown', image_generated_at=None, image_style=None)
            cached = {key: state['result'].get(key, defaults.get(key)) for key in IMAGE_FIELDS}
            state['result'].update(cached)
            store.save(db, payload.rewrite_id, state)
        else:
            prompt = build_image_prompt(state['result'])
            attempt = {**dict(image_id=payload.rewrite_id, prompt=prompt, model=IMAGE_MODEL, quality=IMAGE_QUALITY, size=IMAGE_SIZE),
                       **(state.get('image_attempt') or {})}
            try:
                cached = recover_image(attempt.get('image_id', payload.rewrite_id), attempt)
            except ValueError as exc:
                raise HTTPException(status_code=409, detail=str(exc)) from exc
            if cached:
                state['result'].update(cached)
                state['image_attempt'] = {**attempt, 'status': 'complete'}
                store.save(db, payload.rewrite_id, state)
            elif state.get('image_attempt'):
                raise HTTPException(status_code=409, detail={
                    'code': 'image_outcome_uncertain',
                    'message': 'Previous image generation had an uncertain outcome.',
                    'attempt_id': state['image_attempt'].get('image_id'),
                    'rewrite_id': payload.rewrite_id,
                })
            else:
                # Commit before contacting OpenAI. Never clear this marker on failure.
                image_style = choose_image_style()
                prompt = build_image_prompt(state['result'], image_style)
                attempt.update(prompt=prompt, image_style=image_style, stage='main',
                               created_at=datetime.now(timezone.utc).isoformat())
                state['image_attempt'] = {**attempt, 'status': 'started'}
                store.save(db, payload.rewrite_id, state)
    if cached:
        sync_image_metadata(payload.rewrite_id, active_pet)
        return cached
    while True:
        try:
            attempt['provider_call_entered_at'] = datetime.now(timezone.utc).isoformat()
            with store.transaction() as db:
                state = read_image_rewrite(db, payload.rewrite_id, active_pet, allow_discarded=True)
                if (state.get('image_attempt') or {}).get('image_id') == attempt['image_id']:
                    state['image_attempt'].update(attempt)
                    store.save(db, payload.rewrite_id, state)
            metadata = get_provider().generate_image(attempt['prompt'], attempt['image_id'])
            attempt['provider_response_received_at'] = datetime.now(timezone.utc).isoformat()
            metadata['image_style'] = attempt['image_style']
            with store.transaction() as db:
                state = read_image_rewrite(db, payload.rewrite_id, active_pet, allow_discarded=True)
                if state.get('discarded'):
                    image_path(attempt['image_id']).unlink(missing_ok=True)
                    raise HTTPException(status_code=410, detail='Draft discarded; generated file removed.')
                state['result'].update(metadata)
                state['image_attempt'].update(attempt, status='complete',
                    persistence_completed_at=datetime.now(timezone.utc).isoformat())
                store.save(db, payload.rewrite_id, state)
            break
        except DefinitiveImageFailure as exc:
            terminal = False
            with store.transaction() as db:
                state = read_image_rewrite(db, payload.rewrite_id, active_pet, allow_discarded=True)
                current = state.get('image_attempt') or {}
                if current.get('image_id', payload.rewrite_id) != attempt['image_id']:
                    raise HTTPException(409, 'Image attempt changed; no automatic paid retry.') from exc
                current['status'] = 'definitive_failed'
                if current.get('retry_count', 0) >= 1:
                    state['image_attempt'] = current
                    store.save(db, payload.rewrite_id, state)
                    terminal = True
                else:
                    state.setdefault('image_attempt_history', []).append(current)
                    attempt = {**current, 'image_id': str(uuid4()), 'status': 'started', 'retry_count': 1,
                               'stage': 'main', 'created_at': datetime.now(timezone.utc).isoformat()}
                    for field in ('provider_call_entered_at', 'provider_response_received_at',
                                  'persistence_completed_at', 'failure_category', 'failure_message'):
                        attempt.pop(field, None)
                    state['image_attempt'] = attempt
                    store.save(db, payload.rewrite_id, state)  # Retry claim precedes the second paid call.
            if terminal:
                raise HTTPException(422, 'Image generation failed twice. Use REDO IMAGE to try again.') from exc
        except BadRequestError as exc:
            with store.transaction() as db:
                state = read_image_rewrite(db, payload.rewrite_id, active_pet, allow_discarded=True)
                current = state.get('image_attempt') or {}
                if current.get('image_id') == attempt['image_id']:
                    current.update(status='definitive_failed', **safe_provider_failure(exc))
                    store.save(db, payload.rewrite_id, state)
            raise HTTPException(422, 'Image request was rejected by the provider; no automatic retry.') from exc
        except Exception as exc:
            with store.transaction() as db:
                state = read_image_rewrite(db, payload.rewrite_id, active_pet, allow_discarded=True)
                if state.get('discarded'):
                    image_path(attempt['image_id']).unlink(missing_ok=True)
                current = state.get('image_attempt') or {}
                if current.get('image_id') == attempt['image_id']:
                    current.update(status='uncertain', failure_category=type(exc).__name__,
                                   failure_message=f'Image provider or local persistence raised {type(exc).__name__}.')
                    store.save(db, payload.rewrite_id, state)
            if isinstance(exc, HTTPException):
                raise
            raise HTTPException(status_code=502, detail='Image outcome uncertain. Use REDO IMAGE only if you choose to make another paid attempt.') from exc
    sync_image_metadata(payload.rewrite_id, active_pet)
    return metadata


class RedoImageRequest(ImageRequest):
    previous_image_url: str | None = Field(default=None, max_length=300)
    replace_nomination: bool = False


class UncertainImageRetryRequest(ImageRequest):
    attempt_id: UUID
    confirmed: bool


@router.post('/retry_uncertain_image')
def retry_uncertain_image(payload: UncertainImageRetryRequest, active_pet: str = Cookie(None)):
    """Spend once only after an owner explicitly accepts an uncertain prior outcome."""
    if not payload.confirmed:
        raise HTTPException(400, 'Explicit retry confirmation is required.')
    with store.transaction() as db:
        state = read_image_rewrite(db, payload.rewrite_id, active_pet)
        if state['result'].get('image_url'):
            return {key: state['result'].get(key) for key in IMAGE_FIELDS}
        unresolved_redo = state.get('image_redo') or {}
        if unresolved_redo and unresolved_redo.get('status') != 'complete':
            raise HTTPException(409, 'A separate image replacement attempt is unresolved; operator review is required.')
        previous = state.get('image_attempt') or {}
        if str(previous.get('image_id')) != str(payload.attempt_id):
            raise HTTPException(409, 'Image attempt changed; retry authorisation was not used.')
        if previous.get('status') not in ('started', 'uncertain'):
            raise HTTPException(409, 'This image attempt is not eligible for uncertain-outcome recovery.')
        try:
            recovered = recover_image(previous['image_id'], previous)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        if recovered:
            state['result'].update(recovered)
            state['image_attempt'] = {**previous, 'status': 'complete'}
            store.save(db, payload.rewrite_id, state)
            return recovered
        state.setdefault('image_attempt_history', []).append({
            **previous, 'status': 'superseded_by_confirmed_retry'
        })
        style = choose_image_style()
        attempt = dict(image_id=str(uuid4()), image_style=style,
                       prompt=build_image_prompt(state['result'], style),
                       model=IMAGE_MODEL, quality=IMAGE_QUALITY, size=IMAGE_SIZE,
                       status='started', stage='main', retry_of=previous['image_id'],
                       created_at=datetime.now(timezone.utc).isoformat(),
                       confirmed_at=datetime.now(timezone.utc).isoformat())
        # This transaction is the single-use claim. A concurrent/replayed request
        # can no longer match payload.attempt_id and therefore cannot spend again.
        state['image_attempt'] = attempt
        store.save(db, payload.rewrite_id, state)
    try:
        attempt['provider_call_entered_at'] = datetime.now(timezone.utc).isoformat()
        with store.transaction() as db:
            state = read_image_rewrite(db, payload.rewrite_id, active_pet)
            if (state.get('image_attempt') or {}).get('image_id') == attempt['image_id']:
                state['image_attempt'].update(attempt)
                store.save(db, payload.rewrite_id, state)
        metadata = get_provider().generate_image(attempt['prompt'], attempt['image_id'])
        attempt['provider_response_received_at'] = datetime.now(timezone.utc).isoformat()
        metadata['image_style'] = attempt['image_style']
        with store.transaction() as db:
            state = read_image_rewrite(db, payload.rewrite_id, active_pet)
            current = state.get('image_attempt') or {}
            if current.get('image_id') != attempt['image_id']:
                raise HTTPException(409, 'Image attempt changed; generated result was not attached.')
            state['result'].update(metadata)
            current.update(attempt, status='complete',
                           persistence_completed_at=datetime.now(timezone.utc).isoformat())
            store.save(db, payload.rewrite_id, state)
    except DefinitiveImageFailure as exc:
        with store.transaction() as db:
            state = read_image_rewrite(db, payload.rewrite_id, active_pet)
            current = state.get('image_attempt') or {}
            if current.get('image_id') == attempt['image_id']:
                current.update(status='definitive_failed', failure_category=type(exc).__name__,
                               failure_message='Provider returned no usable image.')
                store.save(db, payload.rewrite_id, state)
        raise HTTPException(422, 'Confirmed image retry failed definitively; no further retry was submitted.') from exc
    except BadRequestError as exc:
        # An HTTP 400 is a definite provider response, not an ambiguous transport
        # outcome. Preserve the claim and require a fresh explicit user decision.
        with store.transaction() as db:
            state = read_image_rewrite(db, payload.rewrite_id, active_pet)
            current = state.get('image_attempt') or {}
            if current.get('image_id') == attempt['image_id']:
                current.update(status='definitive_failed', **safe_provider_failure(exc))
                store.save(db, payload.rewrite_id, state)
        raise HTTPException(422, 'Confirmed image retry was rejected by the provider; no automatic retry.') from exc
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise
        with store.transaction() as db:
            state = read_image_rewrite(db, payload.rewrite_id, active_pet)
            current = state.get('image_attempt') or {}
            if current.get('image_id') == attempt['image_id']:
                current.update(status='uncertain', failure_category=type(exc).__name__,
                               failure_message=f'Image provider or local persistence raised {type(exc).__name__}.')
                store.save(db, payload.rewrite_id, state)
        raise HTTPException(502, 'Confirmed image retry outcome is uncertain; no automatic retry.') from exc
    sync_image_metadata(payload.rewrite_id, active_pet)
    return metadata


def finish_image_redo(db, rewrite_id, state, metadata):
    state['result'].update(metadata)
    state['image_redo']['status'] = 'complete'
    state['image_synced'] = False
    # Keep historical claims/files as evidence, but never pair old video with new image.
    if state.get('video'):
        state['video_detached'] = True
    store.save(db, rewrite_id, state)


@router.post('/redo_image')
def redo_image(payload: RedoImageRequest, active_pet: str = Cookie(None)):
    with store.transaction() as db:
        state = read_image_rewrite(db, payload.rewrite_id, active_pet)
        nominated = bool(state.get('entry_id') or state.get('nomination_pending') or state['result'].get('nominated'))
        if nominated and not payload.replace_nomination:
            raise HTTPException(409, 'Nominated images cannot be replaced.')
        previous = state.get('image_redo')
        if previous and previous['previous_image_url'] == payload.previous_image_url:
            if previous['status'] == 'complete':
                return {key: state['result'].get(key) for key in IMAGE_FIELDS}
            raise HTTPException(409, 'Replacement attempt already started; no paid retry.')
        if previous and previous['status'] != 'complete':
            raise HTTPException(409, 'Replacement needs operator review; no paid retry.')
        current_url = state['result'].get('image_url')
        main_attempt = state.get('image_attempt') or {}
        if not current_url and main_attempt.get('status') in ('started', 'uncertain'):
            raise HTTPException(409, 'Main image outcome is uncertain; use the explicit confirmed recovery flow.')
        if state.get('generating') or (current_url and current_url != payload.previous_image_url):
            raise HTTPException(409, 'Current saved image required.')
        if not current_url and (payload.previous_image_url is not None or not state.get('image_attempt')):
            raise HTTPException(409, 'A terminal image attempt is required.')
        style = choose_image_style(exclude=state['result'].get('image_style'))
        attempt = dict(image_id=str(uuid4()), previous_image_url=payload.previous_image_url,
                       image_style=style, prompt=build_image_prompt(state['result'], style),
                       model=IMAGE_MODEL, quality=IMAGE_QUALITY, size=IMAGE_SIZE, status='started')
        if previous:
            state.setdefault('image_redo_history', []).append(previous)
        state['image_redo'] = attempt
        store.save(db, payload.rewrite_id, state)  # Permanent claim before the paid call.
    try:
        metadata = get_provider().generate_image(attempt['prompt'], attempt['image_id'])
        metadata['image_style'] = attempt['image_style']
        with store.transaction() as db:
            state = read_image_rewrite(db, payload.rewrite_id, active_pet)
            # A GET can recover this file before the worker returns. Never overwrite
            # a newer replacement (or a nomination) after such recovery.
            if state['image_redo']['image_id'] != attempt['image_id'] or state['image_redo']['status'] == 'complete':
                return {key: state['result'].get(key) for key in IMAGE_FIELDS}
            finish_image_redo(db, payload.rewrite_id, state, metadata)
        if nominated:
            sync_image_metadata(payload.rewrite_id, active_pet)
            from newsmuncher.services.video import service as videos
            videos.replace(entries_collection(), payload.rewrite_id, active_pet)
        return metadata
    except BadRequestError as exc:
        with store.transaction() as db:
            state = read_image_rewrite(db, payload.rewrite_id, active_pet)
            current = state.get('image_redo') or {}
            if current.get('image_id') == attempt['image_id']:
                current.update(status='definitive_failed', **safe_provider_failure(exc))
                store.save(db, payload.rewrite_id, state)
        raise HTTPException(422, 'Replacement image was rejected by the provider; no automatic retry.') from exc
    except Exception as exc:
        # Preserve the old image and permanent attempt, including uncertain outcomes.
        raise HTTPException(502, 'Replacement unavailable; old image retained. No automatic paid retry.') from exc


@router.get('/loading_images')
def loading_images(active_pet: str = Cookie(None)):
    """Owner-scoped current images only; no generation or metadata mutation."""
    if not active_pet:
        raise HTTPException(401, 'No active pet selected.')
    import random
    urls = {}
    with store.transaction() as db:
        for (encoded,) in db.execute('SELECT state FROM rewrites'):
            state = json.loads(encoded)
            if state.get('owner') != active_pet or state.get('discarded'):
                continue
            url = state.get('result', {}).get('image_url', '')
            try:
                path = image_path(url.removeprefix('/generated-images/').removesuffix('.png'))
                if url == f'/generated-images/{path.name}' and not path.is_symlink() and path.is_file():
                    urls[url] = state.get('entry_id')
            except (ValueError, TypeError, AttributeError):
                continue
    from newsmuncher.services.jingles import service as jingles
    return {'images': [{'image_url': url, 'jingle_url': jingles.saved_url(urls[url])}
                       for url in random.sample(sorted(urls), min(5, len(urls)))]}


@router.get('/image_result/{rewrite_id}')
def get_image_result(rewrite_id: str, active_pet: str = Cookie(None)):
    # Read-only restoration: refreshing never calls a paid provider.
    with store.transaction() as db:
        state = read_image_rewrite(db, rewrite_id, active_pet)
        redo = state.get('image_redo')
        if redo and redo['status'] != 'complete' and not state.get('entry_id'):
            try:
                recovered = recover_image(redo['image_id'], redo)
            except ValueError:
                recovered = None
            if recovered:
                finish_image_redo(db, rewrite_id, state, recovered)
        if not state['result'].get('image_url') or not all(k in state['result'] for k in IMAGE_FIELDS if k != 'image_style'):
            attempt = {**dict(prompt=build_image_prompt(state['result']), model=IMAGE_MODEL),
                       **(state.get('image_attempt') or {})}
            try:
                recovered = recover_image(attempt.get('image_id', rewrite_id), attempt)
            except ValueError:
                recovered = None
            if recovered:
                state['result'].update(recovered)
                store.save(db, rewrite_id, state)
        if state['result'].get('image_url'):
            defaults = dict(image_prompt=build_image_prompt(state['result']), image_model='unknown',
                            image_provider='unknown', image_generated_at=None, image_style=None)
            for key, value in defaults.items():
                state['result'].setdefault(key, value)
            store.save(db, rewrite_id, state)
        result = state['result'].copy()
        result['nominated'] = bool(state.get('entry_id') or result.get('nominated'))
        result['image_redo_pending'] = bool(state.get('image_redo') and state['image_redo']['status'] != 'complete')
        result['image_generation_failed'] = bool(not result.get('image_url') and state.get('image_attempt'))
        uncertain = state.get('image_attempt') or {}
        result['image_outcome_uncertain'] = bool(
            not result.get('image_url') and uncertain.get('status') in ('started', 'uncertain'))
        result['image_attempt_id'] = uncertain.get('image_id') if result['image_outcome_uncertain'] else None
    if result.get('image_url'):
        sync_image_metadata(rewrite_id, active_pet)
    return result


def bank_image_rewrite(request, rewrite_id, payload=None):
    owner = request.cookies.get('active_pet')
    # Persist before HTTP: a timeout may mean Mongo committed successfully.
    with store.transaction() as db:
        state = read_image_rewrite(db, rewrite_id, owner)
        if state.get('generating'):
            raise HTTPException(status_code=409, detail='Rewrite is not ready.')
        if state.get('image_redo') and state['image_redo']['status'] != 'complete':
            raise HTTPException(409, 'Image replacement unresolved; restore status before nomination.')
        if not state['entry_id']:
            state['nomination_pending'] = True
            store.save(db, rewrite_id, state)
    with store.transaction() as db:
        state = read_image_rewrite(db, rewrite_id, owner)
        payload_data = payload.model_dump() if payload is not None else None
        if payload_data is not None:
            saved_title = str(state['result'].get('crazyReplacement1Title') or '')
            saved_body = str(state['result'].get('crazyReplacement1Extract') or '')
            submitted_title = str(payload_data.get('crazyReplacement1Title') or '')
            submitted_body = str(payload_data.get('crazyReplacement1Extract') or '')
            text_changed = submitted_title != saved_title or submitted_body != saved_body
            # The title field is hidden in the Creator UI. If the user edits the
            # article while leaving that generated title untouched, refresh a
            # title whose words no longer occur in the edited article. An
            # explicitly changed title always takes precedence.
            if submitted_title == saved_title and submitted_body != saved_body:
                title_words = {
                    word.rstrip('s') for word in re.findall(r"[a-z0-9']+", submitted_title.lower())
                    if len(word) > 3 and word not in {
                        'about', 'after', 'again', 'from', 'into', 'over', 'that',
                        'their', 'there', 'these', 'this', 'with', 'while',
                    }
                }
                body_words = {
                    word.rstrip('s') for word in re.findall(r"[a-z0-9']+", submitted_body.lower())
                }
                if title_words - body_words:
                    first_sentence = re.split(
                        r"(?<=[.!?])\s+", submitted_body.strip(), maxsplit=1)[0]
                    if first_sentence:
                        payload_data['crazyReplacement1Title'] = final_title(
                            submitted_body, first_sentence)
            if text_changed and (state['result'].get('image_url') or
                                 (state.get('image_attempt') or {}).get('status') == 'complete'):
                previous_attempt = state.pop('image_attempt', None)
                if previous_attempt:
                    state.setdefault('image_attempt_history', []).append({
                        **previous_attempt, 'status': 'invalidated_by_text_edit'})
                for field in IMAGE_FIELDS:
                    state['result'].pop(field, None)
                state['image_synced'] = False
                for image_id in {rewrite_id,
                                 str((previous_attempt or {}).get('image_id') or '')}:
                    if image_id:
                        try:
                            image_path(image_id).unlink(missing_ok=True)
                        except (ValueError, OSError):
                            pass
        if state['entry_id'] and payload is not None and any(
                state['result'].get(key) != value for key, value in payload_data.items()):
            try:
                response = requests.put(f"{ENTRIES_API_BASE_URL}/entry/{state['entry_id']}",
                    params=payload_data, cookies={'active_pet': owner}, timeout=15)
                response.raise_for_status()
                state['result'].update(payload_data)
                store.save(db, rewrite_id, state)
            except requests.RequestException as exc:
                raise HTTPException(status_code=502, detail='Could not update nominated response.') from exc
        if not state['entry_id']:
            if payload is not None:
                state['result'].update(payload_data)
            try:
                response = requests.post(f'{ENTRIES_API_BASE_URL}/create/',
                    json={**state['result'], 'image_owner': owner},
                    cookies={'active_pet': owner}, timeout=15)
                response.raise_for_status()
                state['entry_id'] = response.json()['id']
                state['result']['nominated'] = True
                state['result']['gallery_status'] = 'pending'
                state.pop('nomination_pending', None)
                state['image_synced'] = bool(state['result'].get('image_url'))
                store.save(db, rewrite_id, state)
            except requests.RequestException as exc:
                raise HTTPException(status_code=502, detail='Could not bank rewrite.') from exc
    if state['result'].get('image_url'):
        sync_image_metadata(rewrite_id, owner)
    if state.get('video'):
        from newsmuncher.api.entries import collection
        from newsmuncher.services.video import service as videos
        videos.sync(collection, rewrite_id, owner)
    # Only clear the matching shared preview, never a newer rewrite.
    if os.path.exists(TEMP_SHIZZ_FILE):
        with open(TEMP_SHIZZ_FILE) as f:
            current = json.load(f)
        if current.get('rewrite_id') == rewrite_id:
            os.remove(TEMP_SHIZZ_FILE)
            if os.path.exists(TEMP_FILE):
                os.remove(TEMP_FILE)
    return {'message': 'Data banked successfully!', 'nominated': True,
            'rewrite_id': rewrite_id,
            'crazyReplacement1Title': state['result'].get('crazyReplacement1Title', ''),
            'crazyReplacement1Extract': state['result'].get('crazyReplacement1Extract', ''),
            'image_url': state['result'].get('image_url')}
