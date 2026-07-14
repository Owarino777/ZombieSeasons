import unreal
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


# ============================================================================
# ZombieSeasons - ZM Black Tide
# Procedural greybox generator for Unreal Engine 5.5.x
# ============================================================================

MAP_FOLDER = "/Game/TopDownShooter/Maps"
MAP_NAME = "ZM_BlackTide_Greybox"
MAP_PATH = f"{MAP_FOLDER}/{MAP_NAME}"

CUBE_MESH_PATH = "/Engine/BasicShapes/Cube.Cube"
CYLINDER_MESH_PATH = "/Engine/BasicShapes/Cylinder.Cylinder"
SPHERE_MESH_PATH = "/Engine/BasicShapes/Sphere.Sphere"
BASIC_MATERIAL_PATH = "/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"
FPS_GAME_MODE_PATH = "/Game/TopDownShooter/Core/BP_FPSGameMode"

DEFAULT_PRIMITIVE_SIZE = 100.0
FLOOR_THICKNESS = 40.0
WALL_THICKNESS = 40.0
WALL_HEIGHT = 520.0
DOOR_HEIGHT = 300.0

MATERIAL_SEARCH_ROOTS = (
    "/Game/TopDownShooter/Ressources/StarterContent/Materials",
    "/Game/StarterContent/Materials",
)


class GenerationError(RuntimeError):
    """Raised when map generation cannot continue safely."""


def log(message: str) -> None:
    """Write an informational message to the Unreal log."""
    unreal.log(f"[ZM Black Tide] {message}")


def warn(message: str) -> None:
    """Write a warning message to the Unreal log."""
    unreal.log_warning(f"[ZM Black Tide] {message}")


def fail(message: str) -> None:
    """Abort generation with a controlled error."""
    unreal.log_error(f"[ZM Black Tide] {message}")
    raise GenerationError(message)


def show_dialog(title: str, message: str) -> None:
    """Display a modal message in Unreal Editor."""
    unreal.EditorDialog.show_message(title, message, unreal.AppMsgType.OK)


def safe_set(obj: unreal.Object, property_name: str, value: object) -> bool:
    """Set an editor property without aborting the complete generation."""
    try:
        obj.set_editor_property(property_name, value)
        return True
    except Exception as error:
        warn(
            f"Unable to set '{property_name}' on "
            f"'{obj.get_name()}': {error}"
        )
        return False


def package_path(asset_path: str) -> str:
    """Return an Unreal package path without the object suffix."""
    return asset_path.split(".", 1)[0]


def map_exists() -> bool:
    """Check whether the generated map already exists."""
    try:
        assets = unreal.EditorAssetLibrary.list_assets(
            MAP_FOLDER,
            recursive=False,
            include_folder=False,
        )
        return any(package_path(path) == MAP_PATH for path in assets)
    except Exception as error:
        warn(f"Unable to inspect map directory: {error}")
        return False


def load_required_asset(asset_path: str) -> unreal.Object:
    """Load a required asset or abort."""
    asset = unreal.EditorAssetLibrary.load_asset(asset_path)
    if asset is None:
        fail(f"Required asset not found: {asset_path}")
    return asset


def list_project_materials() -> List[str]:
    """List material assets from known project folders."""
    assets: List[str] = []

    for directory in MATERIAL_SEARCH_ROOTS:
        try:
            assets.extend(
                unreal.EditorAssetLibrary.list_assets(
                    directory,
                    recursive=True,
                    include_folder=False,
                )
            )
        except Exception as error:
            warn(f"Unable to scan '{directory}': {error}")

    return assets


def find_material(
    assets: Sequence[str],
    keyword_groups: Sequence[Sequence[str]],
    fallback: unreal.MaterialInterface,
) -> unreal.MaterialInterface:
    """Find a material using keywords, otherwise return the fallback."""
    indexed = [(path, path.lower()) for path in assets]

    for keywords in keyword_groups:
        lowered = tuple(keyword.lower() for keyword in keywords)

        for path, path_lower in indexed:
            if all(keyword in path_lower for keyword in lowered):
                asset = unreal.EditorAssetLibrary.load_asset(path)
                if isinstance(asset, unreal.MaterialInterface):
                    log(f"Material selected: {path}")
                    return asset

    return fallback


def configure_actor(
    actor: unreal.Actor,
    label: str,
    folder: str,
    tags: Optional[Iterable[str]] = None,
) -> unreal.Actor:
    """Apply label, folder and gameplay metadata."""
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
    folder: str = "ZM_BlackTide",
    tags: Optional[Iterable[str]] = None,
) -> unreal.Actor:
    """Spawn and configure an actor."""
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
        actor_class,
        location,
        rotation or unreal.Rotator(0.0, 0.0, 0.0),
    )

    if actor is None:
        fail(f"Unable to spawn '{label}'.")

    return configure_actor(actor, label, folder, tags)


