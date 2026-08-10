"""Create the deterministic ZombieSeasons Winter district greybox.

Run from Unreal Editor only after Stage 5 Autumn has passed and been committed:

py "C:/Users/malik/Documents/Unreal Projects/ZombieSeasons/Content/Python/ZombieSeasons/MapGeneration/06_create_winter.py"

Stage 6 creates topology-critical Winter geometry only: roads, industrial POI
footprints, loading-yard and power-station combat spaces, elevated traversal, and
the three required Winter shortcuts. Final City Sample/Fab art, zombie spawns, loot,
and runtime objective adapters remain deferred to later stages.
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


STAGE = "Winter"
MODE = "CREATE"
ENGINE_CUBE = "/Engine/BasicShapes/Cube.Cube"

WINTER_GROUND_Z = 500.0
ROAD_THICKNESS = 36.0
ROAD_CENTER_OFFSET = ROAD_THICKNESS * 0.5 + 2.0
MAIN_ROAD_WIDTH = 1200.0
SECONDARY_ROAD_WIDTH = 700.0
SERVICE_ROAD_WIDTH = 500.0
PATH_WIDTH = 420.0

STANDARD_WALL_HEIGHT = 520.0
STANDARD_WALL_THICKNESS = 100.0
ARENA_WALL_HEIGHT = 560.0
ARENA_WALL_THICKNESS = 110.0
FLOOR_THICKNESS = 24.0

EDITOR_GREYBOX_LAYERS = (
    "DL_ZS_Greybox",
    "DL_ZS_Winter",
)
EDITOR_GAMEPLAY_LAYERS = (
    "DL_ZS_Greybox",
    "DL_ZS_Gameplay",
    "DL_ZS_Winter",
)

# Frozen production anchors from 07_Production_World_Specification.md.
POI_ANCHORS: dict[str, tuple[float, float, float]] = {
    "Warehouse": (32000.0, -33000.0, 500.0),
    "LoadingYardArena": (53000.0, -43000.0, 400.0),
    "MaintenanceWorkshops": (35000.0, -66000.0, 500.0),
    "PowerStation": (65000.0, -66000.0, 700.0),
    "CoolingChannel": (78000.0, -56000.0, 300.0),
    "SewerControlRoom": (25000.0, -78000.0, -500.0),
    "DamServiceRoadGate": (76000.0, -33000.0, 600.0),
}

# Explicit 3D road endpoints prevent hard vertical steps between Hub and Winter.
# Tuple: id, start(x,y,z), end(x,y,z), width.
ROAD_SEGMENTS: tuple[
    tuple[str, tuple[float, float, float], tuple[float, float, float], float], ...
] = (
    (
        "Main_Entry",
        (15000.0, -15000.0, 20.0),
        (32000.0, -33000.0, WINTER_GROUND_Z + ROAD_CENTER_OFFSET),
        MAIN_ROAD_WIDTH,
    ),
    (
        "Warehouse_Loading",
        (32000.0, -33000.0, WINTER_GROUND_Z + ROAD_CENTER_OFFSET),
        (53000.0, -43000.0, 400.0 + ROAD_CENTER_OFFSET),
        900.0,
    ),
    (
        "Warehouse_Workshops",
        (32000.0, -33000.0, WINTER_GROUND_Z + ROAD_CENTER_OFFSET),
        (35000.0, -66000.0, WINTER_GROUND_Z + ROAD_CENTER_OFFSET),
        SECONDARY_ROAD_WIDTH,
    ),
    (
        "Loading_Power",
        (53000.0, -43000.0, 400.0 + ROAD_CENTER_OFFSET),
        (65000.0, -66000.0, 700.0 + ROAD_CENTER_OFFSET),
        900.0,
    ),
    (
        "Workshops_Power",
        (35000.0, -66000.0, WINTER_GROUND_Z + ROAD_CENTER_OFFSET),
        (65000.0, -66000.0, 700.0 + ROAD_CENTER_OFFSET),
        SECONDARY_ROAD_WIDTH,
    ),
    (
        "Power_Cooling",
        (65000.0, -66000.0, 700.0 + ROAD_CENTER_OFFSET),
        (78000.0, -56000.0, 300.0 + ROAD_CENTER_OFFSET),
        SECONDARY_ROAD_WIDTH,
    ),
    (
        "Loading_DamGate",
        (53000.0, -43000.0, 400.0 + ROAD_CENTER_OFFSET),
        (76000.0, -33000.0, 600.0 + ROAD_CENTER_OFFSET),
        900.0,
    ),
    (
        "Cooling_Service",
        (78000.0, -56000.0, 300.0 + ROAD_CENTER_OFFSET),
        (82000.0, -43000.0, 500.0 + ROAD_CENTER_OFFSET),
        SERVICE_ROAD_WIDTH,
    ),
    (
        "Southern_Cross_Stub",
        (35000.0, -66000.0, WINTER_GROUND_Z + ROAD_CENTER_OFFSET),
        (16000.0, -70000.0, 300.0 + ROAD_CENTER_OFFSET),
        SECONDARY_ROAD_WIDTH,
    ),
    (
        "Eastern_Cross_Stub",
        (76000.0, -33000.0, 600.0 + ROAD_CENTER_OFFSET),
        (79000.0, -17000.0, 500.0 + ROAD_CENTER_OFFSET),
        SERVICE_ROAD_WIDTH,
    ),
    (
        "Extraction_Handoff",
        (76000.0, -33000.0, 600.0 + ROAD_CENTER_OFFSET),
        (79000.0, -31000.0, 700.0 + ROAD_CENTER_OFFSET),
        MAIN_ROAD_WIDTH,
    ),
)

# Required Winter topology improvements from 02_District_Specifications.md.
SHORTCUT_SEGMENTS: tuple[
    tuple[str, tuple[float, float, float], tuple[float, float, float], float], ...
] = (
    (
        "WarehouseConveyorBridge",
        (34000.0, -34500.0, 1850.0),
        (42500.0, -38500.0, 1850.0),
        PATH_WIDTH,
    ),
    (
        "UtilityTunnel",
        (35000.0, -66000.0, 300.0),
        (25000.0, -78000.0, -480.0),
        SERVICE_ROAD_WIDTH,
    ),
    (
        "DamServiceRoad",
        (65000.0, -66000.0, 700.0 + ROAD_CENTER_OFFSET + 4.0),
        (76000.0, -33000.0, 600.0 + ROAD_CENTER_OFFSET + 4.0),
        SECONDARY_ROAD_WIDTH,
    ),
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
            "Unsaved map packages are open. Save or discard them before Stage 6: "
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
        fail(f"Unsupported Winter generation mode: {MODE}")
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

    if actor_with_stable_id("Autumn.StageSentinel") is None:
        fail("Stage 5 Autumn checkpoint is unavailable. Do not generate Winter yet.")

    existing = stage_actors(STAGE)
    if existing:
        fail(
            f"Refusing to duplicate Winter generation: {len(existing)} Stage-6 actors "
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
    add_generation_tags(actor, stage=STAGE, district="Winter", stable_id=stable_id)
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
        fail(f"Unable to spawn Winter actor: {label}")
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


def direction_rotator(dx: float, dy: float, dz: float) -> Any:
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


def spawn_segment_3d(
    mesh: Any,
    *,
    label: str,
    stable_id: str,
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    width: float,
    thickness: float,
    folder: str,
    collision: bool = True,
) -> Any:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    dz = end[2] - start[2]
    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    if length <= 0.0:
        fail(f"Zero-length Winter segment requested: {stable_id}")

    actor = spawn_box(
        mesh,
        label=label,
        stable_id=stable_id,
        center=(
            (start[0] + end[0]) * 0.5,
            (start[1] + end[1]) * 0.5,
            (start[2] + end[2]) * 0.5,
        ),
        size=(length, width, thickness),
        folder=folder,
        collision=collision,
    )
    actor.set_actor_rotation(direction_rotator(dx, dy, dz), False)
    return actor


def wall_pair_with_gap(
    mesh: Any,
    *,
    prefix: str,
    side: str,
    center: tuple[float, float],
    axis: str,
    total_length: float,
    gap_width: float,
    wall_height: float,
    wall_thickness: float,
    ground_z: float,
    folder: str,
) -> int:
    segment_length = (total_length - gap_width) * 0.5
    if segment_length <= 0.0:
        fail(f"Invalid wall/gap dimensions for {prefix}.{side}")
    offset = gap_width * 0.5 + segment_length * 0.5

    for suffix, sign in (("A", -1.0), ("B", 1.0)):
        if axis == "X":
            actor_center = (
                center[0] + sign * offset,
                center[1],
                ground_z + wall_height * 0.5,
            )
            size = (segment_length, wall_thickness, wall_height)
        else:
            actor_center = (
                center[0],
                center[1] + sign * offset,
                ground_z + wall_height * 0.5,
            )
            size = (wall_thickness, segment_length, wall_height)

        spawn_box(
            mesh,
            label=f"ZS_Winter_{prefix}_{side}_{suffix}",
            stable_id=f"Winter.{prefix}.{side}.{suffix}",
            center=actor_center,
            size=size,
            folder=folder,
        )
    return 2


def create_open_structure(
    mesh: Any,
    *,
    prefix: str,
    center: tuple[float, float],
    width: float,
    depth: float,
    ground_z: float,
    south_gap: float,
    east_gap: float,
    wall_height: float,
    folder: str,
) -> int:
    half_w = width * 0.5
    half_d = depth * 0.5
    count = 0

    spawn_box(
        mesh,
        label=f"ZS_Winter_{prefix}_Floor",
        stable_id=f"Winter.{prefix}.Floor",
        center=(center[0], center[1], ground_z + FLOOR_THICKNESS * 0.5),
        size=(width, depth, FLOOR_THICKNESS),
        folder=folder,
    )
    count += 1

    spawn_box(
        mesh,
        label=f"ZS_Winter_{prefix}_Wall_North",
        stable_id=f"Winter.{prefix}.Wall.North",
        center=(center[0], center[1] + half_d, ground_z + wall_height * 0.5),
        size=(width, STANDARD_WALL_THICKNESS, wall_height),
        folder=folder,
    )
    count += 1

    spawn_box(
        mesh,
        label=f"ZS_Winter_{prefix}_Wall_West",
        stable_id=f"Winter.{prefix}.Wall.West",
        center=(center[0] - half_w, center[1], ground_z + wall_height * 0.5),
        size=(STANDARD_WALL_THICKNESS, depth, wall_height),
        folder=folder,
    )
    count += 1

    count += wall_pair_with_gap(
        mesh,
        prefix=f"{prefix}.Wall",
        side="South",
        center=(center[0], center[1] - half_d),
        axis="X",
        total_length=width,
        gap_width=south_gap,
        wall_height=wall_height,
        wall_thickness=STANDARD_WALL_THICKNESS,
        ground_z=ground_z,
        folder=folder,
    )
    count += wall_pair_with_gap(
        mesh,
        prefix=f"{prefix}.Wall",
        side="East",
        center=(center[0] + half_w, center[1]),
        axis="Y",
        total_length=depth,
        gap_width=east_gap,
        wall_height=wall_height,
        wall_thickness=STANDARD_WALL_THICKNESS,
        ground_z=ground_z,
        folder=folder,
    )
    return count


def create_stage_sentinel(mesh: Any) -> int:
    spawn_box(
        mesh,
        label="ZS_Winter_StageSentinel",
        stable_id="Winter.StageSentinel",
        center=(52000.0, -52000.0, 5200.0),
        size=(80.0, 80.0, 80.0),
        folder="ZombieSeasons/Winter/System",
        collision=False,
        persistent=True,
        editor_only=True,
    )
    return 1


def create_roads(mesh: Any) -> int:
    for road_id, start, end, width in ROAD_SEGMENTS:
        spawn_segment_3d(
            mesh,
            label=f"ZS_Winter_Road_{road_id}",
            stable_id=f"Winter.Road.{road_id}",
            start=start,
            end=end,
            width=width,
            thickness=ROAD_THICKNESS,
            folder="ZombieSeasons/Winter/Roads",
        )
    return len(ROAD_SEGMENTS)


def create_shortcuts(mesh: Any) -> int:
    for shortcut_id, start, end, width in SHORTCUT_SEGMENTS:
        spawn_segment_3d(
            mesh,
            label=f"ZS_Winter_Shortcut_{shortcut_id}",
            stable_id=f"Winter.Shortcut.{shortcut_id}",
            start=start,
            end=end,
            width=width,
            thickness=ROAD_THICKNESS,
            folder="ZombieSeasons/Winter/Shortcuts",
        )
    return len(SHORTCUT_SEGMENTS)


def create_warehouse(mesh: Any) -> int:
    center = (32000.0, -33000.0)
    ground_z = WINTER_GROUND_Z
    width = 6200.0
    depth = 4800.0
    half_w = width * 0.5
    half_d = depth * 0.5
    count = 0

    spawn_box(
        mesh,
        label="ZS_Winter_Warehouse_Floor",
        stable_id="Winter.Warehouse.Floor",
        center=(center[0], center[1], ground_z + FLOOR_THICKNESS * 0.5),
        size=(width, depth, FLOOR_THICKNESS),
        folder="ZombieSeasons/Winter/POI/Warehouse",
    )
    count += 1

    count += wall_pair_with_gap(
        mesh,
        prefix="Warehouse.Wall",
        side="South",
        center=(center[0], center[1] - half_d),
        axis="X",
        total_length=width,
        gap_width=1200.0,
        wall_height=STANDARD_WALL_HEIGHT,
        wall_thickness=STANDARD_WALL_THICKNESS,
        ground_z=ground_z,
        folder="ZombieSeasons/Winter/POI/Warehouse",
    )
    count += wall_pair_with_gap(
        mesh,
        prefix="Warehouse.Wall",
        side="East",
        center=(center[0] + half_w, center[1]),
        axis="Y",
        total_length=depth,
        gap_width=1000.0,
        wall_height=STANDARD_WALL_HEIGHT,
        wall_thickness=STANDARD_WALL_THICKNESS,
        ground_z=ground_z,
        folder="ZombieSeasons/Winter/POI/Warehouse",
    )

    for side, wall_center, size in (
        ("North", (center[0], center[1] + half_d), (width, STANDARD_WALL_THICKNESS, STANDARD_WALL_HEIGHT)),
        ("West", (center[0] - half_w, center[1]), (STANDARD_WALL_THICKNESS, depth, STANDARD_WALL_HEIGHT)),
    ):
        spawn_box(
            mesh,
            label=f"ZS_Winter_Warehouse_Wall_{side}",
            stable_id=f"Winter.Warehouse.Wall.{side}",
            center=(wall_center[0], wall_center[1], ground_z + STANDARD_WALL_HEIGHT * 0.5),
            size=size,
            folder="ZombieSeasons/Winter/POI/Warehouse",
        )
        count += 1

    for index, x in enumerate((30500.0, 32000.0, 33500.0), start=1):
        spawn_box(
            mesh,
            label=f"ZS_Winter_Warehouse_Aisle_{index}",
            stable_id=f"Winter.Warehouse.Aisle.{index}",
            center=(x, -33000.0, ground_z + 160.0),
            size=(500.0, 3000.0, 320.0),
            folder="ZombieSeasons/Winter/POI/Warehouse/Aisles",
        )
        count += 1

    spawn_box(
        mesh,
        label="ZS_Winter_Warehouse_Catwalk",
        stable_id="Winter.Warehouse.Catwalk",
        center=(32000.0, -33000.0, 1550.0),
        size=(5000.0, 320.0, 30.0),
        folder="ZombieSeasons/Winter/POI/Warehouse/Traversal",
    )
    count += 1
    return count


def create_loading_yard(mesh: Any) -> int:
    center = (53000.0, -43000.0)
    ground_z = 400.0
    width = 8500.0
    depth = 8500.0
    half_w = width * 0.5
    half_d = depth * 0.5
    count = 0

    spawn_box(
        mesh,
        label="ZS_Winter_LoadingYard_Floor",
        stable_id="Winter.LoadingYard.Floor",
        center=(center[0], center[1], ground_z + FLOOR_THICKNESS * 0.5),
        size=(width, depth, FLOOR_THICKNESS),
        folder="ZombieSeasons/Winter/POI/LoadingYard",
    )
    count += 1

    # Three exits: north, south, and east. West remains a solid pressure edge.
    for side, wall_center, axis in (
        ("North", (center[0], center[1] + half_d), "X"),
        ("South", (center[0], center[1] - half_d), "X"),
        ("East", (center[0] + half_w, center[1]), "Y"),
    ):
        count += wall_pair_with_gap(
            mesh,
            prefix="LoadingYard.Wall",
            side=side,
            center=wall_center,
            axis=axis,
            total_length=width if axis == "X" else depth,
            gap_width=1400.0,
            wall_height=ARENA_WALL_HEIGHT,
            wall_thickness=ARENA_WALL_THICKNESS,
            ground_z=ground_z,
            folder="ZombieSeasons/Winter/POI/LoadingYard",
        )

    spawn_box(
        mesh,
        label="ZS_Winter_LoadingYard_Wall_West",
        stable_id="Winter.LoadingYard.Wall.West",
        center=(center[0] - half_w, center[1], ground_z + ARENA_WALL_HEIGHT * 0.5),
        size=(ARENA_WALL_THICKNESS, depth, ARENA_WALL_HEIGHT),
        folder="ZombieSeasons/Winter/POI/LoadingYard",
    )
    count += 1

    for index, (x, y) in enumerate(
        ((51000.0, -41500.0), (54800.0, -41700.0), (51500.0, -45200.0), (55000.0, -45100.0)),
        start=1,
    ):
        spawn_box(
            mesh,
            label=f"ZS_Winter_LoadingYard_Cover_{index}",
            stable_id=f"Winter.LoadingYard.Cover.{index}",
            center=(x, y, ground_z + 150.0),
            size=(1000.0, 500.0, 300.0),
            folder="ZombieSeasons/Winter/POI/LoadingYard/Cover",
        )
        count += 1
    return count


def create_workshops(mesh: Any) -> int:
    count = create_open_structure(
        mesh,
        prefix="Workshops",
        center=(35000.0, -66000.0),
        width=5600.0,
        depth=4200.0,
        ground_z=WINTER_GROUND_Z,
        south_gap=1000.0,
        east_gap=900.0,
        wall_height=500.0,
        folder="ZombieSeasons/Winter/POI/Workshops",
    )
    for index, x in enumerate((34000.0, 36000.0), start=1):
        spawn_box(
            mesh,
            label=f"ZS_Winter_Workshops_Separator_{index}",
            stable_id=f"Winter.Workshops.Separator.{index}",
            center=(x, -66000.0, WINTER_GROUND_Z + 220.0),
            size=(100.0, 2400.0, 440.0),
            folder="ZombieSeasons/Winter/POI/Workshops",
        )
        count += 1
    return count


def create_power_station(mesh: Any) -> int:
    center = (65000.0, -66000.0)
    ground_z = 700.0
    width = 9000.0
    depth = 6500.0
    half_w = width * 0.5
    half_d = depth * 0.5
    count = 0

    spawn_box(
        mesh,
        label="ZS_Winter_PowerStation_Floor",
        stable_id="Winter.PowerStation.Floor",
        center=(center[0], center[1], ground_z + FLOOR_THICKNESS * 0.5),
        size=(width, depth, FLOOR_THICKNESS),
        folder="ZombieSeasons/Winter/POI/PowerStation",
    )
    count += 1

    for side, wall_center in (
        ("North", (center[0], center[1] + half_d)),
        ("South", (center[0], center[1] - half_d)),
    ):
        count += wall_pair_with_gap(
            mesh,
            prefix="PowerStation.Wall",
            side=side,
            center=wall_center,
            axis="X",
            total_length=width,
            gap_width=1400.0,
            wall_height=ARENA_WALL_HEIGHT,
            wall_thickness=ARENA_WALL_THICKNESS,
            ground_z=ground_z,
            folder="ZombieSeasons/Winter/POI/PowerStation",
        )

    for side, x in (("West", center[0] - half_w), ("East", center[0] + half_w)):
        spawn_box(
            mesh,
            label=f"ZS_Winter_PowerStation_Wall_{side}",
            stable_id=f"Winter.PowerStation.Wall.{side}",
            center=(x, center[1], ground_z + ARENA_WALL_HEIGHT * 0.5),
            size=(ARENA_WALL_THICKNESS, depth, ARENA_WALL_HEIGHT),
            folder="ZombieSeasons/Winter/POI/PowerStation",
        )
        count += 1

    for index, (x, y, sx, sy) in enumerate(
        (
            (62500.0, -65000.0, 1400.0, 900.0),
            (67500.0, -65000.0, 1400.0, 900.0),
            (62500.0, -67500.0, 1400.0, 900.0),
            (67500.0, -67500.0, 1400.0, 900.0),
        ),
        start=1,
    ):
        spawn_box(
            mesh,
            label=f"ZS_Winter_PowerStation_Machinery_{index}",
            stable_id=f"Winter.PowerStation.Machinery.{index}",
            center=(x, y, ground_z + 500.0),
            size=(sx, sy, 1000.0),
            folder="ZombieSeasons/Winter/POI/PowerStation/Machinery",
        )
        count += 1

    for suffix, center_pos, size in (
        ("Longitudinal", (65000.0, -66000.0, 2050.0), (7600.0, 320.0, 30.0)),
        ("Cross", (65000.0, -66000.0, 2050.0), (320.0, 5200.0, 30.0)),
    ):
        spawn_box(
            mesh,
            label=f"ZS_Winter_PowerStation_Catwalk_{suffix}",
            stable_id=f"Winter.PowerStation.Catwalk.{suffix}",
            center=center_pos,
            size=size,
            folder="ZombieSeasons/Winter/POI/PowerStation/Traversal",
        )
        count += 1

    for stage_name, x in (("A", 62500.0), ("B", 65000.0), ("C", 67500.0)):
        spawn_box(
            mesh,
            label=f"ZS_Winter_PowerStation_DefensePad_{stage_name}",
            stable_id=f"Winter.PowerStation.DefensePad.{stage_name}",
            center=(x, -66000.0, ground_z + 18.0),
            size=(1800.0, 1500.0, 36.0),
            folder="ZombieSeasons/Winter/POI/PowerStation/DefenseStages",
        )
        count += 1
    return count


def create_cooling_channel(mesh: Any) -> int:
    ground_z = 300.0
    count = 0
    spawn_box(
        mesh,
        label="ZS_Winter_CoolingChannel_Floor",
        stable_id="Winter.CoolingChannel.Floor",
        center=(78000.0, -56000.0, ground_z - 120.0),
        size=(7000.0, 1800.0, 60.0),
        folder="ZombieSeasons/Winter/POI/CoolingChannel",
    )
    count += 1
    for side, y in (("North", -54900.0), ("South", -57100.0)):
        spawn_box(
            mesh,
            label=f"ZS_Winter_CoolingChannel_Wall_{side}",
            stable_id=f"Winter.CoolingChannel.Wall.{side}",
            center=(78000.0, y, ground_z + 180.0),
            size=(7000.0, 120.0, 600.0),
            folder="ZombieSeasons/Winter/POI/CoolingChannel",
        )
        count += 1
    spawn_box(
        mesh,
        label="ZS_Winter_CoolingChannel_Bridge",
        stable_id="Winter.CoolingChannel.Bridge",
        center=(78000.0, -56000.0, ground_z + 500.0),
        size=(900.0, 2600.0, 40.0),
        folder="ZombieSeasons/Winter/POI/CoolingChannel/Traversal",
    )
    count += 1
    spawn_box(
        mesh,
        label="ZS_Winter_CoolingChannel_MaintenancePad",
        stable_id="Winter.CoolingChannel.MaintenancePad",
        center=(80500.0, -56000.0, ground_z + 20.0),
        size=(1600.0, 1500.0, 40.0),
        folder="ZombieSeasons/Winter/POI/CoolingChannel",
    )
    count += 1
    return count


def create_sewer_control(mesh: Any) -> int:
    count = create_open_structure(
        mesh,
        prefix="SewerControl",
        center=(25000.0, -78000.0),
        width=4200.0,
        depth=3200.0,
        ground_z=-500.0,
        south_gap=900.0,
        east_gap=800.0,
        wall_height=460.0,
        folder="ZombieSeasons/Winter/POI/SewerControl",
    )
    spawn_box(
        mesh,
        label="ZS_Winter_SewerControl_ConsoleMass",
        stable_id="Winter.SewerControl.ConsoleMass",
        center=(25000.0, -77200.0, -300.0),
        size=(1600.0, 500.0, 400.0),
        folder="ZombieSeasons/Winter/POI/SewerControl",
    )
    count += 1
    return count


def create_dam_service_gate(mesh: Any) -> int:
    ground_z = 600.0
    count = 0
    for suffix, y in (("A", -33750.0), ("B", -32250.0)):
        spawn_box(
            mesh,
            label=f"ZS_Winter_DamGate_Pillar_{suffix}",
            stable_id=f"Winter.DamGate.Pillar.{suffix}",
            center=(76000.0, y, ground_z + 300.0),
            size=(300.0, 300.0, 600.0),
            folder="ZombieSeasons/Winter/POI/DamGate",
        )
        count += 1
    spawn_box(
        mesh,
        label="ZS_Winter_DamGate_Beam",
        stable_id="Winter.DamGate.Beam",
        center=(76000.0, -33000.0, ground_z + 650.0),
        size=(300.0, 1800.0, 160.0),
        folder="ZombieSeasons/Winter/POI/DamGate",
    )
    count += 1
    spawn_box(
        mesh,
        label="ZS_Winter_DamGate_ControlBooth",
        stable_id="Winter.DamGate.ControlBooth",
        center=(74800.0, -34700.0, ground_z + 260.0),
        size=(1400.0, 1000.0, 520.0),
        folder="ZombieSeasons/Winter/POI/DamGate",
    )
    count += 1
    return count


def create_industrial_masses(mesh: Any) -> int:
    masses = (
        ("BlockA", (43000.0, -30000.0), (4200.0, 2600.0, 1200.0)),
        ("BlockB", (44000.0, -56000.0), (3500.0, 2400.0, 1000.0)),
        ("BlockC", (56000.0, -56000.0), (3800.0, 2400.0, 1350.0)),
        ("BlockD", (73000.0, -47000.0), (3400.0, 2300.0, 1100.0)),
        ("BlockE", (47000.0, -74000.0), (3600.0, 2500.0, 950.0)),
        ("BlockF", (76000.0, -71000.0), (4300.0, 2600.0, 1450.0)),
        ("BlockG", (60000.0, -26000.0), (3200.0, 2200.0, 900.0)),
        ("BlockH", (82000.0, -36000.0), (3000.0, 2200.0, 1050.0)),
    )
    for suffix, center, size in masses:
        spawn_box(
            mesh,
            label=f"ZS_Winter_IndustrialMass_{suffix}",
            stable_id=f"Winter.IndustrialMass.{suffix}",
            center=(center[0], center[1], WINTER_GROUND_Z + size[2] * 0.5),
            size=size,
            folder="ZombieSeasons/Winter/IndustrialMasses",
        )
    return len(masses)


def create_poi_anchor_markers(mesh: Any) -> int:
    count = 0
    for name, (x, y, z) in POI_ANCHORS.items():
        spawn_box(
            mesh,
            label=f"ZS_Winter_POI_{name}",
            stable_id=f"Winter.POI.{name}",
            center=(x, y, max(z, -500.0) + 1200.0),
            size=(120.0, 120.0, 2400.0),
            folder="ZombieSeasons/Winter/POI/Anchors",
            collision=False,
            gameplay_marker=True,
            editor_only=True,
        )
        count += 1
    return count


def save_level() -> None:
    if not get_level_subsystem().save_current_level():
        fail("Winter actors were generated but the greybox level could not be saved.")


def position_viewport() -> None:
    try:
        subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        if subsystem is not None:
            subsystem.set_level_viewport_camera_info(
                unreal.Vector(56000.0, -12000.0, 50000.0),
                unreal.Rotator(roll=0.0, pitch=-42.0, yaw=-90.0),
            )
    except Exception as error:
        warn(f"Unable to position viewport for Winter review: {error}")


def run() -> None:
    preflight()
    log("Stage 6 preflight passed. Creating deterministic Winter greybox.")

    mesh = unreal.load_asset(ENGINE_CUBE)
    if mesh is None:
        fail(f"Engine cube disappeared after preflight: {ENGINE_CUBE}")

    sentinel_count = create_stage_sentinel(mesh)
    road_count = create_roads(mesh)
    shortcut_count = create_shortcuts(mesh)
    warehouse_count = create_warehouse(mesh)
    loading_yard_count = create_loading_yard(mesh)
    workshops_count = create_workshops(mesh)
    power_station_count = create_power_station(mesh)
    cooling_channel_count = create_cooling_channel(mesh)
    sewer_control_count = create_sewer_control(mesh)
    dam_gate_count = create_dam_service_gate(mesh)
    industrial_mass_count = create_industrial_masses(mesh)
    poi_marker_count = create_poi_anchor_markers(mesh)

    expected = (
        sentinel_count
        + road_count
        + shortcut_count
        + warehouse_count
        + loading_yard_count
        + workshops_count
        + power_station_count
        + cooling_channel_count
        + sewer_control_count
        + dam_gate_count
        + industrial_mass_count
        + poi_marker_count
    )
    generated = stage_actors(STAGE)
    if len(generated) != expected:
        fail(
            "Winter generation count mismatch before save: "
            f"expected {expected}, found {len(generated)} loaded tagged actors."
        )

    main_start = ROAD_SEGMENTS[0][1]
    main_end = ROAD_SEGMENTS[0][2]
    horizontal_run = math.hypot(main_end[0] - main_start[0], main_end[1] - main_start[1])
    rise = main_end[2] - main_start[2]
    entry_grade_percent = (rise / horizontal_run) * 100.0

    save_level()
    position_viewport()

    report = write_json_report(
        "winter_generation.json",
        {
            "status": "PASS",
            "stage": STAGE,
            "mode": MODE,
            "map": GREYBOX_MAP,
            "generated_actor_count": len(generated),
            "road_surface_count": road_count,
            "shortcut_route_count": shortcut_count,
            "warehouse_actor_count": warehouse_count,
            "loading_yard_actor_count": loading_yard_count,
            "workshops_actor_count": workshops_count,
            "power_station_actor_count": power_station_count,
            "cooling_channel_actor_count": cooling_channel_count,
            "sewer_control_actor_count": sewer_control_count,
            "dam_gate_actor_count": dam_gate_count,
            "industrial_mass_count": industrial_mass_count,
            "poi_anchor_marker_count": poi_marker_count,
            "required_shortcuts": [item[0] for item in SHORTCUT_SEGMENTS],
            "loading_yard_target_footprint_m": [85, 85],
            "loading_yard_exit_count": 3,
            "power_station_defense_stage_count": 3,
            "power_station_primary_exit_count": 2,
            "entry_transition_rise_cm": rise,
            "entry_transition_horizontal_run_cm": horizontal_run,
            "entry_transition_grade_percent": entry_grade_percent,
            "objective_adapter_created": False,
            "zombie_spawn_markers_created": False,
            "loot_markers_created": False,
            "final_art_assets_loaded": False,
            "historical_maps_modified": False,
        },
    )

    summary = (
        "Winter greybox generation PASSED.\n\n"
        f"Map: {GREYBOX_MAP}\n"
        f"Generated Winter actors: {len(generated)}\n"
        f"Playable roads: {road_count}\n"
        f"Required shortcuts: {shortcut_count}\n"
        f"Warehouse actors: {warehouse_count}\n"
        f"Loading-yard actors: {loading_yard_count}\n"
        f"Workshops actors: {workshops_count}\n"
        f"Power-station actors: {power_station_count}\n"
        f"Cooling-channel actors: {cooling_channel_count}\n"
        f"Sewer-control actors: {sewer_control_count}\n"
        f"Dam-gate actors: {dam_gate_count}\n"
        f"Industrial masses: {industrial_mass_count}\n"
        f"POI anchor markers: {poi_marker_count}\n"
        f"Hub -> Winter entry grade: {entry_grade_percent:.3f}%\n\n"
        "Zombie spawns, loot and runtime objective adapters remain deferred to Stage 9.\n"
        "No final Fab/City Sample art was loaded.\n"
        f"Report:\n{report}"
    )
    log(summary.replace("\n", " "))
    show_editor_message("ZombieSeasons World Generation — Stage 6", summary)


if __name__ == "__main__":
    run()
