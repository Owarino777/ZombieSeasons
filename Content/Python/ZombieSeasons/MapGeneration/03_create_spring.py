"""Create the deterministic ZombieSeasons Spring district greybox.

Run from Unreal Editor only after Stage 2 has passed and the Hub checkpoint is
committed:

py "C:/Users/malik/Documents/Unreal Projects/ZombieSeasons/Content/Python/ZombieSeasons/MapGeneration/03_create_spring.py"

Stage 3 creates topology-critical Spring geometry only: roads, POI footprints,
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


STAGE = "Spring"
MODE = "CREATE"
ENGINE_CUBE = "/Engine/BasicShapes/Cube.Cube"

SPRING_GROUND_Z = 200.0
ROAD_THICKNESS = 36.0
MAIN_ROAD_WIDTH = 1200.0
SECONDARY_ROAD_WIDTH = 700.0
SERVICE_ROAD_WIDTH = 500.0
PATH_WIDTH = 420.0

STANDARD_WALL_HEIGHT = 420.0
STANDARD_WALL_THICKNESS = 80.0
ARENA_WALL_HEIGHT = 520.0
ARENA_WALL_THICKNESS = 100.0
FLOOR_THICKNESS = 24.0

EDITOR_GREYBOX_LAYERS = (
    "DL_ZS_Greybox",
    "DL_ZS_Spring",
)
EDITOR_GAMEPLAY_LAYERS = (
    "DL_ZS_Greybox",
    "DL_ZS_Gameplay",
    "DL_ZS_Spring",
)

# Frozen production anchors from 07_Production_World_Specification.md.
POI_ANCHORS: dict[str, tuple[float, float, float]] = {
    "Residential": (-31000.0, 67000.0, 200.0),
    "Park": (-34000.0, 38000.0, 100.0),
    "School": (-55000.0, 58000.0, 300.0),
    "Gym": (-60000.0, 52000.0, 300.0),
    "Greenhouses": (-71000.0, 31000.0, 100.0),
    "Relay": (-57000.0, 60000.0, 800.0),
    "DrainageEntrance": (-62000.0, 20000.0, -100.0),
}

# Playable route topology. The first segment continues the Stage-2 NW connector.
ROAD_SEGMENTS: tuple[
    tuple[str, tuple[float, float], tuple[float, float], float], ...
] = (
    ("Main_Entry", (-15000.0, 15000.0), (-45000.0, 45000.0), MAIN_ROAD_WIDTH),
    ("Main_School", (-45000.0, 45000.0), (-55000.0, 58000.0), 1000.0),
    ("Residential_Avenue", (-45000.0, 45000.0), (-31000.0, 67000.0), SECONDARY_ROAD_WIDTH),
    ("Park_Loop_A", (-45000.0, 45000.0), (-34000.0, 38000.0), SECONDARY_ROAD_WIDTH),
    ("Park_Loop_B", (-34000.0, 38000.0), (-28000.0, 52000.0), SECONDARY_ROAD_WIDTH),
    ("Residential_Cross", (-28000.0, 52000.0), (-31000.0, 67000.0), SECONDARY_ROAD_WIDTH),
    ("School_Gym", (-55000.0, 58000.0), (-60000.0, 52000.0), SECONDARY_ROAD_WIDTH),
    ("Greenhouse_Service", (-45000.0, 45000.0), (-71000.0, 31000.0), SERVICE_ROAD_WIDTH),
    ("Drainage_Service", (-71000.0, 31000.0), (-62000.0, 20000.0), SERVICE_ROAD_WIDTH),
)

# Required Spring shortcuts from the district specification.
SHORTCUT_SEGMENTS: tuple[
    tuple[str, tuple[float, float], tuple[float, float], float], ...
] = (
    # School service gate returns toward the Hub arterial.
    ("SchoolServiceGate", (-53500.0, 55500.0), (-47000.0, 48500.0), PATH_WIDTH),
    # Collapsed garden wall links residential streets directly to the park.
    ("CollapsedGardenWall", (-30500.0, 61000.0), (-33500.0, 44000.0), PATH_WIDTH),
    # Drainage path prepares the greenhouse -> sewer shortcut endpoint.
    ("GreenhouseDrainage", (-69000.0, 28500.0), (-62000.0, 20000.0), PATH_WIDTH),
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
            "Unsaved map packages are open. Save or discard them before Stage 3: "
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


def preflight() -> None:
    if MODE != "CREATE":
        fail(f"Unsupported Spring generation mode: {MODE}")
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

    # Hub actors are intentionally non-spatial and therefore make a reliable
    # checkpoint guard even when Spring World Partition cells are not loaded.
    if len(stage_actors("Hub")) < 50:
        fail("Stage 2 Hub checkpoint is not available. Do not generate Spring yet.")

    existing = stage_actors(STAGE)
    if existing:
        fail(
            f"Refusing to duplicate Spring generation: {len(existing)} Stage-3 actors "
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
    add_generation_tags(actor, stage=STAGE, district="Spring", stable_id=stable_id)
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
        fail(f"Unable to spawn Spring actor: {label}")
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
        fail(f"Zero-length Spring segment requested: {stable_id}")
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
    # Always-loaded editor-only sentinel prevents accidental duplicate Stage-3 runs
    # even when Spring World Partition cells are currently unloaded.
    spawn_box(
        mesh,
        label="ZS_Spring_StageSentinel",
        stable_id="Spring.StageSentinel",
        center=(-50000.0, 50000.0, 4500.0),
        size=(80.0, 80.0, 80.0),
        folder="ZombieSeasons/Spring/System",
        collision=False,
        persistent=True,
        editor_only=True,
    )
    return 1


def create_roads(mesh: Any) -> int:
    count = 0
    road_z = SPRING_GROUND_Z + ROAD_THICKNESS * 0.5 + 2.0
    for road_id, start, end, width in ROAD_SEGMENTS:
        spawn_segment(
            mesh,
            label=f"ZS_Spring_Road_{road_id}",
            stable_id=f"Spring.Road.{road_id}",
            start=start,
            end=end,
            width=width,
            z=road_z,
            folder="ZombieSeasons/Spring/Roads",
        )
        count += 1
    return count


def create_shortcuts(mesh: Any) -> int:
    count = 0
    path_z = SPRING_GROUND_Z + ROAD_THICKNESS * 0.5 + 4.0
    for shortcut_id, start, end, width in SHORTCUT_SEGMENTS:
        spawn_segment(
            mesh,
            label=f"ZS_Spring_Shortcut_{shortcut_id}",
            stable_id=f"Spring.Shortcut.{shortcut_id}",
            start=start,
            end=end,
            width=width,
            z=path_z,
            folder="ZombieSeasons/Spring/Shortcuts",
        )
        count += 1
    return count


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
            label=f"ZS_Spring_{prefix}_{side}_{suffix}",
            stable_id=f"Spring.{prefix}.{side}.{suffix}",
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
    wall_thickness: float,
    folder: str,
) -> int:
    count = 0
    half_w = width * 0.5
    half_d = depth * 0.5

    spawn_box(
        mesh,
        label=f"ZS_Spring_{prefix}_Floor",
        stable_id=f"Spring.{prefix}.Floor",
        center=(center[0], center[1], ground_z + FLOOR_THICKNESS * 0.5),
        size=(width, depth, FLOOR_THICKNESS),
        folder=folder,
    )
    count += 1

    spawn_box(
        mesh,
        label=f"ZS_Spring_{prefix}_Wall_North",
        stable_id=f"Spring.{prefix}.Wall.North",
        center=(center[0], center[1] + half_d, ground_z + wall_height * 0.5),
        size=(width, wall_thickness, wall_height),
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
        wall_thickness=wall_thickness,
        ground_z=ground_z,
        folder=folder,
    )

    spawn_box(
        mesh,
        label=f"ZS_Spring_{prefix}_Wall_West",
        stable_id=f"Spring.{prefix}.Wall.West",
        center=(center[0] - half_w, center[1], ground_z + wall_height * 0.5),
        size=(wall_thickness, depth, wall_height),
        folder=folder,
    )
    count += 1

    if east_gap is None:
        spawn_box(
            mesh,
            label=f"ZS_Spring_{prefix}_Wall_East",
            stable_id=f"Spring.{prefix}.Wall.East",
            center=(center[0] + half_w, center[1], ground_z + wall_height * 0.5),
            size=(wall_thickness, depth, wall_height),
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
            wall_thickness=wall_thickness,
            ground_z=ground_z,
            folder=folder,
        )
    return count


def create_school(mesh: Any) -> int:
    count = create_open_structure(
        mesh,
        prefix="School",
        center=(-55000.0, 58000.0),
        width=7200.0,
        depth=5000.0,
        ground_z=SPRING_GROUND_Z,
        south_gap=1200.0,
        east_gap=1100.0,
        wall_height=460.0,
        wall_thickness=90.0,
        folder="ZombieSeasons/Spring/POI/School",
    )

    # Two interior partitions create readable short school sightlines while keeping
    # a >= 300 cm mandatory combat passage through the middle.
    for suffix, y in (("North", 59300.0), ("South", 56700.0)):
        spawn_box(
            mesh,
            label=f"ZS_Spring_School_Interior_{suffix}",
            stable_id=f"Spring.School.Interior.{suffix}",
            center=(-56500.0, y, SPRING_GROUND_Z + 180.0),
            size=(60.0, 1800.0, 360.0),
            folder="ZombieSeasons/Spring/POI/School/Interior",
        )
        count += 1
    return count


def create_gym_arena(mesh: Any) -> int:
    # ~60 x 55 m arena: inside the frozen 50–65 m Spring arena target.
    center = (-60000.0, 52000.0)
    width = 6000.0
    depth = 5500.0
    half_w = width * 0.5
    half_d = depth * 0.5
    count = 0

    spawn_box(
        mesh,
        label="ZS_Spring_Gym_Floor",
        stable_id="Spring.Gym.Floor",
        center=(center[0], center[1], SPRING_GROUND_Z + FLOOR_THICKNESS * 0.5),
        size=(width, depth, FLOOR_THICKNESS),
        folder="ZombieSeasons/Spring/POI/Gym",
    )
    count += 1

    # North and South are the two mandatory exits.
    count += wall_pair_with_gap(
        mesh,
        prefix="Gym.Wall",
        side="North",
        center=(center[0], center[1] + half_d),
        axis="X",
        total_length=width,
        gap_width=1000.0,
        wall_height=ARENA_WALL_HEIGHT,
        wall_thickness=ARENA_WALL_THICKNESS,
        ground_z=SPRING_GROUND_Z,
        folder="ZombieSeasons/Spring/POI/Gym",
    )
    count += wall_pair_with_gap(
        mesh,
        prefix="Gym.Wall",
        side="South",
        center=(center[0], center[1] - half_d),
        axis="X",
        total_length=width,
        gap_width=1000.0,
        wall_height=ARENA_WALL_HEIGHT,
        wall_thickness=ARENA_WALL_THICKNESS,
        ground_z=SPRING_GROUND_Z,
        folder="ZombieSeasons/Spring/POI/Gym",
    )

    spawn_box(
        mesh,
        label="ZS_Spring_Gym_Wall_West",
        stable_id="Spring.Gym.Wall.West",
        center=(center[0] - half_w, center[1], SPRING_GROUND_Z + ARENA_WALL_HEIGHT * 0.5),
        size=(ARENA_WALL_THICKNESS, depth, ARENA_WALL_HEIGHT),
        folder="ZombieSeasons/Spring/POI/Gym",
    )
    count += 1

    # East wall contains the unlockable gallery exit topology.
    count += wall_pair_with_gap(
        mesh,
        prefix="Gym.Wall",
        side="EastUnlockable",
        center=(center[0] + half_w, center[1]),
        axis="Y",
        total_length=depth,
        gap_width=900.0,
        wall_height=ARENA_WALL_HEIGHT,
        wall_thickness=ARENA_WALL_THICKNESS,
        ground_z=SPRING_GROUND_Z,
        folder="ZombieSeasons/Spring/POI/Gym",
    )

    # Simple raised gallery route. Stage 9 will attach the actual gate/trigger marker.
    spawn_box(
        mesh,
        label="ZS_Spring_Gym_UpperGallery",
        stable_id="Spring.Gym.UpperGallery",
        center=(-56500.0, 52000.0, SPRING_GROUND_Z + 350.0),
        size=(1600.0, 800.0, 40.0),
        folder="ZombieSeasons/Spring/POI/Gym/Gallery",
    )
    count += 1
    return count


def create_residential(mesh: Any) -> int:
    # Four solid house footprints frame a readable suburban loop; art pass replaces
    # these masses only after traversal validation.
    houses = (
        ("A", (-35000.0, 68000.0), (2600.0, 1900.0, 750.0)),
        ("B", (-30500.0, 71000.0), (2300.0, 1800.0, 650.0)),
        ("C", (-26000.0, 67000.0), (2500.0, 2000.0, 700.0)),
        ("D", (-30500.0, 63000.0), (2200.0, 1700.0, 620.0)),
    )
    for suffix, center, size in houses:
        spawn_box(
            mesh,
            label=f"ZS_Spring_Residential_House_{suffix}",
            stable_id=f"Spring.Residential.House.{suffix}",
            center=(center[0], center[1], SPRING_GROUND_Z + size[2] * 0.5),
            size=size,
            folder="ZombieSeasons/Spring/POI/Residential",
        )
    return len(houses)


def create_park(mesh: Any) -> int:
    # Low obstacles establish cover/scavenging lanes without turning the park into
    # a combat arena. The middle stays open for low-pressure traversal.
    obstacles = (
        ("Planter_N", (-34000.0, 41000.0), (4200.0, 350.0, 110.0)),
        ("Planter_S", (-34000.0, 35000.0), (4200.0, 350.0, 110.0)),
        ("Wall_W", (-37500.0, 38000.0), (350.0, 2800.0, 150.0)),
        ("Wall_E", (-30500.0, 38000.0), (350.0, 2800.0, 150.0)),
        ("Cover_A", (-35500.0, 39000.0), (700.0, 500.0, 160.0)),
        ("Cover_B", (-32500.0, 37000.0), (700.0, 500.0, 160.0)),
    )
    for suffix, center, size in obstacles:
        spawn_box(
            mesh,
            label=f"ZS_Spring_Park_{suffix}",
            stable_id=f"Spring.Park.{suffix}",
            center=(center[0], center[1], SPRING_GROUND_Z + size[2] * 0.5),
            size=size,
            folder="ZombieSeasons/Spring/POI/Park",
        )
    return len(obstacles)


def create_greenhouses(mesh: Any) -> int:
    greenhouse_specs = (
        ("A", (-73500.0, 33000.0), 12.0),
        ("B", (-70000.0, 31000.0), 12.0),
        ("C", (-66500.0, 29000.0), 12.0),
    )
    count = 0
    for suffix, center, yaw in greenhouse_specs:
        spawn_box(
            mesh,
            label=f"ZS_Spring_Greenhouse_{suffix}",
            stable_id=f"Spring.Greenhouse.{suffix}",
            center=(center[0], center[1], SPRING_GROUND_Z + 210.0),
            size=(3000.0, 1200.0, 420.0),
            folder="ZombieSeasons/Spring/POI/Greenhouses",
            yaw=yaw,
        )
        count += 1
    return count


def create_drainage_entrance(mesh: Any) -> int:
    # Physical stairwell/portal placeholder descending toward the Stage-7 sewer
    # junction. It deliberately does not build the sewer corridor yet.
    spawn_box(
        mesh,
        label="ZS_Spring_DrainageEntrance",
        stable_id="Spring.DrainageEntrance.Structure",
        center=(-62000.0, 20000.0, SPRING_GROUND_Z + 180.0),
        size=(1800.0, 1200.0, 360.0),
        folder="ZombieSeasons/Spring/POI/Drainage",
    )
    spawn_box(
        mesh,
        label="ZS_Spring_DrainagePortal",
        stable_id="Spring.DrainageEntrance.Portal",
        center=(-62000.0, 19400.0, SPRING_GROUND_Z + 110.0),
        size=(700.0, 90.0, 220.0),
        folder="ZombieSeasons/Spring/POI/Drainage",
        collision=False,
        gameplay_marker=True,
        editor_only=True,
    )
    return 2


def create_relay_landmark(mesh: Any) -> int:
    # Spatial landmark only; the real objective adapter is Stage 9.
    base_z = 300.0
    spawn_box(
        mesh,
        label="ZS_Spring_Relay_Mast",
        stable_id="Spring.Relay.Landmark",
        center=(-57000.0, 60000.0, base_z + 1200.0),
        size=(180.0, 180.0, 2400.0),
        folder="ZombieSeasons/Spring/POI/School/Relay",
    )
    spawn_box(
        mesh,
        label="ZS_Spring_Relay_ObjectiveAnchor",
        stable_id="Spring.Relay.ObjectiveAnchor",
        center=POI_ANCHORS["Relay"],
        size=(350.0, 350.0, 350.0),
        folder="ZombieSeasons/Spring/POI/School/Relay",
        collision=False,
        gameplay_marker=True,
        editor_only=True,
    )
    return 2


def create_poi_anchor_markers(mesh: Any) -> int:
    # Readability markers are editor-only and non-colliding. Relay and Drainage have
    # dedicated topology actors above, so avoid duplicate anchor markers for them.
    count = 0
    for name in ("Residential", "Park", "School", "Gym", "Greenhouses"):
        x, y, z = POI_ANCHORS[name]
        spawn_box(
            mesh,
            label=f"ZS_Spring_POI_{name}",
            stable_id=f"Spring.POI.{name}",
            center=(x, y, max(SPRING_GROUND_Z, z) + 900.0),
            size=(120.0, 120.0, 1800.0),
            folder="ZombieSeasons/Spring/POI/Anchors",
            collision=False,
            gameplay_marker=True,
            editor_only=True,
        )
        count += 1
    return count


def save_level() -> None:
    if not get_level_subsystem().save_current_level():
        fail("Spring actors were generated but the greybox level could not be saved.")


def position_viewport() -> None:
    try:
        subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        if subsystem is not None:
            subsystem.set_level_viewport_camera_info(
                unreal.Vector(-50000.0, 18000.0, 42000.0),
                unreal.Rotator(roll=0.0, pitch=-42.0, yaw=90.0),
            )
    except Exception as error:
        warn(f"Unable to position viewport for Spring review: {error}")


def run() -> None:
    preflight()
    log("Stage 3 preflight passed. Creating deterministic Spring greybox.")

    mesh = unreal.load_asset(ENGINE_CUBE)
    if mesh is None:
        fail(f"Engine cube disappeared after preflight: {ENGINE_CUBE}")

    sentinel_count = create_stage_sentinel(mesh)
    road_count = create_roads(mesh)
    shortcut_count = create_shortcuts(mesh)
    residential_count = create_residential(mesh)
    park_count = create_park(mesh)
    school_count = create_school(mesh)
    gym_count = create_gym_arena(mesh)
    greenhouse_count = create_greenhouses(mesh)
    drainage_count = create_drainage_entrance(mesh)
    relay_count = create_relay_landmark(mesh)
    poi_marker_count = create_poi_anchor_markers(mesh)

    expected = (
        sentinel_count
        + road_count
        + shortcut_count
        + residential_count
        + park_count
        + school_count
        + gym_count
        + greenhouse_count
        + drainage_count
        + relay_count
        + poi_marker_count
    )
    generated = stage_actors(STAGE)
    if len(generated) != expected:
        fail(
            "Spring generation count mismatch before save: "
            f"expected {expected}, found {len(generated)} loaded tagged actors."
        )

    save_level()
    position_viewport()

    report = write_json_report(
        "spring_generation.json",
        {
            "status": "PASS",
            "stage": STAGE,
            "mode": MODE,
            "map": GREYBOX_MAP,
            "generated_actor_count": len(generated),
            "road_surface_count": road_count,
            "shortcut_route_count": shortcut_count,
            "residential_actor_count": residential_count,
            "park_actor_count": park_count,
            "school_actor_count": school_count,
            "gym_actor_count": gym_count,
            "greenhouse_actor_count": greenhouse_count,
            "drainage_actor_count": drainage_count,
            "relay_actor_count": relay_count,
            "poi_anchor_marker_count": poi_marker_count,
            "required_shortcuts": [item[0] for item in SHORTCUT_SEGMENTS],
            "gym_target_footprint_m": [60, 55],
            "gym_exit_topology": "2 mandatory ground exits + 1 unlockable gallery route",
            "objective_adapter_created": False,
            "zombie_spawn_markers_created": False,
            "loot_markers_created": False,
            "final_art_assets_loaded": False,
            "historical_maps_modified": False,
        },
    )

    summary = (
        "Spring greybox generation PASSED.\n\n"
        f"Map: {GREYBOX_MAP}\n"
        f"Generated Spring actors: {len(generated)}\n"
        f"Playable roads: {road_count}\n"
        f"Required shortcuts: {shortcut_count}\n"
        f"School actors: {school_count}\n"
        f"Gym arena actors: {gym_count}\n"
        f"Residential masses: {residential_count}\n"
        f"Park actors: {park_count}\n"
        f"Greenhouses: {greenhouse_count}\n"
        f"POI anchor markers: {poi_marker_count}\n\n"
        "Zombie spawns, loot and runtime objective adapters remain deferred to Stage 9.\n"
        "No final Fab/City Sample art was loaded.\n"
        f"Report:\n{report}"
    )
    log(summary.replace("\n", " "))
    show_editor_message("ZombieSeasons World Generation — Stage 3", summary)


if __name__ == "__main__":
    run()