def spawn_mesh(
    label: str,
    mesh: unreal.StaticMesh,
    location: unreal.Vector,
    size: unreal.Vector,
    material: unreal.MaterialInterface,
    rotation: Optional[unreal.Rotator] = None,
    folder: str = "ZM_BlackTide/Architecture",
    tags: Optional[Iterable[str]] = None,
    collision_enabled: bool = True,
) -> unreal.StaticMeshActor:
    """Spawn a static mesh actor using dimensions in centimeters."""
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
    component.set_material(0, material)

    actor.set_actor_scale3d(
        unreal.Vector(
            size.x / DEFAULT_PRIMITIVE_SIZE,
            size.y / DEFAULT_PRIMITIVE_SIZE,
            size.z / DEFAULT_PRIMITIVE_SIZE,
        )
    )
    actor.set_actor_enable_collision(collision_enabled)

    return actor


def spawn_box(
    label: str,
    cube_mesh: unreal.StaticMesh,
    location: unreal.Vector,
    size: unreal.Vector,
    material: unreal.MaterialInterface,
    rotation: Optional[unreal.Rotator] = None,
    folder: str = "ZM_BlackTide/Architecture",
    tags: Optional[Iterable[str]] = None,
    collision_enabled: bool = True,
) -> unreal.StaticMeshActor:
    """Spawn a box based on the engine cube mesh."""
    return spawn_mesh(
        label,
        cube_mesh,
        location,
        size,
        material,
        rotation,
        folder,
        tags,
        collision_enabled,
    )


def spawn_cylinder(
    label: str,
    cylinder_mesh: unreal.StaticMesh,
    location: unreal.Vector,
    diameter: float,
    height: float,
    material: unreal.MaterialInterface,
    folder: str,
    tags: Optional[Iterable[str]] = None,
) -> unreal.StaticMeshActor:
    """Spawn a cylinder based on diameter and height."""
    return spawn_mesh(
        label,
        cylinder_mesh,
        location,
        unreal.Vector(diameter, diameter, height),
        material,
        unreal.Rotator(0.0, 0.0, 0.0),
        folder,
        tags,
    )


def spawn_sphere(
    label: str,
    sphere_mesh: unreal.StaticMesh,
    location: unreal.Vector,
    diameter: float,
    material: unreal.MaterialInterface,
    folder: str,
    tags: Optional[Iterable[str]] = None,
) -> unreal.StaticMeshActor:
    """Spawn a sphere based on diameter."""
    return spawn_mesh(
        label,
        sphere_mesh,
        location,
        unreal.Vector(diameter, diameter, diameter),
        material,
        unreal.Rotator(0.0, 0.0, 0.0),
        folder,
        tags,
    )


def create_floor(
    name: str,
    cube_mesh: unreal.StaticMesh,
    center_x: float,
    center_y: float,
    size_x: float,
    size_y: float,
    material: unreal.MaterialInterface,
    z: float = 0.0,
) -> None:
    """Create a playable floor slab."""
    spawn_box(
        f"Floor_{name}",
        cube_mesh,
        unreal.Vector(center_x, center_y, z - FLOOR_THICKNESS / 2.0),
        unreal.Vector(size_x, size_y, FLOOR_THICKNESS),
        material,
        folder="ZM_BlackTide/Architecture/Floors",
        tags=("ZS_Floor", f"Zone_{name}"),
    )


def subtract_openings(
    full_length: float,
    openings: Sequence[Tuple[float, float]],
) -> List[Tuple[float, float]]:
    """Return solid intervals after subtracting openings."""
    half = full_length / 2.0
    cursor = -half
    result: List[Tuple[float, float]] = []

    normalized = sorted(
        (
            max(-half, offset - width / 2.0),
            min(half, offset + width / 2.0),
        )
        for offset, width in openings
    )

    for start, end in normalized:
        if start > cursor:
            result.append((cursor, start))
        cursor = max(cursor, end)

    if cursor < half:
        result.append((cursor, half))

    return result


