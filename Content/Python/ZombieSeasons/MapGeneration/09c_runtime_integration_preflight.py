"""Read-only preflight for ZombieSeasons Stage 9C runtime integration.

This stage verifies that the frozen Stage 9B marker contract can be consumed by a
project-owned runtime layer without guessing Blueprint EventGraph internals.

Run from Unreal Editor:

py "C:/Users/malik/Documents/Unreal Projects/ZombieSeasons/Content/Python/ZombieSeasons/MapGeneration/09c_runtime_integration_preflight.py"

No map, Blueprint, config, or project file is modified.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import unreal


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from zs_generation_common import (  # noqa: E402
    GREYBOX_MAP,
    actor_has_tag,
    log,
    show_editor_message,
    warn,
    write_json_report,
)


STAGE = "RuntimeIntegrationPreflight"
GAMEPLAY_STAGE_TAG = "ZS.Stage.GameplayLayout"
PROJECT_ROOT = SCRIPT_DIR.parents[3]
SAVED_VALIDATION = PROJECT_ROOT / "Saved" / "ZombieSeasonsWorldGeneration" / "Validation"
GAMEPLAY_LAYOUT_REPORT = SAVED_VALIDATION / "gameplay_layout_generation.json"
GRAPH_AUDIT_REPORT = SAVED_VALIDATION / "gameplay_blueprint_graph_audit.json"
UPROJECT_PATH = PROJECT_ROOT / "ZombieSeasons.uproject"

EXPECTED_MARKER_TOTAL = 470
EXPECTED_MARKER_TYPES = {
    "ZombieSpawnCandidate": 211,
    "SpawnGroup": 53,
    "HordeTrigger": 18,
    "LootPoint": 148,
    "Objective": 38,
    "SafeZoneContract": 1,
    "ExtractionControllerContract": 1,
}

BLUEPRINT_PATHS = {
    "enemy": "/Game/TopDownShooter/Core/BP_Enemy",
    "enemy_controller": "/Game/TopDownShooter/Core/AIC_Enemy",
    "enemy_spawner": "/Game/TopDownShooter/Core/BP_EnemySpawner",
    "game_mode": "/Game/TopDownShooter/Core/BP_GameMode",
    "fps_game_mode": "/Game/TopDownShooter/Core/BP_FPSGameMode",
    "fps_character": "/Game/TopDownShooter/Core/BP_FPSCharacter",
}


def safe_text(value: Any, *, limit: int = 500) -> str:
    try:
        text = str(value)
    except Exception as error:
        text = f"<unprintable:{type(error).__name__}>"
    return text if len(text) <= limit else text[: limit - 3] + "..."


def load_blueprint_class(asset_path: str) -> Any | None:
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
    return generated_class


def get_default_object(generated_class: Any) -> Any | None:
    if generated_class is None:
        return None

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


def read_property(obj: Any, name: str) -> dict[str, Any]:
    if obj is None:
        return {"available": False, "value": None, "error": "object unavailable"}

    try:
        value = obj.get_editor_property(name)
        return {"available": True, "value": safe_text(value), "error": None}
    except Exception as editor_error:
        try:
            value = getattr(obj, name)
            return {"available": True, "value": safe_text(value), "error": None}
        except Exception as attr_error:
            return {
                "available": False,
                "value": None,
                "error": f"{type(editor_error).__name__}; {type(attr_error).__name__}",
            }


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as error:
        warn(f"Unable to read {path.name}: {error}")
        return None


def inspect_project_shape() -> dict[str, Any]:
    data: dict[str, Any] = {}
    if UPROJECT_PATH.is_file():
        try:
            data = json.loads(UPROJECT_PATH.read_text(encoding="utf-8"))
        except Exception as error:
            warn(f"Unable to parse ZombieSeasons.uproject: {error}")

    source_dir = PROJECT_ROOT / "Source"
    plugin_dir = PROJECT_ROOT / "Plugins" / "ZombieSeasonsRuntime"
    build_cs = sorted(str(path.relative_to(PROJECT_ROOT)) for path in source_dir.rglob("*.Build.cs")) if source_dir.is_dir() else []

    return {
        "project_root": str(PROJECT_ROOT),
        "uproject_exists": UPROJECT_PATH.is_file(),
        "uproject_modules": data.get("Modules", []),
        "source_directory_exists": source_dir.is_dir(),
        "build_cs_files": build_cs,
        "runtime_plugin_exists": plugin_dir.is_dir(),
        "blueprint_only_shape": not source_dir.is_dir() and not data.get("Modules"),
    }


def inspect_visual_studio() -> dict[str, Any]:
    if os.name != "nt":
        return {"platform": os.name, "vswhere_found": False, "cpp_toolchain_found": False}

    candidates = []
    pf86 = os.environ.get("ProgramFiles(x86)")
    if pf86:
        candidates.append(Path(pf86) / "Microsoft Visual Studio" / "Installer" / "vswhere.exe")

    vswhere = next((path for path in candidates if path.is_file()), None)
    if vswhere is None:
        return {"platform": "windows", "vswhere_found": False, "cpp_toolchain_found": False}

    try:
        result = subprocess.run(
            [
                str(vswhere),
                "-latest",
                "-products",
                "*",
                "-requires",
                "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
                "-property",
                "installationPath",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        installation = result.stdout.strip()
        return {
            "platform": "windows",
            "vswhere_found": True,
            "vswhere_path": str(vswhere),
            "cpp_toolchain_found": bool(installation),
            "visual_studio_installation": installation or None,
            "vswhere_exit_code": result.returncode,
        }
    except Exception as error:
        return {
            "platform": "windows",
            "vswhere_found": True,
            "vswhere_path": str(vswhere),
            "cpp_toolchain_found": False,
            "error": str(error),
        }


def inspect_blueprints() -> dict[str, Any]:
    report: dict[str, Any] = {}
    classes: dict[str, Any] = {}

    for key, path in BLUEPRINT_PATHS.items():
        generated_class = load_blueprint_class(path)
        classes[key] = generated_class
        cdo = get_default_object(generated_class)
        report[key] = {
            "asset_path": path,
            "class_resolved": generated_class is not None,
            "class": safe_text(generated_class),
            "cdo_resolved": cdo is not None,
            "properties": {},
        }

        if key == "enemy":
            for prop in (
                "ai_controller_class",
                "auto_possess_ai",
                "can_be_damaged",
                "spawn_collision_handling_method",
                "can_affect_navigation_generation",
            ):
                report[key]["properties"][prop] = read_property(cdo, prop)

            movement_probe = read_property(cdo, "character_movement")
            report[key]["properties"]["character_movement"] = movement_probe
            if movement_probe["available"]:
                try:
                    movement = cdo.get_editor_property("character_movement")
                    report[key]["movement"] = {
                        "max_walk_speed": read_property(movement, "max_walk_speed"),
                        "max_acceleration": read_property(movement, "max_acceleration"),
                        "orient_rotation_to_movement": read_property(movement, "orient_rotation_to_movement"),
                    }
                except Exception:
                    pass

        elif key in ("game_mode", "fps_game_mode"):
            for prop in ("default_pawn_class", "hud_class", "player_controller_class"):
                report[key]["properties"][prop] = read_property(cdo, prop)

        elif key == "fps_character":
            for prop in ("can_be_damaged", "spawn_collision_handling_method"):
                report[key]["properties"][prop] = read_property(cdo, prop)

    report["direct_runtime_classes_ready"] = bool(classes.get("enemy") and classes.get("enemy_controller"))
    return report


def inspect_loaded_markers() -> dict[str, Any]:
    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    if subsystem is None:
        return {"available": False, "loaded_stage_9b_actor_count": 0, "marker_types": {}}

    actors = [
        actor
        for actor in (subsystem.get_all_level_actors() or [])
        if actor_has_tag(actor, GAMEPLAY_STAGE_TAG)
    ]

    counts: dict[str, int] = {}
    for actor in actors:
        tags = [str(tag) for tag in (actor.get_editor_property("tags") or [])]
        marker_type = next((tag.split("ZS.MarkerType.", 1)[1] for tag in tags if tag.startswith("ZS.MarkerType.")), None)
        if marker_type:
            counts[marker_type] = counts.get(marker_type, 0) + 1

    return {
        "available": True,
        "loaded_stage_9b_actor_count": len(actors),
        "marker_types": counts,
        "expected_total": EXPECTED_MARKER_TOTAL,
        "expected_marker_types": EXPECTED_MARKER_TYPES,
        "note": "World Partition may unload spatial markers; loaded counts are advisory only.",
    }


def inspect_saved_contracts() -> dict[str, Any]:
    gameplay = load_json(GAMEPLAY_LAYOUT_REPORT)
    graph = load_json(GRAPH_AUDIT_REPORT)

    gameplay_pass = bool(gameplay and gameplay.get("status") == "PASS")
    graph_nodes_exposed = bool(
        graph
        and graph.get("summary", {}).get("graph_introspection_usable")
    )

    return {
        "gameplay_layout_report_found": gameplay is not None,
        "gameplay_layout_pass": gameplay_pass,
        "graph_audit_report_found": graph is not None,
        "graph_nodes_exposed_to_python": graph_nodes_exposed,
        "runtime_adapter_binding_status": (
            gameplay.get("validation", {}).get("runtime_adapter_binding_status") if gameplay else None
        ),
    }


def run() -> None:
    log("Stage 9C runtime-integration preflight started. No project asset will be modified.")

    project_shape = inspect_project_shape()
    toolchain = inspect_visual_studio()
    blueprint_report = inspect_blueprints()
    markers = inspect_loaded_markers()
    saved_contracts = inspect_saved_contracts()

    direct_classes_ready = bool(blueprint_report.get("direct_runtime_classes_ready"))
    marker_contract_ready = bool(saved_contracts.get("gameplay_layout_pass"))
    cxx_plugin_recommended = not saved_contracts.get("graph_nodes_exposed_to_python", False)

    blockers: list[str] = []
    warnings: list[str] = []

    if not marker_contract_ready:
        blockers.append("Stage 9B saved gameplay-layout report is missing or not PASS.")
    if not direct_classes_ready:
        blockers.append("BP_Enemy and/or AIC_Enemy generated class could not be resolved.")
    if cxx_plugin_recommended and not toolchain.get("cpp_toolchain_found", False):
        warnings.append("Visual Studio C++ toolchain was not confirmed automatically; runtime plugin compilation must be verified before enabling it.")
    if markers.get("loaded_stage_9b_actor_count", 0) != EXPECTED_MARKER_TOTAL:
        warnings.append("Not all 470 Stage 9B actors are currently loaded. This can be normal with World Partition.")

    status = "PASS" if not blockers else "BLOCKED"
    strategy = (
        "CXX_RUNTIME_PLUGIN_DIRECT_BP_ENEMY_AND_AIC_ENEMY"
        if status == "PASS" and cxx_plugin_recommended
        else "UNRESOLVED"
    )

    report_path = write_json_report(
        "runtime_integration_preflight.json",
        {
            "status": status,
            "stage": STAGE,
            "read_only": True,
            "map_contract": GREYBOX_MAP,
            "project_shape": project_shape,
            "toolchain": toolchain,
            "blueprints": blueprint_report,
            "loaded_markers": markers,
            "saved_contracts": saved_contracts,
            "decision": {
                "runtime_strategy": strategy,
                "cxx_runtime_plugin_recommended": cxx_plugin_recommended,
                "direct_runtime_classes_ready": direct_classes_ready,
                "stage_9b_contract_ready": marker_contract_ready,
                "reason": (
                    "UE 5.5 Python can discover the existing EventGraphs but cannot expose their node arrays. "
                    "A small project-owned C++ runtime plugin can consume the deterministic TargetPoint tags, "
                    "spawn BP_Enemy/AIC_Enemy explicitly, and own objectives/hordes without mutating vendor or legacy Blueprint graphs."
                ),
            },
            "blockers": blockers,
            "warnings": warnings,
        },
    )

    message = (
        f"Stage 9C runtime-integration preflight {status}.\n\n"
        f"Stage 9B contract ready: {marker_contract_ready}\n"
        f"BP_Enemy + AIC_Enemy classes ready: {direct_classes_ready}\n"
        f"Project currently Blueprint-only shape: {project_shape.get('blueprint_only_shape')}\n"
        f"Visual Studio C++ toolchain confirmed: {toolchain.get('cpp_toolchain_found', False)}\n"
        f"Loaded Stage 9B actors: {markers.get('loaded_stage_9b_actor_count', 0)}/{EXPECTED_MARKER_TOTAL}\n"
        f"Recommended runtime strategy: {strategy}\n\n"
        f"Blockers: {len(blockers)}\n"
        f"Warnings: {len(warnings)}\n\n"
        "No map, Blueprint, config, or project file was modified.\n\n"
        f"Report: {report_path}"
    )
    log(message.replace("\n", " "))
    show_editor_message("ZombieSeasons World Generation — Stage 9C Preflight", message)


if __name__ == "__main__":
    run()
