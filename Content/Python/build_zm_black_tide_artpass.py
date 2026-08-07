import random
import unreal
from dataclasses import dataclass
from typing import Iterable, Optional, Sequence, Tuple


# ============================================================================
# ZombieSeasons - ZM Black Tide Art Pass
# Non-destructive environment dressing for Unreal Engine 5.5.x
# ============================================================================

SOURCE_MAP = "/Game/TopDownShooter/Maps/ZM_BlackTide_Greybox"
DESTINATION_MAP = "/Game/TopDownShooter/Maps/ZM_BlackTide_ArtPass"
MAIN_MAP = "/Game/TopDownShooter/Maps/MainMap"
SEED = 24071996

ROOT = "/Game/TopDownShooter/Ressources/StarterContent"

ASSET_PATHS = {
    "wall_400x400": f"{ROOT}/Architecture/Wall_400x400",
    "wall_door_400x400": f"{ROOT}/Architecture/Wall_Door_400x400",
    "wall_window_400x400": f"{ROOT}/Architecture/Wall_Window_400x400",
    "floor_400x400": f"{ROOT}/Architecture/Floor_400x400",
    "pillar_50x500": f"{ROOT}/Architecture/Pillar_50x500",
    "chair": f"{ROOT}/Props/SM_Chair",
    "couch": f"{ROOT}/Props/SM_Couch",
    "door": f"{ROOT}/Props/SM_Door",
    "door_frame": f"{ROOT}/Props/SM_DoorFrame",
    "glass_window": f"{ROOT}/Props/SM_GlassWindow",
    "lamp_ceiling": f"{ROOT}/Props/SM_Lamp_Ceiling",
    "lamp_wall": f"{ROOT}/Props/SM_Lamp_Wall",
    "pillar_frame": f"{ROOT}/Props/SM_PillarFrame",
    "pillar_frame_300": f"{ROOT}/Props/SM_PillarFrame300",
    "rock": f"{ROOT}/Props/SM_Rock",
    "shelf": f"{ROOT}/Props/SM_Shelf",
    "stairs": f"{ROOT}/Props/SM_Stairs",
    "statue": f"{ROOT}/Props/SM_Statue",
    "table": f"{ROOT}/Props/SM_TableRound",
    "window_frame": f"{ROOT}/Props/SM_WindowFrame",
    "cube": f"{ROOT}/Shapes/Shape_Cube",
    "cylinder": f"{ROOT}/Shapes/Shape_Cylinder",
    "plane": f"{ROOT}/Shapes/Shape_Plane",
    "pipe": f"{ROOT}/Shapes/Shape_Pipe",
    "pipe_90": f"{ROOT}/Shapes/Shape_Pipe_90",
    "pipe_180": f"{ROOT}/Shapes/Shape_Pipe_180",
    "torus": f"{ROOT}/Shapes/Shape_Torus",
    "concrete_grime": f"{ROOT}/Materials/M_Concrete_Grime",
    "concrete_panels": f"{ROOT}/Materials/M_Concrete_Panels",
    "concrete_poured": f"{ROOT}/Materials/M_Concrete_Poured",
    "brick_old": f"{ROOT}/Materials/M_Brick_Clay_Old",
    "brick_cut": f"{ROOT}/Materials/M_Brick_Cut_Stone",
    "cobble_rough": f"{ROOT}/Materials/M_CobbleStone_Rough",
    "gravel": f"{ROOT}/Materials/M_Ground_Gravel",
    "moss": f"{ROOT}/Materials/M_Ground_Moss",
    "metal_rust": f"{ROOT}/Materials/M_Metal_Rust",
    "metal_steel": f"{ROOT}/Materials/M_Metal_Steel",
    "tech_panel": f"{ROOT}/Materials/M_Tech_Panel",
    "tech_hex": f"{ROOT}/Materials/M_Tech_Hex_Tile",
    "tech_pulse": f"{ROOT}/Materials/M_Tech_Hex_Tile_Pulse",
    "glass": f"{ROOT}/Materials/M_Glass",
    "wood_worn": f"{ROOT}/Materials/M_Wood_Floor_Walnut_Worn",
    "water_ocean": f"{ROOT}/Materials/M_Water_Ocean",
    "effect_fire": f"{ROOT}/Blueprints/Blueprint_Effect_Fire",
    "effect_smoke": f"{ROOT}/Blueprints/Blueprint_Effect_Smoke",
    "effect_sparks": f"{ROOT}/Blueprints/Blueprint_Effect_Sparks",
    "effect_steam": f"{ROOT}/Blueprints/Blueprint_Effect_Steam",
    "ceiling_light_bp": f"{ROOT}/Blueprints/Blueprint_CeilingLight",
    "wall_sconce_bp": f"{ROOT}/Blueprints/Blueprint_WallSconce",
    "wind_sound": f"{ROOT}/Audio/Starter_Wind05",
    "fire_sound": f"{ROOT}/Audio/Fire01_Cue",
    "steam_sound": f"{ROOT}/Audio/Steam01_Cue",
    "light_sound": f"{ROOT}/Audio/Light02_Cue",
}


@dataclass(frozen=True)
class Zone:
    name: str
    center: Tuple[float, float, float]
    size: Tuple[float, float, float]
    palette: Tuple[int, int, int]


ZONES = (
    Zone("SpawnPlaza", (0.0, 0.0, 0.0), (5200.0, 5200.0, 650.0), (255, 115, 45)),
    Zone("Theatre", (-9000.0, 3200.0, 0.0), (6000.0, 5200.0, 650.0), (200, 50, 35)),
    Zone("Clinic", (9000.0, 3200.0, 0.0), (6000.0, 5200.0, 650.0), (75, 170, 255)),
    Zone("NightMarket", (0.0, 10000.0, 0.0), (8200.0, 4400.0, 520.0), (210, 55, 180)),
    Zone("PowerStation", (0.0, -10200.0, 0.0), (8200.0, 5200.0, 720.0), (255, 145, 35)),
    Zone("UndergroundLab", (0.0, -16000.0, -1600.0), (8200.0, 6200.0, 600.0), (50, 180, 210)),
    Zone("SecretChamber", (6200.0, -16000.0, -1600.0), (3800.0, 3800.0, 620.0), (170, 45, 255)),
)


class ArtPassError(RuntimeError):
    """Raised when the art pass cannot continue safely."""


def log(message: str) -> None:
    """Write a progress message to the Unreal log."""
    unreal.log(f"[ZM Black Tide ArtPass] {message}")


def warn(message: str) -> None:
    """Write a non-fatal warning to the Unreal log."""
    unreal.log_warning(f"[ZM Black Tide ArtPass] {message}")


def fail(message: str) -> None:
    """Abort the operation with a controlled error."""
    unreal.log_error(f"[ZM Black Tide ArtPass] {message}")
    raise ArtPassError(message)