def create_room_shell(
    name: str,
    cube_mesh: unreal.StaticMesh,
    center: unreal.Vector,
    size_x: float,
    size_y: float,
    height: float,
    material: unreal.MaterialInterface,
    openings: Optional[Dict[str, Sequence[Tuple[float, float]]]] = None,
    z_base: float = 0.0,
) -> None:
    """Create a rectangular room with doorway gaps."""
    openings = openings or {}
    folder = f"ZM_BlackTide/Architecture/Rooms/{name}"
    wall_z = z_base + height / 2.0

    for side in ("N", "S"):
        y = center.y + (size_y / 2.0 if side == "N" else -size_y / 2.0)

        for index, (start, end) in enumerate(
            subtract_openings(size_x, openings.get(side, ()))
        ):
            length = end - start
            x = center.x + (start + end) / 2.0

            spawn_box(
                f"Wall_{name}_{side}_{index:02d}",
                cube_mesh,
                unreal.Vector(x, y, wall_z),
                unreal.Vector(length, WALL_THICKNESS, height),
                material,
                folder=folder,
                tags=("ZS_Wall", f"Zone_{name}", f"Side_{side}"),
            )

    for side in ("E", "W"):
        x = center.x + (size_x / 2.0 if side == "E" else -size_x / 2.0)

        for index, (start, end) in enumerate(
            subtract_openings(size_y, openings.get(side, ()))
        ):
            length = end - start
            y = center.y + (start + end) / 2.0

            spawn_box(
                f"Wall_{name}_{side}_{index:02d}",
                cube_mesh,
                unreal.Vector(x, y, wall_z),
                unreal.Vector(WALL_THICKNESS, length, height),
                material,
                folder=folder,
                tags=("ZS_Wall", f"Zone_{name}", f"Side_{side}"),
            )


def create_door(
    name: str,
    cube_mesh: unreal.StaticMesh,
    location: unreal.Vector,
    size: unreal.Vector,
    material: unreal.MaterialInterface,
    cost: int,
    stage: int,
    secret: bool = False,
) -> None:
    """Create a tagged progression door placeholder."""
    tags = ["ZS_Door", f"Cost_{cost}", f"Stage_{stage}"]
    if secret:
        tags.append("ZS_SecretDoor")

    spawn_box(
        name,
        cube_mesh,
        location,
        size,
        material,
        folder="ZM_BlackTide/Gameplay/Doors",
        tags=tags,
    )


def create_marker(
    name: str,
    location: unreal.Vector,
    folder: str,
    tags: Iterable[str],
    yaw: float = 0.0,
) -> unreal.TargetPoint:
    """Create a tagged target point for future Blueprint systems."""
    return spawn_actor(
        unreal.TargetPoint,
        name,
        location,
        unreal.Rotator(0.0, yaw, 0.0),
        folder,
        tags,
    )


def create_point_light(
    name: str,
    location: unreal.Vector,
    color: unreal.Color,
    intensity: float,
    radius: float,
) -> None:
    """Create a zone guidance light."""
    actor = spawn_actor(
        unreal.PointLight,
        name,
        location,
        folder="ZM_BlackTide/Lighting/Local",
        tags=("ZS_GuidanceLight",),
    )

    component = actor.get_component_by_class(unreal.PointLightComponent)
    if component is None:
        return

    safe_set(component, "intensity", intensity)
    safe_set(component, "attenuation_radius", radius)
    safe_set(component, "light_color", color)
    safe_set(component, "cast_shadows", True)


def create_staircase(
    name: str,
    cube_mesh: unreal.StaticMesh,
    start: unreal.Vector,
    count: int,
    width: float,
    depth: float,
    height: float,
    direction: unreal.Vector,
    material: unreal.MaterialInterface,
) -> None:
    """Create a staircase from repeated box steps."""
    for index in range(count):
        spawn_box(
            f"Stair_{name}_{index:02d}",
            cube_mesh,
            unreal.Vector(
                start.x + direction.x * depth * index,
                start.y + direction.y * depth * index,
                start.z + height * index + height / 2.0,
            ),
            unreal.Vector(width, depth, abs(height)),
            material,
            folder=f"ZM_BlackTide/Architecture/Stairs/{name}",
            tags=("ZS_Stair",),
        )


