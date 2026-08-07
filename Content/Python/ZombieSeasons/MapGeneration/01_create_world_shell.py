"""Create the non-destructive ZombieSeasons partitioned greybox world shell.

Run from Unreal Editor only after 00_validate_environment.py passes:

py "C:/Users/malik/Documents/Unreal Projects/ZombieSeasons/Content/Python/ZombieSeasons/MapGeneration/01_create_world_shell.py"

The script creates /Game/ZombieSeasons/Maps/Development/L_ZS_World_Greybox
as a blank World Partition level, creates the required Data Layers, lays out the
frozen world/district bounds and elevation baselines, and adds editor-only road
graph placeholders. It never touches the historical reference maps.
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
    PLAYABLE_MAX_X,
    PLAYABLE_MAX_Y,
    PLAYABLE_MIN_X,
    PLAYABLE_MIN_Y,
    add_generation_tags,
    editor_asset_exists,
    fail,
    log,
    show_editor_message,
    warn,
    write_json_report,
)


STAGE = "WorldShell"
MODE = "CREATE"
ENGINE_CUBE = "/Engine/BasicShapes/Cube.Cube"
RUNTIME_GRID_CELL_SIZE_CM = 12800
RUNTIME_GRID_LOADING_RANGE_CM = 38400.0
GROUND_TILE_SIZE_CM = 17500.0
GROUND_THICKNESS_CM = 40.0
ROAD_GUIDE_Z_CM = 1600.0
ROAD_GUIDE_THICKNESS_CM = 35.0
BOUNDARY_GUIDE_Z_CM = 1100.0
BOUNDARY_GUIDE_WIDTH_CM = 80.0

DATA_LAYER_NAMES = (
    "DL_ZS_Greybox",
    "DL_ZS_Gameplay",
    "DL_ZS_FinalArt",
    "DL_ZS_Hub",
    "DL_ZS_Spring",
    "DL_ZS_Summer",
    "DL_ZS_Autumn",
    "DL_ZS_Winter",
    "DL_ZS_Sewers",
    "DL_ZS_Extraction",
)

# Frozen bounds from 07_Production_World_Specification.md.
DISTRICT_BOUNDS: dict[str, tuple[float, float, float, float, float]] = {
    "Hub": (-15000.0, 15000.0, -15000.0, 15000.0, 0.0),
    "Spring": (-85000.0, -15000.0, 15000.0, 85000.0, 200.0),
    "Summer": (15000.0, 85000.0, 15000.0, 85000.0, 0.0),
    "Autumn": (-85000.0, -15000.0, -85000.0, -15000.0, 300.0),
    "Winter": (15000.0, 85000.0, -85000.0, -15000.0, 500.0),
    "Extraction": (72000.0, 90000.0, -45000.0, -15000.0, 800.0),
}

DISTRICT_DATA_LAYERS = {
    "Hub": "DL_ZS_Hub",
    "Spring": "DL_ZS_Spring",
    "Summer": "DL_ZS_Summer",
    "Autumn": "DL_ZS_Autumn",
    "Winter": "DL_ZS_Winter",
    "Extraction": "DL_ZS_Extraction",
    "Shared": None,
}

# Stage-1 road topology placeholders only. Actual road surfaces are created by
# district stages after topology and traversal are validated.
ROAD_SEGMENTS: tuple[tuple[str, str, tuple[float, float], tuple[float, float], float], ...] = (
    # Rounded-square Hub ring.
    ("R_HUB_N", "Hub", (-7000.0, 10000.0), (7000.0, 10000.0), 1200.0),
    ("R_HUB_NE", "Hub", (7000.0, 10000.0), (10000.0, 7000.0), 1200.0),
    ("R_HUB_E", "Hub", (10000.0, 7000.0), (10000.0, -7000.0), 1200.0),
    ("R_HUB_SE", "Hub", (10000.0, -7000.0), (7000.0, -10000.0), 1200.0),
    ("R_HUB_S", "Hub", (7000.0, -10000.0), (-7000.0, -10000.0), 1200.0),
    ("R_HUB_SW", "Hub", (-7000.0, -10000.0), (-10000.0, -7000.0), 1200.0),
    ("R_HUB_W", "Hub", (-10000.0, -7000.0), (-10000.0, 7000.0), 1200.0),
    ("R_HUB_NW", "Hub", (-10000.0, 7000.0), (-7000.0, 10000.0), 1200.0),
    # Radial arterials.
    ("R_SPRING", "Spring", (-8000.0, 8000.0), (-45000.0, 45000.0), 1200.0),
    ("R_SUMMER", "Summer", (8000.0, 8000.0), (45000.0, 45000.0), 1200.0),
    ("R_AUTUMN", "Autumn", (-8000.0, -8000.0), (-45000.0, -45000.0), 1200.0),
    ("R_WINTER", "Winter", (8000.0, -8000.0), (45000.0, -45000.0), 1200.0),
    # Cross-city continuity.
    ("R_NORTH_CROSS", "Shared", (-60000.0, 60000.0), (60000.0, 60000.0), 700.0),
    ("R_SOUTH_CROSS", "Shared", (-60000.0, -60000.0), (60000.0, -60000.0), 700.0),
    ("R_WEST_SERVICE", "Shared", (-60000.0, 60000.0), (-60000.0, -60000.0), 500.0),
    ("R_EAST_SERVICE", "Shared", (60000.0, 60000.0), (60000.0, -60000.0), 500.0),
    ("R_EXTRACTION", "Extraction", (56000.0, -45000.0), (85000.0, -30000.0), 900.0),
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
        fail("Unable to resolve the current editor world.")
    return world


def check_dirty_maps() -> None:
    utility = getattr(unreal, "EditorLoadingAndSavingUtils", None)
    if utility is None:
        warn("EditorLoadingAndSavingUtils unavailable; dirty-map preflight skipped.")
        return
    dirty = list(utility.get_dirty_map_packages() or [])
    if dirty:
        package_names = [str(package.get_name()) for package in dirty]
        fail(
            "Unsaved map packages are open. Save or discard them before Stage 1: "
            + ", ".join(package_names)
        )


def preflight() -> None:
    if MODE != "CREATE":
        fail(f"Unsupported Stage-1 mode: {MODE}. This first pass supports CREATE only.")

    if editor_asset_exists(GREYBOX_MAP):
        fail(
            f"Refusing to overwrite existing greybox map: {GREYBOX_MAP}. "
            "Stage 1 is CREATE-only for the first production pass."
        )

    required_symbols = (
        "LevelEditorSubsystem",
        "EditorActorSubsystem",
        "UnrealEditorSubsystem",
        "StaticMeshActor",
        "DataLayerEditorSubsystem",
    )
    missing = [name for name in required_symbols if not hasattr(unreal, name)]
    if missing:
        fail("Required Unreal Python APIs missing: " + ", ".join(missing))

    level_subsystem = get_level_subsystem()
    if not hasattr(level_subsystem, "new_level"):
        fail("LevelEditorSubsystem.new_level is unavailable.")

    data_layer_subsystem = unreal.get_editor_subsystem(unreal.DataLayerEditorSubsystem)
    if data_layer_subsystem is None:
        fail("DataLayerEditorSubsystem is unavailable.")
    for method_name in (
        "create_data_layer",
        "rename_data_layer",
        "add_actor_to_data_layer",
        "get_data_layer_from_label",
    ):
        if not hasattr(data_layer_subsystem, method_name):
            fail(f"DataLayerEditorSubsystem.{method_name} is unavailable in this editor build.")

    if unreal.load_asset(ENGINE_CUBE) is None:
        fail(f"Required engine primitive is unavailable: {ENGINE_CUBE}")

    check_dirty_maps()


def set_actor_identity(
    actor: Any,
    *,
    label: str,
    district: str,
    stable_id: str,
    folder: str,
    editor_only: bool = False,
) -> None:
    try:
        actor.set_actor_label(label, mark_dirty=True)
    except TypeError:
        actor.set_actor_label(label)
    actor.set_folder_path(unreal.Name(folder))
    add_generation_tags(actor, stage=STAGE, district=district, stable_id=stable_id)
    try:
        actor.set_editor_property("is_spatially_loaded", True)
    except Exception as error:
        warn(f"Unable to mark {label} spatially loaded: {error}")
    if editor_only:
        try:
            actor.set_editor_property("is_editor_only_actor", True)
        except Exception as error:
            warn(f"Unable to mark {label} editor-only: {error}")


def set_static_mesh(actor: Any, mesh: Any) -> Any:
    component = actor.get_editor_property("static_mesh_component")
    if component is None or not component.set_static_mesh(mesh):
        fail(f"Unable to assign engine cube to actor {actor}")
    return component


def disable_collision(component: Any) -> None:
    try:
        component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    except Exception as error:
        warn(f"Unable to disable guide collision: {error}")


def create_partitioned_level() -> None:
    level_subsystem = get_level_subsystem()
    try:
        success = bool(level_subsystem.new_level(GREYBOX_MAP, True))
    except TypeError:
        fail(
            "This Unreal build does not expose LevelEditorSubsystem.new_level(asset_path, "
            "is_partitioned_world). UE 5.5 is required for the safe Stage-1 path."
        )
    if not success:
        fail(f"Unable to create partitioned greybox map: {GREYBOX_MAP}")


def configure_world_partition() -> tuple[bool, bool]:
    """Enable streaming and best-effort configure the documented runtime grid."""
    world = get_editor_world()
    world_settings = world.get_world_settings()
    if world_settings is None:
        fail("Current world has no WorldSettings actor.")

    partition = world_settings.get_editor_property("world_partition")
    if partition is None:
        fail("New map was not created with World Partition enabled.")

    streaming_configured = False
    try:
        partition.set_editor_property("enable_streaming", True)
        streaming_configured = True
    except Exception as error:
        warn(f"World Partition exists but streaming flag could not be set through Python: {error}")

    grid_configured = False
    try:
        runtime_hash = partition.get_editor_property("runtime_hash")
        if runtime_hash is None:
            raise RuntimeError("World Partition runtime_hash is None")

        grids = list(runtime_hash.get_editor_property("grids") or [])
        if grids:
            grid = grids[0]
        else:
            grid_class = getattr(unreal, "SpatialHashRuntimeGrid", None)
            if grid_class is None:
                raise RuntimeError("unreal.SpatialHashRuntimeGrid is unavailable")
            grid = grid_class()
            grids = [grid]

        grid.set_editor_property("grid_name", unreal.Name("MainGrid"))
        grid.set_editor_property("cell_size", RUNTIME_GRID_CELL_SIZE_CM)
        grid.set_editor_property("loading_range", RUNTIME_GRID_LOADING_RANGE_CM)
        grid.set_editor_property("priority", 0)
        grid.set_editor_property("block_on_slow_streaming", False)
        grids[0] = grid
        runtime_hash.set_editor_property("grids", grids)
        grid_configured = True
    except Exception as error:
        # UE 5.5 exposes World Partition creation reliably, but some runtime-hash
        # internals are not consistently reflected to Python across builds.
        warn(
            "World Partition runtime-grid values could not be persisted through the "
            f"current Python reflection API: {error}. Target remains cell=12800 cm, "
            "loading range=38400 cm and must be verified in World Settings before art pass."
        )

    return streaming_configured, grid_configured


def create_data_layers() -> dict[str, Any]:
    subsystem = unreal.get_editor_subsystem(unreal.DataLayerEditorSubsystem)
    if subsystem is None:
        fail("DataLayerEditorSubsystem unavailable after level creation.")

    created: dict[str, Any] = {}
    for name in DATA_LAYER_NAMES:
        existing = subsystem.get_data_layer_from_label(unreal.Name(name))
        if existing is not None:
            fail(f"Unexpected existing Data Layer in new map: {name}")

        data_layer = subsystem.create_data_layer(None)
        if data_layer is None:
            fail(f"Unable to create Data Layer: {name}")
        if not subsystem.rename_data_layer(data_layer, unreal.Name(name)):
            fail(f"Unable to rename Data Layer to: {name}")

        # These layers are intended to remain available in packaged greybox tests.
        runtime_type = getattr(getattr(unreal, "DataLayerType", None), "RUNTIME", None)
        if runtime_type is not None:
            try:
                data_layer.set_editor_property("data_layer_type", runtime_type)
            except Exception:
                pass
        try:
            data_layer.set_editor_property(
                "initial_runtime_state", unreal.DataLayerRuntimeState.ACTIVATED
            )
            data_layer.set_editor_property("is_initially_loaded_in_editor", True)
            data_layer.set_editor_property("is_initially_visible", True)
        except Exception as error:
            warn(f"Unable to set initial state for {name}: {error}")
        created[name] = data_layer

    return created


def add_actor_to_layers(actor: Any, layer_names: tuple[str, ...], layers: dict[str, Any]) -> None:
    subsystem = unreal.get_editor_subsystem(unreal.DataLayerEditorSubsystem)
    if subsystem is None:
        fail("DataLayerEditorSubsystem unavailable while assigning actors.")
    for name in layer_names:
        layer = layers.get(name)
        if layer is None:
            fail(f"Unknown Data Layer assignment requested: {name}")
        subsystem.add_actor_to_data_layer(actor, layer)


def spawn_box(
    mesh: Any,
    *,
    label: str,
    stable_id: str,
    district: str,
    center: tuple[float, float, float],
    size: tuple[float, float, float],
    yaw: float = 0.0,
    folder: str,
    layers: dict[str, Any],
    layer_names: tuple[str, ...],
    editor_only: bool = False,
    collision: bool = True,
) -> Any:
    actor = get_actor_subsystem().spawn_actor_from_class(
        unreal.StaticMeshActor,
        unreal.Vector(*center),
        unreal.Rotator(0.0, yaw, 0.0),
    )
    if actor is None:
        fail(f"Unable to spawn shell actor: {label}")
    component = set_static_mesh(actor, mesh)
    actor.set_actor_scale3d(
        unreal.Vector(size[0] / 100.0, size[1] / 100.0, size[2] / 100.0)
    )
    if not collision:
        disable_collision(component)
    set_actor_identity(
        actor,
        label=label,
        district=district,
        stable_id=stable_id,
        folder=folder,
        editor_only=editor_only,
    )
    add_actor_to_layers(actor, layer_names, layers)
    return actor


def tiled_ground(
    mesh: Any,
    district: str,
    bounds: tuple[float, float, float, float, float],
    layers: dict[str, Any],
) -> int:
    min_x, max_x, min_y, max_y, ground_z = bounds
    width = max_x - min_x
    depth = max_y - min_y

    columns = max(1, math.ceil(width / GROUND_TILE_SIZE_CM))
    rows = max(1, math.ceil(depth / GROUND_TILE_SIZE_CM))
    tile_w = width / columns
    tile_d = depth / rows
    count = 0

    district_layer = DISTRICT_DATA_LAYERS[district]
    layer_names = ("DL_ZS_Greybox", district_layer) if district_layer else ("DL_ZS_Greybox",)

    for row in range(rows):
        for column in range(columns):
            center_x = min_x + tile_w * (column + 0.5)
            center_y = min_y + tile_d * (row + 0.5)
            surface_z = ground_z
            center_z = surface_z - GROUND_THICKNESS_CM * 0.5
            stable_id = f"WorldShell.Ground.{district}.{row:02d}.{column:02d}"
            spawn_box(
                mesh,
                label=f"ZS_WS_Ground_{district}_{row:02d}_{column:02d}",
                stable_id=stable_id,
                district=district,
                center=(center_x, center_y, center_z),
                size=(tile_w, tile_d, GROUND_THICKNESS_CM),
                folder=f"ZombieSeasons/WorldShell/Ground/{district}",
                layers=layers,
                layer_names=layer_names,
            )
            count += 1
    return count


def spawn_outline(
    mesh: Any,
    *,
    name: str,
    district: str,
    bounds: tuple[float, float, float, float, float],
    layers: dict[str, Any],
) -> int:
    min_x, max_x, min_y, max_y, _ = bounds
    center_x = (min_x + max_x) * 0.5
    center_y = (min_y + max_y) * 0.5
    width = max_x - min_x
    depth = max_y - min_y
    z = BOUNDARY_GUIDE_Z_CM
    district_layer = DISTRICT_DATA_LAYERS.get(district)
    layer_names = ("DL_ZS_Greybox", district_layer) if district_layer else ("DL_ZS_Greybox",)

    edges = (
        ("N", (center_x, max_y, z), (width, BOUNDARY_GUIDE_WIDTH_CM, 60.0)),
        ("S", (center_x, min_y, z), (width, BOUNDARY_GUIDE_WIDTH_CM, 60.0)),
        ("E", (max_x, center_y, z), (BOUNDARY_GUIDE_WIDTH_CM, depth, 60.0)),
        ("W", (min_x, center_y, z), (BOUNDARY_GUIDE_WIDTH_CM, depth, 60.0)),
    )
    for suffix, center, size in edges:
        spawn_box(
            mesh,
            label=f"ZS_WS_Boundary_{name}_{suffix}",
            stable_id=f"WorldShell.Boundary.{name}.{suffix}",
            district=district,
            center=center,
            size=size,
            folder=f"ZombieSeasons/WorldShell/Boundaries/{name}",
            layers=layers,
            layer_names=layer_names,
            editor_only=True,
            collision=False,
        )
    return len(edges)


def spawn_road_guide(
    mesh: Any,
    *,
    road_id: str,
    district: str,
    start: tuple[float, float],
    end: tuple[float, float],
    width: float,
    layers: dict[str, Any],
) -> None:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.hypot(dx, dy)
    if length <= 0.0:
        fail(f"Road guide {road_id} has zero length.")
    yaw = math.degrees(math.atan2(dy, dx))
    center = ((start[0] + end[0]) * 0.5, (start[1] + end[1]) * 0.5, ROAD_GUIDE_Z_CM)

    district_layer = DISTRICT_DATA_LAYERS.get(district)
    layer_names = ("DL_ZS_Greybox", district_layer) if district_layer else ("DL_ZS_Greybox",)
    spawn_box(
        mesh,
        label=f"ZS_WS_RoadGuide_{road_id}",
        stable_id=f"WorldShell.Road.{road_id}",
        district=district,
        center=center,
        size=(length, width, ROAD_GUIDE_THICKNESS_CM),
        yaw=yaw,
        folder="ZombieSeasons/WorldShell/RoadGraph",
        layers=layers,
        layer_names=layer_names,
        editor_only=True,
        collision=False,
    )


def spawn_world_corner_markers(mesh: Any, layers: dict[str, Any]) -> int:
    points = (
        ("NW", PLAYABLE_MIN_X, PLAYABLE_MAX_Y),
        ("NE", PLAYABLE_MAX_X, PLAYABLE_MAX_Y),
        ("SE", PLAYABLE_MAX_X, PLAYABLE_MIN_Y),
        ("SW", PLAYABLE_MIN_X, PLAYABLE_MIN_Y),
    )
    for name, x, y in points:
        spawn_box(
            mesh,
            label=f"ZS_WS_WorldCorner_{name}",
            stable_id=f"WorldShell.WorldCorner.{name}",
            district="Shared",
            center=(x, y, 1500.0),
            size=(250.0, 250.0, 3000.0),
            folder="ZombieSeasons/WorldShell/WorldBounds",
            layers=layers,
            layer_names=("DL_ZS_Greybox",),
            editor_only=True,
            collision=False,
        )
    return len(points)


def save_level() -> None:
    if not get_level_subsystem().save_current_level():
        fail("World shell was generated but the greybox level could not be saved.")


def position_viewport() -> None:
    try:
        subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        if subsystem is not None:
            subsystem.set_level_viewport_camera_info(
                unreal.Vector(0.0, 0.0, 190000.0),
                unreal.Rotator(-90.0, 0.0, 0.0),
            )
    except Exception as error:
        warn(f"Unable to reposition viewport for world-shell review: {error}")


def run() -> None:
    preflight()
    log("Stage 1 preflight passed. Creating blank partitioned greybox level.")

    create_partitioned_level()
    streaming_configured, grid_configured = configure_world_partition()
    layers = create_data_layers()
    cube_mesh = unreal.load_asset(ENGINE_CUBE)
    if cube_mesh is None:
        fail(f"Engine cube disappeared after map creation: {ENGINE_CUBE}")

    ground_count = 0
    boundary_count = 0
    for district, bounds in DISTRICT_BOUNDS.items():
        ground_count += tiled_ground(cube_mesh, district, bounds, layers)
        boundary_count += spawn_outline(
            cube_mesh,
            name=district,
            district=district,
            bounds=bounds,
            layers=layers,
        )

    # Full playable world envelope, separate from district ownership bounds.
    world_bounds = (
        PLAYABLE_MIN_X,
        PLAYABLE_MAX_X,
        PLAYABLE_MIN_Y,
        PLAYABLE_MAX_Y,
        0.0,
    )
    boundary_count += spawn_outline(
        cube_mesh,
        name="PlayableWorld",
        district="Shared",
        bounds=world_bounds,
        layers=layers,
    )
    corner_count = spawn_world_corner_markers(cube_mesh, layers)

    for road_id, district, start, end, width in ROAD_SEGMENTS:
        spawn_road_guide(
            cube_mesh,
            road_id=road_id,
            district=district,
            start=start,
            end=end,
            width=width,
            layers=layers,
        )

    save_level()
    position_viewport()

    report = write_json_report(
        "world_shell_generation.json",
        {
            "status": "PASS",
            "stage": STAGE,
            "mode": MODE,
            "map": GREYBOX_MAP,
            "world_partition_created": True,
            "runtime_streaming_configured": streaming_configured,
            "runtime_grid_python_configured": grid_configured,
            "runtime_grid_target_cell_size_cm": RUNTIME_GRID_CELL_SIZE_CM,
            "runtime_grid_target_loading_range_cm": RUNTIME_GRID_LOADING_RANGE_CM,
            "data_layers": list(DATA_LAYER_NAMES),
            "ground_tile_count": ground_count,
            "boundary_guide_count": boundary_count,
            "world_corner_marker_count": corner_count,
            "road_guide_count": len(ROAD_SEGMENTS),
            "final_art_assets_loaded": False,
            "historical_maps_modified": False,
        },
    )

    warnings = 0 if grid_configured else 1
    summary = (
        "World shell generation PASSED.\n\n"
        f"Map: {GREYBOX_MAP}\n"
        f"Ground tiles: {ground_count}\n"
        f"Road guides: {len(ROAD_SEGMENTS)}\n"
        f"Data Layers: {len(DATA_LAYER_NAMES)}\n"
        f"Warnings requiring review: {warnings}\n\n"
        f"Report:\n{report}"
    )
    log(summary.replace("\n", " "))
    show_editor_message("ZombieSeasons World Generation — Stage 1", summary)


if __name__ == "__main__":
    run()
