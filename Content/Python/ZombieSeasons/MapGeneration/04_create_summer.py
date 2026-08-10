"""Create the deterministic ZombieSeasons Summer district greybox.

Run from Unreal Editor only after Stage 3 and the Spring transition repair have
passed and been committed:

py "C:/Users/malik/Documents/Unreal Projects/ZombieSeasons/Content/Python/ZombieSeasons/MapGeneration/04_create_summer.py"

Stage 4 creates topology-critical Summer geometry only: roads, POI footprints,
combat/traversal spaces, and the three required shortcut routes. Final City Sample,
Fab art, zombie spawns, loot and runtime objective adapters remain deferred to later
stages.
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


STAGE = "Summer"
MODE = "CREATE"
ENGINE_CUBE = "/Engine/BasicShapes/Cube.Cube"

SUMMER_GROUND_Z = 0.0
ROAD_THICKNESS = 36.0
MAIN_ROAD_WIDTH = 1200.0
SECONDARY_ROAD_WIDTH = 700.0
SERVICE_ROAD_WIDTH = 500.0
PATH_WIDTH = 420.0

STANDARD_WALL_HEIGHT = 420.0
STANDARD_WALL_THICKNESS = 80.0
ARENA_WALL_HEIGHT = 480.0
ARENA_WALL_THICKNESS = 100.0
FLOOR_THICKNESS = 24.0

EDITOR_GREYBOX_LAYERS = (
    "DL_ZS_Greybox",
    "DL_ZS_Summer",
)
EDITOR_GAMEPLAY_LAYERS = (
    "DL_ZS_Greybox",
    "DL_ZS_Gameplay",
    "DL_ZS_Summer",
)

# Frozen production anchors from 07_Production_World_Specification.md.
POI_ANCHORS: dict[str, tuple[float, float, float]] = {
    "GasStation": (31000.0, 64000.0, 0.0),
    "Motel": (53000.0, 56000.0, 100.0),
    "ParkingArena": (63000.0, 34000.0, 0.0),
    "Boardwalk": (48000.0, 77000.0, 100.0),
    "BeachService": (68000.0, 69000.0, 0.0),
    "AmusementPier": (76000.0, 82000.0, 100.0),
    "StormDrainEntrance": (24000.0, 31000.0, -100.0),
}

# The entry starts exactly at the north-east edge of the Hub/shared square.
# Summer and Hub share a 0 cm baseline, so no elevation repair is required here.
ROAD_SEGMENTS: tuple[
    tuple[str, tuple[float, float], tuple[float, float], float], ...
] = (
    ("Main_Entry", (15000.0, 15000.0), (45000.0, 45000.0), MAIN_ROAD_WIDTH),
    ("Gas_Avenue", (45000.0, 45000.0), (31000.0, 64000.0), 900.0),
    ("Motel_Avenue", (45000.0, 45000.0), (53000.0, 56000.0), SECONDARY_ROAD_WIDTH),
    ("Parking_Main", (45000.0, 45000.0), (63000.0, 34000.0), 900.0),
    ("Boardwalk_Access", (53000.0, 56000.0), (48000.0, 77000.0), SECONDARY_ROAD_WIDTH),
    ("Beach_Service", (53000.0, 56000.0), (68000.0, 69000.0), SECONDARY_ROAD_WIDTH),
    ("Pier_Access", (68000.0, 69000.0), (76000.0, 82000.0), SERVICE_ROAD_WIDTH),
    ("Parking_Cross", (63000.0, 34000.0), (68000.0, 69000.0), SECONDARY_ROAD_WIDTH),
    ("StormDrain_Service", (45000.0, 45000.0), (24000.0, 31000.0), SERVICE_ROAD_WIDTH),
)

# Required Summer shortcuts from 02_District_Specifications.md.
SHORTCUT_SEGMENTS: tuple[
    tuple[str, tuple[float, float], tuple[float, float], float], ...
] = (
    # Rooftop/fire-escape route behind the motel block.
    ("MotelFireEscape", (54800.0, 57500.0), (59500.0, 61000.0), PATH_WIDTH),
    # Storm drain prepares the Stage-7 sewer connection.
    ("StormDrain", (30000.0, 36500.0), (24000.0, 31000.0), PATH_WIDTH),
    # Boardwalk maintenance route returns toward the Hub/ring-road side.
    ("BoardwalkMaintenanceGate", (47000.0, 74000.0), (39000.0, 60000.0), PATH_WIDTH),
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
            "Unsaved map packages are open. Save or discard them before Stage 4: "
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
        fail(f"Unsupported Summer generation mode: {MODE}")
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

    # Stage 3 created this always-loaded sentinel specifically so downstream stages
    # can verify the checkpoint even when Spring World Partition cells are unloaded.
    if actor_with_stable_id("Spring.StageSentinel") is None:
        fail("Stage 3 Spring checkpoint is unavailable. Do not generate Summer yet.")

    existing = stage_actors(STAGE)
    if existing:
        fail(
            f"Refusing to duplicate Summer generation: {len(existing)} Stage-4 actors "
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
    add_generation_tags(actor, stage=STAGE, district="Summer", stable_id=stable_id)
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
    collision: bool = True,
    gameplay_marker: bool = False,
    persistent: bool = False,
    editor_only: bool = False,
) -> Any:
    actor = get_actor_subsystem().spawn_actor_from_class(
        unreal.StaticMeshActor,
        unreal.Vector(*center),
        unreal.Rotator(roll=0.0, pitch=0.0, yaw=yaw),
    )
    if actor is None:
        fail(f"Unable to spawn Summer actor: {label}")
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


def spawn_segment(
    mesh: Any,
    *,
    label: str,
    stable_id: str,
    start: tuple[float, float],
    end: tuple[float, float],
    width: float,
    z: float,
    folder: str,
    collision: bool = True,
) -> Any:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.hypot(dx, dy)
    if length <= 0.0:
        fail(f"Zero-length Summer segment requested: {stable_id}")
    yaw = math.degrees(math.atan2(dy, dx))
    return spawn_box(
        mesh,
        label=label,
        stable_id=stable_id,
        center=((start[0] + end[0]) * 0.5, (start[1] + end[1]) * 0.5, z),
        size=(length, width, ROAD_THICKNESS),
        folder=folder,
        yaw=yaw,
        collision=collision,
    )


def create_stage_sentinel(mesh: Any) -> int:
    spawn_box(
        mesh,
        label="ZS_Summer_StageSentinel",
        stable_id="Summer.StageSentinel",
        center=(50000.0, 50000.0, 4500.0),
        size=(80.0, 80.0, 80.0),
        folder="ZombieSeasons/Summer/System",
        collision=False,
        persistent=True,
        editor_only=True,
    )
    return 1


def create_roads(mesh: Any) -> int:
    road_z = SUMMER_GROUND_Z + ROAD_THICKNESS * 0.5 + 2.0
    for road_id, start, end, width in ROAD_SEGMENTS:
        spawn_segment(
            mesh,
            label=f"ZS_Summer_Road_{road_id}",
            stable_id=f"Summer.Road.{road_id}",
            start=start,
            end=end,
            width=width,
            z=road_z,
            folder="ZombieSeasons/Summer/Roads",
        )
    return len(ROAD_SEGMENTS)


def create_shortcuts(mesh: Any) -> int:
    path_z = SUMMER_GROUND_Z + ROAD_THICKNESS * 0.5 + 4.0
    for shortcut_id, start, end, width in SHORTCUT_SEGMENTS:
        spawn_segment(
            mesh,
            label=f"ZS_Summer_Shortcut_{shortcut_id}",
            stable_id=f"Summer.Shortcut.{shortcut_id}",
            start=start,
            end=end,
            width=width,
            z=path_z,
            folder="ZombieSeasons/Summer/Shortcuts",
        )
    return len(SHORTCUT_SEGMENTS)


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
            label=f"ZS_Summer_{prefix}_{side}_{suffix}",
            stable_id=f"Summer.{prefix}.{side}.{suffix}",
            center=actor_center,
            size=size,
            folder=folder,
        )
    return 2


def create_gas_station(mesh: Any) -> int:
    # Open forecourt with shop mass, canopy and pump islands. Final fuel objective
    # adapter is intentionally deferred to Stage 9.
    specs = (
        ("Shop", (31000.0, 65200.0, 350.0), (3200.0, 1900.0, 700.0)),
        ("Canopy", (31000.0, 62500.0, 430.0), (4200.0, 2600.0, 80.0)),
        ("CanopyPillar_A", (29600.0, 62500.0, 220.0), (140.0, 140.0, 440.0)),
        ("CanopyPillar_B", (32400.0, 62500.0, 220.0), (140.0, 140.0, 440.0)),
        ("PumpIsland_A", (30200.0, 62500.0, 90.0), (500.0, 1300.0, 180.0)),
        ("PumpIsland_B", (31800.0, 62500.0, 90.0), (500.0, 1300.0, 180.0)),
    )
    for suffix, center, size in specs:
        spawn_box(
            mesh,
            label=f"ZS_Summer_GasStation_{suffix}",
            stable_id=f"Summer.GasStation.{suffix}",
            center=center,
            size=size,
            folder="ZombieSeasons/Summer/POI/GasStation",
        )
    return len(specs)


def create_motel(mesh: Any) -> int:
    # U-shaped motel footprint leaves a readable vehicle court and supports a
    # player-only upper/fire-escape shortcut in later traversal setup.
    specs = (
        ("Wing_West", (50000.0, 56000.0, 430.0), (1800.0, 6200.0, 860.0)),
        ("Wing_East", (56000.0, 56000.0, 430.0), (1800.0, 6200.0, 860.0)),
        ("Wing_North", (53000.0, 58600.0, 430.0), (4200.0, 1000.0, 860.0)),
        ("Office", (53000.0, 53500.0, 310.0), (2200.0, 1200.0, 620.0)),
        ("UpperWalk_W", (51200.0, 56000.0, 520.0), (500.0, 5200.0, 50.0)),
        ("UpperWalk_E", (54800.0, 56000.0, 520.0), (500.0, 5200.0, 50.0)),
        ("RoofBridge", (53000.0, 58200.0, 560.0), (3600.0, 500.0, 50.0)),
    )
    for suffix, center, size in specs:
        spawn_box(
            mesh,
            label=f"ZS_Summer_Motel_{suffix}",
            stable_id=f"Summer.Motel.{suffix}",
            center=center,
            size=size,
            folder="ZombieSeasons/Summer/POI/Motel",
        )
    return len(specs)


def create_parking_arena(mesh: Any) -> int:
    # 80 x 75 m arena inside the frozen Summer parking target of 70–90 m.
    center = (63000.0, 34000.0)
    width = 8000.0
    depth = 7500.0
    half_w = width * 0.5
    half_d = depth * 0.5
    count = 0

    spawn_box(
        mesh,
        label="ZS_Summer_ParkingArena_Floor",
        stable_id="Summer.ParkingArena.Floor",
        center=(center[0], center[1], SUMMER_GROUND_Z + FLOOR_THICKNESS * 0.5),
        size=(width, depth, FLOOR_THICKNESS),
        folder="ZombieSeasons/Summer/POI/ParkingArena",
    )
    count += 1

    # Three exits: west, north and east. South remains a pressure wall.
    count += wall_pair_with_gap(
        mesh,
        prefix="ParkingArena.Wall",
        side="West",
        center=(center[0] - half_w, center[1]),
        axis="Y",
        total_length=depth,
        gap_width=1400.0,
        wall_height=ARENA_WALL_HEIGHT,
        wall_thickness=ARENA_WALL_THICKNESS,
        ground_z=SUMMER_GROUND_Z,
        folder="ZombieSeasons/Summer/POI/ParkingArena",
    )
    count += wall_pair_with_gap(
        mesh,
        prefix="ParkingArena.Wall",
        side="North",
        center=(center[0], center[1] + half_d),
        axis="X",
        total_length=width,
        gap_width=1400.0,
        wall_height=ARENA_WALL_HEIGHT,
        wall_thickness=ARENA_WALL_THICKNESS,
        ground_z=SUMMER_GROUND_Z,
        folder="ZombieSeasons/Summer/POI/ParkingArena",
    )
    count += wall_pair_with_gap(
        mesh,
        prefix="ParkingArena.Wall",
        side="East",
        center=(center[0] + half_w, center[1]),
        axis="Y",
        total_length=depth,
        gap_width=1400.0,
        wall_height=ARENA_WALL_HEIGHT,
        wall_thickness=ARENA_WALL_THICKNESS,
        ground_z=SUMMER_GROUND_Z,
        folder="ZombieSeasons/Summer/POI/ParkingArena",
    )
    spawn_box(
        mesh,
        label="ZS_Summer_ParkingArena_Wall_South",
        stable_id="Summer.ParkingArena.Wall.South",
        center=(center[0], center[1] - half_d, SUMMER_GROUND_Z + ARENA_WALL_HEIGHT * 0.5),
        size=(width, ARENA_WALL_THICKNESS, ARENA_WALL_HEIGHT),
        folder="ZombieSeasons/Summer/POI/ParkingArena",
    )
    count += 1

    # Low vehicle-island placeholders create flanking lanes without final vehicles.
    for suffix, x, y in (
        ("A", 61200.0, 33000.0),
        ("B", 63000.0, 35000.0),
        ("C", 64800.0, 33000.0),
    ):
        spawn_box(
            mesh,
            label=f"ZS_Summer_ParkingArena_Cover_{suffix}",
            stable_id=f"Summer.ParkingArena.Cover.{suffix}",
            center=(x, y, 90.0),
            size=(900.0, 2200.0, 180.0),
            folder="ZombieSeasons/Summer/POI/ParkingArena/Cover",
        )
        count += 1
    return count


def create_boardwalk(mesh: Any) -> int:
    # Long pressure route with lateral escape branches and retreat capability.
    count = 0
    segments = (
        ("Main_A", (44000.0, 74500.0), (52000.0, 74500.0), 1800.0),
        ("Main_B", (52000.0, 74500.0), (52000.0, 79000.0), 1800.0),
        ("Lateral_W", (45500.0, 74500.0), (45500.0, 71500.0), 900.0),
        ("Lateral_E", (52000.0, 76500.0), (55500.0, 76500.0), 900.0),
    )
    for suffix, start, end, width in segments:
        spawn_segment(
            mesh,
            label=f"ZS_Summer_Boardwalk_{suffix}",
            stable_id=f"Summer.Boardwalk.{suffix}",
            start=start,
            end=end,
            width=width,
            z=SUMMER_GROUND_Z + 120.0,
            folder="ZombieSeasons/Summer/POI/Boardwalk",
        )
        count += 1

    # Landmark/service masses along the boardwalk edge.
    for suffix, center, size in (
        ("Kiosk_A", (46500.0, 76000.0, 260.0), (1200.0, 900.0, 520.0)),
        ("Kiosk_B", (50000.0, 77500.0, 260.0), (1200.0, 900.0, 520.0)),
    ):
        spawn_box(
            mesh,
            label=f"ZS_Summer_Boardwalk_{suffix}",
            stable_id=f"Summer.Boardwalk.{suffix}",
            center=center,
            size=size,
            folder="ZombieSeasons/Summer/POI/Boardwalk",
        )
        count += 1
    return count


def create_beach_service(mesh: Any) -> int:
    specs = (
        ("A", (65000.0, 69000.0, 300.0), (2200.0, 1800.0, 600.0)),
        ("B", (68000.0, 70500.0, 260.0), (2000.0, 1600.0, 520.0)),
        ("C", (71000.0, 68500.0, 300.0), (2400.0, 1800.0, 600.0)),
    )
    for suffix, center, size in specs:
        spawn_box(
            mesh,
            label=f"ZS_Summer_BeachService_{suffix}",
            stable_id=f"Summer.BeachService.{suffix}",
            center=center,
            size=size,
            folder="ZombieSeasons/Summer/POI/BeachService",
        )
    return len(specs)


def create_amusement_pier(mesh: Any) -> int:
    count = 0
    # Pier deck points toward the north-east edge but remains within world bounds.
    spawn_segment(
        mesh,
        label="ZS_Summer_AmusementPier_Deck",
        stable_id="Summer.AmusementPier.Deck",
        start=(72000.0, 78000.0),
        end=(80500.0, 85000.0),
        width=1600.0,
        z=SUMMER_GROUND_Z + 150.0,
        folder="ZombieSeasons/Summer/POI/AmusementPier",
    )
    count += 1
    for suffix, center, size in (
        ("Service_A", (75500.0, 81200.0, 330.0), (1600.0, 1200.0, 660.0)),
        ("Service_B", (78500.0, 83500.0, 280.0), (1400.0, 1100.0, 560.0)),
        ("RideLandmark", (77000.0, 82000.0, 1500.0), (300.0, 300.0, 3000.0)),
    ):
        spawn_box(
            mesh,
            label=f"ZS_Summer_AmusementPier_{suffix}",
            stable_id=f"Summer.AmusementPier.{suffix}",
            center=center,
            size=size,
            folder="ZombieSeasons/Summer/POI/AmusementPier",
        )
        count += 1
    return count


def create_storm_drain(mesh: Any) -> int:
    spawn_box(
        mesh,
        label="ZS_Summer_StormDrainEntrance",
        stable_id="Summer.StormDrainEntrance.Structure",
        center=(24000.0, 31000.0, 180.0),
        size=(1800.0, 1200.0, 360.0),
        folder="ZombieSeasons/Summer/POI/StormDrain",
    )
    spawn_box(
        mesh,
        label="ZS_Summer_StormDrainPortal",
        stable_id="Summer.StormDrainEntrance.Portal",
        center=(24000.0, 30400.0, 110.0),
        size=(700.0, 90.0, 220.0),
        folder="ZombieSeasons/Summer/POI/StormDrain",
        collision=False,
        gameplay_marker=True,
        editor_only=True,
    )
    return 2


def create_poi_anchor_markers(mesh: Any) -> int:
    count = 0
    for name in (
        "GasStation",
        "Motel",
        "ParkingArena",
        "Boardwalk",
        "BeachService",
        "AmusementPier",
    ):
        x, y, z = POI_ANCHORS[name]
        spawn_box(
            mesh,
            label=f"ZS_Summer_POI_{name}",
            stable_id=f"Summer.POI.{name}",
            center=(x, y, max(SUMMER_GROUND_Z, z) + 900.0),
            size=(120.0, 120.0, 1800.0),
            folder="ZombieSeasons/Summer/POI/Anchors",
            collision=False,
            gameplay_marker=True,
            editor_only=True,
        )
        count += 1
    return count


def save_level() -> None:
    if not get_level_subsystem().save_current_level():
        fail("Summer actors were generated but the greybox level could not be saved.")


def position_viewport() -> None:
    try:
        subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        if subsystem is not None:
            subsystem.set_level_viewport_camera_info(
                unreal.Vector(50000.0, 18000.0, 42000.0),
                unreal.Rotator(roll=0.0, pitch=-42.0, yaw=90.0),
            )
    except Exception as error:
        warn(f"Unable to position viewport for Summer review: {error}")


def run() -> None:
    preflight()
    log("Stage 4 preflight passed. Creating deterministic Summer greybox.")

    mesh = unreal.load_asset(ENGINE_CUBE)
    if mesh is None:
        fail(f"Engine cube disappeared after preflight: {ENGINE_CUBE}")

    sentinel_count = create_stage_sentinel(mesh)
    road_count = create_roads(mesh)
    shortcut_count = create_shortcuts(mesh)
    gas_count = create_gas_station(mesh)
    motel_count = create_motel(mesh)
    parking_count = create_parking_arena(mesh)
    boardwalk_count = create_boardwalk(mesh)
    beach_service_count = create_beach_service(mesh)
    pier_count = create_amusement_pier(mesh)
    drain_count = create_storm_drain(mesh)
    poi_marker_count = create_poi_anchor_markers(mesh)

    expected = (
        sentinel_count
        + road_count
        + shortcut_count
        + gas_count
        + motel_count
        + parking_count
        + boardwalk_count
        + beach_service_count
        + pier_count
        + drain_count
        + poi_marker_count
    )
    generated = stage_actors(STAGE)
    if len(generated) != expected:
        fail(
            "Summer generation count mismatch before save: "
            f"expected {expected}, found {len(generated)} loaded tagged actors."
        )

    save_level()
    position_viewport()

    report = write_json_report(
        "summer_generation.json",
        {
            "status": "PASS",
            "stage": STAGE,
            "mode": MODE,
            "map": GREYBOX_MAP,
            "generated_actor_count": len(generated),
            "road_surface_count": road_count,
            "shortcut_route_count": shortcut_count,
            "gas_station_actor_count": gas_count,
            "motel_actor_count": motel_count,
            "parking_arena_actor_count": parking_count,
            "boardwalk_actor_count": boardwalk_count,
            "beach_service_actor_count": beach_service_count,
            "amusement_pier_actor_count": pier_count,
            "storm_drain_actor_count": drain_count,
            "poi_anchor_marker_count": poi_marker_count,
            "required_shortcuts": [item[0] for item in SHORTCUT_SEGMENTS],
            "parking_target_footprint_m": [80, 75],
            "parking_exit_topology": "3 mandatory exits",
            "boardwalk_topology": "long pressure route + 2 lateral exits + retreat",
            "objective_adapters_created": False,
            "zombie_spawn_markers_created": False,
            "loot_markers_created": False,
            "final_art_assets_loaded": False,
            "historical_maps_modified": False,
        },
    )

    summary = (
        "Summer greybox generation PASSED.\n\n"
        f"Map: {GREYBOX_MAP}\n"
        f"Generated Summer actors: {len(generated)}\n"
        f"Playable roads: {road_count}\n"
        f"Required shortcuts: {shortcut_count}\n"
        f"Gas-station actors: {gas_count}\n"
        f"Motel actors: {motel_count}\n"
        f"Parking-arena actors: {parking_count}\n"
        f"Boardwalk actors: {boardwalk_count}\n"
        f"Beach-service actors: {beach_service_count}\n"
        f"Amusement-pier actors: {pier_count}\n"
        f"POI anchor markers: {poi_marker_count}\n\n"
        "Zombie spawns, loot and runtime objective adapters remain deferred to Stage 9.\n"
        "No final Fab/City Sample art was loaded.\n"
        f"Report:\n{report}"
    )
    log(summary.replace("\n", " "))
    show_editor_message("ZombieSeasons World Generation — Stage 4", summary)


if __name__ == "__main__":
    run()
