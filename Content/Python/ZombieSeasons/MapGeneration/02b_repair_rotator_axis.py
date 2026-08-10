"""Repair Stage-1/Stage-2 greybox rotations created with positional Rotator args.

UE 5.5 Python exposes unreal.Rotator as (roll, pitch, yaw). Earlier generation
scripts passed the intended yaw as the second positional argument, so rotated road
segments were pitched vertically instead of yawed in the XY plane.

This one-time repair is deliberately deterministic:
- requires the complete Stage-1 and Stage-2 actor sets to be loaded;
- derives every intended road yaw from the frozen topology, never from the current
  broken transform;
- resets all other generated StaticMesh actors from these two stages to zero
  rotation, because none of them are intentionally tilted;
- patches the Stage-1/Stage-2 source files locally so a future regeneration cannot
  reproduce the same positional-argument bug;
- saves the current World Partition map and writes a validation report.

Run once from the Unreal Editor session that currently has L_ZS_World_Greybox open:

py "C:/Users/malik/Documents/Unreal Projects/ZombieSeasons/Content/Python/ZombieSeasons/MapGeneration/02b_repair_rotator_axis.py"
"""

from __future__ import annotations

import math
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
    editor_asset_exists,
    fail,
    log,
    show_editor_message,
    warn,
    write_json_report,
)


EXPECTED_WORLD_SHELL_ACTORS = 121
EXPECTED_HUB_ACTORS = 54
ANGLE_TOLERANCE_DEG = 0.05

STAGE1_SOURCE = SCRIPT_DIR / "01_create_world_shell.py"
STAGE2_SOURCE = SCRIPT_DIR / "02_create_hub.py"

STAGE1_ROADS: tuple[
    tuple[str, tuple[float, float], tuple[float, float]], ...
] = (
    ("R_HUB_N", (-7000.0, 10000.0), (7000.0, 10000.0)),
    ("R_HUB_NE", (7000.0, 10000.0), (10000.0, 7000.0)),
    ("R_HUB_E", (10000.0, 7000.0), (10000.0, -7000.0)),
    ("R_HUB_SE", (10000.0, -7000.0), (7000.0, -10000.0)),
    ("R_HUB_S", (7000.0, -10000.0), (-7000.0, -10000.0)),
    ("R_HUB_SW", (-7000.0, -10000.0), (-10000.0, -7000.0)),
    ("R_HUB_W", (-10000.0, -7000.0), (-10000.0, 7000.0)),
    ("R_HUB_NW", (-10000.0, 7000.0), (-7000.0, 10000.0)),
    ("R_SPRING", (-8000.0, 8000.0), (-45000.0, 45000.0)),
    ("R_SUMMER", (8000.0, 8000.0), (45000.0, 45000.0)),
    ("R_AUTUMN", (-8000.0, -8000.0), (-45000.0, -45000.0)),
    ("R_WINTER", (8000.0, -8000.0), (45000.0, -45000.0)),
    ("R_NORTH_CROSS", (-60000.0, 60000.0), (60000.0, 60000.0)),
    ("R_SOUTH_CROSS", (-60000.0, -60000.0), (60000.0, -60000.0)),
    ("R_WEST_SERVICE", (-60000.0, 60000.0), (-60000.0, -60000.0)),
    ("R_EAST_SERVICE", (60000.0, 60000.0), (60000.0, -60000.0)),
    ("R_EXTRACTION", (56000.0, -45000.0), (85000.0, -30000.0)),
)

STAGE2_ROADS: tuple[
    tuple[str, tuple[float, float], tuple[float, float]], ...
] = (
    ("Hub.Road.Ring.N", (-7000.0, 10000.0), (7000.0, 10000.0)),
    ("Hub.Road.Ring.NE", (7000.0, 10000.0), (10000.0, 7000.0)),
    ("Hub.Road.Ring.E", (10000.0, 7000.0), (10000.0, -7000.0)),
    ("Hub.Road.Ring.SE", (10000.0, -7000.0), (7000.0, -10000.0)),
    ("Hub.Road.Ring.S", (7000.0, -10000.0), (-7000.0, -10000.0)),
    ("Hub.Road.Ring.SW", (-7000.0, -10000.0), (-10000.0, -7000.0)),
    ("Hub.Road.Ring.W", (-10000.0, -7000.0), (-10000.0, 7000.0)),
    ("Hub.Road.Ring.NW", (-10000.0, 7000.0), (-7000.0, 10000.0)),
    ("Hub.Road.SafeZoneConnector.North", (0.0, 6000.0), (0.0, 10000.0)),
    ("Hub.Road.SafeZoneConnector.East", (6000.0, 0.0), (10000.0, 0.0)),
    ("Hub.Road.SafeZoneConnector.South", (0.0, -6000.0), (0.0, -10000.0)),
    ("Hub.Road.SafeZoneConnector.West", (-6000.0, 0.0), (-10000.0, 0.0)),
    ("Hub.Road.DistrictConnector.Spring", (-8000.0, 8000.0), (-15000.0, 15000.0)),
    ("Hub.Road.DistrictConnector.Summer", (8000.0, 8000.0), (15000.0, 15000.0)),
    ("Hub.Road.DistrictConnector.Autumn", (-8000.0, -8000.0), (-15000.0, -15000.0)),
    ("Hub.Road.DistrictConnector.Winter", (8000.0, -8000.0), (15000.0, -15000.0)),
)


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