def create_environment() -> None:
    """Create the night atmosphere."""
    moon = spawn_actor(
        unreal.DirectionalLight,
        "Lighting_Moon",
        unreal.Vector(0.0, 0.0, 8000.0),
        unreal.Rotator(-32.0, -28.0, 0.0),
        "ZM_BlackTide/Lighting",
        ("ZS_Moon",),
    )

    moon_component = moon.get_component_by_class(
        unreal.DirectionalLightComponent
    )
    if moon_component is not None:
        safe_set(moon_component, "intensity", 2.2)
        safe_set(
            moon_component,
            "light_color",
            unreal.Color(150, 175, 255, 255),
        )
        safe_set(moon_component, "atmosphere_sun_light", True)

    spawn_actor(
        unreal.SkyAtmosphere,
        "Lighting_SkyAtmosphere",
        unreal.Vector(0.0, 0.0, 0.0),
        folder="ZM_BlackTide/Lighting",
    )

    sky_light = spawn_actor(
        unreal.SkyLight,
        "Lighting_SkyLight",
        unreal.Vector(0.0, 0.0, 2500.0),
        folder="ZM_BlackTide/Lighting",
    )
    sky_component = sky_light.get_component_by_class(unreal.SkyLightComponent)
    if sky_component is not None:
        safe_set(sky_component, "intensity", 0.55)
        safe_set(sky_component, "real_time_capture", True)

    fog = spawn_actor(
        unreal.ExponentialHeightFog,
        "Lighting_HeightFog",
        unreal.Vector(0.0, 0.0, -300.0),
        folder="ZM_BlackTide/Lighting",
    )
    fog_component = fog.get_component_by_class(
        unreal.ExponentialHeightFogComponent
    )
    if fog_component is not None:
        safe_set(fog_component, "fog_density", 0.018)
        safe_set(fog_component, "fog_height_falloff", 0.22)
        safe_set(
            fog_component,
            "fog_inscattering_color",
            unreal.LinearColor(0.03, 0.06, 0.11, 1.0),
        )
        safe_set(fog_component, "volumetric_fog", True)


