"""Repair the Spring-to-Hub elevation transition in the generated greybox.

Stage 3 intentionally uses the frozen Spring baseline at +200 cm while the Hub
baseline is 0 cm. The original Spring Main_Entry road was spawned flat at the
Spring road elevation, which leaves an abrupt ~200 cm discontinuity where it meets
the Stage-2 Hub NW connector. The production specification requires district
transitions to blend over distance, so this repair grades the existing Main_Entry
road instead of creating duplicate geometry.

Run once after 03_create_spring.py has passed:

py "C:/Users/malik/Documents/Unreal Projects/ZombieSeasons/Content/Python/ZombieSeasons/MapGeneration/03b_repair_spring_entry_grade.py"

The script modifies only the generated actor tagged ZS.Id.Spring.Road.Main_Entry.
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
    fail,
    log,
    show_editor_message,
    warn,
    write_json_report,
)


STAGE = "SpringEntryGradeRepair"
TARGET_STABLE_TAG = "ZS.Id.Spring.Road.Main_Entry"
REPAIR_TAG = "ZS.Spring.EntryGrade.Repaired"

# Frozen topology. The Stage-2 Hub district connector reaches the Spring boundary
# at (-15000,+15000) with a road center at Z=20 cm. Stage 3 roads sit at Z=220 cm
# over the Spring +200 cm ground baseline. Grading the full Main_Entry segment gives
# a very gentle transition instead of a 2 m step.
START = (-15000.0, 15000.0, 20.0)
END = (-45000.0, 45000.0, 220.0)
WIDTH = 1200.0
THICKNESS = 36.0


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
    try:
        path = str(get_editor_world().get_path_name())
    except Exception:
        return False
    return path.startswith(GREYBOX_MAP + ".") or path == GREYBOX_MAP


def ensure_target_world_loaded() -> None:
    if is_target_world_loaded():
        return
    if not get_level_subsystem().load_level(GREYBOX_MAP):
        fail(f"Unable to load greybox map: {GREYBOX_MAP}")
    if not is_target_world_loaded():
        fail("Greybox map did not become the active editor world.")


def actor_tags(actor: Any) -> list[str]:
    try:
        return [str(item) for item in (actor.get_editor_property("tags") or [])]
    except Exception:
        return []


def find_target_actor() -> Any:
    matches = []
    for actor in list(get_actor_subsystem().get_all_level_actors() or []):
        if actor_has_tag(actor, TARGET_STABLE_TAG):
            matches.append(actor)
    if len(matches) != 1:
        fail(
            "Expected exactly one generated Spring Main_Entry actor, "
            f"found {len(matches)}. Do not apply a blind repair."
        )
    return matches[0]


def make_direction_rotator(dx: float, dy: float, dz: float) -> Any:
    direction = unreal.Vector(dx, dy, dz)
    math_library = getattr(unreal, "MathLibrary", None)
    if math_library is not None and hasattr(math_library, "make_rot_from_x"):
        try:
            return math_library.make_rot_from_x(direction)
        except Exception as error:
            warn(f"MathLibrary.make_rot_from_x failed; using explicit yaw/pitch: {error}")

    horizontal = math.hypot(dx, dy)
    yaw = math.degrees(math.atan2(dy, dx))
    pitch = math.degrees(math.atan2(dz, horizontal))
    return unreal.Rotator(roll=0.0, pitch=pitch, yaw=yaw)


def apply_grade(actor: Any) -> dict[str, float]:
    dx = END[0] - START[0]
    dy = END[1] - START[1]
    dz = END[2] - START[2]
    horizontal_length = math.hypot(dx, dy)
    length_3d = math.sqrt(dx * dx + dy * dy + dz * dz)
    pitch_degrees = math.degrees(math.atan2(dz, horizontal_length))

    center = unreal.Vector(
        (START[0] + END[0]) * 0.5,
        (START[1] + END[1]) * 0.5,
        (START[2] + END[2]) * 0.5,
    )
    rotation = make_direction_rotator(dx, dy, dz)

    actor.set_actor_location(center, False, False)
    actor.set_actor_rotation(rotation, False)
    actor.set_actor_scale3d(
        unreal.Vector(length_3d / 100.0, WIDTH / 100.0, THICKNESS / 100.0)
    )

    tags = actor_tags(actor)
    if REPAIR_TAG not in tags:
        tags.append(REPAIR_TAG)
        actor.set_editor_property("tags", [unreal.Name(tag) for tag in tags])

    return {
        "horizontal_length_cm": horizontal_length,
        "length_3d_cm": length_3d,
        "rise_cm": dz,
        "pitch_degrees": pitch_degrees,
        "grade_percent": (dz / horizontal_length) * 100.0,
    }


def validate_transform(actor: Any) -> None:
    location = actor.get_actor_location()
    expected_center = (
        (START[0] + END[0]) * 0.5,
        (START[1] + END[1]) * 0.5,
        (START[2] + END[2]) * 0.5,
    )
    tolerance = 1.0
    actual = (float(location.x), float(location.y), float(location.z))
    if any(abs(actual[index] - expected_center[index]) > tolerance for index in range(3)):
        fail(
            "Spring Main_Entry repair transform did not persist at the expected center: "
            f"expected={expected_center}, actual={actual}"
        )


def save_level() -> None:
    if not get_level_subsystem().save_current_level():
        fail("Spring transition was repaired but the greybox level could not be saved.")


def position_viewport() -> None:
    try:
        subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        if subsystem is not None:
            subsystem.set_level_viewport_camera_info(
                unreal.Vector(-21000.0, 8000.0, 8000.0),
                unreal.Rotator(roll=0.0, pitch=-20.0, yaw=135.0),
            )
    except Exception as error:
        warn(f"Unable to position viewport for transition review: {error}")


def run() -> None:
    ensure_target_world_loaded()
    actor = find_target_actor()

    if actor_has_tag(actor, REPAIR_TAG):
        fail("Spring Main_Entry already carries the grade-repair tag; refusing duplicate repair.")

    stats = apply_grade(actor)
    validate_transform(actor)
    save_level()
    position_viewport()

    report = write_json_report(
        "spring_entry_grade_repair.json",
        {
            "status": "PASS",
            "stage": STAGE,
            "map": GREYBOX_MAP,
            "target_actor": str(actor.get_actor_label()),
            "target_stable_tag": TARGET_STABLE_TAG,
            "repair_tag": REPAIR_TAG,
            "start_cm": list(START),
            "end_cm": list(END),
            "width_cm": WIDTH,
            "thickness_cm": THICKNESS,
            **stats,
        },
    )

    summary = (
        "Spring entry-grade repair PASSED.\n\n"
        "The +200 cm Spring baseline is intentional.\n"
        "The abrupt Hub/Spring step was not intentional and is now graded across Main_Entry.\n"
        f"Rise: {stats['rise_cm']:.1f} cm\n"
        f"Horizontal run: {stats['horizontal_length_cm']:.1f} cm\n"
        f"Grade: {stats['grade_percent']:.3f}%\n"
        f"Pitch: {stats['pitch_degrees']:.3f} degrees\n\n"
        f"Report:\n{report}"
    )
    log(summary.replace("\n", " "))
    show_editor_message("ZombieSeasons World Generation — Spring Transition Repair", summary)


if __name__ == "__main__":
    run()
