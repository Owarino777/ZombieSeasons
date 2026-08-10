"""Audit the project-owned gameplay Blueprint contracts needed by ZombieSeasons Stage 9.

Run from Unreal Editor after Stage 8 extraction is committed:

py "C:/Users/malik/Documents/Unreal Projects/ZombieSeasons/Content/Python/ZombieSeasons/MapGeneration/09a_audit_gameplay_contracts.py"

This script is read-only with respect to project assets and maps. It loads only the small,
explicit gameplay Blueprint set below and writes a focused JSON report that Stage 9B uses
to decide what can be reused directly and what must be wrapped by ZombieSeasons adapters.
"""

from __future__ import annotations

import inspect
import sys
from pathlib import Path
from typing import Any

import unreal


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from zs_generation_common import (  # noqa: E402
    editor_asset_exists,
    fail,
    log,
    show_editor_message,
    warn,
    write_json_report,
)


STAGE = "GameplayContractAudit"

# Explicit project-owned assets only. No Fab/City Sample content is touched by this audit.
TARGETS: tuple[tuple[str, str], ...] = (
    ("fps_character", "/Game/TopDownShooter/Core/BP_FPSCharacter"),
    ("base_character", "/Game/TopDownShooter/Core/BP_Character"),
    ("enemy", "/Game/TopDownShooter/Core/BP_Enemy"),
    ("enemy_controller", "/Game/TopDownShooter/Core/AIC_Enemy"),
    ("enemy_spawner", "/Game/TopDownShooter/Core/BP_EnemySpawner"),
    ("game_mode", "/Game/TopDownShooter/Core/BP_GameMode"),
    ("fps_game_mode", "/Game/TopDownShooter/Core/BP_FPSGameMode"),
    ("damage_interface", "/Game/TopDownShooter/Core/BPI_Damageable"),
    ("game_mode_interface", "/Game/TopDownShooter/Core/BPI_GameMode_MP"),
    ("hud", "/Game/TopDownShooter/Core/WBP_InGameHUD"),
    ("gun", "/Game/TopDownShooter/Core/Weapon/BP_Gun"),
    ("projectile", "/Game/TopDownShooter/Core/Weapon/BP_Projectile"),
)

# We keep the audit focused. Unreal wrappers expose a very large inherited API surface;
# these tokens retain names relevant to the zombie/wave/FPS integration contract.
RELEVANT_TOKENS: tuple[str, ...] = (
    "enemy",
    "spawn",
    "wave",
    "health",
    "damage",
    "dead",
    "death",
    "kill",
    "alive",
    "player",
    "character",
    "controller",
    "pawn",
    "hud",
    "ui",
    "weapon",
    "gun",
    "projectile",
    "ammo",
    "score",
    "start",
    "stop",
    "complete",
    "remaining",
    "count",
    "max",
    "interval",
    "delay",
    "radius",
    "navigation",
    "nav",
    "target",
    "game_mode",
    "gamemode",
    "interface",
)

# Common Blueprint variable spellings. These are probes only; missing properties are
# expected and are not errors. Successful probes give us concrete default values.
PROPERTY_PROBES: tuple[str, ...] = (
    "enemy_class",
    "enemy_to_spawn",
    "enemy_type",
    "enemy_count",
    "enemy_count_max",
    "max_enemies",
    "max_enemy_count",
    "number_of_enemies",
    "remaining_enemies",
    "spawn_count",
    "spawn_interval",
    "spawn_delay",
    "spawn_radius",
    "spawn_distance",
    "wave",
    "wave_index",
    "wave_number",
    "current_wave",
    "max_waves",
    "health",
    "max_health",
    "player_health",
    "is_dead",
    "is_alive",
    "hud",
    "hud_class",
    "in_game_hud",
    "weapon",
    "weapon_class",
    "gun",
    "gun_class",
    "projectile",
    "projectile_class",
    "damage",
    "damage_amount",
    "score",
)


def safe_text(value: Any, *, limit: int = 500) -> str:
    """Serialize an Unreal/Python value without recursively walking UObject graphs."""
    try:
        text = str(value)
    except Exception as error:
        text = f"<unprintable:{type(error).__name__}>"
    if len(text) > limit:
        return text[: limit - 3] + "..."
    return text