def get_editor_world() -> Any:
    subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    if subsystem is None:
        fail("UnrealEditorSubsystem is unavailable.")
    world = subsystem.get_editor_world()
    if world is None:
        fail("Unable to resolve current editor world.")
    return world


def is_target_world_loaded() -> bool:
    path = str(get_editor_world().get_path_name())
    return path == GREYBOX_MAP or path.startswith(GREYBOX_MAP + ".")


def all_loaded_actors() -> list[Any]:
    return list(get_actor_subsystem().get_all_level_actors() or [])


def actors_for_stage(stage: str) -> list[Any]:
    return [
        actor
        for actor in all_loaded_actors()
        if actor_has_tag(actor, f"ZS.Stage.{stage}")
    ]


def stable_id(actor: Any) -> str | None:
    try:
        tags = actor.get_editor_property("tags") or []
    except Exception:
        return None
    prefix = "ZS.Id."
    for value in tags:
        text = str(value)
        if text.startswith(prefix):
            return text[len(prefix) :]
    return None


def yaw_between(start: tuple[float, float], end: tuple[float, float]) -> float:
    return math.degrees(math.atan2(end[1] - start[1], end[0] - start[0]))


def desired_yaws() -> dict[str, float]:
    result: dict[str, float] = {}
    for road_id, start, end in STAGE1_ROADS:
        result[f"WorldShell.Road.{road_id}"] = yaw_between(start, end)
    for asset_id, start, end in STAGE2_ROADS:
        result[asset_id] = yaw_between(start, end)
    return result


def normalized_angle(value: float) -> float:
    value = (value + 180.0) % 360.0 - 180.0
    return 180.0 if abs(value + 180.0) < 1e-8 else value


def angle_distance(a: float, b: float) -> float:
    return abs(normalized_angle(a - b))


def rotator_is_correct(rotation: Any, desired_yaw: float) -> bool:
    return (
        abs(float(rotation.roll)) <= ANGLE_TOLERANCE_DEG
        and abs(float(rotation.pitch)) <= ANGLE_TOLERANCE_DEG
        and angle_distance(float(rotation.yaw), desired_yaw) <= ANGLE_TOLERANCE_DEG
    )


def patch_generation_sources() -> list[str]:
    replacements = {
        STAGE1_SOURCE: (
            (
                "unreal.Rotator(0.0, yaw, 0.0)",
                "unreal.Rotator(roll=0.0, pitch=0.0, yaw=yaw)",
            ),
            (
                "unreal.Rotator(-90.0, 0.0, 0.0)",
                "unreal.Rotator(roll=0.0, pitch=-90.0, yaw=0.0)",
            ),
        ),
        STAGE2_SOURCE: (
            (
                "unreal.Rotator(0.0, yaw, 0.0)",
                "unreal.Rotator(roll=0.0, pitch=0.0, yaw=yaw)",
            ),
            (
                "unreal.Rotator(-35.0, 0.0, 0.0)",
                "unreal.Rotator(roll=0.0, pitch=-35.0, yaw=90.0)",
            ),
        ),
    }

    changed_files: list[str] = []
    for path, file_replacements in replacements.items():
        if not path.is_file():
            fail(f"Generation source file missing: {path}")
        original = path.read_text(encoding="utf-8")
        updated = original
        for old, new in file_replacements:
            if old in updated:
                updated = updated.replace(old, new)
            elif new not in updated:
                fail(
                    f"Unable to patch expected Rotator expression in {path.name}: {old}"
                )
        if updated != original:
            path.write_text(updated, encoding="utf-8", newline="\n")
            changed_files.append(path.name)
    return changed_files


