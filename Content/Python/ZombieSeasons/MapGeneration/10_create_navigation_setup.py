"""Create the Stage 10 navigation bounds for the ZombieSeasons greybox world.

The script intentionally creates navigation-support geometry only. Building a complete
World Partition NavMesh remains an explicit editor build step so a potentially expensive
navigation build is never triggered unexpectedly by Python.

Run with L_ZS_World_Greybox open, all intended editor regions loaded, and PIE stopped:

py "C:/Users/malik/Documents/Unreal Projects/ZombieSeasons/Content/Python/ZombieSeasons/MapGeneration/10_create_navigation_setup.py"
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
    add_generation_tags,
    actor_has_tag,
    fail,
    log,
    show_editor_message,
    write_json_report,
)


STAGE = "NavigationSetup"
STAGE_TAG = f"ZS.Stage.{STAGE}"
NAV_BOUNDS_ID = "Navigation.WorldBounds"
NAV_FOLDER = "ZombieSeasons/Navigation"

# World bounds are +/- 90,000 cm. The vertical range deliberately covers the sewer
# network below grade and the elevated dam/extraction route above grade.
NAV_CENTER = unreal.Vector(0.0, 0.0, 2500.0)
TARGET_HALF_EXTENT = unreal.Vector(90000.0, 90000.0, 7500.0)
MIN_ACCEPTED_HALF_EXTENT = unreal.Vector(89500.0, 89500.0, 7000.0)


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


def is_target_world_loaded() -> bool:
    path = str(get_world().get_path_name())
    return path.startswith(GREYBOX_MAP + ".") or path == GREYBOX_MAP


def all_loaded_actors() -> list[Any]:
    return list(get_actor_subsystem().get_all_level_actors() or [])


def stage_actors() -> list[Any]:
    return [actor for actor in all_loaded_actors() if actor_has_tag(actor, STAGE_TAG)]


def actor_bounds(actor: Any) -> tuple[unreal.Vector, unreal.Vector]:
    try:
        origin, extent = actor.get_actor_bounds(False, False)
        return origin, extent
    except TypeError:
        origin, extent = actor.get_actor_bounds(False)
        return origin, extent


def scale_volume_to_target(actor: Any) -> tuple[unreal.Vector, unreal.Vector]:
    _, initial_extent = actor_bounds(actor)
    if initial_extent.x <= 1.0 or initial_extent.y <= 1.0 or initial_extent.z <= 1.0:
        fail(
            "Spawned NavMeshBoundsVolume has unusable default brush bounds: "
            f"{initial_extent}"
        )

    scale = unreal.Vector(
        TARGET_HALF_EXTENT.x / initial_extent.x,
        TARGET_HALF_EXTENT.y / initial_extent.y,
        TARGET_HALF_EXTENT.z / initial_extent.z,
    )
    actor.set_actor_scale3d(scale)

    origin, final_extent = actor_bounds(actor)
    if (
        final_extent.x < MIN_ACCEPTED_HALF_EXTENT.x
        or final_extent.y < MIN_ACCEPTED_HALF_EXTENT.y
        or final_extent.z < MIN_ACCEPTED_HALF_EXTENT.z
    ):
        fail(
            "NavMeshBoundsVolume did not scale to the frozen playable bounds. "
            f"Final origin={origin} extent={final_extent} scale={scale}"
        )

    return origin, final_extent


def set_identity(actor: Any) -> None:
    try:
        actor.set_actor_label("ZS_Navigation_WorldBounds", mark_dirty=True)
    except TypeError:
        actor.set_actor_label("ZS_Navigation_WorldBounds")
    actor.set_folder_path(unreal.Name(NAV_FOLDER))
    add_generation_tags(
        actor,
        stage=STAGE,
        district="Shared",
        stable_id=NAV_BOUNDS_ID,
    )

    # Keep the bounds definition persistent. World Partition navigation data itself is
    # built/streamed separately; the bounds volume has no gameplay collision.
    try:
        actor.set_editor_property("is_spatially_loaded", False)
    except Exception:
        pass

    try:
        actor.set_editor_property("layers", [unreal.Name("ZS_Navigation")])
    except Exception:
        pass


def count_gameplay_markers() -> int:
    return sum(
        1
        for actor in all_loaded_actors()
        if actor_has_tag(actor, "ZS.Stage.GameplayLayout")
    )


def main() -> None:
    log("Stage 10 navigation setup started.")

    level_subsystem = get_level_subsystem()
    if level_subsystem.is_in_play_in_editor():
        fail("Stop PIE before Stage 10 navigation setup.")
    if not is_target_world_loaded():
        fail("L_ZS_World_Greybox must be the active editor world for Stage 10.")
    if not hasattr(unreal, "NavMeshBoundsVolume"):
        fail("UE Python does not expose NavMeshBoundsVolume in this editor build.")

    existing = stage_actors()
    if existing:
        fail(
            f"Refusing to duplicate Stage 10 navigation setup: {len(existing)} generated "
            "NavigationSetup actor(s) already exist."
        )

    loaded_gameplay_markers = count_gameplay_markers()
    if loaded_gameplay_markers < 100:
        fail(
            "Too few Stage 9 gameplay markers are loaded to trust the navigation setup "
            f"checkpoint ({loaded_gameplay_markers} found). Load the intended World Partition "
            "editor region before running Stage 10."
        )

    actor = get_actor_subsystem().spawn_actor_from_class(
        unreal.NavMeshBoundsVolume,
        NAV_CENTER,
        unreal.Rotator(roll=0.0, pitch=0.0, yaw=0.0),
        transient=False,
    )
    if actor is None:
        fail("Unable to spawn NavMeshBoundsVolume.")

    set_identity(actor)
    origin, extent = scale_volume_to_target(actor)

    if not level_subsystem.save_current_level():
        fail("Navigation bounds were created but Unreal failed to save the greybox map.")

    recast_count = sum(
        1
        for item in all_loaded_actors()
        if "RecastNavMesh" in str(item.get_class().get_name())
        or str(item.get_name()).startswith("RecastNavMesh")
    )

    report = write_json_report(
        "navigation_setup.json",
        {
            "stage": "10_NAVIGATION_SETUP",
            "status": "PASS",
            "map": str(get_world().get_path_name()),
            "nav_bounds_actor": str(actor.get_path_name()),
            "nav_bounds_origin": str(origin),
            "nav_bounds_half_extent": str(extent),
            "loaded_gameplay_markers_at_setup": loaded_gameplay_markers,
            "recast_navmesh_actors_visible_after_setup": recast_count,
            "manual_world_partition_nav_build_required": True,
            "build_instructions": [
                "Set n.bNavmeshAllowPartitionedBuildingFromEditor 1 in the editor command line.",
                "Use Build > Build Paths and confirm the World Partition navigation build dialog.",
                "Press P to verify green navigation coverage before PIE.",
            ],
        },
    )

    message = (
        "Stage 10 navigation setup PASSED.\n\n"
        f"Bounds origin: {origin}\n"
        f"Bounds half extent: {extent}\n"
        f"Loaded gameplay markers: {loaded_gameplay_markers}\n"
        f"Visible RecastNavMesh actors: {recast_count}\n\n"
        "The bounds are saved, but the World Partition NavMesh still requires Build Paths.\n"
        "After the build, press P and verify green coverage before PIE.\n\n"
        f"Report: {report}"
    )
    log(message.replace("\n", "  "))
    show_editor_message("ZombieSeasons — Stage 10", message)


if __name__ == "__main__":
    main()
