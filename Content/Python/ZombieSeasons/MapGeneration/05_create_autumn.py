"""Create the deterministic ZombieSeasons Autumn district greybox.

Run from Unreal Editor only after Stage 4 Summer has passed and been committed:

py "C:/Users/malik/Documents/Unreal Projects/ZombieSeasons/Content/Python/ZombieSeasons/MapGeneration/05_create_autumn.py"

Stage 5 creates topology-critical Autumn geometry only: roads, dense civic POI
footprints, two combat spaces, vertical traversal, alleys, and the three required
shortcut routes. Final City Sample/Fab art, zombie spawns, loot and runtime objective
adapters remain deferred to later stages.
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


STAGE = "Autumn"
MODE = "CREATE"
ENGINE_CUBE = "/Engine/BasicShapes/Cube.Cube"

AUTUMN_GROUND_Z = 300.0
ROAD_THICKNESS = 36.0
ROAD_CENTER_OFFSET = ROAD_THICKNESS * 0.5 + 2.0
MAIN_ROAD_WIDTH = 1200.0
SECONDARY_ROAD_WIDTH = 700.0
SERVICE_ROAD_WIDTH = 500.0
ALLEY_WIDTH = 400.0
PATH_WIDTH = 420.0

STANDARD_WALL_HEIGHT = 500.0
STANDARD_WALL_THICKNESS = 90.0
ARENA_WALL_HEIGHT = 520.0
ARENA_WALL_THICKNESS = 100.0
FLOOR_THICKNESS = 24.0

EDITOR_GREYBOX_LAYERS = (
    "DL_ZS_Greybox",
    "DL_ZS_Autumn",
)
EDITOR_GAMEPLAY_LAYERS = (
    "DL_ZS_Greybox",
    "DL_ZS_Gameplay",
    "DL_ZS_Autumn",
)

# Frozen production anchors from 07_Production_World_Specification.md.
POI_ANCHORS: dict[str, tuple[float, float, float]] = {
    "ChurchSquare": (-35000.0, -35000.0, 300.0),
    "MarketHall": (-54000.0, -43000.0, 300.0),
    "ApartmentBlock": (-69000.0, -61000.0, 500.0),
    "TownHall": (-41000.0, -66000.0, 400.0),
    "PoliceStation": (-66000.0, -29000.0, 300.0),
    "Clinic": (-23000.0, -48000.0, 200.0),
    "PoliceGarageArena": (-62000.0, -24000.0, 300.0),
}

# Road segments carry explicit Z endpoints. This prevents a repeat of the Spring
# hard-step bug: Autumn intentionally sits +300 cm above the Hub, so Main_Entry is
# generated as a shallow grade from the Hub/shared boundary to the civic center.
# Tuple: id, start(x,y,z), end(x,y,z), width.
ROAD_SEGMENTS: tuple[
    tuple[str, tuple[float, float, float], tuple[float, float, float], float], ...
] = (
    (
        "Main_Entry",
        (-15000.0, -15000.0, 20.0),
        (-35000.0, -35000.0, AUTUMN_GROUND_Z + ROAD_CENTER_OFFSET),
        MAIN_ROAD_WIDTH,
    ),
    (
        "Church_Market",
        (-35000.0, -35000.0, AUTUMN_GROUND_Z + ROAD_CENTER_OFFSET),
        (-54000.0, -43000.0, AUTUMN_GROUND_Z + ROAD_CENTER_OFFSET),
        900.0,
    ),
    (
        "Church_Clinic",
        (-35000.0, -35000.0, AUTUMN_GROUND_Z + ROAD_CENTER_OFFSET),
        (-23000.0, -48000.0, AUTUMN_GROUND_Z + ROAD_CENTER_OFFSET),
        SECONDARY_ROAD_WIDTH,
    ),
    (
        "Market_Police",
        (-54000.0, -43000.0, AUTUMN_GROUND_Z + ROAD_CENTER_OFFSET),
        (-66000.0, -29000.0, AUTUMN_GROUND_Z + ROAD_CENTER_OFFSET),
        SECONDARY_ROAD_WIDTH,
    ),
    (
        "Market_TownHall",
        (-54000.0, -43000.0, AUTUMN_GROUND_Z + ROAD_CENTER_OFFSET),
        (-41000.0, -66000.0, AUTUMN_GROUND_Z + ROAD_CENTER_OFFSET),
        SECONDARY_ROAD_WIDTH,
    ),
    (
        "Market_Apartment",
        (-54000.0, -43000.0, AUTUMN_GROUND_Z + ROAD_CENTER_OFFSET),
        (-69000.0, -61000.0, AUTUMN_GROUND_Z + ROAD_CENTER_OFFSET),
        SECONDARY_ROAD_WIDTH,
    ),
    (
        "TownHall_Apartment",
        (-41000.0, -66000.0, AUTUMN_GROUND_Z + ROAD_CENTER_OFFSET),
        (-69000.0, -61000.0, AUTUMN_GROUND_Z + ROAD_CENTER_OFFSET),
        SECONDARY_ROAD_WIDTH,
    ),
    (
        "Police_Garage",
        (-66000.0, -29000.0, AUTUMN_GROUND_Z + ROAD_CENTER_OFFSET),
        (-62000.0, -24000.0, AUTUMN_GROUND_Z + ROAD_CENTER_OFFSET),
        SERVICE_ROAD_WIDTH,
    ),
    (
        "Western_Service_Stub",
        (-66000.0, -29000.0, AUTUMN_GROUND_Z + ROAD_CENTER_OFFSET),
        (-79000.0, -17000.0, AUTUMN_GROUND_Z + ROAD_CENTER_OFFSET),
        SERVICE_ROAD_WIDTH,
    ),
    (
        "Southern_Cross_Stub",
        (-41000.0, -66000.0, AUTUMN_GROUND_Z + ROAD_CENTER_OFFSET),
        (-16000.0, -70000.0, AUTUMN_GROUND_Z + ROAD_CENTER_OFFSET),
        SECONDARY_ROAD_WIDTH,
    ),
)

# Required Autumn shortcuts from 02_District_Specifications.md.
# The apartment bridge is intentionally elevated and already represents the physical
# rooftop traversal surface; the actual unlock/gate behavior remains Stage 9 work.
SHORTCUT_SEGMENTS: tuple[
    tuple[str, tuple[float, float, float], tuple[float, float, float], float], ...
] = (
    (
        "MarketLoadingCorridor",
        (-56500.0, -45500.0, AUTUMN_GROUND_Z + ROAD_CENTER_OFFSET + 4.0),
        (-49500.0, -50500.0, AUTUMN_GROUND_Z + ROAD_CENTER_OFFSET + 4.0),
        PATH_WIDTH,
    ),
    (
        "ApartmentRooftopBridge",
        (-67500.0, -59500.0, 1750.0),
        (-61500.0, -57000.0, 1750.0),
        420.0,
    ),
    (
        "PoliceGarageGate",
        (-62000.0, -24000.0, AUTUMN_GROUND_Z + ROAD_CENTER_OFFSET + 4.0),
        (-47000.0, -19000.0, AUTUMN_GROUND_Z + ROAD_CENTER_OFFSET + 4.0),
        SERVICE_ROAD_WIDTH,
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
            "Unsaved map packages are open. Save or discard them before Stage 5: "
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
        fail(f"Unsupported Autumn generation mode: {MODE}")
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

    if actor_with_stable_id("Summer.StageSentinel") is None:
        fail("Stage 4 Summer checkpoint is unavailable. Do not generate Autumn yet.")

    existing = stage_actors(STAGE)
    if existing:
        fail(
            f"Refusing to duplicate Autumn generation: {len(existing)} Stage-5 actors "
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
    add_generation_tags(actor, stage=STAGE, district="Autumn", stable_id=stable_id)
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
        fail(f"Unable to spawn Autumn actor: {label}")
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
        fail(f"Zero-length Autumn segment requested: {stable_id}")

    actor = get_actor_subsystem().spawn_actor_from_class(
        unreal.StaticMeshActor,
        unreal.Vector(
            (start[0] + end[0]) * 0.5,
            (start[1] + end[1]) * 0.5,
            (start[2] + end[2]) * 0.5,
        ),
        direction_rotator(dx, dy, dz),
    )
    if actor is None:
        fail(f"Unable to spawn Autumn segment: {label}")

    component = set_mesh(actor, mesh)
    actor.set_actor_scale3d(
        unreal.Vector(length / 100.0, width / 100.0, thickness / 100.0)
    )
    set_collision(component, collision)
    set_actor_identity(
        actor,
        label=label,
        stable_id=stable_id,
        folder=folder,
    )
    return actor


def create_stage_sentinel(mesh: Any) -> int:
    spawn_box(
        mesh,
        label="ZS_Autumn_StageSentinel",
        stable_id="Autumn.StageSentinel",
        center=(-50000.0, -50000.0, 4800.0),
        size=(80.0, 80.0, 80.0),
        folder="ZombieSeasons/Autumn/System",
        collision=False,
        persistent=True,
        editor_only=True,
    )
    return 1


def create_roads(mesh: Any) -> int:
    for road_id, start, end, width in ROAD_SEGMENTS:
        spawn_segment_3d(
            mesh,
            label=f"ZS_Autumn_Road_{road_id}",
            stable_id=f"Autumn.Road.{road_id}",
            start=start,
            end=end,
            width=width,
            thickness=ROAD_THICKNESS,
            folder="ZombieSeasons/Autumn/Roads",
        )
    return len(ROAD_SEGMENTS)


def create_shortcuts(mesh: Any) -> int:
    for shortcut_id, start, end, width in SHORTCUT_SEGMENTS:
        spawn_segment_3d(
            mesh,
            label=f"ZS_Autumn_Shortcut_{shortcut_id}",
            stable_id=f"Autumn.Shortcut.{shortcut_id}",
            start=start,
            end=end,
            width=width,
            thickness=ROAD_THICKNESS,
            folder="ZombieSeasons/Autumn/Shortcuts",
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
            label=f"ZS_Autumn_{prefix}_{side}_{suffix}",
            stable_id=f"Autumn.{prefix}.{side}.{suffix}",
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
    east_gap: float | None,
    wall_height: float,
    folder: str,
) -> int:
    count = 0
    half_w = width * 0.5
    half_d = depth * 0.5

    spawn_box(
        mesh,
        label=f"ZS_Autumn_{prefix}_Floor",
        stable_id=f"Autumn.{prefix}.Floor",
        center=(center[0], center[1], ground_z + FLOOR_THICKNESS * 0.5),
        size=(width, depth, FLOOR_THICKNESS),
        folder=folder,
    )
    count += 1

    spawn_box(
        mesh,
        label=f"ZS_Autumn_{prefix}_Wall_North",
        stable_id=f"Autumn.{prefix}.Wall.North",
        center=(center[0], center[1] + half_d, ground_z + wall_height * 0.5),
        size=(width, STANDARD_WALL_THICKNESS, wall_height),
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

    spawn_box(
        mesh,
        label=f"ZS_Autumn_{prefix}_Wall_West",
        stable_id=f"Autumn.{prefix}.Wall.West",
        center=(center[0] - half_w, center[1], ground_z + wall_height * 0.5),
        size=(STANDARD_WALL_THICKNESS, depth, wall_height),
        folder=folder,
    )
    count += 1

    if east_gap is None:
        spawn_box(
            mesh,
            label=f"ZS_Autumn_{prefix}_Wall_East",
            stable_id=f"Autumn.{prefix}.Wall.East",
            center=(center[0] + half_w, center[1], ground_z + wall_height * 0.5),
            size=(STANDARD_WALL_THICKNESS, depth, wall_height),
            folder=folder,
        )
        count += 1
    else:
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


def create_church_square(mesh: Any) -> int:
    # 62 x 62 m horde arena, inside the frozen Autumn 55–70 m target.
    center = (-35000.0, -35000.0)
    width = 6200.0
    depth = 6200.0
    half_w = width * 0.5
    half_d = depth * 0.5
    count = 0

    spawn_box(
        mesh,
        label="ZS_Autumn_ChurchSquare_Floor",
        stable_id="Autumn.ChurchSquare.Floor",
        center=(center[0], center[1], AUTUMN_GROUND_Z + FLOOR_THICKNESS * 0.5),
        size=(width, depth, FLOOR_THICKNESS),
        folder="ZombieSeasons/Autumn/POI/ChurchSquare",
    )
    count += 1

    # Three exits: North, East, South. West remains a pressure wall.
    for side, axis, wall_center, total, gap in (
        ("North", "X", (center[0], center[1] + half_d), width, 1100.0),
        ("East", "Y", (center[0] + half_w, center[1]), depth, 1100.0),
        ("South", "X", (center[0], center[1] - half_d), width, 1100.0),
    ):
        count += wall_pair_with_gap(
            mesh,
            prefix="ChurchSquare.Wall",
            side=side,
            center=wall_center,
            axis=axis,
            total_length=total,
            gap_width=gap,
            wall_height=ARENA_WALL_HEIGHT,
            wall_thickness=ARENA_WALL_THICKNESS,
            ground_z=AUTUMN_GROUND_Z,
            folder="ZombieSeasons/Autumn/POI/ChurchSquare",
        )

    spawn_box(
        mesh,
        label="ZS_Autumn_ChurchSquare_Wall_West",
        stable_id="Autumn.ChurchSquare.Wall.West",
        center=(center[0] - half_w, center[1], AUTUMN_GROUND_Z + ARENA_WALL_HEIGHT * 0.5),
        size=(ARENA_WALL_THICKNESS, depth, ARENA_WALL_HEIGHT),
        folder="ZombieSeasons/Autumn/POI/ChurchSquare",
    )
    count += 1
    return count


def create_market_hall(mesh: Any) -> int:
    return create_open_structure(
        mesh,
        prefix="MarketHall",
        center=(-54000.0, -43000.0),
        width=7000.0,
        depth=4500.0,
        ground_z=AUTUMN_GROUND_Z,
        south_gap=1200.0,
        east_gap=1000.0,
        wall_height=520.0,
        folder="ZombieSeasons/Autumn/POI/MarketHall",
    )


def create_apartment_block(mesh: Any) -> int:
    count = create_open_structure(
        mesh,
        prefix="Apartment",
        center=(-69000.0, -61000.0),
        width=5800.0,
        depth=4800.0,
        ground_z=AUTUMN_GROUND_Z,
        south_gap=900.0,
        east_gap=900.0,
        wall_height=900.0,
        folder="ZombieSeasons/Autumn/POI/Apartment",
    )

    # Readable vertical route: two interior cores and a roof slab. The rooftop bridge
    # itself is one of the required shortcut segments above.
    for suffix, x in (("CoreA", -70400.0), ("CoreB", -67600.0)):
        spawn_box(
            mesh,
            label=f"ZS_Autumn_Apartment_{suffix}",
            stable_id=f"Autumn.Apartment.{suffix}",
            center=(x, -61000.0, AUTUMN_GROUND_Z + 450.0),
            size=(700.0, 1600.0, 900.0),
            folder="ZombieSeasons/Autumn/POI/Apartment/Interior",
        )
        count += 1

    spawn_box(
        mesh,
        label="ZS_Autumn_Apartment_RoofRoute",
        stable_id="Autumn.Apartment.RoofRoute",
        center=(-69000.0, -61000.0, 1500.0),
        size=(5200.0, 1200.0, 40.0),
        folder="ZombieSeasons/Autumn/POI/Apartment/Rooftop",
    )
    count += 1
    return count


def create_town_hall(mesh: Any) -> int:
    return create_open_structure(
        mesh,
        prefix="TownHall",
        center=(-41000.0, -66000.0),
        width=5600.0,
        depth=4200.0,
        ground_z=AUTUMN_GROUND_Z,
        south_gap=1100.0,
        east_gap=900.0,
        wall_height=620.0,
        folder="ZombieSeasons/Autumn/POI/TownHall",
    )


def create_police_station(mesh: Any) -> int:
    count = create_open_structure(
        mesh,
        prefix="PoliceStation",
        center=(-66000.0, -29000.0),
        width=5800.0,
        depth=4400.0,
        ground_z=AUTUMN_GROUND_Z,
        south_gap=1000.0,
        east_gap=900.0,
        wall_height=620.0,
        folder="ZombieSeasons/Autumn/POI/PoliceStation",
    )

    # Garage defense space: 52 x 38 m mixed interior/garage arena with two exits.
    center = (-62000.0, -24000.0)
    width = 5200.0
    depth = 3800.0
    half_w = width * 0.5
    half_d = depth * 0.5

    spawn_box(
        mesh,
        label="ZS_Autumn_PoliceGarage_Floor",
        stable_id="Autumn.PoliceGarage.Floor",
        center=(center[0], center[1], AUTUMN_GROUND_Z + FLOOR_THICKNESS * 0.5),
        size=(width, depth, FLOOR_THICKNESS),
        folder="ZombieSeasons/Autumn/POI/PoliceStation/Garage",
    )
    count += 1

    # North and South exits remain open for controlled reinforcement flow.
    for side, wall_center in (
        ("North", (center[0], center[1] + half_d)),
        ("South", (center[0], center[1] - half_d)),
    ):
        count += wall_pair_with_gap(
            mesh,
            prefix="PoliceGarage.Wall",
            side=side,
            center=wall_center,
            axis="X",
            total_length=width,
            gap_width=1100.0,
            wall_height=ARENA_WALL_HEIGHT,
            wall_thickness=ARENA_WALL_THICKNESS,
            ground_z=AUTUMN_GROUND_Z,
            folder="ZombieSeasons/Autumn/POI/PoliceStation/Garage",
        )

    for side, x in (("West", center[0] - half_w), ("East", center[0] + half_w)):
        spawn_box(
            mesh,
            label=f"ZS_Autumn_PoliceGarage_Wall_{side}",
            stable_id=f"Autumn.PoliceGarage.Wall.{side}",
            center=(x, center[1], AUTUMN_GROUND_Z + ARENA_WALL_HEIGHT * 0.5),
            size=(ARENA_WALL_THICKNESS, depth, ARENA_WALL_HEIGHT),
            folder="ZombieSeasons/Autumn/POI/PoliceStation/Garage",
        )
        count += 1
    return count


def create_clinic(mesh: Any) -> int:
    return create_open_structure(
        mesh,
        prefix="Clinic",
        center=(-23000.0, -48000.0),
        width=4500.0,
        depth=3200.0,
        ground_z=AUTUMN_GROUND_Z,
        south_gap=900.0,
        east_gap=800.0,
        wall_height=480.0,
        folder="ZombieSeasons/Autumn/POI/Clinic",
    )


def create_dense_urban_masses(mesh: Any) -> int:
    # Six solid civic blocks create alley pressure and short sightlines around the
    # route graph. They remain replaceable art-pass masses rather than final buildings.
    masses = (
        ("BlockA", (-47000.0, -31500.0), (3600.0, 2500.0, 950.0)),
        ("BlockB", (-50500.0, -55500.0), (3200.0, 2400.0, 1100.0)),
        ("BlockC", (-58500.0, -52500.0), (3400.0, 2200.0, 900.0)),
        ("BlockD", (-74500.0, -44000.0), (3000.0, 2500.0, 1200.0)),
        ("BlockE", (-30000.0, -59000.0), (3300.0, 2300.0, 850.0)),
        ("BlockF", (-74000.0, -30000.0), (2800.0, 2100.0, 1000.0)),
    )
    for suffix, center, size in masses:
        spawn_box(
            mesh,
            label=f"ZS_Autumn_UrbanMass_{suffix}",
            stable_id=f"Autumn.UrbanMass.{suffix}",
            center=(center[0], center[1], AUTUMN_GROUND_Z + size[2] * 0.5),
            size=size,
            folder="ZombieSeasons/Autumn/UrbanMasses",
        )
    return len(masses)


def create_poi_anchor_markers(mesh: Any) -> int:
    count = 0
    for name, (x, y, z) in POI_ANCHORS.items():
        spawn_box(
            mesh,
            label=f"ZS_Autumn_POI_{name}",
            stable_id=f"Autumn.POI.{name}",
            center=(x, y, max(AUTUMN_GROUND_Z, z) + 1000.0),
            size=(120.0, 120.0, 2000.0),
            folder="ZombieSeasons/Autumn/POI/Anchors",
            collision=False,
            gameplay_marker=True,
            editor_only=True,
        )
        count += 1
    return count


def save_level() -> None:
    if not get_level_subsystem().save_current_level():
        fail("Autumn actors were generated but the greybox level could not be saved.")


def position_viewport() -> None:
    try:
        subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        if subsystem is not None:
            subsystem.set_level_viewport_camera_info(
                unreal.Vector(-52000.0, -12000.0, 46000.0),
                unreal.Rotator(roll=0.0, pitch=-42.0, yaw=-90.0),
            )
    except Exception as error:
        warn(f"Unable to position viewport for Autumn review: {error}")


def run() -> None:
    preflight()
    log("Stage 5 preflight passed. Creating deterministic Autumn greybox.")

    mesh = unreal.load_asset(ENGINE_CUBE)
    if mesh is None:
        fail(f"Engine cube disappeared after preflight: {ENGINE_CUBE}")

    sentinel_count = create_stage_sentinel(mesh)
    road_count = create_roads(mesh)
    shortcut_count = create_shortcuts(mesh)
    church_count = create_church_square(mesh)
    market_count = create_market_hall(mesh)
    apartment_count = create_apartment_block(mesh)
    town_hall_count = create_town_hall(mesh)
    police_count = create_police_station(mesh)
    clinic_count = create_clinic(mesh)
    urban_mass_count = create_dense_urban_masses(mesh)
    poi_marker_count = create_poi_anchor_markers(mesh)

    expected = (
        sentinel_count
        + road_count
        + shortcut_count
        + church_count
        + market_count
        + apartment_count
        + town_hall_count
        + police_count
        + clinic_count
        + urban_mass_count
        + poi_marker_count
    )
    generated = stage_actors(STAGE)
    if len(generated) != expected:
        fail(
            "Autumn generation count mismatch before save: "
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
        "autumn_generation.json",
        {
            "status": "PASS",
            "stage": STAGE,
            "mode": MODE,
            "map": GREYBOX_MAP,
            "generated_actor_count": len(generated),
            "road_surface_count": road_count,
            "shortcut_route_count": shortcut_count,
            "church_square_actor_count": church_count,
            "market_hall_actor_count": market_count,
            "apartment_actor_count": apartment_count,
            "town_hall_actor_count": town_hall_count,
            "police_station_and_garage_actor_count": police_count,
            "clinic_actor_count": clinic_count,
            "urban_mass_count": urban_mass_count,
            "poi_anchor_marker_count": poi_marker_count,
            "required_shortcuts": [item[0] for item in SHORTCUT_SEGMENTS],
            "church_square_target_footprint_m": [62, 62],
            "church_square_exit_count": 3,
            "police_garage_exit_count": 2,
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
        "Autumn greybox generation PASSED.\n\n"
        f"Map: {GREYBOX_MAP}\n"
        f"Generated Autumn actors: {len(generated)}\n"
        f"Playable roads: {road_count}\n"
        f"Required shortcuts: {shortcut_count}\n"
        f"Church-square actors: {church_count}\n"
        f"Market-hall actors: {market_count}\n"
        f"Apartment actors: {apartment_count}\n"
        f"Town-hall actors: {town_hall_count}\n"
        f"Police/garage actors: {police_count}\n"
        f"Clinic actors: {clinic_count}\n"
        f"Urban masses: {urban_mass_count}\n"
        f"POI anchor markers: {poi_marker_count}\n"
        f"Hub -> Autumn entry grade: {entry_grade_percent:.3f}%\n\n"
        "Zombie spawns, loot and runtime objective adapters remain deferred to Stage 9.\n"
        "No final Fab/City Sample art was loaded.\n"
        f"Report:\n{report}"
    )
    log(summary.replace("\n", " "))
    show_editor_message("ZombieSeasons World Generation — Stage 5", summary)


if __name__ == "__main__":
    run()
