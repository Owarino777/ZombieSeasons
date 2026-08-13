"""Stage 12: automated loaded-greybox acceptance gate for ZombieSeasons."""
from __future__ import annotations
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
import unreal

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from zs_generation_common import (
    GREYBOX_MAP, PLAYABLE_MAX_X, PLAYABLE_MAX_Y, PLAYABLE_MIN_X, PLAYABLE_MIN_Y,
    actor_has_tag, approved_manifest_rows, editor_asset_exists, fail, log,
    show_editor_message, write_json_report,
)

GAMEPLAY_STAGE_TAG = "ZS.Stage.GameplayLayout"
LIGHTING_STAGE_TAG = "ZS.Stage.LightingBaseline"
NAV_STAGE_TAG = "ZS.Stage.NavigationSetup"
HUB_PROTECTED_RADIUS = 6000.0
WORLD_TOLERANCE_CM = 2000.0

EXPECTED_ROLES = {
    "ZombieSpawnCandidate": 211,
    "SpawnGroup": 53,
    "HordeTrigger": 18,
    "LootPoint": 148,
    "Objective": 38,
    "SafeZoneContract": 1,
    "ExtractionControllerContract": 1,
}
EXPECTED_SPAWNS_BY_DISTRICT = {
    "Hub": 8, "Spring": 32, "Summer": 36, "Autumn": 40,
    "Winter": 46, "Sewers": 21, "Extraction": 28,
}
REQUIRED_DISTRICTS = ("Hub", "Spring", "Summer", "Autumn", "Winter", "Sewers", "Extraction")
REQUIRED_RUNTIME_ASSETS = (
    "/Game/TopDownShooter/Core/BP_Enemy",
    "/Game/TopDownShooter/Core/AIC_Enemy",
    "/Game/TopDownShooter/Core/BP_FPSCharacter",
    "/Game/TopDownShooter/Core/BP_FPSGameMode",
    "/Game/TopDownShooter/Core/Weapon/BP_Projectile",
)


def _editor_subsystem():
    value = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    if value is None:
        fail("UnrealEditorSubsystem is unavailable.")
    return value


def _actor_subsystem():
    value = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    if value is None:
        fail("EditorActorSubsystem is unavailable.")
    return value


def _world():
    subsystem = _editor_subsystem()
    if subsystem.get_game_world():
        fail("Stop PIE before Stage 12.")
    value = subsystem.get_editor_world()
    if value is None:
        fail("No editor world is open.")
    return value


def _tags(actor: Any) -> list[str]:
    try:
        return [str(value) for value in (actor.get_editor_property("tags") or [])]
    except Exception:
        return []


def _prefixed(values: list[str], prefix: str) -> list[str]:
    return [value[len(prefix):] for value in values if value.startswith(prefix)]


def _label(actor: Any) -> str:
    try:
        return str(actor.get_actor_label())
    except Exception:
        return str(actor.get_name())


def _nav_projection(world: Any, spawn_actors: list[Any]) -> dict[str, Any]:
    if not hasattr(unreal, "NavigationSystemV1"):
        return {"status": "UNAVAILABLE", "checked": 0, "failed": []}
    extent = unreal.Vector(600.0, 600.0, 1000.0)
    failed_ids = []
    checked = 0
    for actor in spawn_actors:
        stable_ids = _prefixed(_tags(actor), "ZS.Id.")
        stable_id = stable_ids[0] if stable_ids else _label(actor)
        try:
            projected = unreal.NavigationSystemV1.project_point_to_navigation(
                world, actor.get_actor_location(), None, None, extent
            )
        except Exception as error:
            return {
                "status": "UNAVAILABLE", "checked": checked,
                "failed": failed_ids, "error": str(error),
            }
        checked += 1
        if projected is None:
            failed_ids.append(stable_id)
    return {
        "status": "PASS" if not failed_ids else "FAIL",
        "checked": checked,
        "failed": failed_ids,
    }


