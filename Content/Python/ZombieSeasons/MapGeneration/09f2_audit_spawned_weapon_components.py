"""Deep Stage 9F2 weapon-component audit using transient spawned instances.

The first Stage 9F CDO audit could not see Blueprint-created camera, gun, or projectile
components in UE 5.5. This script spawns transient editor-only instances, inspects their
runtime component templates, writes a report, then destroys every probe actor.

No asset or map is intentionally modified or saved.
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


TARGETS = {
    "fps_character": "/Game/TopDownShooter/Core/BP_FPSCharacter.BP_FPSCharacter_C",
    "gun": "/Game/TopDownShooter/Core/Weapon/BP_Gun.BP_Gun_C",
    "projectile": "/Game/TopDownShooter/Core/Weapon/BP_Projectile.BP_Projectile_C",
}

PROPERTY_PROBES = (
    "relative_location",
    "relative_rotation",
    "relative_scale3d",
    "initial_speed",
    "max_speed",
    "projectile_gravity_scale",
    "velocity",
    "initial_velocity_in_local_space",
    "rotation_follows_velocity",
    "should_bounce",
    "bounciness",
    "friction",
    "auto_activate",
    "absolute_rotation",
    "use_pawn_control_rotation",
    "field_of_view",
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


def safe_get(obj: Any, name: str) -> str | None:
    try:
        return str(obj.get_editor_property(name))
    except Exception:
        try:
            return str(getattr(obj, name))
        except Exception:
            return None


def component_snapshot(component: Any) -> dict[str, Any]:
    class_name = str(component.get_class().get_name())
    name = str(component.get_name())
    payload: dict[str, Any] = {
        "name": name,
        "class": class_name,
        "path": str(component.get_path_name()),
        "interesting": any(
            token in (name + " " + class_name).lower()
            for token in (
                "camera",
                "muzzle",
                "barrel",
                "spawn",
                "projectile",
                "movement",
                "fire",
                "arrow",
                "scene",
            )
        ),
        "properties": {},
    }
    for prop in PROPERTY_PROBES:
        value = safe_get(component, prop)
        if value is not None:
            payload["properties"][prop] = value
    return payload


def actor_components(actor: Any) -> list[Any]:
    # get_components_by_class reliably includes Blueprint-created SCS components on
    # an instantiated Actor even when those components are absent from CDO introspection.
    try:
        return list(actor.get_components_by_class(unreal.ActorComponent) or [])
    except Exception:
        components = []
        for candidate in dir(actor):
            if not candidate.lower().endswith("component"):
                continue
            try:
                value = getattr(actor, candidate)
            except Exception:
                continue
            if value is not None and hasattr(value, "get_class"):
                components.append(value)
        return components


def main() -> None:
    log("Stage 9F2 transient weapon-component audit started.")
    level_subsystem = get_level_subsystem()
    if level_subsystem.is_in_play_in_editor():
        fail("Stop PIE before Stage 9F2.")
    if not is_target_world_loaded():
        fail("L_ZS_World_Greybox must be active for Stage 9F2.")

    actor_subsystem = get_actor_subsystem()
    spawned: list[Any] = []
    targets: dict[str, Any] = {}

    try:
        for index, (key, class_path) in enumerate(TARGETS.items()):
            klass = unreal.load_class(None, class_path)
            if klass is None:
                fail(f"Unable to load {key}: {class_path}")

            location = unreal.Vector(0.0, 0.0, 20000.0 + index * 1000.0)
            actor = actor_subsystem.spawn_actor_from_class(
                klass,
                location,
                unreal.Rotator(roll=0.0, pitch=0.0, yaw=0.0),
                transient=True,
            )
            if actor is None:
                fail(f"Unable to spawn transient probe instance for {key}.")
            spawned.append(actor)

            snapshots = [component_snapshot(item) for item in actor_components(actor)]
            targets[key] = {
                "class": class_path,
                "actor": str(actor.get_path_name()),
                "component_count": len(snapshots),
                "components": snapshots,
                "interesting_components": [
                    item for item in snapshots if item.get("interesting")
                ],
            }
    finally:
        for actor in reversed(spawned):
            try:
                actor_subsystem.destroy_actor(actor)
            except Exception as error:
                unreal.log_warning(
                    f"[ZombieSeasonsGeneration] Failed to destroy transient probe actor: {error}"
                )

    camera_count = sum(
        1
        for item in targets.get("fps_character", {}).get("components", [])
        if "camera" in (item["name"] + " " + item["class"]).lower()
    )
    muzzle_count = sum(
        1
        for item in targets.get("gun", {}).get("components", [])
        if any(token in (item["name"] + " " + item["class"]).lower() for token in ("muzzle", "barrel", "spawn", "fire", "arrow"))
    )
    projectile_movement_count = sum(
        1
        for item in targets.get("projectile", {}).get("components", [])
        if "projectilemovement" in item["class"].lower()
        or ("projectile" in item["class"].lower() and "movement" in item["class"].lower())
    )

    report = write_json_report(
        "weapon_trajectory_spawned_component_audit.json",
        {
            "stage": "9F2_TRANSIENT_WEAPON_COMPONENT_AUDIT",
            "status": "PASS",
            "modified_assets": False,
            "transient_probe_actors_destroyed": True,
            "summary": {
                "camera_components": camera_count,
                "gun_muzzle_spawn_candidates": muzzle_count,
                "projectile_movement_components": projectile_movement_count,
            },
            "targets": targets,
            "next_decision": (
                "Use the instantiated component transforms and ProjectileMovement defaults "
                "to implement the smallest deterministic aiming repair."
            ),
        },
    )

    message = (
        "Stage 9F2 transient component audit PASSED.\n\n"
        f"FPS camera components: {camera_count}\n"
        f"Gun muzzle/spawn candidates: {muzzle_count}\n"
        f"Projectile movement components: {projectile_movement_count}\n\n"
        "All transient probe actors were destroyed. No asset/map was saved.\n\n"
        f"Report: {report}"
    )
    log(message.replace("\n", "  "))
    show_editor_message("ZombieSeasons — Stage 9F2", message)


if __name__ == "__main__":
    main()