def repair_map_rotations() -> tuple[int, int, list[str]]:
    shell = actors_for_stage("WorldShell")
    hub = actors_for_stage("Hub")
    if len(shell) != EXPECTED_WORLD_SHELL_ACTORS:
        fail(
            "Stage-1 actor set is not fully loaded; refusing partial repair. "
            f"Expected {EXPECTED_WORLD_SHELL_ACTORS}, found {len(shell)}."
        )
    if len(hub) != EXPECTED_HUB_ACTORS:
        fail(
            "Stage-2 actor set is not fully loaded; refusing partial repair. "
            f"Expected {EXPECTED_HUB_ACTORS}, found {len(hub)}."
        )

    yaw_map = desired_yaws()
    changed = 0
    static_mesh_count = 0
    changed_labels: list[str] = []

    for actor in (*shell, *hub):
        if not isinstance(actor, unreal.StaticMeshActor):
            continue
        static_mesh_count += 1
        asset_id = stable_id(actor)
        if asset_id is None:
            fail(f"Generated actor has no stable ZS.Id tag: {actor.get_actor_label()}")
        target_yaw = yaw_map.get(asset_id, 0.0)
        current = actor.get_actor_rotation()
        if rotator_is_correct(current, target_yaw):
            continue
        desired = unreal.Rotator(roll=0.0, pitch=0.0, yaw=target_yaw)
        if not actor.set_actor_rotation(desired, False):
            # set_actor_rotation can return None in some editor builds even when the
            # transform succeeds, so verify instead of trusting the return value.
            pass
        verified = actor.get_actor_rotation()
        if not rotator_is_correct(verified, target_yaw):
            fail(
                f"Rotation repair did not persist for {actor.get_actor_label()}: "
                f"wanted yaw={target_yaw:.3f}, got roll={verified.roll:.3f}, "
                f"pitch={verified.pitch:.3f}, yaw={verified.yaw:.3f}"
            )
        changed += 1
        changed_labels.append(actor.get_actor_label())

    return changed, static_mesh_count, changed_labels


def verify_all_rotations() -> None:
    yaw_map = desired_yaws()
    failures: list[str] = []
    for actor in (*actors_for_stage("WorldShell"), *actors_for_stage("Hub")):
        if not isinstance(actor, unreal.StaticMeshActor):
            continue
        asset_id = stable_id(actor)
        if asset_id is None:
            failures.append(f"{actor.get_actor_label()}: missing stable id")
            continue
        expected_yaw = yaw_map.get(asset_id, 0.0)
        rotation = actor.get_actor_rotation()
        if not rotator_is_correct(rotation, expected_yaw):
            failures.append(
                f"{actor.get_actor_label()}: roll={rotation.roll:.3f}, "
                f"pitch={rotation.pitch:.3f}, yaw={rotation.yaw:.3f}, "
                f"expected yaw={expected_yaw:.3f}"
            )
    if failures:
        fail("Post-repair rotation validation failed: " + " | ".join(failures[:8]))


def save_level() -> None:
    if not get_level_subsystem().save_current_level():
        fail("Rotation repair succeeded in memory but the map could not be saved.")


def position_viewport() -> None:
    try:
        subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        if subsystem is not None:
            subsystem.set_level_viewport_camera_info(
                unreal.Vector(0.0, -26000.0, 20000.0),
                unreal.Rotator(roll=0.0, pitch=-32.0, yaw=90.0),
            )
    except Exception as error:
        warn(f"Unable to reposition viewport after rotation repair: {error}")


def run() -> None:
    if not editor_asset_exists(GREYBOX_MAP):
        fail("Greybox map does not exist.")
    if not is_target_world_loaded():
        fail(
            "L_ZS_World_Greybox must already be open for this repair. "
            "Do not restart the editor before running it."
        )

    log("Rotator-axis repair preflight passed. Repairing Stage-1/Stage-2 transforms.")
    source_files_changed = patch_generation_sources()
    changed_count, static_mesh_count, changed_labels = repair_map_rotations()
    verify_all_rotations()
    save_level()
    position_viewport()

    report = write_json_report(
        "rotator_axis_repair.json",
        {
            "status": "PASS",
            "map": GREYBOX_MAP,
            "world_shell_actor_count": EXPECTED_WORLD_SHELL_ACTORS,
            "hub_actor_count": EXPECTED_HUB_ACTORS,
            "generated_static_mesh_actor_count": static_mesh_count,
            "rotations_changed": changed_count,
            "source_files_changed": source_files_changed,
            "changed_actor_labels": changed_labels,
            "repair_reason": "UE 5.5 unreal.Rotator positional signature is roll, pitch, yaw; intended yaw was previously passed as pitch.",
        },
    )

    summary = (
        "Rotator-axis repair PASSED.\n\n"
        f"Generated StaticMesh actors verified: {static_mesh_count}\n"
        f"Transforms corrected: {changed_count}\n"
        f"Source files patched locally: {len(source_files_changed)}\n"
        "Stage 1 + Stage 2 rotations now use explicit keyword axes.\n\n"
        f"Report:\n{report}"
    )
    log(summary.replace("\n", " "))
    show_editor_message("ZombieSeasons — Rotation Repair", summary)


if __name__ == "__main__":
    run()