def is_relevant_name(name: str) -> bool:
    lowered = name.lower()
    return any(token in lowered for token in RELEVANT_TOKENS)


def classify_attributes(obj: Any) -> dict[str, list[str]]:
    """Split relevant wrapper names into callable/non-callable buckets."""
    functions: list[str] = []
    properties: list[str] = []
    unreadable: list[str] = []

    try:
        names = sorted(set(dir(obj)))
    except Exception:
        return {
            "functions": [],
            "properties": [],
            "unreadable": ["<dir failed>"],
        }

    for name in names:
        if name.startswith("_") or not is_relevant_name(name):
            continue
        try:
            value = getattr(obj, name)
        except Exception:
            unreadable.append(name)
            continue
        if callable(value):
            functions.append(name)
        else:
            properties.append(name)

    return {
        "functions": functions,
        "properties": properties,
        "unreadable": unreadable,
    }


def load_blueprint_class(asset_path: str) -> Any | None:
    """Resolve the generated class using the safest available UE 5.5 editor route."""
    loader = getattr(unreal.EditorAssetLibrary, "load_blueprint_class", None)
    if callable(loader):
        try:
            resolved = loader(asset_path)
            if resolved is not None:
                return resolved
        except Exception as error:
            warn(f"load_blueprint_class failed for {asset_path}: {error}")

    asset = unreal.load_asset(asset_path)
    if asset is None:
        return None

    generated_class = getattr(asset, "generated_class", None)
    if callable(generated_class):
        try:
            return generated_class()
        except Exception as error:
            warn(f"generated_class() failed for {asset_path}: {error}")
    elif generated_class is not None:
        return generated_class

    return None


def get_default_object(generated_class: Any) -> Any | None:
    getter = getattr(unreal, "get_default_object", None)
    if callable(getter):
        try:
            return getter(generated_class)
        except Exception:
            pass

    class_getter = getattr(generated_class, "get_default_object", None)
    if callable(class_getter):
        try:
            return class_getter()
        except Exception:
            pass
    return None


def resolve_super_class(generated_class: Any) -> str | None:
    getter = getattr(generated_class, "get_super_class", None)
    if not callable(getter):
        return None
    try:
        parent = getter()
    except Exception:
        return None
    if parent is None:
        return None
    return safe_text(parent)


def probe_editor_properties(cdo: Any) -> dict[str, str]:
    values: dict[str, str] = {}
    if cdo is None:
        return values
    for name in PROPERTY_PROBES:
        try:
            value = cdo.get_editor_property(name)
        except Exception:
            continue
        values[name] = safe_text(value)
    return values


def find_referencers(asset_path: str) -> list[str]:
    try:
        refs = unreal.EditorAssetLibrary.find_package_referencers_for_asset(
            asset_path,
            load_assets_to_confirm=False,
        )
    except TypeError:
        try:
            refs = unreal.EditorAssetLibrary.find_package_referencers_for_asset(asset_path, False)
        except Exception:
            return []
    except Exception:
        return []
    return sorted(str(item) for item in (refs or []))


def inspect_target(key: str, asset_path: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "key": key,
        "asset_path": asset_path,
        "asset_exists": editor_asset_exists(asset_path),
        "asset_type": None,
        "generated_class": None,
        "super_class": None,
        "asset_relevant_attributes": {},
        "class_relevant_attributes": {},
        "cdo_relevant_attributes": {},
        "cdo_property_probe_values": {},
        "referencers": [],
        "warnings": [],
    }

    if not result["asset_exists"]:
        result["warnings"].append("Asset does not exist.")
        return result

    asset = unreal.load_asset(asset_path)
    if asset is None:
        result["warnings"].append("Asset exists but unreal.load_asset returned None.")
        return result

    result["asset_type"] = type(asset).__name__
    result["asset_relevant_attributes"] = classify_attributes(asset)
    result["referencers"] = find_referencers(asset_path)

    generated_class = load_blueprint_class(asset_path)
    if generated_class is None:
        # Blueprint interfaces and some non-Actor assets may not resolve through the
        # same generated-class route. We still retain their asset-level information.
        result["warnings"].append("Generated class could not be resolved.")
        return result

    result["generated_class"] = safe_text(generated_class)
    result["super_class"] = resolve_super_class(generated_class)
    result["class_relevant_attributes"] = classify_attributes(generated_class)

    cdo = get_default_object(generated_class)
    if cdo is None:
        result["warnings"].append("Class default object could not be resolved.")
        return result

    result["cdo_relevant_attributes"] = classify_attributes(cdo)
    result["cdo_property_probe_values"] = probe_editor_properties(cdo)
    return result


