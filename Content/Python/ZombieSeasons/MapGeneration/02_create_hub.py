"""Create the deterministic ZombieSeasons Hub greybox on the Stage-1 world shell.

Run from Unreal Editor only after Stage 1 has passed and its World Partition files
have been committed:

py "C:/Users/malik/Documents/Unreal Projects/ZombieSeasons/Content/Python/ZombieSeasons/MapGeneration/02_create_hub.py"

This stage creates only project-owned greybox geometry and stable gameplay markers.
It does not load City Sample/Fab production art and it does not invent runtime
behaviour for the BP_ZS_* adapters that do not exist yet.
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


STAGE = "Hub"
MODE = "CREATE"
ENGINE_CUBE = "/Engine/BasicShapes/Cube.Cube"

# Frozen Hub contract from 07_Production_World_Specification.md.
HUB_MIN = -15000.0
HUB_MAX = 15000.0
SAFE_ZONE_HALF_EXTENT = 6000.0
HUB_RING_INNER = 8500.0
HUB_RING_OUTER = 10500.0
ROAD_Z = 18.0
ROAD_THICKNESS = 36.0
RING_ROAD_WIDTH = 1200.0
CONNECTOR_ROAD_WIDTH = 900.0
DISTRICT_CONNECTOR_WIDTH = 1200.0

SAFEHOUSE_WIDTH = 5200.0
SAFEHOUSE_DEPTH = 4200.0
SAFEHOUSE_WALL_HEIGHT = 420.0
SAFEHOUSE_WALL_THICKNESS = 80.0
SAFEHOUSE_FLOOR_THICKNESS = 24.0
SAFEHOUSE_MAIN_DOOR_WIDTH = 1600.0
SAFEHOUSE_SERVICE_DOOR_WIDTH = 1400.0

PERIMETER_WALL_HEIGHT = 520.0
PERIMETER_WALL_THICKNESS = 100.0
PERIMETER_GATE_WIDTH = 1800.0
GATE_PILLAR_SIZE = 260.0
GATE_PILLAR_HEIGHT = 720.0
GATE_BEAM_HEIGHT = 180.0

EDITOR_GREYBOX_LAYERS = (
    "DL_ZS_Greybox",
    "DL_ZS_Hub",
)
EDITOR_GAMEPLAY_LAYERS = (
    "DL_ZS_Greybox",
    "DL_ZS_Gameplay",
    "DL_ZS_Hub",
)

# Ring geometry follows the Stage-1 topology, but these are playable collision
# surfaces at ground level rather than editor-only topology guides.
RING_SEGMENTS: tuple[tuple[str, tuple[float, float], tuple[float, float]], ...] = (
    ("N", (-7000.0, 10000.0), (7000.0, 10000.0)),
    ("NE", (7000.0, 10000.0), (10000.0, 7000.0)),
    ("E", (10000.0, 7000.0), (10000.0, -7000.0)),
    ("SE", (10000.0, -7000.0), (7000.0, -10000.0)),
    ("S", (7000.0, -10000.0), (-7000.0, -10000.0)),
    ("SW", (-7000.0, -10000.0), (-10000.0, -7000.0)),
    ("W", (-10000.0, -7000.0), (-10000.0, 7000.0)),
    ("NW", (-10000.0, 7000.0), (-7000.0, 10000.0)),
)

# Safe-zone exits to the ring road. These are deliberately cardinal because the
# frozen Hub POI anchors define North/East/South/West exterior gates.
CARDINAL_CONNECTORS: tuple[
    tuple[str, tuple[float, float], tuple[float, float]], ...
] = (
    ("North", (0.0, SAFE_ZONE_HALF_EXTENT), (0.0, 10000.0)),
    ("East", (SAFE_ZONE_HALF_EXTENT, 0.0), (10000.0, 0.0)),
    ("South", (0.0, -SAFE_ZONE_HALF_EXTENT), (0.0, -10000.0)),
    ("West", (-SAFE_ZONE_HALF_EXTENT, 0.0), (-10000.0, 0.0)),
)

# First playable stretch of each district arterial. District stages continue these
# roads into the actual neighbourhood layouts.
DISTRICT_CONNECTORS: tuple[
    tuple[str, str, tuple[float, float], tuple[float, float]], ...
] = (
    ("Spring", "NW", (-8000.0, 8000.0), (-15000.0, 15000.0)),
    ("Summer", "NE", (8000.0, 8000.0), (15000.0, 15000.0)),
    ("Autumn", "SW", (-8000.0, -8000.0), (-15000.0, -15000.0)),
    ("Winter", "SE", (8000.0, -8000.0), (15000.0, -15000.0)),
)

OUTER_GATE_ANCHORS = {
    "North": (0.0, 10500.0, 0.0),
    "East": (10500.0, 0.0, 0.0),
    "South": (0.0, -10500.0, 0.0),
    "West": (-10500.0, 0.0, 0.0),
}


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
            "Unsaved map packages are open. Save or discard them before Stage 2: "
            + ", ".join(names)
        )


def ensure_target_world_loaded() -> None:
    if is_target_world_loaded():
        return
    check_dirty_maps_before_load()
    if not get_level_subsystem().load_level(GREYBOX_MAP):
        fail(f"Unable to load Stage-1 greybox map: {GREYBOX_MAP}")
    if not is_target_world_loaded():
        fail("LevelEditorSubsystem reported success but the greybox world is not active.")


def all_loaded_actors() -> list[Any]:
    return list(get_actor_subsystem().get_all_level_actors() or [])


def stage_actors(stage_name: str) -> list[Any]:
    tag = f"ZS.Stage.{stage_name}"
    return [actor for actor in all_loaded_actors() if actor_has_tag(actor, tag)]


def preflight() -> None:
    if MODE != "CREATE":
        fail(f"Unsupported Hub generation mode: {MODE}")
    if not editor_asset_exists(GREYBOX_MAP):
        fail("Stage-1 greybox map does not exist. Run 01_create_world_shell.py first.")

    required_symbols = (
        "LevelEditorSubsystem",
        "EditorActorSubsystem",
        "UnrealEditorSubsystem",
        "StaticMeshActor",
        "PlayerStart",
    )
    missing = [name for name in required_symbols if not hasattr(unreal, name)]
    if missing:
        fail("Required Unreal Python symbols missing: " + ", ".join(missing))

    ensure_target_world_loaded()

    world_shell = stage_actors("WorldShell")
    if len(world_shell) < 100:
        fail(
            "The loaded greybox does not expose enough Stage-1 WorldShell actors "
            f"({len(world_shell)} found). Do not generate the Hub on an incomplete shell."
        )

    existing_hub = stage_actors(STAGE)
    if existing_hub:
        fail(
            f"Refusing to duplicate Hub generation: {len(existing_hub)} Stage-2 actors "
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
    editor_only: bool = False,
) -> None:
    try:
        actor.set_actor_label(label, mark_dirty=True)
    except TypeError:
        actor.set_actor_label(label)
    actor.set_folder_path(unreal.Name(folder))
    add_generation_tags(actor, stage=STAGE, district="Hub", stable_id=stable_id)
    set_editor_layers(
        actor,
        EDITOR_GAMEPLAY_LAYERS if gameplay_marker else EDITOR_GREYBOX_LAYERS,
    )

    # Hub is intentionally always loaded: it is the persistent navigation and safe
    # zone anchor for the whole game, and the actor count is small.
    try:
        actor.set_editor_property("is_spatially_loaded", False)
    except Exception as error:
        warn(f"Unable to make {label} non-spatial/persistent: {error}")

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
    editor_only: bool = False,
) -> Any:
    actor = get_actor_subsystem().spawn_actor_from_class(
        unreal.StaticMeshActor,
        unreal.Vector(*center),
        unreal.Rotator(roll=0.0, pitch=0.0, yaw=yaw),
    )
    if actor is None:
        fail(f"Unable to spawn Hub actor: {label}")
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
    thickness: float,
    folder: str,
    collision: bool = True,
) -> Any:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.hypot(dx, dy)
    if length <= 0.0:
        fail(f"Zero-length Hub segment requested: {stable_id}")
    yaw = math.degrees(math.atan2(dy, dx))
    return spawn_box(
        mesh,
        label=label,
        stable_id=stable_id,
        center=((start[0] + end[0]) * 0.5, (start[1] + end[1]) * 0.5, z),
        size=(length, width, thickness),
        folder=folder,
        yaw=yaw,
        collision=collision,
    )


def create_ring_roads(mesh: Any) -> int:
    count = 0
    for suffix, start, end in RING_SEGMENTS:
        spawn_segment(
            mesh,
            label=f"ZS_Hub_RingRoad_{suffix}",
            stable_id=f"Hub.Road.Ring.{suffix}",
            start=start,
            end=end,
            width=RING_ROAD_WIDTH,
            z=ROAD_Z,
            thickness=ROAD_THICKNESS,
            folder="ZombieSeasons/Hub/Roads/Ring",
        )
        count += 1

    for name, start, end in CARDINAL_CONNECTORS:
        spawn_segment(
            mesh,
            label=f"ZS_Hub_Connector_{name}",
            stable_id=f"Hub.Road.SafeZoneConnector.{name}",
            start=start,
            end=end,
            width=CONNECTOR_ROAD_WIDTH,
            z=ROAD_Z + 1.0,
            thickness=ROAD_THICKNESS,
            folder="ZombieSeasons/Hub/Roads/SafeZoneConnectors",
        )
        count += 1

    for district, suffix, start, end in DISTRICT_CONNECTORS:
        spawn_segment(
            mesh,
            label=f"ZS_Hub_DistrictConnector_{district}",
            stable_id=f"Hub.Road.DistrictConnector.{district}",
            start=start,
            end=end,
            width=DISTRICT_CONNECTOR_WIDTH,
            z=ROAD_Z + 2.0,
            thickness=ROAD_THICKNESS,
            folder="ZombieSeasons/Hub/Roads/DistrictConnectors",
        )
        count += 1
    return count


def create_safehouse_floor(mesh: Any) -> int:
    spawn_box(
        mesh,
        label="ZS_Hub_Safehouse_Floor",
        stable_id="Hub.Safehouse.Floor",
        center=(0.0, 0.0, SAFEHOUSE_FLOOR_THICKNESS * 0.5),
        size=(SAFEHOUSE_WIDTH, SAFEHOUSE_DEPTH, SAFEHOUSE_FLOOR_THICKNESS),
        folder="ZombieSeasons/Hub/Safehouse/Structure",
    )
    return 1


def wall_pair_with_gap(
    mesh: Any,
    *,
    side: str,
    axis: str,
    fixed: float,
    total_length: float,
    gap_width: float,
    wall_height: float,
    wall_thickness: float,
    stable_prefix: str,
    folder: str,
) -> int:
    segment_length = (total_length - gap_width) * 0.5
    if segment_length <= 0.0:
        fail(f"Invalid wall/gap dimensions for {stable_prefix}")
    offset = gap_width * 0.5 + segment_length * 0.5
    z = wall_height * 0.5

    for suffix, sign in (("A", -1.0), ("B", 1.0)):
        if axis == "X":
            center = (sign * offset, fixed, z)
            size = (segment_length, wall_thickness, wall_height)
        else:
            center = (fixed, sign * offset, z)
            size = (wall_thickness, segment_length, wall_height)
        spawn_box(
            mesh,
            label=f"ZS_Hub_{stable_prefix}_{side}_{suffix}",
            stable_id=f"Hub.{stable_prefix}.{side}.{suffix}",
            center=center,
            size=size,
            folder=folder,
        )
    return 2


def create_safehouse(mesh: Any) -> int:
    count = create_safehouse_floor(mesh)
    half_w = SAFEHOUSE_WIDTH * 0.5
    half_d = SAFEHOUSE_DEPTH * 0.5

    # North wall remains solid. South is the main entrance; East is a service exit;
    # West remains solid to make the interior less symmetrical during combat.
    spawn_box(
        mesh,
        label="ZS_Hub_Safehouse_Wall_North",
        stable_id="Hub.Safehouse.Wall.North",
        center=(0.0, half_d, SAFEHOUSE_WALL_HEIGHT * 0.5),
        size=(SAFEHOUSE_WIDTH, SAFEHOUSE_WALL_THICKNESS, SAFEHOUSE_WALL_HEIGHT),
        folder="ZombieSeasons/Hub/Safehouse/Structure",
    )
    count += 1
    count += wall_pair_with_gap(
        mesh,
        side="South",
        axis="X",
        fixed=-half_d,
        total_length=SAFEHOUSE_WIDTH,
        gap_width=SAFEHOUSE_MAIN_DOOR_WIDTH,
        wall_height=SAFEHOUSE_WALL_HEIGHT,
        wall_thickness=SAFEHOUSE_WALL_THICKNESS,
        stable_prefix="Safehouse.Wall",
        folder="ZombieSeasons/Hub/Safehouse/Structure",
    )
    spawn_box(
        mesh,
        label="ZS_Hub_Safehouse_Wall_West",
        stable_id="Hub.Safehouse.Wall.West",
        center=(-half_w, 0.0, SAFEHOUSE_WALL_HEIGHT * 0.5),
        size=(SAFEHOUSE_WALL_THICKNESS, SAFEHOUSE_DEPTH, SAFEHOUSE_WALL_HEIGHT),
        folder="ZombieSeasons/Hub/Safehouse/Structure",
    )
    count += 1
    count += wall_pair_with_gap(
        mesh,
        side="East",
        axis="Y",
        fixed=half_w,
        total_length=SAFEHOUSE_DEPTH,
        gap_width=SAFEHOUSE_SERVICE_DOOR_WIDTH,
        wall_height=SAFEHOUSE_WALL_HEIGHT,
        wall_thickness=SAFEHOUSE_WALL_THICKNESS,
        stable_prefix="Safehouse.Wall",
        folder="ZombieSeasons/Hub/Safehouse/Structure",
    )

    # Operations-room partition around the frozen objective-board anchor region.
    spawn_box(
        mesh,
        label="ZS_Hub_OperationsRoom_Partition_W",
        stable_id="Hub.Safehouse.OperationsRoom.Partition.W",
        center=(-1250.0, 1200.0, 180.0),
        size=(60.0, 1700.0, 360.0),
        folder="ZombieSeasons/Hub/Safehouse/Interior",
    )
    spawn_box(
        mesh,
        label="ZS_Hub_OperationsRoom_Partition_E",
        stable_id="Hub.Safehouse.OperationsRoom.Partition.E",
        center=(1250.0, 1200.0, 180.0),
        size=(60.0, 1700.0, 360.0),
        folder="ZombieSeasons/Hub/Safehouse/Interior",
    )
    count += 2
    return count


def create_safe_zone_perimeter(mesh: Any) -> int:
    count = 0
    extent = SAFE_ZONE_HALF_EXTENT
    total = extent * 2.0
    for side, axis, fixed in (
        ("North", "X", extent),
        ("South", "X", -extent),
        ("East", "Y", extent),
        ("West", "Y", -extent),
    ):
        count += wall_pair_with_gap(
            mesh,
            side=side,
            axis=axis,
            fixed=fixed,
            total_length=total,
            gap_width=PERIMETER_GATE_WIDTH,
            wall_height=PERIMETER_WALL_HEIGHT,
            wall_thickness=PERIMETER_WALL_THICKNESS,
            stable_prefix="Perimeter.Wall",
            folder="ZombieSeasons/Hub/Perimeter/Walls",
        )
    return count


def create_outer_gate(mesh: Any, name: str, anchor: tuple[float, float, float]) -> int:
    x, y, _ = anchor
    horizontal = name in {"North", "South"}
    lateral = 1150.0
    pillar_z = GATE_PILLAR_HEIGHT * 0.5

    for suffix, sign in (("A", -1.0), ("B", 1.0)):
        center = (
            (x + sign * lateral, y, pillar_z)
            if horizontal
            else (x, y + sign * lateral, pillar_z)
        )
        spawn_box(
            mesh,
            label=f"ZS_Hub_OuterGate_{name}_Pillar_{suffix}",
            stable_id=f"Hub.OuterGate.{name}.Pillar.{suffix}",
            center=center,
            size=(GATE_PILLAR_SIZE, GATE_PILLAR_SIZE, GATE_PILLAR_HEIGHT),
            folder="ZombieSeasons/Hub/OuterGates",
        )

    beam_size = (
        (2600.0, GATE_PILLAR_SIZE, GATE_BEAM_HEIGHT)
        if horizontal
        else (GATE_PILLAR_SIZE, 2600.0, GATE_BEAM_HEIGHT)
    )
    spawn_box(
        mesh,
        label=f"ZS_Hub_OuterGate_{name}_Beam",
        stable_id=f"Hub.OuterGate.{name}.Beam",
        center=(x, y, GATE_PILLAR_HEIGHT - GATE_BEAM_HEIGHT * 0.5),
        size=beam_size,
        folder="ZombieSeasons/Hub/OuterGates",
    )
    return 3


def create_outer_gates(mesh: Any) -> int:
    return sum(create_outer_gate(mesh, name, anchor) for name, anchor in OUTER_GATE_ANCHORS.items())


def create_plaza(mesh: Any) -> int:
    # Four walkable courtyard slabs around the safehouse leave the safehouse itself
    # and the cardinal connector corridors clearly readable.
    slabs = (
        ("North", (0.0, 4550.0, 12.0), (7200.0, 1800.0, 20.0)),
        ("South", (0.0, -4550.0, 12.0), (7200.0, 1800.0, 20.0)),
        ("East", (4550.0, 0.0, 12.0), (1800.0, 7200.0, 20.0)),
        ("West", (-4550.0, 0.0, 12.0), (1800.0, 7200.0, 20.0)),
    )
    for name, center, size in slabs:
        spawn_box(
            mesh,
            label=f"ZS_Hub_Courtyard_{name}",
            stable_id=f"Hub.Courtyard.{name}",
            center=center,
            size=size,
            folder="ZombieSeasons/Hub/Courtyard",
        )
    return len(slabs)


def create_player_start() -> int:
    actor = get_actor_subsystem().spawn_actor_from_class(
        unreal.PlayerStart,
        unreal.Vector(0.0, -1200.0, 120.0),
        unreal.Rotator(0.0, 0.0, 0.0),
    )
    if actor is None:
        fail("Unable to create Hub PlayerStart.")
    set_actor_identity(
        actor,
        label="ZS_Hub_PlayerStart",
        stable_id="Hub.PlayerStart.Initial",
        folder="ZombieSeasons/Hub/Gameplay",
        gameplay_marker=True,
    )
    return 1


def create_gameplay_markers(mesh: Any) -> int:
    markers = (
        (
            "OperationsRoom",
            "Hub.Marker.OperationsRoom",
            (0.0, 1500.0, 130.0),
            (500.0, 500.0, 260.0),
        ),
        (
            "ObjectiveBoard",
            "Hub.Marker.ObjectiveBoard",
            (0.0, 2020.0, 175.0),
            (700.0, 70.0, 350.0),
        ),
        (
            "SafeZoneCenter",
            "Hub.Marker.SafeZone",
            (0.0, 0.0, 75.0),
            (300.0, 300.0, 150.0),
        ),
        (
            "ZombieNavExclusionPlaceholder",
            "Hub.Marker.ZombieNavExclusion",
            (0.0, 0.0, 1050.0),
            (SAFE_ZONE_HALF_EXTENT * 2.0, SAFE_ZONE_HALF_EXTENT * 2.0, 40.0),
        ),
    )
    for name, stable_id, center, size in markers:
        spawn_box(
            mesh,
            label=f"ZS_Hub_Marker_{name}",
            stable_id=stable_id,
            center=center,
            size=size,
            folder="ZombieSeasons/Hub/Gameplay/Markers",
            collision=False,
            gameplay_marker=True,
            editor_only=True,
        )
    return len(markers)


def save_level() -> None:
    if not get_level_subsystem().save_current_level():
        fail("Hub actors were generated but the greybox level could not be saved.")


def position_viewport() -> None:
    try:
        subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        if subsystem is not None:
            subsystem.set_level_viewport_camera_info(
                unreal.Vector(0.0, -25000.0, 25000.0),
                unreal.Rotator(roll=0.0, pitch=-35.0, yaw=90.0),
            )
    except Exception as error:
        warn(f"Unable to position the viewport for Hub review: {error}")


def run() -> None:
    preflight()
    log("Stage 2 preflight passed. Creating deterministic Hub greybox.")

    mesh = unreal.load_asset(ENGINE_CUBE)
    if mesh is None:
        fail(f"Engine cube disappeared after preflight: {ENGINE_CUBE}")

    road_count = create_ring_roads(mesh)
    safehouse_count = create_safehouse(mesh)
    perimeter_count = create_safe_zone_perimeter(mesh)
    gate_count = create_outer_gates(mesh)
    plaza_count = create_plaza(mesh)
    player_start_count = create_player_start()
    marker_count = create_gameplay_markers(mesh)

    generated = stage_actors(STAGE)
    expected = (
        road_count
        + safehouse_count
        + perimeter_count
        + gate_count
        + plaza_count
        + player_start_count
        + marker_count
    )
    if len(generated) != expected:
        fail(
            "Hub generation count mismatch before save: "
            f"expected {expected}, found {len(generated)} tagged actors."
        )

    save_level()
    position_viewport()

    report = write_json_report(
        "hub_generation.json",
        {
            "status": "PASS",
            "stage": STAGE,
            "mode": MODE,
            "map": GREYBOX_MAP,
            "generated_actor_count": len(generated),
            "road_surface_count": road_count,
            "safehouse_actor_count": safehouse_count,
            "perimeter_wall_count": perimeter_count,
            "outer_gate_actor_count": gate_count,
            "courtyard_slab_count": plaza_count,
            "player_start_count": player_start_count,
            "gameplay_marker_count": marker_count,
            "safe_zone_half_extent_cm": SAFE_ZONE_HALF_EXTENT,
            "final_art_assets_loaded": False,
            "data_layer_strategy": "Editor Layers + ZS tags until WP Data Layer adapters are implemented",
            "zombie_navigation_exclusion": "deterministic marker only; actual nav configuration deferred to Stage 10",
            "historical_maps_modified": False,
        },
    )

    summary = (
        "Hub greybox generation PASSED.\n\n"
        f"Map: {GREYBOX_MAP}\n"
        f"Generated Hub actors: {len(generated)}\n"
        f"Playable road surfaces: {road_count}\n"
        f"Safehouse actors: {safehouse_count}\n"
        f"Perimeter walls: {perimeter_count}\n"
        f"Outer-gate actors: {gate_count}\n"
        f"Gameplay markers: {marker_count}\n"
        "PlayerStart: 1\n\n"
        "No final Fab/City Sample art was loaded.\n"
        f"Report:\n{report}"
    )
    log(summary.replace("\n", " "))
    show_editor_message("ZombieSeasons World Generation — Stage 2", summary)


if __name__ == "__main__":
    run()