def show_message(title: str, message: str) -> None:
    """Display a modal message inside Unreal Editor."""
    unreal.EditorDialog.show_message(title, message, unreal.AppMsgType.OK)


def safe_set(obj: object, property_name: str, value: object) -> bool:
    """Set an editor property without stopping the complete art pass."""
    try:
        obj.set_editor_property(property_name, value)
        return True
    except Exception as error:
        object_name = (
            obj.get_name()
            if hasattr(obj, "get_name")
            else obj.__class__.__name__
        )
        warn(f"{object_name}.{property_name}: {error}")
        return False


def package_exists(path: str) -> bool:
    """Return whether an Unreal package exists."""
    folder = path.rsplit("/", 1)[0]

    try:
        assets = unreal.EditorAssetLibrary.list_assets(
            folder,
            recursive=False,
            include_folder=False,
        )
    except Exception as error:
        warn(f"Unable to inspect '{folder}': {error}")
        return False

    normalized = path.split(".", 1)[0]
    return any(asset.split(".", 1)[0] == normalized for asset in assets)


def load_asset(path: str, required: bool = True) -> Optional[unreal.Object]:
    """Load an Unreal asset by package path."""
    asset = unreal.EditorAssetLibrary.load_asset(path)

    if asset is None and required:
        fail(f"Required asset not found: {path}")

    return asset


def load_blueprint_class(path: str) -> Optional[type]:
    """Load a Blueprint generated class."""
    try:
        return unreal.EditorAssetLibrary.load_blueprint_class(path)
    except Exception as error:
        warn(f"Unable to load Blueprint class '{path}': {error}")
        return None


def configure_actor(
    actor: unreal.Actor,
    label: str,
    folder: str,
    tags: Optional[Iterable[str]] = None,
) -> unreal.Actor:
    """Apply stable editor metadata to an actor."""
    actor.set_actor_label(label)
    actor.set_folder_path(unreal.Name(folder))

    if tags:
        actor.set_editor_property(
            "tags",
            [unreal.Name(tag) for tag in tags],
        )

    return actor


def spawn_actor(
    actor_class: type,
    label: str,
    location: unreal.Vector,
    rotation: Optional[unreal.Rotator] = None,
    folder: str = "ZM_BlackTide_ArtPass",
    tags: Optional[Iterable[str]] = None,
) -> unreal.Actor:
    """Spawn a generic actor."""
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
        actor_class,
        location,
        rotation or unreal.Rotator(0.0, 0.0, 0.0),
    )

    if actor is None:
        fail(f"Unable to spawn actor '{label}'.")

    return configure_actor(actor, label, folder, tags)


def mesh_world_size(mesh: unreal.StaticMesh) -> unreal.Vector:
    """Return the native mesh size in centimeters."""
    bounds = mesh.get_bounds()
    extent = bounds.box_extent

    return unreal.Vector(
        max(extent.x * 2.0, 1.0),
        max(extent.y * 2.0, 1.0),
        max(extent.z * 2.0, 1.0),
    )


def spawn_mesh(
    label: str,
    mesh: unreal.StaticMesh,
    location: unreal.Vector,
    rotation: Optional[unreal.Rotator] = None,
    desired_size: Optional[unreal.Vector] = None,
    scale: Optional[unreal.Vector] = None,
    material: Optional[unreal.MaterialInterface] = None,
    folder: str = "ZM_BlackTide_ArtPass/Geometry",
    tags: Optional[Iterable[str]] = None,
    collision_enabled: bool = True,
) -> unreal.StaticMeshActor:
    """Spawn a static mesh with dimensions or direct scale."""
    actor = spawn_actor(
        unreal.StaticMeshActor,
        label,
        location,
        rotation,
        folder,
        tags,
    )

    component = actor.static_mesh_component
    component.set_static_mesh(mesh)

    if desired_size is not None:
        native_size = mesh_world_size(mesh)
        actor.set_actor_scale3d(
            unreal.Vector(
                desired_size.x / native_size.x,
                desired_size.y / native_size.y,
                desired_size.z / native_size.z,
            )
        )
    elif scale is not None:
        actor.set_actor_scale3d(scale)

    if material is not None:
        component.set_material(0, material)

    actor.set_actor_enable_collision(collision_enabled)
    return actor


def spawn_blueprint(
    asset_key: str,
    label: str,
    location: unreal.Vector,
    rotation: Optional[unreal.Rotator] = None,
    scale: Optional[unreal.Vector] = None,
    folder: str = "ZM_BlackTide_ArtPass/Effects",
    tags: Optional[Iterable[str]] = None,
) -> Optional[unreal.Actor]:
    """Spawn a Blueprint actor when its generated class is available."""
    actor_class = load_blueprint_class(ASSET_PATHS[asset_key])

    if actor_class is None:
        return None

    actor = spawn_actor(
        actor_class,
        label,
        location,
        rotation,
        folder,
        tags,
    )

    if scale is not None:
        actor.set_actor_scale3d(scale)

    return actor


def spawn_point_light(
    label: str,
    location: unreal.Vector,
    color: Tuple[int, int, int],
    intensity: float,
    radius: float,
    folder: str,
    cast_shadows: bool = True,
) -> unreal.PointLight:
    """Spawn a point light used as visual guidance."""
    actor = spawn_actor(
        unreal.PointLight,
        label,
        location,
        folder=folder,
        tags=("ZS_ArtLight",),
    )

    component = actor.get_component_by_class(unreal.PointLightComponent)

    if component is not None:
        safe_set(component, "light_color", unreal.Color(*color, 255))
        safe_set(component, "intensity", intensity)
        safe_set(component, "attenuation_radius", radius)
        safe_set(component, "cast_shadows", cast_shadows)
        safe_set(component, "source_radius", 12.0)

    return actor


def spawn_spot_light(
    label: str,
    location: unreal.Vector,
    rotation: unreal.Rotator,
    color: Tuple[int, int, int],
    intensity: float,
    radius: float,
    inner_angle: float,
    outer_angle: float,
    folder: str,
) -> unreal.SpotLight:
    """Spawn a spot light used for dramatic composition."""
    actor = spawn_actor(
        unreal.SpotLight,
        label,
        location,
        rotation,
        folder,
        ("ZS_ArtLight", "ZS_SpotLight"),
    )

    component = actor.get_component_by_class(unreal.SpotLightComponent)

    if component is not None:
        safe_set(component, "light_color", unreal.Color(*color, 255))
        safe_set(component, "intensity", intensity)
        safe_set(component, "attenuation_radius", radius)
        safe_set(component, "inner_cone_angle", inner_angle)
        safe_set(component, "outer_cone_angle", outer_angle)
        safe_set(component, "cast_shadows", True)

    return actor