def create_layout(
    cube: unreal.StaticMesh,
    cylinder: unreal.StaticMesh,
    sphere: unreal.StaticMesh,
    concrete: unreal.MaterialInterface,
    brick: unreal.MaterialInterface,
    metal: unreal.MaterialInterface,
    floor_mat: unreal.MaterialInterface,
    accent: unreal.MaterialInterface,
) -> None:
    """Create the complete multi-zone layout."""

    # Main traversal network.
    create_floor("SpawnPlaza", cube, 0, 0, 5200, 5200, floor_mat)
    create_floor("WestStreet", cube, -6500, 0, 7800, 2200, concrete)
    create_floor("EastStreet", cube, 6500, 0, 7800, 2200, concrete)
    create_floor("NorthAvenue", cube, 0, 6200, 2400, 7600, concrete)
    create_floor("SouthServiceRoad", cube, 0, -6500, 2400, 7800, concrete)
    create_floor("Theatre", cube, -9000, 3200, 6000, 5200, floor_mat)
    create_floor("Clinic", cube, 9000, 3200, 6000, 5200, concrete)
    create_floor("NightMarket", cube, 0, 10000, 8200, 4400, concrete)
    create_floor("PowerStation", cube, 0, -10200, 8200, 5200, metal)
    create_floor("UndergroundLab", cube, 0, -16000, 8200, 6200, metal, -1600)
    create_floor("SecretChamber", cube, 6200, -16000, 3800, 3800, metal, -1600)

    # Major interiors.
    create_room_shell(
        "Theatre",
        cube,
        unreal.Vector(-9000, 3200, 0),
        6000,
        5200,
        650,
        brick,
        {"S": ((0, 520),), "E": ((-900, 500),), "N": ((900, 420),)},
    )

    create_room_shell(
        "Clinic",
        cube,
        unreal.Vector(9000, 3200, 0),
        6000,
        5200,
        650,
        concrete,
        {"S": ((0, 520),), "W": ((-900, 500),), "N": ((-900, 420),)},
    )

    create_room_shell(
        "PowerStation",
        cube,
        unreal.Vector(0, -10200, 0),
        8200,
        5200,
        720,
        metal,
        {"N": ((0, 600),), "S": ((0, 600),), "E": ((-900, 420),)},
    )

    create_room_shell(
        "UndergroundLab",
        cube,
        unreal.Vector(0, -16000, -1600),
        8200,
        6200,
        600,
        metal,
        {"N": ((0, 620),), "E": ((0, 520),)},
        -1600,
    )

    create_room_shell(
        "SecretChamber",
        cube,
        unreal.Vector(6200, -16000, -1600),
        3800,
        3800,
        620,
        brick,
        {"W": ((0, 520),)},
        -1600,
    )

    # Central landmark.
    spawn_cylinder(
        "Landmark_RitualBase",
        cylinder,
        unreal.Vector(0, 0, 100),
        1400,
        200,
        brick,
        "ZM_BlackTide/SetDress/Landmarks",
        ("ZS_Landmark", "ZS_Ritual"),
    )
    spawn_cylinder(
        "Landmark_RitualColumn",
        cylinder,
        unreal.Vector(0, 0, 420),
        500,
        640,
        metal,
        "ZM_BlackTide/SetDress/Landmarks",
        ("ZS_Landmark", "ZS_Ritual"),
    )
    spawn_sphere(
        "Landmark_AbyssCore",
        sphere,
        unreal.Vector(0, 0, 780),
        360,
        accent,
        "ZM_BlackTide/SetDress/Landmarks",
        ("ZS_EasterEgg", "ZS_AbyssCore"),
    )

    # Plaza cover.
    for index, (x, y, yaw) in enumerate(
        (
            (-1800, -1750, 45),
            (1800, -1750, -45),
            (-1800, 1750, -45),
            (1800, 1750, 45),
        ),
        start=1,
    ):
        spawn_box(
            f"Cover_Plaza_{index:02d}",
            cube,
            unreal.Vector(x, y, 90),
            unreal.Vector(900, 180, 180),
            concrete,
            unreal.Rotator(0.0, yaw, 0.0),
            "ZM_BlackTide/Architecture/Cover",
            ("ZS_Cover", "Zone_SpawnPlaza"),
        )

    # Theatre stage, balcony and upper route.
    spawn_box(
        "Theatre_Stage",
        cube,
        unreal.Vector(-9000, 5000, 110),
        unreal.Vector(3000, 900, 220),
        floor_mat,
        folder="ZM_BlackTide/Architecture/Rooms/Theatre",
        tags=("ZS_Landmark", "Zone_Theatre"),
    )
    spawn_box(
        "Theatre_Balcony",
        cube,
        unreal.Vector(-9000, 2200, 430),
        unreal.Vector(4300, 1200, 80),
        metal,
        folder="ZM_BlackTide/Architecture/Rooms/Theatre",
        tags=("ZS_UpperRoute", "Zone_Theatre"),
    )
    create_staircase(
        "TheatreWest",
        cube,
        unreal.Vector(-11200, 1700, 0),
        9,
        800,
        130,
        48,
        unreal.Vector(0.0, 1.0, 0.0),
        metal,
    )

    # Clinic interior.
    for index, y in enumerate((1900, 3200, 4500), start=1):
        spawn_box(
            f"Clinic_WardDivider_{index:02d}",
            cube,
            unreal.Vector(9000, y, 160),
            unreal.Vector(1800, 80, 320),
            concrete,
            folder="ZM_BlackTide/Architecture/Rooms/Clinic",
            tags=("ZS_InteriorWall", "Zone_Clinic"),
        )

    # Market maze.
    stalls = (
        (-2800, 9300, 0),
        (-900, 10400, 90),
        (1000, 9200, 0),
        (2900, 10400, 90),
        (-2800, 10800, 90),
        (2800, 9000, 0),
    )
    for index, (x, y, yaw) in enumerate(stalls, start=1):
        spawn_box(
            f"Market_Stall_{index:02d}",
            cube,
            unreal.Vector(x, y, 130),
            unreal.Vector(1300, 750, 260),
            brick if index % 2 else metal,
            unreal.Rotator(0.0, yaw, 0.0),
            "ZM_BlackTide/Architecture/Market",
            ("ZS_Cover", "Zone_NightMarket"),
        )
        spawn_box(
            f"Market_Canopy_{index:02d}",
            cube,
            unreal.Vector(x, y, 330),
            unreal.Vector(1450, 850, 40),
            accent,
            unreal.Rotator(0.0, yaw, 0.0),
            "ZM_BlackTide/Architecture/Market",
            ("ZS_Canopy",),
            False,
        )

    # Power station generators.
    for index, x in enumerate((-2500, 0, 2500), start=1):
        spawn_cylinder(
            f"Power_Generator_{index:02d}",
            cylinder,
            unreal.Vector(x, -10200, 230),
            900,
            460,
            metal,
            "ZM_BlackTide/SetDress/PowerStation",
            ("ZS_Generator", f"Generator_{index}"),
        )

    # Descent to the laboratory.
    create_staircase(
        "LabDescent",
        cube,
        unreal.Vector(-550, -12800, -80),
        20,
        1100,
        160,
        -76,
        unreal.Vector(0.0, -1.0, 0.0),
        metal,
    )
    create_floor("LabAccess", cube, 0, -13900, 2200, 3600, metal, -1520)

    # Lab cells and secret reactor.
    for index, x in enumerate((-2200, 0, 2200), start=1):
        spawn_box(
            f"Lab_ContainmentCell_{index:02d}",
            cube,
            unreal.Vector(x, -16000, -1310),
            unreal.Vector(1200, 1700, 580),
            concrete,
            folder="ZM_BlackTide/Architecture/Lab",
            tags=("ZS_ContainmentCell", f"Cell_{index}"),
        )

    spawn_cylinder(
        "Secret_AbyssReactor",
        cylinder,
        unreal.Vector(6200, -16000, -1250),
        1500,
        700,
        metal,
        "ZM_BlackTide/SetDress/Secrets",
        ("ZS_EasterEgg", "ZS_FinalReactor"),
    )
    spawn_sphere(
        "Secret_ReactorCore",
        sphere,
        unreal.Vector(6200, -16000, -800),
        700,
        accent,
        "ZM_BlackTide/SetDress/Secrets",
        ("ZS_EasterEgg", "ZS_FinalCore"),
    )

    # Progression doors.
    create_door(
        "Door_Theatre_750",
        cube,
        unreal.Vector(-6500, 0, 150),
        unreal.Vector(60, 520, DOOR_HEIGHT),
        metal,
        750,
        1,
    )
    create_door(
        "Door_Clinic_1000",
        cube,
        unreal.Vector(6500, 0, 150),
        unreal.Vector(60, 520, DOOR_HEIGHT),
        metal,
        1000,
        1,
    )
    create_door(
        "Door_Market_1250",
        cube,
        unreal.Vector(0, 6500, 150),
        unreal.Vector(520, 60, DOOR_HEIGHT),
        metal,
        1250,
        2,
    )
    create_door(
        "Door_Power_1500",
        cube,
        unreal.Vector(0, -6500, 150),
        unreal.Vector(520, 60, DOOR_HEIGHT),
        metal,
        1500,
        2,
    )
    create_door(
        "Door_Lab_2000",
        cube,
        unreal.Vector(0, -13300, -1450),
        unreal.Vector(520, 60, DOOR_HEIGHT),
        metal,
        2000,
        3,
    )
    create_door(
        "Door_Secret_ThreeSeals",
        cube,
        unreal.Vector(4300, -16000, -1300),
        unreal.Vector(60, 520, 600),
        accent,
        0,
        4,
        True,
    )

    # Boundary walls.
    boundary_height = 850.0
    boundaries = (
        ("Boundary_West", -12500, -3000, 100, 30000),
        ("Boundary_East", 12500, -3000, 100, 30000),
        ("Boundary_North", 0, 12500, 25000, 100),
        ("Boundary_South", 0, -19200, 25000, 100),
    )
    for name, x, y, sx, sy in boundaries:
        z = -1175 if name == "Boundary_South" else boundary_height / 2.0
        spawn_box(
            name,
            cube,
            unreal.Vector(x, y, z),
            unreal.Vector(sx, sy, boundary_height),
            brick,
            folder="ZM_BlackTide/Architecture/Boundary",
            tags=("ZS_Boundary",),
        )


