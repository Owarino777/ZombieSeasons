"""Set the ZombieSeasons greybox map to the existing FPS GameMode.

This fixes a runtime mismatch where L_ZS_World_Greybox was starting with
BP_GameMode (default pawn BP_Hero) instead of BP_FPSGameMode
(default pawn BP_FPSCharacter).

Run from Unreal Editor with the greybox map open and PIE stopped:

py "C:/Users/malik/Documents/Unreal Projects/ZombieSeasons/Content/Python/ZombieSeasons/MapGeneration/09e_fix_greymap_fps_gamemode.py"
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import unreal


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from zs_generation_common import (  # noqa: E402
    GREYBOX_MAP,
    fail,
    log,
    show_editor_message,
    write_json_report,
)


STAGE = "9E_FPS_GAMEMODE_FIX"
FPS_GAME_MODE_CLASS_PATH = "/Game/TopDownShooter/Core/BP_FPSGameMode.BP_FPSGameMode_C"
EXPECTED_DEFAULT_PAWN_PATH = "/Game/TopDownShooter/Core/BP_FPSCharacter.BP_FPSCharacter_C"


def get_level_subsystem() -> Any:
    subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if subsystem is None:
        fail("LevelEditorSubsystem is unavailable.")
    return subsystem


def get_editor_world() -> Any:
    subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    if subsystem is None:
        fail("UnrealEditorSubsystem is unavailable.")
    world = subsystem.get_editor_world()
    if world is None:
        fail("Unable to resolve the current editor world.")
    return world


def is_target_world_loaded() -> bool:
    path = str(get_editor_world().get_path_name())
    return path.startswith(GREYBOX_MAP + ".") or path == GREYBOX_MAP


def describe_class(value: Any) -> str:
    if value is None:
        return "None"
    try:
        return str(value.get_path_name())
    except Exception:
        return str(value)


def resolve_default_pawn(game_mode_class: Any) -> str:
    if game_mode_class is None:
        return "None"
    try:
        cdo = unreal.get_default_object(game_mode_class)
        pawn_class = cdo.get_editor_property("default_pawn_class")
        return describe_class(pawn_class)
    except Exception as error:
        return f"UNRESOLVED: {error}"


def main() -> None:
    log("Stage 9E FPS GameMode fix started.")

    level_subsystem = get_level_subsystem()
    if level_subsystem.is_in_play_in_editor():
        fail("Stop PIE before applying the Stage 9E map GameMode fix.")

    if not is_target_world_loaded():
        fail(
            "L_ZS_World_Greybox must be the active editor world before Stage 9E. "
            "This script intentionally refuses to modify another map."
        )

    game_mode_class = unreal.load_class(None, FPS_GAME_MODE_CLASS_PATH)
    if game_mode_class is None:
        fail(f"Unable to load FPS GameMode generated class: {FPS_GAME_MODE_CLASS_PATH}")

    default_pawn = resolve_default_pawn(game_mode_class)
    if default_pawn != EXPECTED_DEFAULT_PAWN_PATH:
        fail(
            "BP_FPSGameMode does not currently resolve BP_FPSCharacter as its default pawn. "
            f"Resolved: {default_pawn}"
        )

    world = get_editor_world()
    world_settings = world.get_world_settings()
    if world_settings is None:
        fail("Current world has no WorldSettings actor.")

    before = world_settings.get_editor_property("default_game_mode")
    before_path = describe_class(before)

    if before != game_mode_class:
        world_settings.set_editor_property("default_game_mode", game_mode_class)
        if not level_subsystem.save_current_level():
            fail("WorldSettings changed but Unreal failed to save the current greybox level.")

    after = world_settings.get_editor_property("default_game_mode")
    after_path = describe_class(after)
    if after != game_mode_class:
        fail(
            "WorldSettings did not retain BP_FPSGameMode after assignment. "
            f"Resolved: {after_path}"
        )

    report = write_json_report(
        "fps_gamemode_fix.json",
        {
            "stage": STAGE,
            "status": "PASS",
            "map": str(world.get_path_name()),
            "before_game_mode": before_path,
            "after_game_mode": after_path,
            "fps_default_pawn": default_pawn,
            "map_saved": True,
            "input_assets_modified": False,
            "note": (
                "Input mappings and mouse scalar were intentionally left unchanged. "
                "Retest FPS movement/look with the correct pawn first."
            ),
        },
    )

    message = (
        "Stage 9E FPS GameMode fix PASSED.\n\n"
        f"Before: {before_path}\n"
        f"After:  {after_path}\n"
        f"Default pawn: {default_pawn}\n\n"
        "No input mapping or sensitivity asset was modified.\n"
        "Retest PIE before changing mouse sensitivity.\n\n"
        f"Report: {report}"
    )
    log(message.replace("\n", "  "))
    show_editor_message("ZombieSeasons — Stage 9E", message)


if __name__ == "__main__":
    main()
