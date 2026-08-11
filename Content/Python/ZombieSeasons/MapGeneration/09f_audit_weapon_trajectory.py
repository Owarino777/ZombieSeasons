"""Audit the existing FPS weapon/projectile transform contract without modifying assets.

This Stage 9F audit exists because the greybox FPS test revealed projectiles travelling
upward instead of following the camera/aim direction. UE 5.5 does not expose the full
Blueprint Event Graph reliably through Python, so this script records every useful
CDO/component transform and projectile movement default that *is* exposed.

Run from Unreal Editor with PIE stopped:

py "C:/Users/malik/Documents/Unreal Projects/ZombieSeasons/Content/Python/ZombieSeasons/MapGeneration/09f_audit_weapon_trajectory.py"
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import unreal


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from zs_generation_common import log, show_editor_message, write_json_report  # noqa: E402


STAGE = "9F_WEAPON_TRAJECTORY_AUDIT"
TARGETS = {
    "fps_character": "/Game/TopDownShooter/Core/BP_FPSCharacter.BP_FPSCharacter_C",
    "gun": "/Game/TopDownShooter/Core/Weapon/BP_Gun.BP_Gun_C",
    "projectile": "/Game/TopDownShooter/Core/Weapon/BP_Projectile.BP_Projectile_C",
}

KEYWORDS = (
    "aim",
    "camera",
    "fire",
    "forward",
    "gun",
    "look",
    "muzzle",
    "projectile",
    "rotation",
    "shoot",
    "spawn",
    "velocity",
)


def describe(value: Any) -> str:
    if value is None:
        return "None"
    try:
        return str(value.get_path_name())
    except Exception:
        return str(value)


def safe_property(obj: Any, name: str) -> Any:
    try:
        return obj.get_editor_property(name)
    except Exception:
        try:
            return getattr(obj, name)
        except Exception:
            return None


def component_snapshot(component: Any) -> dict[str, Any]:
    snapshot: dict[str, Any] = {
        "name": str(component.get_name()),
        "class": describe(component.get_class()),
    }

    for name in (
        "relative_location",
        "relative_rotation",
        "relative_scale3d",
        "component_velocity",
        "use_attach_parent_bound",
    ):
        value = safe_property(component, name)
        if value is not None:
            snapshot[name] = str(value)

    if isinstance(component, unreal.CameraComponent):
        for name in ("field_of_view", "use_pawn_control_rotation"):
            value = safe_property(component, name)
            if value is not None:
                snapshot[name] = str(value)

    if isinstance(component, unreal.ProjectileMovementComponent):
        for name in (
            "initial_speed",
            "max_speed",
            "velocity",
            "initial_velocity_in_local_space",
            "rotation_follows_velocity",
            "projectile_gravity_scale",
            "bounciness",
            "should_bounce",
        ):
            value = safe_property(component, name)
            if value is not None:
                snapshot[name] = str(value)

    return snapshot


def reflected_candidates(cdo: Any) -> dict[str, str]:
    result: dict[str, str] = {}
    for name in dir(cdo):
        lowered = name.lower()
        if not any(keyword in lowered for keyword in KEYWORDS):
            continue
        if name.startswith("_"):
            continue
        try:
            value = getattr(cdo, name)
        except Exception:
            continue
        if callable(value):
            continue
        text = str(value)
        if len(text) > 800:
            text = text[:800] + "..."
        result[name] = text
    return dict(sorted(result.items()))


def inspect_class(path: str) -> dict[str, Any]:
    cls = unreal.load_class(None, path)
    if cls is None:
        return {"present": False, "path": path}

    cdo = unreal.get_default_object(cls)
    components: list[dict[str, Any]] = []
    component_error = ""
    try:
        values = list(cdo.get_components_by_class(unreal.ActorComponent) or [])
        components = [component_snapshot(component) for component in values]
    except Exception as error:
        component_error = str(error)

    return {
        "present": True,
        "path": path,
        "class": describe(cls),
        "cdo": describe(cdo),
        "components": components,
        "component_probe_error": component_error,
        "reflected_candidates": reflected_candidates(cdo),
    }


def main() -> None:
    log("Stage 9F weapon trajectory audit started. No asset or map will be modified.")

    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if level_subsystem is not None and level_subsystem.is_in_play_in_editor():
        raise RuntimeError("Stop PIE before running the Stage 9F weapon trajectory audit.")

    targets = {name: inspect_class(path) for name, path in TARGETS.items()}

    projectile_components = targets["projectile"].get("components", [])
    projectile_movement = [
        item
        for item in projectile_components
        if "ProjectileMovementComponent" in item.get("class", "")
    ]

    gun_components = targets["gun"].get("components", [])
    suspicious_gun_components = [
        item
        for item in gun_components
        if any(
            keyword in item.get("name", "").lower()
            for keyword in ("muzzle", "spawn", "projectile", "arrow", "fire")
        )
    ]

    fps_components = targets["fps_character"].get("components", [])
    camera_components = [
        item
        for item in fps_components
        if "CameraComponent" in item.get("class", "")
    ]

    report = write_json_report(
        "weapon_trajectory_audit.json",
        {
            "stage": STAGE,
            "status": "PASS",
            "targets": targets,
            "summary": {
                "projectile_movement_components": len(projectile_movement),
                "suspicious_gun_components": len(suspicious_gun_components),
                "camera_components": len(camera_components),
            },
            "modified_assets": False,
            "next_decision": (
                "Use exposed muzzle/component/projectile defaults to select the smallest safe "
                "trajectory repair. If the firing graph remains opaque, prefer a project-owned "
                "runtime aim adapter over destructive edits to the binary Blueprint graph."
            ),
        },
    )

    message = (
        "Stage 9F weapon trajectory audit completed.\n\n"
        f"Projectile movement components: {len(projectile_movement)}\n"
        f"Gun muzzle/spawn-like components: {len(suspicious_gun_components)}\n"
        f"FPS camera components: {len(camera_components)}\n\n"
        "No Blueprint or map was modified.\n\n"
        f"Report: {report}"
    )
    log(message.replace("\n", "  "))
    show_editor_message("ZombieSeasons — Stage 9F", message)


if __name__ == "__main__":
    main()