def spawn_ambient_sound(
    label: str,
    location: unreal.Vector,
    sound_path: str,
    volume: float,
    radius: float,
    folder: str,
) -> Optional[unreal.AmbientSound]:
    """Spawn a looping ambient sound when the sound asset is available."""
    sound = load_asset(sound_path, required=False)

    if sound is None:
        return None

    actor = spawn_actor(
        unreal.AmbientSound,
        label,
        location,
        folder=folder,
        tags=("ZS_Ambience",),
    )

    component = actor.get_component_by_class(unreal.AudioComponent)

    if component is not None:
        safe_set(component, "sound", sound)
        safe_set(component, "volume_multiplier", volume)
        attenuation = component.get_editor_property("attenuation_settings")
        if attenuation is None:
            safe_set(component, "override_attenuation", True)
            settings = component.get_editor_property("attenuation_overrides")
            safe_set(settings, "falloff_distance", radius)
            safe_set(component, "attenuation_overrides", settings)

    return actor


def duplicate_source_map() -> None:
    """Duplicate the greybox into a separate non-destructive art-pass map."""
    if not package_exists(SOURCE_MAP):
        fail(f"Source map not found: {SOURCE_MAP}")

    if package_exists(DESTINATION_MAP):
        fail(
            f"The destination map already exists: {DESTINATION_MAP}\n"
            "Delete or rename it manually before running this script again."
        )

    current_world = unreal.get_editor_subsystem(
        unreal.UnrealEditorSubsystem
    ).get_editor_world()

    if current_world is not None:
        current_name = current_world.get_path_name().split(".", 1)[0]
        if current_name == SOURCE_MAP:
            fail(
                "Run the art pass while MainMap or another map is open. "
                "The source map must not be the currently loaded level."
            )

    duplicated = unreal.EditorAssetLibrary.duplicate_asset(
        SOURCE_MAP,
        DESTINATION_MAP,
    )

    if duplicated is None:
        fail("Unable to duplicate the greybox map.")

    if not unreal.EditorLevelLibrary.load_level(DESTINATION_MAP):
        fail("Unable to open the duplicated art-pass map.")


def build_asset_library() -> dict:
    """Load every mesh and material required by the art pass."""
    library = {}

    for key, path in ASSET_PATHS.items():
        if key.startswith("effect_") or key.endswith("_bp"):
            continue

        if key.endswith("_sound"):
            continue

        library[key] = load_asset(path, required=False)

    missing = [
        key
        for key, value in library.items()
        if value is None
    ]

    if missing:
        warn("Optional assets missing: " + ", ".join(sorted(missing)))

    return library