def summarize(targets: dict[str, dict[str, Any]]) -> dict[str, Any]:
    present = [key for key, row in targets.items() if row["asset_exists"]]
    classes = [key for key, row in targets.items() if row["generated_class"]]
    with_probe_values = [
        key for key, row in targets.items() if row["cdo_property_probe_values"]
    ]

    spawner = targets.get("enemy_spawner", {})
    spawner_names = set(
        spawner.get("cdo_relevant_attributes", {}).get("functions", [])
        + spawner.get("cdo_relevant_attributes", {}).get("properties", [])
        + list(spawner.get("cdo_property_probe_values", {}).keys())
    )

    game_mode = targets.get("game_mode", {})
    game_mode_names = set(
        game_mode.get("cdo_relevant_attributes", {}).get("functions", [])
        + game_mode.get("cdo_relevant_attributes", {}).get("properties", [])
    )

    return {
        "target_count": len(targets),
        "assets_present": len(present),
        "generated_classes_resolved": len(classes),
        "targets_with_concrete_property_probes": len(with_probe_values),
        "enemy_spawner_relevant_symbol_count": len(spawner_names),
        "game_mode_relevant_symbol_count": len(game_mode_names),
        "all_required_core_assets_present": all(
            targets[key]["asset_exists"]
            for key in (
                "fps_character",
                "enemy",
                "enemy_controller",
                "enemy_spawner",
                "game_mode",
                "fps_game_mode",
                "damage_interface",
                "game_mode_interface",
            )
        ),
    }


def run() -> None:
    missing_symbols = [
        name
        for name in ("EditorAssetLibrary",)
        if not hasattr(unreal, name)
    ]
    if missing_symbols:
        fail("Required Unreal editor symbols missing: " + ", ".join(missing_symbols))

    log("Stage 9A targeted gameplay-contract audit started. No map actors will be modified.")

    targets: dict[str, dict[str, Any]] = {}
    for key, asset_path in TARGETS:
        log(f"Auditing {key}: {asset_path}")
        targets[key] = inspect_target(key, asset_path)

    summary = summarize(targets)
    report = write_json_report(
        "gameplay_contract_audit.json",
        {
            "status": "PASS" if summary["all_required_core_assets_present"] else "WARN",
            "stage": STAGE,
            "read_only": True,
            "targets": targets,
            "summary": summary,
        },
    )

    message = (
        "Gameplay contract audit completed.\n\n"
        f"Assets present: {summary['assets_present']}/{summary['target_count']}\n"
        f"Generated classes resolved: {summary['generated_classes_resolved']}\n"
        f"Targets with concrete property probes: {summary['targets_with_concrete_property_probes']}\n"
        f"EnemySpawner relevant symbols: {summary['enemy_spawner_relevant_symbol_count']}\n"
        f"GameMode relevant symbols: {summary['game_mode_relevant_symbol_count']}\n"
        f"Core gameplay assets present: {summary['all_required_core_assets_present']}\n\n"
        "No map or Blueprint was modified.\n\n"
        f"Report: {report}"
    )
    log(message.replace("\n", " "))
    show_editor_message(
        "ZombieSeasons World Generation — Stage 9A",
        message,
    )


if __name__ == "__main__":
    try:
        run()
    except Exception as error:
        unreal.log_error(f"[ZombieSeasonsGeneration] Stage 9A failed: {error}")
        raise