def main(show_dialog: bool = True):
    world = _world()
    world_path = str(world.get_path_name())
    if not (world_path == GREYBOX_MAP or world_path.startswith(GREYBOX_MAP + ".")):
        fail("L_ZS_World_Greybox must be open for Stage 12.")

    actors = list(_actor_subsystem().get_all_level_actors() or [])
    errors, warnings = [], []

    gameplay = [actor for actor in actors if actor_has_tag(actor, GAMEPLAY_STAGE_TAG)]
    if len(gameplay) != 470:
        errors.append(
            f"Expected all 470 gameplay markers loaded, found {len(gameplay)}. "
            "Load the complete 1.8 x 1.8 km World Partition region and rerun."
        )

    generated = [actor for actor in actors if actor_has_tag(actor, "ZS.Generated")]
    stage_counts, district_counts = Counter(), Counter()
    stable_id_owners = defaultdict(list)
    malformed_generated, outside_bounds = [], []

    for actor in generated:
        actor_tags = _tags(actor)
        stages = _prefixed(actor_tags, "ZS.Stage.")
        districts = _prefixed(actor_tags, "ZS.District.")
        ids = _prefixed(actor_tags, "ZS.Id.")
        for value in stages:
            stage_counts[value] += 1
        for value in districts:
            district_counts[value] += 1
        for value in ids:
            stable_id_owners[value].append(_label(actor))
        if not stages or not districts:
            malformed_generated.append(_label(actor))
        location = actor.get_actor_location()
        if (
            location.x < PLAYABLE_MIN_X - WORLD_TOLERANCE_CM
            or location.x > PLAYABLE_MAX_X + WORLD_TOLERANCE_CM
            or location.y < PLAYABLE_MIN_Y - WORLD_TOLERANCE_CM
            or location.y > PLAYABLE_MAX_Y + WORLD_TOLERANCE_CM
        ):
            outside_bounds.append({
                "actor": _label(actor),
                "location": [location.x, location.y, location.z],
            })

    if malformed_generated:
        errors.append(f"{len(malformed_generated)} generated actor(s) are missing stage/district tags.")
    if outside_bounds:
        errors.append(f"{len(outside_bounds)} generated actor(s) are outside playable XY bounds.")
    for district in REQUIRED_DISTRICTS:
        if district_counts[district] <= 0:
            errors.append(f"Required district has no loaded generated actors: {district}")

    duplicates = {k: v for k, v in stable_id_owners.items() if len(v) > 1}
    if duplicates:
        errors.append(f"Duplicate stable IDs found: {len(duplicates)}")

    role_counts, spawn_counts = Counter(), Counter()
    high_value_count = general_loot_count = 0
    hub_spawn_violations, spawn_actors = [], []

    for actor in gameplay:
        actor_tags = _tags(actor)
        roles = _prefixed(actor_tags, "ZS.MarkerType.")
        districts = _prefixed(actor_tags, "ZS.District.")
        role = roles[0] if roles else ""
        district = districts[0] if districts else ""
        if role:
            role_counts[role] += 1
        if role == "ZombieSpawnCandidate":
            spawn_counts[district] += 1
            spawn_actors.append(actor)
            location = actor.get_actor_location()
            if math.hypot(location.x, location.y) < HUB_PROTECTED_RADIUS:
                hub_spawn_violations.append(_label(actor))
        if role == "LootPoint":
            if "ZS.LootTier.HighValue" in actor_tags:
                high_value_count += 1
            elif "ZS.LootTier.General" in actor_tags:
                general_loot_count += 1

    for role, expected in EXPECTED_ROLES.items():
        actual = role_counts[role]
        if actual != expected:
            errors.append(f"{role}: expected {expected}, got {actual}")
    if general_loot_count != 124:
        errors.append(f"General loot: expected 124, got {general_loot_count}")
    if high_value_count != 24:
        errors.append(f"High-value loot: expected 24, got {high_value_count}")
    for district, expected in EXPECTED_SPAWNS_BY_DISTRICT.items():
        actual = spawn_counts[district]
        if actual != expected:
            errors.append(f"{district} spawns: expected {expected}, got {actual}")
    if hub_spawn_violations:
        errors.append(f"{len(hub_spawn_violations)} zombie spawn marker(s) are inside the 6000 cm Hub radius.")

    lighting = [actor for actor in actors if actor_has_tag(actor, LIGHTING_STAGE_TAG)]
    if len(lighting) != 4:
        errors.append(f"LightingBaseline must have 4 actors, found {len(lighting)}.")

    nav_bounds = [actor for actor in actors if actor_has_tag(actor, NAV_STAGE_TAG)]
    if len(nav_bounds) != 1:
        errors.append(f"NavigationSetup must have 1 tagged bounds actor, found {len(nav_bounds)}.")

    recast = [
        actor for actor in actors
        if "RecastNavMesh" in str(actor.get_class().get_name())
        or str(actor.get_name()).startswith("RecastNavMesh")
    ]
    nav_chunks = [
        actor for actor in actors
        if "NavigationDataChunkActor" in str(actor.get_class().get_name())
        or "NavDataChunk" in str(actor.get_name())
    ]
    if not recast:
        errors.append("No RecastNavMesh actor is loaded.")
    if not nav_chunks:
        errors.append("No World Partition NavigationDataChunkActor is loaded.")

    nav_projection = _nav_projection(world, spawn_actors)
    if nav_projection["status"] == "FAIL":
        failed_count = len(nav_projection["failed"])
        ratio = failed_count / max(1, nav_projection["checked"])
        if ratio > 0.05:
            errors.append(
                f"Nav projection failed for {failed_count}/{nav_projection['checked']} spawn markers."
            )
        else:
            warnings.append(
                f"Nav projection missed {failed_count}/{nav_projection['checked']} spawn markers; final QA item."
            )
    elif nav_projection["status"] == "UNAVAILABLE":
        warnings.append("Python nav projection unavailable; runtime zombie-chase test remains acceptance evidence.")

    missing_runtime_assets = [
        path for path in REQUIRED_RUNTIME_ASSETS
        if not unreal.EditorAssetLibrary.does_asset_exist(path)
    ]
    if missing_runtime_assets:
        errors.append("Missing runtime assets: " + ", ".join(missing_runtime_assets))

    manifest_rows = approved_manifest_rows()
    missing_manifest_assets = [
        row["object_path"] for row in manifest_rows
        if not editor_asset_exists(row["object_path"])
    ]
    if len(manifest_rows) != 201:
        warnings.append(
            f"Approved generator-enabled manifest count is {len(manifest_rows)} instead of frozen 201."
        )
    if missing_manifest_assets:
        errors.append(f"{len(missing_manifest_assets)} approved production asset path(s) do not resolve.")

    game_mode = "UNKNOWN"
    try:
        settings = world.get_world_settings()
        game_mode_class = settings.get_editor_property("default_game_mode")
        game_mode = str(game_mode_class.get_path_name()) if game_mode_class else "None"
        if "BP_FPSGameMode" not in game_mode:
            errors.append(f"World default game mode is not BP_FPSGameMode: {game_mode}")
    except Exception as error:
        warnings.append(f"Unable to inspect WorldSettings GameMode: {error}")

    status = "PASS" if not errors else "FAIL"
    report = write_json_report("generated_world_validation.json", {
        "stage": "12_GENERATED_WORLD_VALIDATION",
        "status": status,
        "map": world_path,
        "loaded_actor_count": len(actors),
        "generated_actor_count": len(generated),
        "stage_counts": dict(stage_counts),
        "district_counts": dict(district_counts),
        "gameplay_marker_count": len(gameplay),
        "role_counts": dict(role_counts),
        "general_loot_count": general_loot_count,
        "high_value_loot_count": high_value_count,
        "spawn_counts_by_district": dict(spawn_counts),
        "hub_spawn_violations": hub_spawn_violations,
        "duplicate_stable_ids": duplicates,
        "malformed_generated_actors": malformed_generated,
        "outside_bounds": outside_bounds,
        "navigation": {
            "recast_count": len(recast),
            "nav_chunk_count": len(nav_chunks),
            "spawn_projection": nav_projection,
        },
        "lighting_baseline_actor_count": len(lighting),
        "runtime_assets_missing": missing_runtime_assets,
        "manifest_approved_generator_enabled_count": len(manifest_rows),
        "manifest_assets_missing": missing_manifest_assets,
        "world_default_game_mode": game_mode,
        "errors": errors,
        "warnings": warnings,
        "manual_later": [
            "60-90 minute objective playthrough",
            "8-12 minute direct traversal timing",
            "horde-arena exit semantics",
            "packaged-build performance",
        ],
    })

    if errors:
        message = (
            f"Stage 12 FAIL: {len(errors)} blocker(s), {len(warnings)} warning(s).\n"
            f"Report: {report}\n\n" + "\n".join(f"- {item}" for item in errors[:8])
        )
        log(message.replace("\n", "  "))
        if show_dialog:
            show_editor_message("ZombieSeasons — Stage 12 FAILED", message)
        fail("Stage 12 validation failed. See generated_world_validation.json.")

    message = (
        "Stage 12 PASS: automated greybox gate passed.\n"
        f"Actors: {len(actors)} | Markers: {len(gameplay)} | Nav chunks: {len(nav_chunks)} | "
        f"Warnings: {len(warnings)}\nReport: {report}"
    )
    log(message.replace("\n", "  "))
    if show_dialog:
        show_editor_message("ZombieSeasons — Stage 12", message)
    return {"status": "PASS", "report": str(report), "warnings": warnings}


if __name__ == "__main__":
    main()