def create_gameplay_markers() -> None:
    """Create markers for systems that will be implemented in Blueprints."""
    spawn_actor(
        unreal.PlayerStart,
        "PlayerStart_BlackTide",
        unreal.Vector(0.0, -1700.0, 140.0),
        unreal.Rotator(0.0, 90.0, 0.0),
        "ZM_BlackTide/Gameplay/Player",
        ("ZS_PlayerStart",),
    )

    enemy_spawns = (
        ("WestAlley", -5400, -1700, 0, 1),
        ("EastAlley", 5400, -1700, 180, 1),
        ("TheatreStage", -9000, 5200, -90, 2),
        ("TheatreBalcony", -9000, 1800, 90, 3),
        ("ClinicWard", 10100, 4500, -135, 2),
        ("ClinicRear", 9000, 5800, -90, 3),
        ("MarketNorth", 0, 11900, -90, 3),
        ("MarketWest", -3800, 10000, 0, 3),
        ("PowerWest", -3500, -10200, 0, 4),
        ("PowerEast", 3500, -10200, 180, 4),
        ("LabNorth", 0, -13700, -90, 5),
        ("LabCells", -2600, -16000, 0, 5),
        ("SecretChamber", 6200, -17800, 90, 6),
    )

    for index, (name, x, y, yaw, tier) in enumerate(enemy_spawns, start=1):
        z = -1500.0 if "Lab" in name or "Secret" in name else 120.0
        create_marker(
            f"EnemySpawn_{index:02d}_{name}",
            unreal.Vector(x, y, z),
            "ZM_BlackTide/Gameplay/EnemySpawns",
            ("ZS_EnemySpawn", f"Tier_{tier}", f"Lane_{index:02d}"),
            yaw,
        )

    wall_weapons = (
        ("Pistol", -2100, -2200, 500),
        ("SMG", -10500, 3200, 950),
        ("Shotgun", 10200, 2000, 1200),
        ("Rifle", -2900, 10000, 1500),
        ("HeavyWeapon", 2600, -10200, 2500),
    )
    for name, x, y, cost in wall_weapons:
        create_marker(
            f"WallWeapon_{name}_{cost}",
            unreal.Vector(x, y, 140),
            "ZM_BlackTide/Gameplay/WallWeapons",
            ("ZS_WallWeapon", f"Weapon_{name}", f"Cost_{cost}"),
        )

    perks = (
        ("Fortitude", -10200, 5200),
        ("QuickHands", 10200, 5200),
        ("FleetFoot", 3200, 10400),
        ("Overcharge", -2900, -11000),
    )
    for index, (name, x, y) in enumerate(perks, start=1):
        create_marker(
            f"Perk_{index:02d}_{name}",
            unreal.Vector(x, y, 120),
            "ZM_BlackTide/Gameplay/Perks",
            ("ZS_Perk", f"Perk_{name}"),
        )

    box_locations = (
        (-10800, 1600),
        (10800, 1600),
        (0, 11200),
        (-3200, -11200),
        (2400, -16000),
    )
    for index, (x, y) in enumerate(box_locations, start=1):
        z = -1500.0 if y < -13000 else 100.0
        create_marker(
            f"MysteryBoxLocation_{index:02d}",
            unreal.Vector(x, y, z),
            "ZM_BlackTide/Gameplay/MysteryBox",
            ("ZS_MysteryBoxLocation", f"Priority_{index}"),
        )

    fuses = (
        ("Theatre", -11100, 5300, 140),
        ("Clinic", 11100, 4900, 140),
        ("Market", 3600, 11100, 140),
    )
    for index, (zone, x, y, z) in enumerate(fuses, start=1):
        create_marker(
            f"EE_Fuse_{index:02d}_{zone}",
            unreal.Vector(x, y, z),
            "ZM_BlackTide/Gameplay/EasterEgg/Fuses",
            ("ZS_EasterEgg", "ZS_Fuse", f"Fuse_{index}", f"Zone_{zone}"),
        )

    seals = (
        ("Blood", -850, 0),
        ("Ash", 850, 0),
        ("Storm", 0, 850),
        ("Void", 0, -850),
    )
    for index, (name, x, y) in enumerate(seals, start=1):
        create_marker(
            f"EE_Seal_{index:02d}_{name}",
            unreal.Vector(x, y, 180),
            "ZM_BlackTide/Gameplay/EasterEgg/Seals",
            ("ZS_EasterEgg", "ZS_RitualSeal", f"Seal_{name}"),
        )

    create_marker(
        "EE_PowerSwitch",
        unreal.Vector(0, -11200, 150),
        "ZM_BlackTide/Gameplay/EasterEgg",
        ("ZS_EasterEgg", "ZS_PowerSwitch", "Stage_2"),
    )
    create_marker(
        "EE_FinalInteraction",
        unreal.Vector(6200, -16000, -900),
        "ZM_BlackTide/Gameplay/EasterEgg",
        ("ZS_EasterEgg", "ZS_FinalInteraction", "Stage_5"),
    )