def add_world_shell(library: dict, rng: random.Random) -> None:
    """Build a dense skyline that hides every empty exterior view."""
    cube = library["cube"]
    concrete = library["concrete_grime"]
    brick = library["brick_old"]
    metal = library["metal_rust"]
    window = library["glass_window"]
    window_frame = library["window_frame"]

    if cube is None:
        fail("Shape_Cube is required for the skyline.")

    rings = (
        ("North", -11800.0, 15000.0, 24, 900.0, 0.0),
        ("South", -11800.0, -21800.0, 24, 900.0, 0.0),
    )

    for side, start_x, y, count, spacing, yaw in rings:
        for index in range(count):
            x = start_x + index * spacing
            width = rng.uniform(760.0, 1120.0)
            depth = rng.uniform(1100.0, 2200.0)
            height = rng.choice((1200.0, 1600.0, 2000.0, 2500.0, 3000.0))
            material = rng.choice((concrete, brick, metal))

            spawn_mesh(
                f"Skyline_{side}_{index:02d}",
                cube,
                unreal.Vector(x, y, height / 2.0 - 80.0),
                desired_size=unreal.Vector(width, depth, height),
                material=material,
                folder="ZM_BlackTide_ArtPass/Skyline",
                tags=("ZS_Skyline", "ZS_NonPlayable"),
            )

            if window is not None and window_frame is not None and index % 2 == 0:
                facade_y = y - depth / 2.0 - 8.0 if side == "North" else y + depth / 2.0 + 8.0
                facade_yaw = 0.0 if side == "South" else 180.0

                for floor_index in range(1, max(2, int(height // 500.0))):
                    spawn_mesh(
                        f"SkylineWindow_{side}_{index:02d}_{floor_index:02d}",
                        window_frame,
                        unreal.Vector(
                            x,
                            facade_y,
                            220.0 + floor_index * 430.0,
                        ),
                        unreal.Rotator(0.0, facade_yaw, 0.0),
                        scale=unreal.Vector(1.5, 1.0, 1.5),
                        material=metal,
                        folder="ZM_BlackTide_ArtPass/Skyline/Windows",
                        tags=("ZS_Window", "ZS_NonPlayable"),
                        collision_enabled=False,
                    )
                    spawn_mesh(
                        f"SkylineGlass_{side}_{index:02d}_{floor_index:02d}",
                        window,
                        unreal.Vector(
                            x,
                            facade_y - (4.0 if side == "North" else -4.0),
                            220.0 + floor_index * 430.0,
                        ),
                        unreal.Rotator(0.0, facade_yaw, 0.0),
                        scale=unreal.Vector(1.45, 1.0, 1.45),
                        material=library["glass"],
                        folder="ZM_BlackTide_ArtPass/Skyline/Windows",
                        tags=("ZS_Window", "ZS_NonPlayable"),
                        collision_enabled=False,
                    )

    for side, x in (("West", -15500.0), ("East", 15500.0)):
        for index in range(34):
            y = -20400.0 + index * 1000.0
            width = rng.uniform(1100.0, 2100.0)
            depth = rng.uniform(780.0, 1150.0)
            height = rng.choice((1100.0, 1500.0, 1900.0, 2400.0, 2900.0))
            material = rng.choice((concrete, brick, metal))

            spawn_mesh(
                f"Skyline_{side}_{index:02d}",
                cube,
                unreal.Vector(x, y, height / 2.0 - 80.0),
                desired_size=unreal.Vector(width, depth, height),
                material=material,
                folder="ZM_BlackTide_ArtPass/Skyline",
                tags=("ZS_Skyline", "ZS_NonPlayable"),
            )

    # Distant sea and horizon plane.
    if library["plane"] is not None and library["water_ocean"] is not None:
        spawn_mesh(
            "Environment_DistantOcean",
            library["plane"],
            unreal.Vector(0.0, 30000.0, -220.0),
            desired_size=unreal.Vector(80000.0, 50000.0, 10.0),
            material=library["water_ocean"],
            folder="ZM_BlackTide_ArtPass/Environment",
            tags=("ZS_Horizon", "ZS_NonPlayable"),
            collision_enabled=False,
        )


def add_roofs_and_facades(library: dict) -> None:
    """Close all main interiors and add readable facade architecture."""
    cube = library["cube"]
    wall = library["wall_400x400"]
    wall_window = library["wall_window_400x400"]
    wall_door = library["wall_door_400x400"]
    concrete = library["concrete_panels"]
    brick = library["brick_old"]
    metal = library["metal_rust"]

    roof_specs = (
        ("Theatre", -9000.0, 3200.0, 6000.0, 5200.0, 650.0, brick),
        ("Clinic", 9000.0, 3200.0, 6000.0, 5200.0, 650.0, concrete),
        ("PowerStation", 0.0, -10200.0, 8200.0, 5200.0, 720.0, metal),
        ("UndergroundLab", 0.0, -16000.0, 8200.0, 6200.0, -1000.0, metal),
        ("SecretChamber", 6200.0, -16000.0, 3800.0, 3800.0, -980.0, brick),
    )

    for name, x, y, sx, sy, z, material in roof_specs:
        spawn_mesh(
            f"Roof_{name}",
            cube,
            unreal.Vector(x, y, z),
            desired_size=unreal.Vector(sx + 120.0, sy + 120.0, 80.0),
            material=material,
            folder="ZM_BlackTide_ArtPass/Architecture/Roofs",
            tags=("ZS_Roof", f"Zone_{name}"),
        )

    facade_zones = (
        ("Theatre", -9000.0, 600.0, 6000.0, brick),
        ("Clinic", 9000.0, 600.0, 6000.0, concrete),
        ("PowerStation", 0.0, -7600.0, 8200.0, metal),
    )

    for name, center_x, y, width, material in facade_zones:
        module_count = max(1, int(width // 400.0))
        start_x = center_x - (module_count - 1) * 200.0

        for index in range(module_count):
            x = start_x + index * 400.0
            mesh = wall
            if index == module_count // 2:
                mesh = wall_door
            elif index % 3 == 0:
                mesh = wall_window

            if mesh is None:
                continue

            spawn_mesh(
                f"Facade_{name}_{index:02d}",
                mesh,
                unreal.Vector(x, y, 200.0),
                scale=unreal.Vector(1.0, 1.0, 1.0),
                material=material,
                folder=f"ZM_BlackTide_ArtPass/Architecture/Facades/{name}",
                tags=("ZS_Facade", f"Zone_{name}"),
            )


def add_street_structure(library: dict) -> None:
    """Add sidewalks, curbs, gates and street-level silhouette."""
    cube = library["cube"]
    concrete = library["concrete_poured"]
    cobble = library["cobble_rough"]
    metal = library["metal_rust"]

    sidewalk_specs = (
        ("WestNorth", -6500.0, 1550.0, 7800.0, 500.0),
        ("WestSouth", -6500.0, -1550.0, 7800.0, 500.0),
        ("EastNorth", 6500.0, 1550.0, 7800.0, 500.0),
        ("EastSouth", 6500.0, -1550.0, 7800.0, 500.0),
        ("NorthWest", -1550.0, 6200.0, 500.0, 7600.0),
        ("NorthEast", 1550.0, 6200.0, 500.0, 7600.0),
        ("SouthWest", -1550.0, -6500.0, 500.0, 7800.0),
        ("SouthEast", 1550.0, -6500.0, 500.0, 7800.0),
    )

    for name, x, y, sx, sy in sidewalk_specs:
        spawn_mesh(
            f"Sidewalk_{name}",
            cube,
            unreal.Vector(x, y, 15.0),
            desired_size=unreal.Vector(sx, sy, 30.0),
            material=cobble,
            folder="ZM_BlackTide_ArtPass/Architecture/Street",
            tags=("ZS_Sidewalk",),
        )

    gate_positions = (
        ("Theatre", -6500.0, 0.0, 90.0),
        ("Clinic", 6500.0, 0.0, 90.0),
        ("Market", 0.0, 6500.0, 0.0),
        ("Power", 0.0, -6500.0, 0.0),
    )

    for name, x, y, yaw in gate_positions:
        if library["pillar_frame_300"] is not None:
            for offset in (-330.0, 330.0):
                px = x + offset if yaw == 0.0 else x
                py = y if yaw == 0.0 else y + offset

                spawn_mesh(
                    f"GatePillar_{name}_{'A' if offset < 0 else 'B'}",
                    library["pillar_frame_300"],
                    unreal.Vector(px, py, 150.0),
                    unreal.Rotator(0.0, yaw, 0.0),
                    scale=unreal.Vector(1.3, 1.3, 1.4),
                    material=metal,
                    folder="ZM_BlackTide_ArtPass/Architecture/Gates",
                    tags=("ZS_Gate", f"Zone_{name}"),
                )

        spawn_spot_light(
            f"GateLight_{name}",
            unreal.Vector(x, y, 420.0),
            unreal.Rotator(-55.0, yaw, 0.0),
            (255, 130, 55) if name != "Clinic" else (80, 170, 255),
            5200.0,
            1600.0,
            18.0,
            42.0,
            "ZM_BlackTide_ArtPass/Lighting/Gates",
        )


def add_theatre_dressing(library: dict) -> None:
    """Dress the theatre as a dense, readable interior landmark."""
    chair = library["chair"]
    couch = library["couch"]
    table = library["table"]
    statue = library["statue"]
    shelf = library["shelf"]
    lamp = library["lamp_wall"]
    wood = library["wood_worn"]
    metal = library["metal_rust"]

    if chair is not None:
        for row in range(5):
            for column in range(9):
                if column == 4:
                    continue

                spawn_mesh(
                    f"TheatreSeat_{row:02d}_{column:02d}",
                    chair,
                    unreal.Vector(
                        -10600.0 + column * 400.0,
                        2100.0 + row * 430.0,
                        45.0,
                    ),
                    unreal.Rotator(0.0, 90.0, 0.0),
                    scale=unreal.Vector(1.0, 1.0, 1.0),
                    material=None,
                    folder="ZM_BlackTide_ArtPass/SetDress/Theatre/Seats",
                    tags=("ZS_Clutter", "Zone_Theatre"),
                )

    if couch is not None:
        for index, x in enumerate((-10800.0, -9000.0, -7200.0), start=1):
            spawn_mesh(
                f"TheatreLobbyCouch_{index:02d}",
                couch,
                unreal.Vector(x, 900.0, 55.0),
                unreal.Rotator(0.0, 180.0, 0.0),
                scale=unreal.Vector(1.1, 1.1, 1.1),
                folder="ZM_BlackTide_ArtPass/SetDress/Theatre/Lobby",
                tags=("ZS_Clutter", "Zone_Theatre"),
            )

    if table is not None:
        for index, x in enumerate((-10100.0, -7900.0), start=1):
            spawn_mesh(
                f"TheatreTable_{index:02d}",
                table,
                unreal.Vector(x, 4700.0, 50.0),
                scale=unreal.Vector(1.2, 1.2, 1.0),
                material=wood,
                folder="ZM_BlackTide_ArtPass/SetDress/Theatre/Stage",
                tags=("ZS_StoryProp", "Zone_Theatre"),
            )

    if statue is not None:
        spawn_mesh(
            "TheatreBrokenIdol",
            statue,
            unreal.Vector(-9000.0, 5000.0, 220.0),
            unreal.Rotator(0.0, 180.0, 0.0),
            scale=unreal.Vector(1.8, 1.8, 1.8),
            material=metal,
            folder="ZM_BlackTide_ArtPass/SetDress/Theatre/Stage",
            tags=("ZS_Landmark", "ZS_EasterEgg"),
        )

    if shelf is not None:
        for index, y in enumerate((1500.0, 3200.0, 4900.0), start=1):
            spawn_mesh(
                f"TheatreBackstageShelf_{index:02d}",
                shelf,
                unreal.Vector(-11600.0, y, 100.0),
                unreal.Rotator(0.0, 90.0, 0.0),
                scale=unreal.Vector(1.2, 1.2, 1.2),
                material=metal,
                folder="ZM_BlackTide_ArtPass/SetDress/Theatre/Backstage",
                tags=("ZS_Clutter", "Zone_Theatre"),
            )

    for index, y in enumerate((1200.0, 2600.0, 4000.0, 5400.0), start=1):
        spawn_blueprint(
            "wall_sconce_bp",
            f"TheatreSconce_{index:02d}",
            unreal.Vector(-11920.0, y, 330.0),
            unreal.Rotator(0.0, 90.0, 0.0),
            folder="ZM_BlackTide_ArtPass/Lighting/Theatre",
            tags=("ZS_ArtLight", "Zone_Theatre"),
        )

    spawn_blueprint(
        "effect_smoke",
        "TheatreStageSmoke",
        unreal.Vector(-9000.0, 5100.0, 120.0),
        scale=unreal.Vector(2.0, 2.0, 2.0),
        folder="ZM_BlackTide_ArtPass/Effects/Theatre",
        tags=("ZS_Ambience", "Zone_Theatre"),
    )


def add_clinic_dressing(library: dict) -> None:
    """Dress the clinic with wards, partitions and cold lighting."""
    shelf = library["shelf"]
    table = library["table"]
    chair = library["chair"]
    glass = library["glass_window"]
    window_frame = library["window_frame"]
    lamp = library["lamp_ceiling"]
    metal = library["metal_steel"]
    tech = library["tech_panel"]

    for row, y in enumerate((1850.0, 3200.0, 4550.0), start=1):
        for column, x in enumerate((7900.0, 9000.0, 10100.0), start=1):
            if shelf is not None:
                spawn_mesh(
                    f"ClinicBed_{row:02d}_{column:02d}",
                    shelf,
                    unreal.Vector(x, y, 70.0),
                    unreal.Rotator(0.0, 90.0, 90.0),
                    scale=unreal.Vector(1.3, 0.7, 1.0),
                    material=metal,
                    folder="ZM_BlackTide_ArtPass/SetDress/Clinic/Wards",
                    tags=("ZS_Clutter", "Zone_Clinic"),
                )

    if table is not None:
        spawn_mesh(
            "ClinicOperatingTable",
            table,
            unreal.Vector(10100.0, 4550.0, 75.0),
            scale=unreal.Vector(1.7, 1.0, 0.8),
            material=metal,
            folder="ZM_BlackTide_ArtPass/SetDress/Clinic/OperatingRoom",
            tags=("ZS_StoryProp", "Zone_Clinic"),
        )

    if chair is not None:
        for index, y in enumerate((1200.0, 1700.0, 2200.0, 2700.0), start=1):
            spawn_mesh(
                f"ClinicWaitingChair_{index:02d}",
                chair,
                unreal.Vector(7350.0, y, 45.0),
                unreal.Rotator(0.0, 0.0, 0.0),
                scale=unreal.Vector(1.0, 1.0, 1.0),
                folder="ZM_BlackTide_ArtPass/SetDress/Clinic/WaitingRoom",
                tags=("ZS_Clutter", "Zone_Clinic"),
            )

    if glass is not None and window_frame is not None:
        for index, y in enumerate((1700.0, 3200.0, 4700.0), start=1):
            spawn_mesh(
                f"ClinicWindowFrame_{index:02d}",
                window_frame,
                unreal.Vector(11980.0, y, 260.0),
                unreal.Rotator(0.0, 90.0, 0.0),
                scale=unreal.Vector(1.8, 1.0, 1.8),
                material=metal,
                folder="ZM_BlackTide_ArtPass/Architecture/ClinicWindows",
                tags=("ZS_Window", "Zone_Clinic"),
            )
            spawn_mesh(
                f"ClinicWindowGlass_{index:02d}",
                glass,
                unreal.Vector(11970.0, y, 260.0),
                unreal.Rotator(0.0, 90.0, 0.0),
                scale=unreal.Vector(1.75, 1.0, 1.75),
                material=library["glass"],
                folder="ZM_BlackTide_ArtPass/Architecture/ClinicWindows",
                tags=("ZS_Window", "Zone_Clinic"),
                collision_enabled=False,
            )

    for index, x in enumerate((7600.0, 9000.0, 10400.0), start=1):
        spawn_blueprint(
            "ceiling_light_bp",
            f"ClinicCeilingLight_{index:02d}",
            unreal.Vector(x, 3200.0, 590.0),
            folder="ZM_BlackTide_ArtPass/Lighting/Clinic",
            tags=("ZS_ArtLight", "Zone_Clinic"),
        )

    spawn_blueprint(
        "effect_sparks",
        "ClinicBrokenPanelSparks",
        unreal.Vector(11200.0, 5200.0, 260.0),
        scale=unreal.Vector(1.4, 1.4, 1.4),
        folder="ZM_BlackTide_ArtPass/Effects/Clinic",
        tags=("ZS_Ambience", "Zone_Clinic"),
    )


def add_market_dressing(library: dict, rng: random.Random) -> None:
    """Turn the market into a dense but readable traversal maze."""
    shelf = library["shelf"]
    table = library["table"]
    chair = library["chair"]
    cube = library["cube"]
    plane = library["plane"]
    rust = library["metal_rust"]
    wood = library["wood_worn"]
    moss = library["moss"]

    stall_positions = (
        (-3100.0, 8900.0, 0.0),
        (-1800.0, 10300.0, 90.0),
        (-200.0, 9000.0, 0.0),
        (1500.0, 10400.0, 90.0),
        (3100.0, 9000.0, 0.0),
        (-3100.0, 11100.0, 90.0),
        (3000.0, 11100.0, 90.0),
    )

    for index, (x, y, yaw) in enumerate(stall_positions, start=1):
        if shelf is not None:
            spawn_mesh(
                f"MarketShelf_{index:02d}",
                shelf,
                unreal.Vector(x, y, 90.0),
                unreal.Rotator(0.0, yaw, 0.0),
                scale=unreal.Vector(1.4, 1.0, 1.3),
                material=rust,
                folder="ZM_BlackTide_ArtPass/SetDress/Market/Stalls",
                tags=("ZS_Clutter", "Zone_NightMarket"),
            )

        if table is not None:
            spawn_mesh(
                f"MarketTable_{index:02d}",
                table,
                unreal.Vector(x + 260.0, y, 55.0),
                unreal.Rotator(0.0, yaw, 0.0),
                scale=unreal.Vector(0.9, 0.9, 0.9),
                material=wood,
                folder="ZM_BlackTide_ArtPass/SetDress/Market/Stalls",
                tags=("ZS_Clutter", "Zone_NightMarket"),
            )

        if plane is not None:
            spawn_mesh(
                f"MarketCanopy_{index:02d}",
                plane,
                unreal.Vector(x, y, 330.0),
                unreal.Rotator(0.0, yaw, 0.0),
                desired_size=unreal.Vector(1500.0, 900.0, 10.0),
                material=library["tech_pulse"] if index % 3 == 0 else moss,
                folder="ZM_BlackTide_ArtPass/Architecture/MarketCanopies",
                tags=("ZS_Canopy", "Zone_NightMarket"),
                collision_enabled=False,
            )

        color = (
            (255, 45, 150)
            if index % 3 == 0
            else (50, 220, 180)
            if index % 3 == 1
            else (255, 150, 45)
        )

        spawn_point_light(
            f"MarketNeon_{index:02d}",
            unreal.Vector(x, y, 300.0),
            color,
            2600.0,
            900.0,
            "ZM_BlackTide_ArtPass/Lighting/Market",
            cast_shadows=False,
        )

    if chair is not None:
        for index in range(12):
            spawn_mesh(
                f"MarketLooseChair_{index:02d}",
                chair,
                unreal.Vector(
                    rng.uniform(-3600.0, 3600.0),
                    rng.uniform(8500.0, 11600.0),
                    45.0,
                ),
                unreal.Rotator(0.0, rng.uniform(0.0, 360.0), 0.0),
                scale=unreal.Vector(1.0, 1.0, 1.0),
                folder="ZM_BlackTide_ArtPass/SetDress/Market/LooseProps",
                tags=("ZS_Clutter", "Zone_NightMarket"),
            )


def add_power_dressing(library: dict) -> None:
    """Add industrial machinery, pipes and live hazards."""
    cylinder = library["cylinder"]
    pipe = library["pipe"]
    pipe_90 = library["pipe_90"]
    pipe_180 = library["pipe_180"]
    torus = library["torus"]
    shelf = library["shelf"]
    rust = library["metal_rust"]
    steel = library["metal_steel"]
    pulse = library["tech_pulse"]

    for index, x in enumerate((-3000.0, 0.0, 3000.0), start=1):
        if cylinder is not None:
            spawn_mesh(
                f"PowerTurbine_{index:02d}",
                cylinder,
                unreal.Vector(x, -10200.0, 250.0),
                unreal.Rotator(0.0, 0.0, 0.0),
                desired_size=unreal.Vector(1050.0, 1050.0, 500.0),
                material=rust,
                folder="ZM_BlackTide_ArtPass/SetDress/Power/Machinery",
                tags=("ZS_Machinery", "Zone_PowerStation"),
            )

        if torus is not None:
            spawn_mesh(
                f"PowerTurbineRing_{index:02d}",
                torus,
                unreal.Vector(x, -10200.0, 520.0),
                unreal.Rotator(0.0, 0.0, 0.0),
                desired_size=unreal.Vector(850.0, 850.0, 180.0),
                material=pulse,
                folder="ZM_BlackTide_ArtPass/SetDress/Power/Machinery",
                tags=("ZS_Machinery", "ZS_EasterEgg"),
            )

    pipe_specs = (
        (-3600.0, -11800.0, 500.0, 0.0),
        (-1800.0, -11800.0, 500.0, 0.0),
        (1800.0, -11800.0, 500.0, 0.0),
        (3600.0, -11800.0, 500.0, 0.0),
    )

    for index, (x, y, z, yaw) in enumerate(pipe_specs, start=1):
        if pipe is not None:
            spawn_mesh(
                f"PowerPipe_{index:02d}",
                pipe,
                unreal.Vector(x, y, z),
                unreal.Rotator(0.0, yaw, 0.0),
                desired_size=unreal.Vector(350.0, 350.0, 1800.0),
                material=rust,
                folder="ZM_BlackTide_ArtPass/SetDress/Power/Pipes",
                tags=("ZS_Pipe", "Zone_PowerStation"),
            )

    spawn_blueprint(
        "effect_steam",
        "PowerSteamLeak",
        unreal.Vector(-3600.0, -11600.0, 350.0),
        scale=unreal.Vector(2.2, 2.2, 2.2),
        folder="ZM_BlackTide_ArtPass/Effects/Power",
        tags=("ZS_Ambience", "Zone_PowerStation"),
    )
    spawn_blueprint(
        "effect_sparks",
        "PowerLivePanel",
        unreal.Vector(3600.0, -11200.0, 360.0),
        scale=unreal.Vector(1.8, 1.8, 1.8),
        folder="ZM_BlackTide_ArtPass/Effects/Power",
        tags=("ZS_Ambience", "Zone_PowerStation"),
    )
    spawn_blueprint(
        "effect_fire",
        "PowerEmergencyFire",
        unreal.Vector(-2600.0, -8500.0, 100.0),
        scale=unreal.Vector(1.7, 1.7, 1.7),
        folder="ZM_BlackTide_ArtPass/Effects/Power",
        tags=("ZS_Ambience", "Zone_PowerStation"),
    )


def add_lab_dressing(library: dict) -> None:
    """Add containment architecture and secret visual language."""
    cube = library["cube"]
    glass = library["glass_window"]
    window_frame = library["window_frame"]
    shelf = library["shelf"]
    pipe = library["pipe"]
    torus = library["torus"]
    metal = library["metal_steel"]
    tech = library["tech_panel"]
    pulse = library["tech_pulse"]
    glass_material = library["glass"]

    for index, x in enumerate((-2500.0, 0.0, 2500.0), start=1):
        spawn_mesh(
            f"LabCellBase_{index:02d}",
            cube,
            unreal.Vector(x, -16000.0, -1450.0),
            desired_size=unreal.Vector(1500.0, 2000.0, 80.0),
            material=tech,
            folder="ZM_BlackTide_ArtPass/Architecture/LabCells",
            tags=("ZS_ContainmentCell", f"Cell_{index}"),
        )

        if window_frame is not None and glass is not None:
            spawn_mesh(
                f"LabCellFrame_{index:02d}",
                window_frame,
                unreal.Vector(x, -14980.0, -1250.0),
                unreal.Rotator(0.0, 0.0, 0.0),
                scale=unreal.Vector(3.0, 1.0, 2.2),
                material=metal,
                folder="ZM_BlackTide_ArtPass/Architecture/LabCells",
                tags=("ZS_ContainmentCell", f"Cell_{index}"),
            )
            spawn_mesh(
                f"LabCellGlass_{index:02d}",
                glass,
                unreal.Vector(x, -14970.0, -1250.0),
                unreal.Rotator(0.0, 0.0, 0.0),
                scale=unreal.Vector(2.9, 1.0, 2.1),
                material=glass_material,
                folder="ZM_BlackTide_ArtPass/Architecture/LabCells",
                tags=("ZS_ContainmentCell", f"Cell_{index}"),
                collision_enabled=False,
            )

        spawn_point_light(
            f"LabCellLight_{index:02d}",
            unreal.Vector(x, -16000.0, -1050.0),
            (45, 190, 230) if index != 2 else (80, 255, 160),
            3600.0,
            1200.0,
            "ZM_BlackTide_ArtPass/Lighting/Lab",
            cast_shadows=False,
        )

    if pipe is not None:
        for index, x in enumerate((-3400.0, -1700.0, 1700.0, 3400.0), start=1):
            spawn_mesh(
                f"LabCeilingPipe_{index:02d}",
                pipe,
                unreal.Vector(x, -16000.0, -1040.0),
                unreal.Rotator(90.0, 0.0, 0.0),
                desired_size=unreal.Vector(260.0, 260.0, 6000.0),
                material=metal,
                folder="ZM_BlackTide_ArtPass/SetDress/Lab/Pipes",
                tags=("ZS_Pipe", "Zone_UndergroundLab"),
            )

    if torus is not None:
        for index in range(3):
            spawn_mesh(
                f"SecretReactorRing_{index:02d}",
                torus,
                unreal.Vector(6200.0, -16000.0, -1250.0 + index * 230.0),
                unreal.Rotator(0.0, index * 25.0, 0.0),
                desired_size=unreal.Vector(
                    1700.0 - index * 250.0,
                    1700.0 - index * 250.0,
                    220.0,
                ),
                material=pulse,
                folder="ZM_BlackTide_ArtPass/SetDress/SecretChamber",
                tags=("ZS_EasterEgg", "ZS_ReactorRing"),
            )

    spawn_blueprint(
        "effect_steam",
        "LabSteamLeak",
        unreal.Vector(-3500.0, -17600.0, -1350.0),
        scale=unreal.Vector(1.6, 1.6, 1.6),
        folder="ZM_BlackTide_ArtPass/Effects/Lab",
        tags=("ZS_Ambience", "Zone_UndergroundLab"),
    )
    spawn_blueprint(
        "effect_sparks",
        "LabDamagedConsole",
        unreal.Vector(3500.0, -14400.0, -1320.0),
        scale=unreal.Vector(1.4, 1.4, 1.4),
        folder="ZM_BlackTide_ArtPass/Effects/Lab",
        tags=("ZS_Ambience", "Zone_UndergroundLab"),
    )


def add_plaza_and_street_clutter(library: dict, rng: random.Random) -> None:
    """Add controlled debris while preserving the main combat lanes."""
    rock = library["rock"]
    chair = library["chair"]
    shelf = library["shelf"]
    door = library["door"]
    table = library["table"]
    statue = library["statue"]
    metal = library["metal_rust"]
    concrete = library["concrete_grime"]

    if statue is not None:
        spawn_mesh(
            "PlazaMemorialStatue",
            statue,
            unreal.Vector(0.0, 0.0, 300.0),
            unreal.Rotator(0.0, 180.0, 0.0),
            scale=unreal.Vector(2.5, 2.5, 2.5),
            material=metal,
            folder="ZM_BlackTide_ArtPass/SetDress/Plaza",
            tags=("ZS_Landmark", "Zone_SpawnPlaza"),
        )

    clutter_centers = (
        (-4300.0, -1200.0),
        (-4300.0, 1200.0),
        (4300.0, -1200.0),
        (4300.0, 1200.0),
        (-1200.0, 4500.0),
        (1200.0, 4500.0),
        (-1200.0, -4700.0),
        (1200.0, -4700.0),
    )

    candidates = tuple(
        asset
        for asset in (rock, chair, shelf, door, table)
        if asset is not None
    )

    for cluster_index, (cx, cy) in enumerate(clutter_centers, start=1):
        for item_index in range(5):
            mesh = rng.choice(candidates)
            spawn_mesh(
                f"StreetClutter_{cluster_index:02d}_{item_index:02d}",
                mesh,
                unreal.Vector(
                    cx + rng.uniform(-320.0, 320.0),
                    cy + rng.uniform(-320.0, 320.0),
                    rng.uniform(35.0, 90.0),
                ),
                unreal.Rotator(
                    rng.uniform(-12.0, 12.0),
                    rng.uniform(0.0, 360.0),
                    rng.uniform(-12.0, 12.0),
                ),
                scale=unreal.Vector(
                    rng.uniform(0.8, 1.4),
                    rng.uniform(0.8, 1.4),
                    rng.uniform(0.8, 1.4),
                ),
                material=None,
                folder="ZM_BlackTide_ArtPass/SetDress/StreetClutter",
                tags=("ZS_Clutter",),
            )

    # Repeated street lamps provide navigation rhythm.
    lamp_positions = (
        (-5000.0, -1500.0, 90.0),
        (-5000.0, 1500.0, -90.0),
        (5000.0, -1500.0, 90.0),
        (5000.0, 1500.0, -90.0),
        (-1500.0, 5500.0, 0.0),
        (1500.0, 5500.0, 180.0),
        (-1500.0, -5500.0, 0.0),
        (1500.0, -5500.0, 180.0),
    )

    for index, (x, y, yaw) in enumerate(lamp_positions, start=1):
        spawn_blueprint(
            "wall_sconce_bp",
            f"StreetLamp_{index:02d}",
            unreal.Vector(x, y, 330.0),
            unreal.Rotator(0.0, yaw, 0.0),
            scale=unreal.Vector(1.4, 1.4, 1.4),
            folder="ZM_BlackTide_ArtPass/Lighting/Street",
            tags=("ZS_ArtLight",),
        )


def add_atmosphere_and_post_process() -> None:
    """Strengthen fog, exposure and cinematic contrast."""
    fog_actors = unreal.EditorLevelLibrary.get_all_level_actors()

    for actor in fog_actors:
        if isinstance(actor, unreal.ExponentialHeightFog):
            component = actor.get_component_by_class(
                unreal.ExponentialHeightFogComponent
            )
            if component is not None:
                safe_set(component, "fog_density", 0.035)
                safe_set(component, "fog_height_falloff", 0.18)
                safe_set(component, "volumetric_fog", True)
                safe_set(component, "volumetric_fog_extinction_scale", 2.0)

    post_process = spawn_actor(
        unreal.PostProcessVolume,
        "PostProcess_BlackTide",
        unreal.Vector(0.0, 0.0, 0.0),
        folder="ZM_BlackTide_ArtPass/PostProcess",
        tags=("ZS_PostProcess",),
    )
    safe_set(post_process, "unbound", True)
    safe_set(post_process, "blend_weight", 1.0)

    try:
        settings = post_process.get_editor_property("settings")
        safe_set(settings, "override_auto_exposure_method", True)
        safe_set(settings, "auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL)
        safe_set(settings, "override_auto_exposure_bias", True)
        safe_set(settings, "auto_exposure_bias", -0.7)
        safe_set(settings, "override_bloom_intensity", True)
        safe_set(settings, "bloom_intensity", 0.45)
        safe_set(settings, "override_vignette_intensity", True)
        safe_set(settings, "vignette_intensity", 0.42)
        safe_set(settings, "override_color_saturation", True)
        safe_set(
            settings,
            "color_saturation",
            unreal.Vector4(0.82, 0.88, 1.0, 1.0),
        )
        safe_set(post_process, "settings", settings)
    except Exception as error:
        warn(f"Post-process settings could not be fully configured: {error}")


def add_zone_lighting() -> None:
    """Create a coherent lighting identity for every major zone."""
    for zone in ZONES:
        x, y, z = zone.center
        r, g, b = zone.palette

        spawn_point_light(
            f"ZoneLight_{zone.name}_Key",
            unreal.Vector(x, y, z + 420.0),
            (r, g, b),
            5000.0 if zone.name != "SecretChamber" else 8500.0,
            2200.0,
            f"ZM_BlackTide_ArtPass/Lighting/{zone.name}",
        )

        spawn_spot_light(
            f"ZoneLight_{zone.name}_Back",
            unreal.Vector(x, y - 900.0, z + 600.0),
            unreal.Rotator(-55.0, 90.0, 0.0),
            (r, g, b),
            4200.0,
            1800.0,
            20.0,
            45.0,
            f"ZM_BlackTide_ArtPass/Lighting/{zone.name}",
        )


def add_ambient_audio() -> None:
    """Create a minimal environmental audio bed."""
    spawn_ambient_sound(
        "Ambient_Wind_North",
        unreal.Vector(0.0, 11000.0, 300.0),
        ASSET_PATHS["wind_sound"],
        0.35,
        14000.0,
        "ZM_BlackTide_ArtPass/Audio",
    )
    spawn_ambient_sound(
        "Ambient_Fire_Power",
        unreal.Vector(-2600.0, -8500.0, 100.0),
        ASSET_PATHS["fire_sound"],
        0.55,
        1800.0,
        "ZM_BlackTide_ArtPass/Audio",
    )
    spawn_ambient_sound(
        "Ambient_Steam_Lab",
        unreal.Vector(-3500.0, -17600.0, -1350.0),
        ASSET_PATHS["steam_sound"],
        0.45,
        1800.0,
        "ZM_BlackTide_ArtPass/Audio",
    )


def validate_result() -> Tuple[int, int]:
    """Return total actor count and art-pass actor count."""
    actors = unreal.EditorLevelLibrary.get_all_level_actors()
    art_pass_count = sum(
        1
        for actor in actors
        if str(actor.get_folder_path()).startswith("ZM_BlackTide_ArtPass")
    )
    return len(actors), art_pass_count


def save_and_focus() -> None:
    """Save the art-pass map and move the editor camera to an overview."""
    if not unreal.EditorLevelLibrary.save_current_level():
        fail("Unable to save the generated art-pass map.")

    try:
        unreal.EditorLevelLibrary.set_level_viewport_camera_info(
            unreal.Vector(22500.0, -25500.0, 18500.0),
            unreal.Rotator(-25.0, 138.0, 0.0),
        )
    except Exception as error:
        warn(f"Unable to position the viewport camera: {error}")

    try:
        unreal.EditorAssetLibrary.sync_browser_to_objects([DESTINATION_MAP])
    except Exception as error:
        warn(f"Unable to select the generated map: {error}")


def build_art_pass() -> None:
    """Build the complete non-destructive environment art pass."""
    rng = random.Random(SEED)

    log("Duplicating the source greybox.")
    duplicate_source_map()

    log("Loading project assets.")
    library = build_asset_library()

    log("Building skyline and world shell.")
    add_world_shell(library, rng)

    log("Closing interiors and building facades.")
    add_roofs_and_facades(library)

    log("Building street structure.")
    add_street_structure(library)

    log("Dressing the central plaza and streets.")
    add_plaza_and_street_clutter(library, rng)

    log("Dressing the theatre.")
    add_theatre_dressing(library)

    log("Dressing the clinic.")
    add_clinic_dressing(library)

    log("Dressing the night market.")
    add_market_dressing(library, rng)

    log("Dressing the power station.")
    add_power_dressing(library)

    log("Dressing the laboratory and secret chamber.")
    add_lab_dressing(library)

    log("Applying lighting and atmosphere.")
    add_zone_lighting()
    add_atmosphere_and_post_process()
    add_ambient_audio()

    total_count, art_pass_count = validate_result()
    save_and_focus()

    show_message(
        "ZombieSeasons - ZM Black Tide Art Pass",
        (
            "La map ZM_BlackTide_ArtPass a été créée sans modifier la greybox.\n\n"
            f"Acteurs totaux : {total_count}\n"
            f"Acteurs ajoutés par l'art pass : {art_pass_count}\n\n"
            "Contenu ajouté :\n"
            "- skyline complète et horizon fermé\n"
            "- toits, façades, trottoirs et portes visuelles\n"
            "- dressing détaillé par zone\n"
            "- éclairage coloré et brouillard renforcé\n"
            "- effets de feu, fumée, vapeur et étincelles\n"
            "- ambiance sonore localisée\n"
            "- post-traitement cinématique\n\n"
            "Map : /Game/TopDownShooter/Maps/ZM_BlackTide_ArtPass"
        ),
    )


try:
    build_art_pass()
except ArtPassError as error:
    show_message("ZM Black Tide Art Pass - Arrêt", str(error))
except Exception as error:
    unreal.log_error(f"[ZM Black Tide ArtPass] Unexpected error: {error}")
    show_message(
        "ZM Black Tide Art Pass - Erreur inattendue",
        (
            f"{error}\n\n"
            "Consulte le Journal de sortie pour identifier la ligne exacte."
        ),
    )