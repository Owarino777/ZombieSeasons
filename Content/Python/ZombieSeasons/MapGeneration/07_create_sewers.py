"""Create the deterministic ZombieSeasons sewer-network greybox.

Run from Unreal Editor only after Stage 6 Winter has passed and been committed:

py "C:/Users/malik/Documents/Unreal Projects/ZombieSeasons/Content/Python/ZombieSeasons/MapGeneration/07_create_sewers.py"

Stage 7 creates the frozen sewer junctions and a restrained traversal network beneath
Hub/Spring/Summer/Autumn/Winter. It deliberately creates geometry and deterministic
markers only. Runtime locks, objective state, zombie spawns, loot, and final art remain
deferred to later stages.
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


STAGE = "Sewers"
MODE = "CREATE"
ENGINE_CUBE = "/Engine/BasicShapes/Cube.Cube"

SEWER_FLOOR_Z = -700.0
FLOOR_THICKNESS = 24.0
CORRIDOR_WIDTH = 600.0
CORRIDOR_WALL_HEIGHT = 420.0
CORRIDOR_WALL_THICKNESS = 60.0
CORRIDOR_CEILING_THICKNESS = 40.0
CHAMBER_SIZE = 1600.0
CHAMBER_HEIGHT = 520.0
CHAMBER_WALL_THICKNESS = 70.0
ACCESS_WIDTH = 500.0
ACCESS_BARRIER_HEIGHT = 160.0
ACCESS_BARRIER_THICKNESS = 40.0

EDITOR_GREYBOX_LAYERS = (
    "DL_ZS_Greybox",
    "DL_ZS_Sewers",
)
EDITOR_GAMEPLAY_LAYERS = (
    "DL_ZS_Greybox",
    "DL_ZS_Gameplay",
    "DL_ZS_Sewers",
)

# Frozen sewer junctions from 07_Production_World_Specification.md.
SEWER_JUNCTIONS: dict[str, tuple[float, float, float]] = {
    "Hub": (0.0, -6000.0, -700.0),
    "Spring": (-40000.0, 18000.0, -700.0),
    "Summer": (28000.0, 20000.0, -700.0),
    "Autumn": (-28000.0, -25000.0, -700.0),
    "Winter": (26000.0, -40000.0, -700.0),
    "Control": (25000.0, -78000.0, -500.0),
}

# Main underground links. These keep the sewer a shortcut network rather than a
# second district. The four district junctions radiate from Hub; Winter continues
# south to the frozen control-room junction defined by the production specification.
NETWORK_LINKS: tuple[tuple[str, str, str], ...] = (
    ("Hub_Spring", "Hub", "Spring"),
    ("Hub_Summer", "Hub", "Summer"),
    ("Hub_Autumn", "Hub", "Autumn"),
    ("Hub_Winter", "Hub", "Winter"),
    ("Winter_Control", "Winter", "Control"),
)

# Surface-to-sewer access surfaces. Spring and Summer use their frozen district
# entrance anchors; Hub gets the initially available maintenance access. Winter's
# Stage-6 UtilityTunnel already terminates at the Control junction, so Stage 7 does
# not duplicate that surface route.
ACCESS_ROUTES: tuple[
    tuple[str, tuple[float, float, float], tuple[float, float, float]], ...
] = (
    ("HubMaintenance", (0.0, -500.0, -80.0), SEWER_JUNCTIONS["Hub"]),
    ("SpringDrainage", (-62000.0, 20000.0, -100.0), SEWER_JUNCTIONS["Spring"]),
    ("SummerStormDrain", (24000.0, 31000.0, -100.0), SEWER_JUNCTIONS["Summer"]),
)

# Runtime progression will later decide when these become traversable. Hub is the
# only segment intended to be open at initial onboarding.
LOCK_MARKERS: tuple[tuple[str, str, bool], ...] = (
    ("HubMaintenance", "Hub", True),
    ("SpringConnection", "Spring", False),
    ("SummerConnection", "Summer", False),
    ("AutumnConnection", "Autumn", False),
    ("WinterConnection", "Winter", False),
    ("ControlConnection", "Control", False),
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
            "Unsaved map packages are open. Save or discard them before Stage 7: "
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
        fail(f"Unsupported sewer generation mode: {MODE}")
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

    if actor_with_stable_id("Winter.StageSentinel") is None:
        fail("Stage 6 Winter checkpoint is unavailable. Do not generate sewers yet.")

    existing = stage_actors(STAGE)
    if existing:
        fail(
            f"Refusing to duplicate sewer generation: {len(existing)} Stage-7 actors "
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
    add_generation_tags(actor, stage=STAGE, district="Sewers", stable_id=stable_id)
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
        fail(f"Unable to spawn sewer actor: {label}")
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


def direction_transform(
    start: tuple[float, float, float],
    end: tuple[float, float, float],
) -> tuple[tuple[float, float, float], float, float, float]:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    dz = end[2] - start[2]
    horizontal = math.hypot(dx, dy)
    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    if length <= 0.0:
        fail(f"Zero-length sewer segment requested: start={start}, end={end}")
    yaw = math.degrees(math.atan2(dy, dx))
    pitch = math.degrees(math.atan2(dz, horizontal))
    center = (
        (start[0] + end[0]) * 0.5,
        (start[1] + end[1]) * 0.5,
        (start[2] + end[2]) * 0.5,
    )
    return center, length, yaw, pitch


def spawn_floor_segment(
    mesh: Any,
    *,
    label: str,
    stable_id: str,
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    width: float,
    folder: str,
) -> Any:
    center, length, yaw, pitch = direction_transform(start, end)
    return spawn_box(
        mesh,
        label=label,
        stable_id=stable_id,
        center=center,
        size=(length, width, FLOOR_THICKNESS),
        folder=folder,
        yaw=yaw,
        pitch=pitch,
    )


def spawn_flat_corridor(mesh: Any, link_id: str, start: tuple[float, float, float], end: tuple[float, float, float]) -> int:
    # Main sewer links are nearly flat. Floors/ceilings follow the tiny longitudinal
    # grade, while side walls remain vertical for robust collision and readable scale.
    folder = f"ZombieSeasons/Sewers/Corridors/{link_id}"
    center, length, yaw, pitch = direction_transform(start, end)
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    horizontal = math.hypot(dx, dy)
    if horizontal <= 0.0:
        fail(f"Sewer corridor has no horizontal run: {link_id}")

    floor_center = (center[0], center[1], center[2] + FLOOR_THICKNESS * 0.5)
    spawn_box(
        mesh,
        label=f"ZS_Sewer_{link_id}_Floor",
        stable_id=f"Sewer.Corridor.{link_id}.Floor",
        center=floor_center,
        size=(length, CORRIDOR_WIDTH, FLOOR_THICKNESS),
        folder=folder,
        yaw=yaw,
        pitch=pitch,
    )

    # Perpendicular offset in XY for the two vertical side walls.
    nx = -dy / horizontal
    ny = dx / horizontal
    wall_offset = CORRIDOR_WIDTH * 0.5 + CORRIDOR_WALL_THICKNESS * 0.5
    wall_center_z = center[2] + FLOOR_THICKNESS + CORRIDOR_WALL_HEIGHT * 0.5
    for side, sign in (("Left", -1.0), ("Right", 1.0)):
        spawn_box(
            mesh,
            label=f"ZS_Sewer_{link_id}_Wall_{side}",
            stable_id=f"Sewer.Corridor.{link_id}.Wall.{side}",
            center=(
                center[0] + nx * wall_offset * sign,
                center[1] + ny * wall_offset * sign,
                wall_center_z,
            ),
            size=(horizontal, CORRIDOR_WALL_THICKNESS, CORRIDOR_WALL_HEIGHT),
            folder=folder,
            yaw=yaw,
        )

    ceiling_z = center[2] + FLOOR_THICKNESS + CORRIDOR_WALL_HEIGHT + CORRIDOR_CEILING_THICKNESS * 0.5
    spawn_box(
        mesh,
        label=f"ZS_Sewer_{link_id}_Ceiling",
        stable_id=f"Sewer.Corridor.{link_id}.Ceiling",
        center=(center[0], center[1], ceiling_z),
        size=(horizontal, CORRIDOR_WIDTH + 2.0 * CORRIDOR_WALL_THICKNESS, CORRIDOR_CEILING_THICKNESS),
        folder=folder,
        yaw=yaw,
    )
    return 4


def wall_pair_with_gap(
    mesh: Any,
    *,
    prefix: str,
    side: str,
    center: tuple[float, float],
    axis: str,
    total_length: float,
    gap_width: float,
    ground_z: float,
    folder: str,
) -> int:
    segment_length = (total_length - gap_width) * 0.5
    if segment_length <= 0.0:
        fail(f"Invalid sewer chamber gap dimensions for {prefix}.{side}")
    offset = gap_width * 0.5 + segment_length * 0.5
    for suffix, sign in (("A", -1.0), ("B", 1.0)):
        if axis == "X":
            actor_center = (
                center[0] + sign * offset,
                center[1],
                ground_z + FLOOR_THICKNESS + CHAMBER_HEIGHT * 0.5,
            )
            size = (segment_length, CHAMBER_WALL_THICKNESS, CHAMBER_HEIGHT)
        else:
            actor_center = (
                center[0],
                center[1] + sign * offset,
                ground_z + FLOOR_THICKNESS + CHAMBER_HEIGHT * 0.5,
            )
            size = (CHAMBER_WALL_THICKNESS, segment_length, CHAMBER_HEIGHT)
        spawn_box(
            mesh,
            label=f"ZS_Sewer_{prefix}_{side}_{suffix}",
            stable_id=f"Sewer.Chamber.{prefix}.Wall.{side}.{suffix}",
            center=actor_center,
            size=size,
            folder=folder,
        )
    return 2


def create_stage_sentinel(mesh: Any) -> int:
    spawn_box(
        mesh,
        label="ZS_Sewer_StageSentinel",
        stable_id="Sewer.StageSentinel",
        center=(0.0, -6000.0, 4200.0),
        size=(80.0, 80.0, 80.0),
        folder="ZombieSeasons/Sewers/System",
        collision=False,
        persistent=True,
        editor_only=True,
    )
    return 1


def create_network_corridors(mesh: Any) -> int:
    count = 0
    for link_id, start_name, end_name in NETWORK_LINKS:
        count += spawn_flat_corridor(
            mesh,
            link_id,
            SEWER_JUNCTIONS[start_name],
            SEWER_JUNCTIONS[end_name],
        )
    return count


def create_junction_chambers(mesh: Any) -> int:
    count = 0
    half = CHAMBER_SIZE * 0.5
    for name, (x, y, z) in SEWER_JUNCTIONS.items():
        folder = f"ZombieSeasons/Sewers/Junctions/{name}"
        spawn_box(
            mesh,
            label=f"ZS_Sewer_Junction_{name}_Floor",
            stable_id=f"Sewer.Junction.{name}.Floor",
            center=(x, y, z + FLOOR_THICKNESS * 0.5),
            size=(CHAMBER_SIZE, CHAMBER_SIZE, FLOOR_THICKNESS),
            folder=folder,
        )
        count += 1

        # Each chamber has wide openings on all four sides. The corridor network can
        # therefore be art-passed/re-routed later without trapping the player.
        count += wall_pair_with_gap(
            mesh,
            prefix=name,
            side="North",
            center=(x, y + half),
            axis="X",
            total_length=CHAMBER_SIZE,
            gap_width=700.0,
            ground_z=z,
            folder=folder,
        )
        count += wall_pair_with_gap(
            mesh,
            prefix=name,
            side="South",
            center=(x, y - half),
            axis="X",
            total_length=CHAMBER_SIZE,
            gap_width=700.0,
            ground_z=z,
            folder=folder,
        )
        count += wall_pair_with_gap(
            mesh,
            prefix=name,
            side="West",
            center=(x - half, y),
            axis="Y",
            total_length=CHAMBER_SIZE,
            gap_width=700.0,
            ground_z=z,
            folder=folder,
        )
        count += wall_pair_with_gap(
            mesh,
            prefix=name,
            side="East",
            center=(x + half, y),
            axis="Y",
            total_length=CHAMBER_SIZE,
            gap_width=700.0,
            ground_z=z,
            folder=folder,
        )

        spawn_box(
            mesh,
            label=f"ZS_Sewer_Junction_{name}_Ceiling",
            stable_id=f"Sewer.Junction.{name}.Ceiling",
            center=(
                x,
                y,
                z + FLOOR_THICKNESS + CHAMBER_HEIGHT + CORRIDOR_CEILING_THICKNESS * 0.5,
            ),
            size=(CHAMBER_SIZE, CHAMBER_SIZE, CORRIDOR_CEILING_THICKNESS),
            folder=folder,
        )
        count += 1
    return count


def create_access_routes(mesh: Any) -> int:
    count = 0
    for access_id, start, end in ACCESS_ROUTES:
        folder = f"ZombieSeasons/Sewers/Access/{access_id}"
        floor = spawn_floor_segment(
            mesh,
            label=f"ZS_Sewer_Access_{access_id}_Floor",
            stable_id=f"Sewer.Access.{access_id}.Floor",
            start=start,
            end=end,
            width=ACCESS_WIDTH,
            folder=folder,
        )
        count += 1

        # Lightweight side barriers make steep/long greybox access surfaces readable
        # without pretending they are final staircases or tunnel architecture.
        center, length, yaw, _pitch = direction_transform(start, end)
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        horizontal = math.hypot(dx, dy)
        if horizontal > 0.0:
            nx = -dy / horizontal
            ny = dx / horizontal
            offset = ACCESS_WIDTH * 0.5 + ACCESS_BARRIER_THICKNESS * 0.5
            for side, sign in (("Left", -1.0), ("Right", 1.0)):
                spawn_box(
                    mesh,
                    label=f"ZS_Sewer_Access_{access_id}_Barrier_{side}",
                    stable_id=f"Sewer.Access.{access_id}.Barrier.{side}",
                    center=(
                        center[0] + nx * offset * sign,
                        center[1] + ny * offset * sign,
                        center[2] + 90.0,
                    ),
                    size=(horizontal, ACCESS_BARRIER_THICKNESS, ACCESS_BARRIER_HEIGHT),
                    folder=folder,
                    yaw=yaw,
                )
                count += 1

        # Add an editor-only access anchor so Stage 9 can replace greybox access with
        # the correct hatch/gate interaction without searching by geometry.
        spawn_box(
            mesh,
            label=f"ZS_Sewer_Access_{access_id}_Marker",
            stable_id=f"Sewer.Access.{access_id}.Marker",
            center=(start[0], start[1], start[2] + 160.0),
            size=(120.0, 120.0, 320.0),
            folder=folder,
            collision=False,
            gameplay_marker=True,
            editor_only=True,
        )
        count += 1
        _ = floor
    return count


def create_gameplay_markers(mesh: Any) -> int:
    count = 0
    for marker_name, junction_name, initially_open in LOCK_MARKERS:
        x, y, z = SEWER_JUNCTIONS[junction_name]
        stable_suffix = "InitiallyOpen" if initially_open else "InitiallyLocked"
        spawn_box(
            mesh,
            label=f"ZS_Sewer_Lock_{marker_name}_{stable_suffix}",
            stable_id=f"Sewer.Lock.{marker_name}",
            center=(x, y, z + 900.0),
            size=(120.0, 120.0, 1800.0),
            folder="ZombieSeasons/Sewers/Gameplay/Locks",
            collision=False,
            gameplay_marker=True,
            persistent=True,
            editor_only=True,
        )
        count += 1

    for name, (x, y, z) in SEWER_JUNCTIONS.items():
        spawn_box(
            mesh,
            label=f"ZS_Sewer_POI_{name}",
            stable_id=f"Sewer.POI.{name}",
            center=(x, y, z + 1200.0),
            size=(100.0, 100.0, 2400.0),
            folder="ZombieSeasons/Sewers/Gameplay/Junctions",
            collision=False,
            gameplay_marker=True,
            editor_only=True,
        )
        count += 1
    return count


def validate_topology() -> dict[str, float | int]:
    # Validate source-of-truth width/height constraints and useful summary metrics.
    if not 500.0 <= CORRIDOR_WIDTH <= 700.0:
        fail(f"Sewer corridor width violates frozen 500-700 cm contract: {CORRIDOR_WIDTH}")
    if not 1200.0 <= CHAMBER_SIZE <= 2000.0:
        fail(f"Sewer chamber size violates frozen 1200-2000 cm contract: {CHAMBER_SIZE}")

    total_network_length = 0.0
    longest_network_link = 0.0
    for _link_id, start_name, end_name in NETWORK_LINKS:
        start = SEWER_JUNCTIONS[start_name]
        end = SEWER_JUNCTIONS[end_name]
        length = math.dist(start, end)
        total_network_length += length
        longest_network_link = max(longest_network_link, length)

    max_access_grade = 0.0
    for _access_id, start, end in ACCESS_ROUTES:
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        dz = end[2] - start[2]
        horizontal = math.hypot(dx, dy)
        if horizontal <= 0.0:
            fail("Sewer access route has zero horizontal run.")
        max_access_grade = max(max_access_grade, abs(dz / horizontal) * 100.0)

    return {
        "network_link_count": len(NETWORK_LINKS),
        "junction_count": len(SEWER_JUNCTIONS),
        "surface_access_count": len(ACCESS_ROUTES),
        "total_network_length_cm": total_network_length,
        "longest_network_link_cm": longest_network_link,
        "max_access_grade_percent": max_access_grade,
    }


def save_level() -> None:
    if not get_level_subsystem().save_current_level():
        fail("Sewer actors were generated but the greybox level could not be saved.")


def position_viewport() -> None:
    try:
        subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        if subsystem is not None:
            subsystem.set_level_viewport_camera_info(
                unreal.Vector(0.0, -10000.0, 28000.0),
                unreal.Rotator(roll=0.0, pitch=-70.0, yaw=-90.0),
            )
    except Exception as error:
        warn(f"Unable to position viewport for sewer review: {error}")


def run() -> None:
    preflight()
    metrics = validate_topology()
    log("Stage 7 preflight passed. Creating deterministic sewer-network greybox.")

    mesh = unreal.load_asset(ENGINE_CUBE)
    if mesh is None:
        fail(f"Engine cube disappeared after preflight: {ENGINE_CUBE}")

    sentinel_count = create_stage_sentinel(mesh)
    corridor_actor_count = create_network_corridors(mesh)
    chamber_actor_count = create_junction_chambers(mesh)
    access_actor_count = create_access_routes(mesh)
    gameplay_marker_count = create_gameplay_markers(mesh)

    expected = (
        sentinel_count
        + corridor_actor_count
        + chamber_actor_count
        + access_actor_count
        + gameplay_marker_count
    )
    generated = stage_actors(STAGE)
    if len(generated) != expected:
        fail(
            "Sewer generation count mismatch before save: "
            f"expected {expected}, found {len(generated)} loaded tagged actors."
        )

    save_level()
    position_viewport()

    report = write_json_report(
        "sewer_generation.json",
        {
            "status": "PASS",
            "stage": STAGE,
            "mode": MODE,
            "map": GREYBOX_MAP,
            "generated_actor_count": len(generated),
            "corridor_actor_count": corridor_actor_count,
            "junction_chamber_actor_count": chamber_actor_count,
            "access_actor_count": access_actor_count,
            "gameplay_marker_count": gameplay_marker_count,
            "junctions": SEWER_JUNCTIONS,
            "network_links": [item[0] for item in NETWORK_LINKS],
            "surface_access_routes": [item[0] for item in ACCESS_ROUTES],
            "initially_open_connection": "HubMaintenance",
            "runtime_locks_created": False,
            "zombie_spawn_markers_created": False,
            "loot_markers_created": False,
            "final_art_assets_loaded": False,
            "historical_maps_modified": False,
            **metrics,
        },
    )

    summary = (
        "Sewer greybox generation PASSED.\n\n"
        f"Map: {GREYBOX_MAP}\n"
        f"Generated sewer actors: {len(generated)}\n"
        f"Frozen junctions: {len(SEWER_JUNCTIONS)}\n"
        f"Network links: {len(NETWORK_LINKS)}\n"
        f"Corridor geometry actors: {corridor_actor_count}\n"
        f"Junction-chamber actors: {chamber_actor_count}\n"
        f"Surface-access actors: {access_actor_count}\n"
        f"Gameplay markers: {gameplay_marker_count}\n"
        f"Total underground network length: {metrics['total_network_length_cm'] / 100.0:.1f} m\n"
        f"Maximum access grade: {metrics['max_access_grade_percent']:.2f}%\n\n"
        "Only HubMaintenance is intended to start unlocked. Runtime lock state, "
        "zombie spawns, loot and objective adapters remain deferred to Stage 9.\n"
        "No final Fab/City Sample art was loaded.\n"
        f"Report:\n{report}"
    )
    log(summary.replace("\n", " "))
    show_editor_message("ZombieSeasons World Generation — Stage 7", summary)


if __name__ == "__main__":
    run()