def create_lighting_pass() -> None:
    """Create a color-guided lighting pass."""
    specs = (
        ("PlazaWarm", -1700, 0, 320, (255, 120, 60), 4600, 2200),
        ("PlazaCold", 1700, 0, 320, (70, 150, 255), 4200, 2200),
        ("TheatreEntry", -6500, 0, 340, (255, 80, 45), 5200, 1900),
        ("TheatreStage", -9000, 4800, 420, (180, 40, 20), 6500, 1700),
        ("ClinicEntry", 6500, 0, 340, (80, 170, 255), 4800, 1900),
        ("ClinicWard", 9000, 3900, 420, (150, 210, 255), 4800, 1700),
        ("MarketWest", -2800, 10000, 360, (255, 80, 160), 4200, 1700),
        ("MarketEast", 2800, 10000, 360, (60, 220, 190), 4200, 1700),
        ("PowerMain", 0, -10200, 430, (255, 145, 40), 7200, 2300),
        ("PowerWarning", -3000, -10800, 300, (255, 20, 20), 3400, 1400),
        ("LabBlue", -2200, -16000, -1100, (60, 120, 255), 5400, 1700),
        ("LabGreen", 2200, -16000, -1100, (60, 255, 180), 5400, 1700),
        ("SecretCore", 6200, -16000, -850, (180, 40, 255), 9000, 2500),
    )

    for name, x, y, z, rgb, intensity, radius in specs:
        create_point_light(
            f"Light_{name}",
            unreal.Vector(x, y, z),
            unreal.Color(rgb[0], rgb[1], rgb[2], 255),
            intensity,
            radius,
        )


