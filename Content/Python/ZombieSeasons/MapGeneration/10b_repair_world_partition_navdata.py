"""Repair the Stage 10 World Partition navigation-data actor.

Stage 10 intentionally created the NavMeshBoundsVolume first. On this UE 5.5 project,
no RecastNavMesh actor was auto-created and Build Paths reported a zero-sized navmesh.
This repair makes the missing navigation-data contract explicit without rebuilding paths.

Run with L_ZS_World_Greybox open, PIE stopped, and the intended World Partition region loaded:

py "C:/Users/malik/Documents/Unreal Projects/ZombieSeasons/Content/Python/ZombieSeasons/MapGeneration/10b_repair_world_partition_navdata.py"
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
    actor_has_tag,
    fail,
    log,
    show_editor_message,
    write_json_report,
)


NAV_STAGE_TAG = "ZS.Stage.NavigationSetup"
EXPECTED_BOUNDS_ID = "ZS.Id.Navigation.WorldBounds"
NAVDATA_LABEL = "RecastNavMesh-Default"


def get_level_subsystem() -> Any:
    subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if subsystem is None:
        fail("LevelEditorSubsystem is unavailable.")
    return subsystem


def get_actor_subsystem() -> Any:
    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    if subsystem is None:
        fail("EditorActorSubsystem is unavailable.")
    return subsystem


def get_world() -> Any:
    subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    if subsystem is None:
        fail("UnrealEditorSubsystem is unavailable.")
    world = subsystem.get_editor_world()
    if world is None:
        fail("Unable to resolve editor world.")
    return world


def all_actors() -> list[Any]:
    return list(get_actor_subsystem().get_all_level_actors() or [])


def is_target_world_loaded() -> bool:
    path = str(get_world().get_path_name())
    return path.startswith(GREYBOX_MAP + ".") or path == GREYBOX_MAP


def find_nav_bounds() -> Any:
    matches = []
    for actor in all_actors():
        class_name = str(actor.get_class().get_name())
        if class_name != "NavMeshBoundsVolume":
            continue
        if actor_has_tag(actor, NAV_STAGE_TAG) and actor_has_tag(actor, EXPECTED_BOUNDS_ID):
            matches.append(actor)
    if len(matches) != 1:
        fail(
            "Expected exactly one Stage 10 NavMeshBoundsVolume, "
            f"found {len(matches)}. Do not create another volume manually."
        )
    return matches[0]


def recast_actors() -> list[Any]:
    return [
        actor
        for actor in all_actors()
        if "RecastNavMesh" in str(actor.get_class().get_name())
        or str(actor.get_name()).startswith("RecastNavMesh")
    ]


def set_if_supported(obj: Any, name: str, value: Any) -> tuple[bool, str]:
    try:
        obj.set_editor_property(name, value)
        resolved = obj.get_editor_property(name)
        return True, str(resolved)
    except Exception as error:
        return False, str(error)


def configure_recast(nav_data: Any) -> dict[str, Any]:
    try:
        nav_data.set_actor_label(NAVDATA_LABEL, mark_dirty=True)
    except TypeError:
        nav_data.set_actor_label(NAVDATA_LABEL)

    outcomes: dict[str, Any] = {}
    properties = (
        ("can_be_main_nav_data", True),
        ("is_world_partitioned", True),
        ("runtime_generation", unreal.RuntimeGenerationType.STATIC),
        ("fixed_tile_pool_size", True),
        ("tile_pool_size", 32768),
        ("is_spatially_loaded", False),
    )
    for name, value in properties:
        ok, resolved = set_if_supported(nav_data, name, value)
        outcomes[name] = {"ok": ok, "resolved": resolved}

    critical = ("can_be_main_nav_data", "is_world_partitioned", "runtime_generation")
    failed = [name for name in critical if not outcomes[name]["ok"]]
    if failed:
        fail("Unable to configure critical RecastNavMesh properties: " + ", ".join(failed))

    return outcomes


def main() -> None:
    log("Stage 10B World Partition NavData repair started.")

    level_subsystem = get_level_subsystem()
    if level_subsystem.is_in_play_in_editor():
        fail("Stop PIE before Stage 10B.")
    if not is_target_world_loaded():
        fail("L_ZS_World_Greybox must be the active editor world for Stage 10B.")
    if not hasattr(unreal, "NavigationSystemV1") or not hasattr(unreal, "RecastNavMesh"):
        fail("UE 5.5 Python does not expose NavigationSystemV1/RecastNavMesh in this build.")

    world = get_world()
    bounds = find_nav_bounds()

    nav_system = unreal.NavigationSystemV1.get_navigation_system(world)
    if nav_system is None:
        fail("The greybox world has no NavigationSystemV1 instance.")

    nav_system_outcomes = {}
    for name, value in (
        ("auto_create_navigation_data", True),
        ("spawn_nav_data_in_nav_bounds_level", False),
    ):
        ok, resolved = set_if_supported(nav_system, name, value)
        nav_system_outcomes[name] = {"ok": ok, "resolved": resolved}

    # Explicitly tell the navigation system that the already-saved Stage 10 bounds changed.
    # This is the supported API hook for bounds updates and may auto-create default NavData.
    try:
        nav_system.on_navigation_bounds_updated(bounds)
    except Exception as error:
        nav_system_outcomes["on_navigation_bounds_updated"] = {
            "ok": False,
            "resolved": str(error),
        }
    else:
        nav_system_outcomes["on_navigation_bounds_updated"] = {
            "ok": True,
            "resolved": "called",
        }

    recasts = recast_actors()
    created = False
    if not recasts:
        nav_data = get_actor_subsystem().spawn_actor_from_class(
            unreal.RecastNavMesh,
            unreal.Vector(0.0, 0.0, 0.0),
            unreal.Rotator(roll=0.0, pitch=0.0, yaw=0.0),
            transient=False,
        )
        if nav_data is None:
            fail("NavigationSystem did not auto-create NavData and explicit RecastNavMesh spawn failed.")
        recasts = [nav_data]
        created = True

    if len(recasts) > 1:
        fail(
            "Multiple RecastNavMesh actors are visible after repair. "
            f"Found {len(recasts)}; refusing to guess which one is authoritative."
        )

    nav_data = recasts[0]
    recast_outcomes = configure_recast(nav_data)

    # Re-register the bounds after the NavData is definitely present.
    try:
        nav_system.on_navigation_bounds_updated(bounds)
        nav_system_outcomes["bounds_updated_after_navdata"] = {
            "ok": True,
            "resolved": "called",
        }
    except Exception as error:
        nav_system_outcomes["bounds_updated_after_navdata"] = {
            "ok": False,
            "resolved": str(error),
        }

    if not level_subsystem.save_current_level():
        fail("Stage 10B configured NavData but Unreal failed to save the greybox map.")

    origin, extent = bounds.get_actor_bounds(False, False)
    report = write_json_report(
        "navigation_navdata_repair.json",
        {
            "stage": "10B_WORLD_PARTITION_NAVDATA_REPAIR",
            "status": "PASS",
            "map": str(world.get_path_name()),
            "bounds_actor": str(bounds.get_path_name()),
            "bounds_origin": str(origin),
            "bounds_extent": str(extent),
            "recast_actor": str(nav_data.get_path_name()),
            "recast_created": created,
            "nav_system": nav_system_outcomes,
            "recast_properties": recast_outcomes,
            "next_step": (
                "Run n.bNavmeshAllowPartitionedBuildingFromEditor 1, then Build > Build Paths. "
                "After a successful build, press P and verify green coverage."
            ),
        },
    )

    message = (
        "Stage 10B World Partition NavData repair PASSED.\n\n"
        f"Recast actor: {nav_data.get_name()}\n"
        f"Created now: {created}\n"
        f"Bounds extent: {extent}\n"
        "World Partition NavMesh: enabled\n"
        "Runtime generation: Static\n"
        "Fixed tile pool: enabled (32768 tiles)\n\n"
        "Now run the partitioned Build Paths again, then press P.\n\n"
        f"Report: {report}"
    )
    log(message.replace("\n", "  "))
    show_editor_message("ZombieSeasons — Stage 10B", message)


if __name__ == "__main__":
    main()
