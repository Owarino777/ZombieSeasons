"""Export structured context for the currently loaded SchoolA1 Unreal level.

Run this file from the Unreal Editor Python environment. It is read-only with
respect to the level and writes Documentation/SchoolA1/Astra/COUR_SCENE.json.
"""

from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime, timezone
from typing import Any

import unreal

EXPECTED_LEVEL_NAME = "L_ZS_School_Expedition"
OUTPUT_RELATIVE_PATH = os.path.join(
    "Documentation", "SchoolA1", "Astra", "COUR_SCENE.json"
)
PROTECTED_PREFIXES = (
    "Scenario", "Commande", "Attente", "Trigger", "PlayerStart",
    "Objective", "Spawn", "Nav", "Interaction", "Compteur",
)
PROTECTED_CLASS_FRAGMENTS = (
    "Scenario", "Trigger", "PlayerStart", "NavMesh", "NavModifier",
    "NavLink", "Objective", "Interaction", "Spawn",
)
PROTECTED_TAGS = {"ZS_Protected", "GameplayCritical"}


def _vector(value: unreal.Vector) -> dict[str, float]:
    return {axis: round(float(getattr(value, axis)), 4) for axis in ("x", "y", "z")}


def _rotator(value: unreal.Rotator) -> dict[str, float]:
    return {axis: round(float(getattr(value, axis)), 4) for axis in ("pitch", "yaw", "roll")}


def _property(obj: Any, name: str, default: Any = None) -> Any:
    if obj is None:
        return default
    try:
        return obj.get_editor_property(name)
    except Exception:
        return default


def _call(obj: Any, name: str, *args: Any, default: Any = None) -> Any:
    if obj is None:
        return default
    try:
        return getattr(obj, name)(*args)
    except Exception:
        return default


