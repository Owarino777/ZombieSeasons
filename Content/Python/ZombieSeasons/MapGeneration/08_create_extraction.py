"""Create the deterministic ZombieSeasons extraction-dam greybox.

Run from Unreal Editor only after Stage 7 sewers has passed and been committed:

py "C:/Users/malik/Documents/Unreal Projects/ZombieSeasons/Content/Python/ZombieSeasons/MapGeneration/08_create_extraction.py"

Stage 8 creates the topology-critical dam finale: Winter handoff, perimeter entry,
control building, two moving-defense positions, final crossing, extraction endpoint,
and deterministic gameplay markers. Runtime objective state, zombie spawns, loot,
NavMesh adapters and final Fab/City Sample art remain deferred to later stages.
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
    add_generation_tags,
    editor_asset_exists,
    fail,
    log,
    show_editor_message,
    warn,
    write_json_report,
)


STAGE = "Extraction"
MODE = "CREATE"
ENGINE_CUBE = "/Engine/BasicShapes/Cube.Cube"

ROAD_THICKNESS = 36.0
ROAD_CENTER_OFFSET = ROAD_THICKNESS * 0.5 + 2.0
MAIN_ROAD_WIDTH = 1200.0
SECONDARY_ROAD_WIDTH = 700.0
FLOOR_THICKNESS = 24.0
STANDARD_WALL_HEIGHT = 500.0
STANDARD_WALL_THICKNESS = 90.0
PARAPET_HEIGHT = 140.0
PARAPET_THICKNESS = 60.0

EDITOR_GREYBOX_LAYERS = (
    "DL_ZS_Greybox",
    "DL_ZS_Extraction",
)
EDITOR_GAMEPLAY_LAYERS = (
    "DL_ZS_Greybox",
    "DL_ZS_Gameplay",
    "DL_ZS_Extraction",
)

# Frozen production anchors from 07_Production_World_Specification.md.
POI_ANCHORS: dict[str, tuple[float, float, float]] = {
    "DamPerimeterEntry": (79000.0, -31000.0, 700.0),
    "ControlBuilding": (84000.0, -31000.0, 900.0),
    "DefensePositionA": (82000.0, -25000.0, 900.0),
    "DefensePositionB": (87000.0, -35000.0, 1000.0),
    "FinalCrossingStart": (84000.0, -21000.0, 1100.0),
    "ExtractionEndpoint": (88000.0, -18000.0, 1200.0),
}

# Road/deck surfaces use explicit 3D endpoints, so the extraction route transitions
# cleanly from the Winter dam gate (+600 cm) to the final +1200 cm endpoint.
ROAD_SEGMENTS: tuple[
    tuple[str, tuple[float, float, float], tuple[float, float, float], float], ...
] = (
    (
        "Winter_Handoff",
        (76000.0, -33000.0, 600.0 + ROAD_CENTER_OFFSET),
        (79000.0, -31000.0, 700.0 + ROAD_CENTER_OFFSET),
        MAIN_ROAD_WIDTH,
    ),
    (
        "Entry_Control",
        (79000.0, -31000.0, 700.0 + ROAD_CENTER_OFFSET),
        (84000.0, -31000.0, 900.0 + ROAD_CENTER_OFFSET),
        900.0,
    ),
    (
        "Entry_DefenseA",
        (79000.0, -31000.0, 700.0 + ROAD_CENTER_OFFSET),
        (82000.0, -25000.0, 900.0 + ROAD_CENTER_OFFSET),
        SECONDARY_ROAD_WIDTH,
    ),
    (
        "Control_DefenseB",
        (84000.0, -31000.0, 900.0 + ROAD_CENTER_OFFSET),
        (87000.0, -35000.0, 1000.0 + ROAD_CENTER_OFFSET),
        SECONDARY_ROAD_WIDTH,
    ),
    (
        "DefenseA_FinalCrossing",
        (82000.0, -25000.0, 900.0 + ROAD_CENTER_OFFSET),
        (84000.0, -21000.0, 1100.0 + ROAD_CENTER_OFFSET),
        900.0,
    ),
    (
        "Final_Dam_Crossing",
        (84000.0, -21000.0, 1100.0 + ROAD_CENTER_OFFSET),
        (88000.0, -18000.0, 1200.0 + ROAD_CENTER_OFFSET),
        MAIN_ROAD_WIDTH,
    ),
)

# Stage-9 will convert these deterministic markers into real objective/horde logic.
GAMEPLAY_MARKERS: tuple[tuple[str, tuple[float, float, float]], ...] = (
    ("Objective.DamControls", (84000.0, -31000.0, 1900.0)),
    ("Horde.DefenseA", (82000.0, -25000.0, 1900.0)),
    ("Horde.DefenseB", (87000.0, -35000.0, 2000.0)),
    ("Gate.FinalCrossing", (84000.0, -21000.0, 2100.0)),
    ("Route.ReturnPressure", (79000.0, -31000.0, 1700.0)),
    ("Extraction.Endpoint", (88000.0, -18000.0, 2200.0)),
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
    try:
        path = str(get_editor_world().get_path_name())
    except Exception:
        return False
    return path.startswith(GREYBOX_MAP + ".") or path == GREYBOX_MAP


def check_dirty_maps_before_load() -> None:
    utility = getattr(unreal, "EditorLoadingAndSavingUtils", None)
    if utility is None:
        return
    try:
        dirty = list(utility.get_dirty_map_packages() or [])
    except Exception:
        return
    if dirty:
        names = [str(package.get_name()) for package in dirty]
        fail(
            "Unsaved map packages are open. Save or discard them before Stage 8: "
            + ", ".join(names)
        )


def ensure_target_world_loaded() -> None:
    if is_target_world_loaded():
        return
    check_dirty_maps_before_load()
    if not get_level_subsystem().load_level(GREYBOX_MAP):
        fail(f"Unable to load greybox map: {GREYBOX_MAP}")
    if not is_target_world_loaded():
        fail("LevelEditorSubsystem reported success but the greybox world is not active.")


def all_loaded_actors() -> list[Any]:
    return list(get_actor_subsystem().get_all_level_actors() or [])


def stage_actors(stage_name: str) -> list[Any]:
    tag = f"ZS.Stage.{stage_name}"
    return [actor for actor in all_loaded_actors() if actor_has_tag(actor, tag)]


def actor_with_stable_id(stable_id: str) -> Any | None:
    tag = f"ZS.Id.{stable_id}"
    for actor in all_loaded_actors():
        if actor_has_tag(actor, tag):
            return actor
    return None


def preflight() -> None:
    if MODE != "CREATE":
        fail(f"Unsupported extraction generation mode: {MODE}")
    if not editor_asset_exists(GREYBOX_MAP):
        fail("Greybox map does not exist. Run Stage 1 first.")

    required_symbols = (
        "LevelEditorSubsystem",
        "EditorActorSubsystem",
        "UnrealEditorSubsystem",
        "StaticMeshActor",
    )
    missing = [name for name in required_symbols if not hasattr(unreal, name)]
    if missing:
        fail("Required Unreal Python symbols missing: " + ", ".join(missing))

    ensure_target_world_loaded()

    if actor_with_stable_id("Sewer.StageSentinel") is None:
        fail("Stage 7 sewer checkpoint is unavailable. Do not generate extraction yet.")
    if actor_with_stable_id("Winter.StageSentinel") is None:
        fail("Stage 6 Winter checkpoint is unavailable. Extraction requires Winter handoff.")

    existing = stage_actors(STAGE)
    if existing:
        fail(
            f"Refusing to duplicate extraction generation: {len(existing)} Stage-8 actors "
            "already exist."
        )

    if unreal.load_asset(ENGINE_CUBE) is None:
        fail(f"Engine greybox primitive is unavailable: {ENGINE_CUBE}")


def set_editor_layers(actor: Any, layers: tuple[str, ...]) -> None:
    try:
        actor.set_editor_property("layers", [unreal.Name(name) for name in layers])
    except Exception as error:
        warn(f"Unable to assign Editor Layers to {actor.get_actor_label()}: {error}")


def set_actor_identity(
    actor: Any,
    *,
    label: str,
    stable_id: str,
    folder: str,
    gameplay_marker: bool = False,
    persistent: bool = False,
    editor_only: bool = False,
) -> None:
    try:
        actor.set_actor_label(label, mark_dirty=True)
    except TypeError:
        actor.set_actor_label(label)
    actor.set_folder_path(unreal.Name(folder))
    add_generation_tags(actor, stage=STAGE, district="Extraction", stable_id=stable_id)
    set_editor_layers(
        actor,
        EDITOR_GAMEPLAY_LAYERS if gameplay_marker else EDITOR_GREYBOX_LAYERS,
    )
    try:
        actor.set_editor_property("is_spatially_loaded", not persistent)
    except Exception as error:
        warn(f"Unable to configure spatial loading for {label}: {error}")
    if editor_only:
        try:
            actor.set_editor_property("is_editor_only_actor", True)
        except Exception as error:
            warn(f"Unable to mark {label} editor-only: {error}")


def set_mesh(actor: Any, mesh: Any) -> Any:
    component = actor.get_editor_property("static_mesh_component")
    if component is None or not component.set_static_mesh(mesh):
        fail(f"Unable to assign greybox cube to {actor}")
    return component


def set_collision(component: Any, enabled: bool) -> None:
    try:
        component.set_collision_enabled(
            unreal.CollisionEnabled.QUERY_AND_PHYSICS
            if enabled
            else unreal.CollisionEnabled.NO_COLLISION
        )
    except Exception as error:
        warn(f"Unable to configure greybox collision: {error}")


def spawn_box(
    mesh: Any,
    *,
    label: str,
    stable_id: str,
    center: tuple[float, float, float],
    size: tuple[float, float, float],
    folder: str,
    yaw: float = 0.0,
    pitch: float = 0.0,
    collision: bool = True,
    gameplay_marker: bool = False,
    persistent: bool = False,
    editor_only: bool = False,
) -> Any:
    actor = get_actor_subsystem().spawn_actor_from_class(
        unreal.StaticMeshActor,
        unreal.Vector(*center),
        unreal.Rotator(roll=0.0, pitch=pitch, yaw=yaw),
    )
    if actor is None:
        fail(f"Unable to spawn extraction actor: {label}")
    component = set_mesh(actor, mesh)
    actor.set_actor_scale3d(
        unreal.Vector(size[0] / 100.0, size[1] / 100.0, size[2] / 100.0)
    )
    set_collision(component, collision)
    set_actor_identity(
        actor,
        label=label,
        stable_id=stable_id,
        folder=folder,
        gameplay_marker=gameplay_marker,
        persistent=persistent,
        editor_only=editor_only,
    )
    return actor


def segment_transform(
    start: tuple[float, float, float],
    end: tuple[float, float, float],
) -> tuple[tuple[float, float, float], float, float, float, float]:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    dz = end[2] - start[2]
    horizontal = math.hypot(dx, dy)
    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    if horizontal <= 0.0 or length <= 0.0:
        fail(f"Invalid extraction segment: start={start}, end={end}")
    center = (
        (start[0] + end[0]) * 0.5,
        (start[1] + end[1]) * 0.5,
        (start[2] + end[2]) * 0.5,
    )
    yaw = math.degrees(math.atan2(dy, dx))
    pitch = math.degrees(math.atan2(dz, horizontal))
    return center, horizontal, length, yaw, pitch


def spawn_route_surface(
    mesh: Any,
    route_id: str,
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    width: float,
) -> int:
    center, _horizontal, length, yaw, pitch = segment_transform(start, end)
    spawn_box(
        mesh,
        label=f"ZS_Extraction_Route_{route_id}",
        stable_id=f"Extraction.Route.{route_id}",
        center=center,
        size=(length, width, ROAD_THICKNESS),
        folder="ZombieSeasons/Extraction/Routes",
        yaw=yaw,
        pitch=pitch,
    )
    return 1


def create_stage_sentinel(mesh: Any) -> int:
    spawn_box(
        mesh,
        label="ZS_Extraction_StageSentinel",
        stable_id="Extraction.StageSentinel",
        center=(82000.0, -30000.0, 5200.0),
        size=(80.0, 80.0, 80.0),
        folder="ZombieSeasons/Extraction/System",
        collision=False,
        persistent=True,
        editor_only=True,
    )
    return 1


def create_routes(mesh: Any) -> int:
    count = 0
    for route_id, start, end, width in ROAD_SEGMENTS:
        count += spawn_route_surface(mesh, route_id, start, end, width)
    return count


def create_perimeter_entry(mesh: Any) -> int:
    x, y, z = POI_ANCHORS["DamPerimeterEntry"]
    folder = "ZombieSeasons/Extraction/PerimeterEntry"
    count = 0

    spawn_box(
        mesh,
        label="ZS_Extraction_Perimeter_Apron",
        stable_id="Extraction.Perimeter.Apron",
        center=(x, y, z + FLOOR_THICKNESS * 0.5),
        size=(4200.0, 3200.0, FLOOR_THICKNESS),
        folder=folder,
    )
    count += 1

    # Two gate towers frame a clear 16 m central opening; nothing blocks the route.
    for side, offset_y in (("North", 1600.0), ("South", -1600.0)):
        spawn_box(
            mesh,
            label=f"ZS_Extraction_Perimeter_Tower_{side}",
            stable_id=f"Extraction.Perimeter.Tower.{side}",
            center=(x, y + offset_y, z + 650.0),
            size=(900.0, 900.0, 1300.0),
            folder=folder,
        )
        count += 1

    for side, offset_y in (("North", 2450.0), ("South", -2450.0)):
        spawn_box(
            mesh,
            label=f"ZS_Extraction_Perimeter_Barrier_{side}",
            stable_id=f"Extraction.Perimeter.Barrier.{side}",
            center=(x + 700.0, y + offset_y, z + 250.0),
            size=(3000.0, 120.0, 500.0),
            folder=folder,
        )
        count += 1
    return count


def create_control_building(mesh: Any) -> int:
    x, y, z = POI_ANCHORS["ControlBuilding"]
    folder = "ZombieSeasons/Extraction/ControlBuilding"
    width = 3600.0
    depth = 2800.0
    wall_h = 600.0
    count = 0

    spawn_box(
        mesh,
        label="ZS_Extraction_Control_Floor",
        stable_id="Extraction.Control.Floor",
        center=(x, y, z + FLOOR_THICKNESS * 0.5),
        size=(width, depth, FLOOR_THICKNESS),
        folder=folder,
    )
    count += 1

    # West/east/north walls; south remains completely open as the mandatory entry.
    for side, cx, cy, sx, sy in (
        ("West", x - width * 0.5, y, STANDARD_WALL_THICKNESS, depth),
        ("East", x + width * 0.5, y, STANDARD_WALL_THICKNESS, depth),
        ("North", x, y + depth * 0.5, width, STANDARD_WALL_THICKNESS),
    ):
        spawn_box(
            mesh,
            label=f"ZS_Extraction_Control_Wall_{side}",
            stable_id=f"Extraction.Control.Wall.{side}",
            center=(cx, cy, z + wall_h * 0.5),
            size=(sx, sy, wall_h),
            folder=folder,
        )
        count += 1

    spawn_box(
        mesh,
        label="ZS_Extraction_Control_ConsoleMass",
        stable_id="Extraction.Control.ConsoleMass",
        center=(x, y + 650.0, z + 90.0),
        size=(1500.0, 450.0, 180.0),
        folder=folder,
    )
    count += 1
    return count


def create_defense_position(
    mesh: Any,
    *,
    name: str,
    anchor_key: str,
    width: float,
    depth: float,
) -> int:
    x, y, z = POI_ANCHORS[anchor_key]
    folder = f"ZombieSeasons/Extraction/Defense/{name}"
    count = 0

    spawn_box(
        mesh,
        label=f"ZS_Extraction_{name}_Floor",
        stable_id=f"Extraction.{name}.Floor",
        center=(x, y, z + FLOOR_THICKNESS * 0.5),
        size=(width, depth, FLOOR_THICKNESS),
        folder=folder,
    )
    count += 1

    # Six cover masses are deliberately offset from the center line, preserving at
    # least two broad exits and avoiding accidental single-entry arena geometry.
    cover_specs = (
        (-0.32, -0.28, 900.0, 500.0, 180.0),
        (+0.30, -0.22, 800.0, 650.0, 220.0),
        (-0.28, +0.24, 700.0, 700.0, 240.0),
        (+0.34, +0.26, 1000.0, 450.0, 190.0),
        (-0.05, -0.36, 500.0, 800.0, 160.0),
        (+0.08, +0.36, 550.0, 700.0, 170.0),
    )
    for index, (fx, fy, sx, sy, sz) in enumerate(cover_specs, start=1):
        spawn_box(
            mesh,
            label=f"ZS_Extraction_{name}_Cover_{index:02d}",
            stable_id=f"Extraction.{name}.Cover.{index:02d}",
            center=(x + fx * width, y + fy * depth, z + sz * 0.5),
            size=(sx, sy, sz),
            folder=folder,
        )
        count += 1
    return count


def create_final_crossing(mesh: Any) -> int:
    start = POI_ANCHORS["FinalCrossingStart"]
    end = POI_ANCHORS["ExtractionEndpoint"]
    center, horizontal, length, yaw, pitch = segment_transform(start, end)
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    nx = -dy / horizontal
    ny = dx / horizontal
    folder = "ZombieSeasons/Extraction/FinalCrossing"
    count = 0

    # The main crossing route already exists as ROAD_SEGMENTS[-1]. Side parapets make
    # the dam readable without blocking forward movement.
    side_offset = MAIN_ROAD_WIDTH * 0.5 + PARAPET_THICKNESS * 0.5
    for side, sign in (("Left", -1.0), ("Right", 1.0)):
        spawn_box(
            mesh,
            label=f"ZS_Extraction_FinalCrossing_Parapet_{side}",
            stable_id=f"Extraction.FinalCrossing.Parapet.{side}",
            center=(
                center[0] + nx * side_offset * sign,
                center[1] + ny * side_offset * sign,
                center[2] + PARAPET_HEIGHT * 0.5 + 10.0,
            ),
            size=(length, PARAPET_THICKNESS, PARAPET_HEIGHT),
            folder=folder,
            yaw=yaw,
            pitch=pitch,
        )
        count += 1

    # Two side-mounted final cover masses; center remains unobstructed.
    for index, (fraction, side_sign) in enumerate(((0.38, -1.0), (0.68, 1.0)), start=1):
        px = start[0] + (end[0] - start[0]) * fraction
        py = start[1] + (end[1] - start[1]) * fraction
        pz = start[2] + (end[2] - start[2]) * fraction
        spawn_box(
            mesh,
            label=f"ZS_Extraction_FinalCrossing_Cover_{index:02d}",
            stable_id=f"Extraction.FinalCrossing.Cover.{index:02d}",
            center=(
                px + nx * side_sign * 380.0,
                py + ny * side_sign * 380.0,
                pz + 90.0,
            ),
            size=(550.0, 300.0, 180.0),
            folder=folder,
            yaw=yaw,
        )
        count += 1
    return count


def create_dam_structural_masses(mesh: Any) -> int:
    # Replaceable art-pass masses sell the dam scale without interfering with the
    # critical route. All sit outside the playable center line.
    masses = (
        ("TurbineBlockA", (89500.0, -30000.0, 1500.0), (900.0, 5000.0, 1500.0)),
        ("TurbineBlockB", (89500.0, -24000.0, 1450.0), (900.0, 4200.0, 1400.0)),
        ("ServiceTowerA", (80500.0, -36500.0, 1700.0), (1500.0, 1500.0, 2200.0)),
        ("ServiceTowerB", (88500.0, -38500.0, 1850.0), (1400.0, 1400.0, 2400.0)),
        ("SpillwayMassA", (90000.0, -34500.0, 400.0), (700.0, 4500.0, 800.0)),
        ("SpillwayMassB", (90000.0, -20500.0, 550.0), (700.0, 3500.0, 900.0)),
    )
    for name, center, size in masses:
        spawn_box(
            mesh,
            label=f"ZS_Extraction_Structure_{name}",
            stable_id=f"Extraction.Structure.{name}",
            center=center,
            size=size,
            folder="ZombieSeasons/Extraction/StructuralMasses",
        )
    return len(masses)


def create_poi_anchor_markers(mesh: Any) -> int:
    count = 0
    for name, (x, y, z) in POI_ANCHORS.items():
        spawn_box(
            mesh,
            label=f"ZS_Extraction_POI_{name}",
            stable_id=f"Extraction.POI.{name}",
            center=(x, y, z + 1100.0),
            size=(100.0, 100.0, 2200.0),
            folder="ZombieSeasons/Extraction/Gameplay/POIAnchors",
            collision=False,
            gameplay_marker=True,
            editor_only=True,
        )
        count += 1
    return count


def create_gameplay_markers(mesh: Any) -> int:
    count = 0
    for stable_suffix, center in GAMEPLAY_MARKERS:
        safe_label = stable_suffix.replace(".", "_")
        spawn_box(
            mesh,
            label=f"ZS_Extraction_{safe_label}",
            stable_id=f"Extraction.{stable_suffix}",
            center=center,
            size=(140.0, 140.0, 1600.0),
            folder="ZombieSeasons/Extraction/Gameplay/Markers",
            collision=False,
            gameplay_marker=True,
            persistent=True,
            editor_only=True,
        )
        count += 1
    return count


def validate_topology() -> dict[str, float | int]:
    x_min, x_max = 72000.0, 90000.0
    y_min, y_max = -45000.0, -15000.0
    for name, (x, y, _z) in POI_ANCHORS.items():
        if not (x_min <= x <= x_max and y_min <= y <= y_max):
            fail(f"Extraction POI {name} lies outside frozen extraction bounds: {(x, y)}")

    max_grade = 0.0
    total_route_length = 0.0
    for route_id, start, end, width in ROAD_SEGMENTS:
        if width < SECONDARY_ROAD_WIDTH:
            fail(f"Extraction route {route_id} is narrower than 700 cm: {width}")
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        dz = end[2] - start[2]
        horizontal = math.hypot(dx, dy)
        if horizontal <= 0.0:
            fail(f"Extraction route {route_id} has no horizontal run.")
        grade = abs(dz / horizontal) * 100.0
        max_grade = max(max_grade, grade)
        total_route_length += math.sqrt(dx * dx + dy * dy + dz * dz)

    final_start = POI_ANCHORS["FinalCrossingStart"]
    final_end = POI_ANCHORS["ExtractionEndpoint"]
    final_crossing_length = math.dist(final_start, final_end)
    if final_end[0] > 90000.0:
        fail("Extraction endpoint exceeds the frozen +90000 cm world bound.")

    return {
        "route_count": len(ROAD_SEGMENTS),
        "total_route_length_cm": total_route_length,
        "maximum_route_grade_percent": max_grade,
        "final_crossing_length_cm": final_crossing_length,
        "poi_anchor_count": len(POI_ANCHORS),
        "gameplay_marker_count": len(GAMEPLAY_MARKERS),
    }


def save_level() -> None:
    if not get_level_subsystem().save_current_level():
        fail("Extraction actors were generated but the greybox level could not be saved.")


def position_viewport() -> None:
    try:
        subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        if subsystem is not None:
            subsystem.set_level_viewport_camera_info(
                unreal.Vector(76000.0, -42000.0, 26000.0),
                unreal.Rotator(roll=0.0, pitch=-48.0, yaw=55.0),
            )
    except Exception as error:
        warn(f"Unable to position viewport for extraction review: {error}")


def run() -> None:
    preflight()
    metrics = validate_topology()
    log("Stage 8 preflight passed. Creating deterministic extraction-dam greybox.")

    mesh = unreal.load_asset(ENGINE_CUBE)
    if mesh is None:
        fail(f"Engine cube disappeared after preflight: {ENGINE_CUBE}")

    sentinel_count = create_stage_sentinel(mesh)
    route_count = create_routes(mesh)
    perimeter_count = create_perimeter_entry(mesh)
    control_count = create_control_building(mesh)
    defense_a_count = create_defense_position(
        mesh,
        name="DefenseA",
        anchor_key="DefensePositionA",
        width=5500.0,
        depth=4500.0,
    )
    defense_b_count = create_defense_position(
        mesh,
        name="DefenseB",
        anchor_key="DefensePositionB",
        width=5200.0,
        depth=4600.0,
    )
    final_crossing_count = create_final_crossing(mesh)
    structural_count = create_dam_structural_masses(mesh)
    poi_marker_count = create_poi_anchor_markers(mesh)
    gameplay_marker_count = create_gameplay_markers(mesh)

    expected = (
        sentinel_count
        + route_count
        + perimeter_count
        + control_count
        + defense_a_count
        + defense_b_count
        + final_crossing_count
        + structural_count
        + poi_marker_count
        + gameplay_marker_count
    )
    generated = stage_actors(STAGE)
    if len(generated) != expected:
        fail(
            "Extraction generation count mismatch before save: "
            f"expected {expected}, found {len(generated)} loaded tagged actors."
        )

    save_level()
    position_viewport()

    report = write_json_report(
        "extraction_generation.json",
        {
            "status": "PASS",
            "stage": STAGE,
            "mode": MODE,
            "map": GREYBOX_MAP,
            "generated_actor_count": len(generated),
            "route_surface_count": route_count,
            "perimeter_actor_count": perimeter_count,
            "control_building_actor_count": control_count,
            "defense_a_actor_count": defense_a_count,
            "defense_b_actor_count": defense_b_count,
            "final_crossing_actor_count": final_crossing_count,
            "structural_mass_count": structural_count,
            "poi_anchor_marker_count": poi_marker_count,
            "gameplay_marker_count": gameplay_marker_count,
            "poi_anchors": POI_ANCHORS,
            "maximum_route_grade_percent": metrics["maximum_route_grade_percent"],
            "total_route_length_cm": metrics["total_route_length_cm"],
            "final_crossing_length_cm": metrics["final_crossing_length_cm"],
            "moving_defense_positions": ["DefenseA", "DefenseB"],
            "runtime_objective_adapters_created": False,
            "zombie_spawn_markers_created": False,
            "loot_markers_created": False,
            "final_art_assets_loaded": False,
            "historical_maps_modified": False,
        },
    )

    summary = (
        "Extraction dam greybox generation PASSED.\n\n"
        f"Map: {GREYBOX_MAP}\n"
        f"Generated extraction actors: {len(generated)}\n"
        f"Playable route surfaces: {route_count}\n"
        f"Perimeter actors: {perimeter_count}\n"
        f"Control-building actors: {control_count}\n"
        f"Defense-A actors: {defense_a_count}\n"
        f"Defense-B actors: {defense_b_count}\n"
        f"Final-crossing actors: {final_crossing_count}\n"
        f"Structural masses: {structural_count}\n"
        f"POI anchor markers: {poi_marker_count}\n"
        f"Gameplay markers: {gameplay_marker_count}\n"
        f"Max route grade: {metrics['maximum_route_grade_percent']:.3f}%\n"
        f"Total extraction-route length: {metrics['total_route_length_cm'] / 100.0:.1f} m\n"
        f"Final crossing length: {metrics['final_crossing_length_cm'] / 100.0:.1f} m\n\n"
        "The final sequence has two moving-defense positions and an unobstructed crossing.\n"
        "Zombie spawns, loot, objective runtime state and final art remain deferred.\n"
        f"Report:\n{report}"
    )
    log(summary.replace("\n", " "))
    show_editor_message("ZombieSeasons World Generation — Stage 8", summary)


if __name__ == "__main__":
    run()
