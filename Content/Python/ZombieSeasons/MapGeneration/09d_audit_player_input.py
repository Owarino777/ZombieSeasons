"""Read-only FPS input and movement audit for ZombieSeasons.

Run from the Unreal Editor Python console:

py "C:/Users/malik/Documents/Unreal Projects/ZombieSeasons/Content/Python/ZombieSeasons/MapGeneration/09d_audit_player_input.py"

The script does not modify assets, mappings, Blueprints, config files, or the map.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import unreal


PROJECT_DIR = Path(unreal.Paths.project_dir())
REPORT_DIR = PROJECT_DIR / "Saved" / "ZombieSeasonsWorldGeneration" / "Validation"
REPORT_PATH = REPORT_DIR / "fps_input_audit.json"
INPUT_CONFIG_PATH = PROJECT_DIR / "Config" / "DefaultInput.ini"

IMC_FPS = "/Game/TopDownShooter/Core/Inputs/IMC_FPS"
FPS_CHARACTER = "/Game/TopDownShooter/Core/BP_FPSCharacter.BP_FPSCharacter_C"
GAME_MODE = "/Game/TopDownShooter/Core/BP_GameMode.BP_GameMode_C"
FPS_GAME_MODE = "/Game/TopDownShooter/Core/BP_FPSGameMode.BP_FPSGameMode_C"


def safe_property(obj: Any, name: str) -> Any:
    try:
        return obj.get_editor_property(name)
    except Exception:
        try:
            return getattr(obj, name)
        except Exception:
            return None


def object_name(obj: Any) -> str:
    if obj is None:
        return "None"
    for getter in ("get_path_name", "get_name"):
        fn = getattr(obj, getter, None)
        if fn:
            try:
                return str(fn())
            except Exception:
                pass
    return str(obj)


def key_name(key: Any) -> str:
    if key is None:
        return "None"
    for attr in ("key_name", "name"):
        value = safe_property(key, attr)
        if value not in (None, ""):
            return str(value)
    return str(key)


def modifier_record(modifier: Any) -> dict[str, Any]:
    record: dict[str, Any] = {
        "class": object_name(modifier.get_class()) if modifier is not None else "None",
        "path": object_name(modifier),
    }
    if modifier is None:
        return record

    # These are the useful Enhanced Input modifier properties for this project.
    for prop in (
        "scalar",
        "x_axis",
        "y_axis",
        "z_axis",
        "order",
        "dead_zone_type",
        "lower_threshold",
        "upper_threshold",
    ):
        value = safe_property(modifier, prop)
        if value is not None:
            try:
                record[prop] = str(value)
            except Exception:
                pass
    return record


def mapping_record(index: int, mapping: Any) -> dict[str, Any]:
    action = safe_property(mapping, "action")
    key = safe_property(mapping, "key")
    modifiers = list(safe_property(mapping, "modifiers") or [])
    triggers = list(safe_property(mapping, "triggers") or [])
    return {
        "index": index,
        "action": object_name(action),
        "action_name": object_name(action).split(".")[-1],
        "key": key_name(key),
        "modifiers": [modifier_record(item) for item in modifiers],
        "triggers": [object_name(item.get_class()) for item in triggers if item is not None],
    }


def audit_mapping_context() -> dict[str, Any]:
    context = unreal.load_asset(IMC_FPS)
    if context is None:
        return {"present": False, "path": IMC_FPS, "mappings": []}

    mappings = list(safe_property(context, "mappings") or [])
    records = [mapping_record(index, mapping) for index, mapping in enumerate(mappings)]

    move_keys = {
        rec["key"]
        for rec in records
        if "MoveAround" in rec["action"]
    }
    look_records = [rec for rec in records if "LookAround" in rec["action"]]

    # Windows reports letter keys by their symbolic names independent of keyboard layout.
    # A French AZERTY-friendly context should contain Z/Q/S/D in addition to any QWERTY
    # fallback mappings.
    azerty_expected = {"Z", "Q", "S", "D"}
    qwerty_expected = {"W", "A", "S", "D"}

    return {
        "present": True,
        "path": IMC_FPS,
        "mapping_count": len(records),
        "mappings": records,
        "move_keys": sorted(move_keys),
        "azerty_complete": azerty_expected.issubset(move_keys),
        "qwerty_complete": qwerty_expected.issubset(move_keys),
        "look_mappings": look_records,
    }


def class_default_object(class_path: str) -> Any | None:
    cls = unreal.load_object(None, class_path)
    if cls is None:
        try:
            cls = unreal.load_class(None, class_path)
        except Exception:
            cls = None
    if cls is None:
        return None
    try:
        return unreal.get_default_object(cls)
    except Exception:
        return None


def audit_character() -> dict[str, Any]:
    cdo = class_default_object(FPS_CHARACTER)
    if cdo is None:
        return {"present": False, "class": FPS_CHARACTER}

    record: dict[str, Any] = {
        "present": True,
        "class": FPS_CHARACTER,
        "cdo": object_name(cdo),
    }

    movement = safe_property(cdo, "character_movement")
    if movement is not None:
        movement_values = {}
        for prop in (
            "max_walk_speed",
            "max_walk_speed_crouched",
            "max_acceleration",
            "braking_deceleration_walking",
            "ground_friction",
            "gravity_scale",
            "jump_z_velocity",
            "air_control",
            "movement_mode",
            "default_land_movement_mode",
        ):
            value = safe_property(movement, prop)
            if value is not None:
                movement_values[prop] = str(value)
        record["character_movement"] = movement_values
    else:
        record["character_movement"] = None

    # Probe exposed Blueprint/CDO variables that may affect input scaling.
    interesting: dict[str, str] = {}
    tokens = ("sens", "mouse", "look", "turn", "move", "speed", "input", "mapping", "context")
    for name in dir(cdo):
        lower = name.lower()
        if not any(token in lower for token in tokens):
            continue
        if name.startswith("_"):
            continue
        value = safe_property(cdo, name)
        if callable(value) or value is None:
            continue
        try:
            text = str(value)
        except Exception:
            continue
        if len(text) <= 500:
            interesting[name] = text
    record["input_related_cdo_properties"] = interesting
    return record


def audit_game_mode(class_path: str) -> dict[str, Any]:
    cdo = class_default_object(class_path)
    if cdo is None:
        return {"present": False, "class": class_path}
    result = {"present": True, "class": class_path}
    for prop in (
        "default_pawn_class",
        "player_controller_class",
        "hud_class",
        "game_state_class",
    ):
        result[prop] = object_name(safe_property(cdo, prop))
    return result


def audit_input_config() -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(INPUT_CONFIG_PATH),
        "present": INPUT_CONFIG_PATH.exists(),
    }
    if not INPUT_CONFIG_PATH.exists():
        return result

    text = INPUT_CONFIG_PATH.read_text(encoding="utf-8", errors="replace")
    for axis in ("MouseX", "MouseY", "Mouse2D"):
        matches = re.findall(
            rf'AxisKeyName="{re.escape(axis)}"[^\n]*?Sensitivity=([0-9.]+)',
            text,
        )
        result[f"{axis}_sensitivities"] = matches

    for option in (
        "bEnableMouseSmoothing",
        "bEnableFOVScaling",
        "bEnableLegacyInputScales",
    ):
        match = re.search(rf"^{option}=(True|False)$", text, re.MULTILINE)
        result[option] = match.group(1) if match else None
    return result


def audit_world() -> dict[str, Any]:
    subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world = subsystem.get_editor_world() if subsystem else None
    if world is None:
        return {"available": False}
    settings = world.get_world_settings()
    result = {
        "available": True,
        "world": object_name(world),
    }
    for prop in ("default_game_mode", "default_game_mode_class"):
        value = safe_property(settings, prop)
        if value is not None:
            result[prop] = object_name(value)
    return result


def main() -> None:
    unreal.log("[ZombieSeasonsGeneration] Stage 9D FPS input audit started. Read-only.")

    mapping = audit_mapping_context()
    character = audit_character()
    game_mode = audit_game_mode(GAME_MODE)
    fps_game_mode = audit_game_mode(FPS_GAME_MODE)
    config = audit_input_config()
    world = audit_world()

    findings: list[str] = []
    if mapping.get("present"):
        if not mapping.get("azerty_complete"):
            findings.append("AZERTY movement mapping is incomplete in IMC_FPS.")
        if not mapping.get("qwerty_complete"):
            findings.append("QWERTY movement mapping is incomplete in IMC_FPS.")
    if character.get("character_movement") is None:
        findings.append("BP_FPSCharacter did not expose a CharacterMovement component on its CDO.")

    report = {
        "stage": "9D_FPS_INPUT_AUDIT",
        "status": "PASS" if mapping.get("present") and character.get("present") else "WARN",
        "mapping_context": mapping,
        "fps_character": character,
        "bp_game_mode": game_mode,
        "bp_fps_game_mode": fps_game_mode,
        "input_config": config,
        "world": world,
        "findings": findings,
        "modified_assets": False,
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    move_keys = ", ".join(mapping.get("move_keys", [])) or "<none>"
    mouse2d = ", ".join(config.get("Mouse2D_sensitivities", [])) or "<unknown>"
    summary = (
        "Stage 9D FPS input audit completed.\n\n"
        f"Status: {report['status']}\n"
        f"IMC_FPS mappings: {mapping.get('mapping_count', 0)}\n"
        f"Move keys: {move_keys}\n"
        f"AZERTY complete: {mapping.get('azerty_complete', False)}\n"
        f"QWERTY complete: {mapping.get('qwerty_complete', False)}\n"
        f"Mouse2D config sensitivity: {mouse2d}\n"
        f"BP_GameMode default pawn: {game_mode.get('default_pawn_class', 'Unknown')}\n"
        f"BP_FPSGameMode default pawn: {fps_game_mode.get('default_pawn_class', 'Unknown')}\n"
        f"Findings: {len(findings)}\n\n"
        "No asset, Blueprint, mapping, config file, or map was modified.\n"
        f"Report: {REPORT_PATH}"
    )

    unreal.log("[ZombieSeasonsGeneration] " + summary.replace("\n", "  "))
    unreal.EditorDialog.show_message(
        "ZombieSeasons — Stage 9D FPS Input Audit",
        summary,
        unreal.AppMsgType.OK,
    )


main()