def create_navigation() -> None:
    """Create a navigation bounds volume covering both vertical layers."""
    nav = spawn_actor(
        unreal.NavMeshBoundsVolume,
        "NavMeshBounds_BlackTide",
        unreal.Vector(0.0, -4000.0, -500.0),
        folder="ZM_BlackTide/Gameplay/Navigation",
        tags=("ZS_Navigation",),
    )
    nav.set_actor_scale3d(unreal.Vector(135.0, 175.0, 30.0))


def apply_fps_game_mode() -> None:
    """Attempt to assign the existing FPS GameMode."""
    try:
        game_mode_class = unreal.EditorAssetLibrary.load_blueprint_class(
            FPS_GAME_MODE_PATH
        )
        if game_mode_class is None:
            warn("BP_FPSGameMode was not found.")
            return

        world = unreal.get_editor_subsystem(
            unreal.UnrealEditorSubsystem
        ).get_editor_world()

        if world is None:
            warn("Unable to access the generated world.")
            return

        safe_set(
            world.get_world_settings(),
            "default_game_mode",
            game_mode_class,
        )
    except Exception as error:
        warn(f"Unable to assign the FPS GameMode: {error}")


def save_and_focus() -> None:
    """Save the map and frame it in the editor viewport."""
    if not unreal.EditorLevelLibrary.save_current_level():
        fail("The generated map could not be saved.")

    try:
        unreal.EditorLevelLibrary.set_level_viewport_camera_info(
            unreal.Vector(18500.0, -23500.0, 19000.0),
            unreal.Rotator(-28.0, 138.0, 0.0),
        )
    except Exception as error:
        warn(f"Unable to position the viewport: {error}")


def create_new_level() -> None:
    """Create a new level without overwriting existing work."""
    unreal.EditorAssetLibrary.make_directory(MAP_FOLDER)

    if map_exists():
        fail(
            f"The map already exists: {MAP_PATH}\n"
            "Delete or rename it manually before rebuilding."
        )

    if not unreal.EditorLevelLibrary.new_level(MAP_PATH):
        fail(f"Unable to create level: {MAP_PATH}")


def build_map() -> None:
    """Build the complete ZM Black Tide greybox."""
    log("Generation started.")

    cube = load_required_asset(CUBE_MESH_PATH)
    cylinder = load_required_asset(CYLINDER_MESH_PATH)
    sphere = load_required_asset(SPHERE_MESH_PATH)
    fallback = load_required_asset(BASIC_MATERIAL_PATH)

    material_assets = list_project_materials()

    concrete = find_material(
        material_assets,
        (("concrete",), ("stone",), ("floor",)),
        fallback,
    )
    brick = find_material(
        material_assets,
        (("brick",), ("wall",), ("stone",)),
        fallback,
    )
    metal = find_material(
        material_assets,
        (("metal",), ("steel",)),
        fallback,
    )
    floor_mat = find_material(
        material_assets,
        (("wood", "floor"), ("tiles",), ("floor",)),
        concrete,
    )
    accent = find_material(
        material_assets,
        (("emissive",), ("glass",), ("metal",)),
        metal,
    )

    create_new_level()
    create_environment()
    create_layout(
        cube,
        cylinder,
        sphere,
        concrete,
        brick,
        metal,
        floor_mat,
        accent,
    )
    create_gameplay_markers()
    create_lighting_pass()
    create_navigation()
    apply_fps_game_mode()
    save_and_focus()

    log("Generation completed successfully.")

    show_dialog(
        "ZombieSeasons - ZM Black Tide",
        (
            "La première passe de ZM Black Tide est terminée.\n\n"
            "Contenu généré :\n"
            "- 7 zones principales et plusieurs boucles\n"
            "- un balcon jouable et un laboratoire souterrain\n"
            "- 6 portes de progression\n"
            "- 13 points de spawn ennemis\n"
            "- armes murales, perks et emplacements de caisse\n"
            "- un secret en cinq étapes\n"
            "- une direction lumineuse complète\n\n"
            f"Map : {MAP_PATH}"
        ),
    )


try:
    build_map()
except GenerationError as error:
    show_dialog("ZM Black Tide - Generation stopped", str(error))
except Exception as error:
    unreal.log_error(f"[ZM Black Tide] Unexpected error: {error}")
    show_dialog(
        "ZM Black Tide - Unexpected error",
        (
            "Une erreur inattendue a interrompu la génération.\n\n"
            f"{error}\n\n"
            "Consulte le Journal de sortie pour le détail."
        ),
    )