def _path(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return str(value.get_path_name())
    except Exception:
        return str(value)


def _class_path(value: Any) -> str:
    try:
        return str(value.get_class().get_path_name())
    except Exception:
        return type(value).__name__


def _materials(component: unreal.MeshComponent) -> list[dict[str, Any]]:
    count = _call(component, "get_num_materials", default=0)
    slots = _call(component, "get_material_slot_names", default=[])
    if not isinstance(count, int):
        return []
    return [
        {
            "index": index,
            "slot_name": str(slots[index]) if index < len(slots) else None,
            "material": _path(_call(component, "get_material", index)),
        }
        for index in range(count)
    ]


def _mesh_component(component: unreal.MeshComponent) -> dict[str, Any]:
    data = {
        "name": str(component.get_name()),
        "class": _class_path(component),
        "mobility": str(_property(component, "mobility", "")),
        "collision": str(_call(component, "get_collision_enabled", default="")),
        "materials": _materials(component),
        "cast_shadow": bool(_property(component, "cast_shadow", False)),
    }
    if isinstance(component, unreal.StaticMeshComponent):
        data["static_mesh"] = _path(_property(component, "static_mesh"))
    elif isinstance(component, unreal.SkeletalMeshComponent):
        data["skeletal_mesh"] = _path(
            _property(component, "skeletal_mesh_asset")
            or _property(component, "skeletal_mesh")
        )
    return data


def _protected(label: str, class_path: str, tags: list[str]) -> tuple[bool, list[str]]:
    reasons = [f"label_prefix:{prefix}" for prefix in PROTECTED_PREFIXES if label.startswith(prefix)]
    reasons += [
        f"class_fragment:{fragment}"
        for fragment in PROTECTED_CLASS_FRAGMENTS
        if fragment.lower() in class_path.lower()
    ]
    reasons += [f"actor_tag:{tag}" for tag in tags if tag in PROTECTED_TAGS]
    return bool(reasons), reasons


def _actor(actor: unreal.Actor) -> dict[str, Any]:
    label = actor.get_actor_label()
    class_path = _class_path(actor)
    tags = sorted(str(tag) for tag in (_property(actor, "tags", []) or []))
    origin, extent = actor.get_actor_bounds(False, True)
    minimum = unreal.Vector(origin.x - extent.x, origin.y - extent.y, origin.z - extent.z)
    maximum = unreal.Vector(origin.x + extent.x, origin.y + extent.y, origin.z + extent.z)
    is_protected, reasons = _protected(label, class_path, tags)
    static_meshes = actor.get_components_by_class(unreal.StaticMeshComponent)
    skeletal_meshes = actor.get_components_by_class(unreal.SkeletalMeshComponent)
    components = list(static_meshes) + list(skeletal_meshes)
    return {
        "label": label,
        "name": str(actor.get_name()),
        "path": str(actor.get_path_name()),
        "class": class_path,
        "folder": str(actor.get_folder_path()),
        "tags": tags,
        "protected": is_protected,
        "protection_reasons": reasons,
        "transform": {
            "location_cm": _vector(actor.get_actor_location()),
            "rotation_deg": _rotator(actor.get_actor_rotation()),
            "scale": _vector(actor.get_actor_scale3d()),
        },
        "bounds": {
            "origin_cm": _vector(origin),
            "extent_cm": _vector(extent),
            "size_cm": _vector(unreal.Vector(extent.x * 2, extent.y * 2, extent.z * 2)),
            "min_cm": _vector(minimum),
            "max_cm": _vector(maximum),
        },
        "mesh_components": [_mesh_component(component) for component in components],
        "light_component_count": len(actor.get_components_by_class(unreal.LightComponent)),
        "is_cine_camera": isinstance(actor, unreal.CineCameraActor),
    }


def _bounds(actors: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not actors:
        return None
    minimum = {
        axis: min(actor["bounds"]["min_cm"][axis] for actor in actors)
        for axis in ("x", "y", "z")
    }
    maximum = {
        axis: max(actor["bounds"]["max_cm"][axis] for actor in actors)
        for axis in ("x", "y", "z")
    }
    return {
        "min_cm": minimum,
        "max_cm": maximum,
        "size_cm": {axis: round(maximum[axis] - minimum[axis], 4) for axis in ("x", "y", "z")},
    }


def export_schoola1_scene() -> str:
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    editor_subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    if actor_subsystem is None or editor_subsystem is None:
        raise RuntimeError("Required Unreal editor subsystems are unavailable.")
    world = editor_subsystem.get_editor_world()
    if world is None:
        raise RuntimeError("No editor world is currently loaded.")

    world_name = str(world.get_name())
    world_path = str(world.get_path_name())
    if EXPECTED_LEVEL_NAME not in world_name and EXPECTED_LEVEL_NAME not in world_path:
        unreal.log_warning(f"Expected {EXPECTED_LEVEL_NAME}, found {world_path}.")

    actors = [_actor(actor) for actor in actor_subsystem.get_all_level_actors()]
    actors.sort(key=lambda item: (item["folder"], item["label"].lower()))
    folders = Counter(actor["folder"] for actor in actors)
    classes = Counter(actor["class"] for actor in actors)
    output = {
        "schema_version": 1,
        "generated": {
            "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "generator": "Scripts/Unreal/export_schoola1_scene.py",
            "project_directory": os.path.normpath(unreal.Paths.project_dir()),
        },
        "level": {
            "expected_name": EXPECTED_LEVEL_NAME,
            "loaded_world_name": world_name,
            "loaded_world_path": world_path,
            "units": "centimeters",
        },
        "summary": {
            "actor_count": len(actors),
            "protected_actor_count": sum(actor["protected"] for actor in actors),
            "actors_with_meshes": sum(bool(actor["mesh_components"]) for actor in actors),
            "actors_with_lights": sum(actor["light_component_count"] > 0 for actor in actors),
            "cine_camera_count": sum(actor["is_cine_camera"] for actor in actors),
            "scene_bounds": _bounds(actors),
        },
        "folder_counts": dict(sorted(folders.items())),
        "class_counts": dict(sorted(classes.items())),
        "actors": actors,
    }
    output_path = os.path.normpath(os.path.join(unreal.Paths.project_dir(), OUTPUT_RELATIVE_PATH))
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="\n") as file:
        json.dump(output, file, ensure_ascii=False, indent=2)
        file.write("\n")
    unreal.log(f"SchoolA1 scene export completed: {output_path}")
    return output_path


if __name__ == "__main__":
    export_schoola1_scene()
