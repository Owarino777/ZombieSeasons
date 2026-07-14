import unreal


MAP_PATH = "/Game/TopDownShooter/Maps/AI_TestMap"

CUBE_MESH_PATH = "/Engine/BasicShapes/Cube.Cube"
SPHERE_MESH_PATH = "/Engine/BasicShapes/Sphere.Sphere"

FLOOR_SIZE_X = 5000.0
FLOOR_SIZE_Y = 5000.0
FLOOR_THICKNESS = 100.0

WALL_HEIGHT = 500.0
WALL_THICKNESS = 100.0

DEFAULT_CUBE_SIZE = 100.0


def log(message: str) -> None:
    """Write an informational message to the Unreal log."""
    unreal.log(f"ZombieSeasons AI Map: {message}")


def fail(message: str) -> None:
    """Stop the script with a visible error."""
    unreal.log_error(f"ZombieSeasons AI Map: {message}")

    unreal.EditorDialog.show_message(
        "ZombieSeasons AI Map",
        message,
        unreal.AppMsgType.OK,
    )

    raise RuntimeError(message)


def load_required_asset(asset_path: str) -> unreal.Object:
    """Load an Unreal asset or stop if it cannot be found."""
    asset = unreal.EditorAssetLibrary.load_asset(asset_path)

    if asset is None:
        fail(f"Unable to load required asset: {asset_path}")

    return asset


def spawn_static_mesh(
    label: str,
    mesh: unreal.StaticMesh,
    location: unreal.Vector,
    scale: unreal.Vector,
) -> unreal.StaticMeshActor:
    """Spawn and configure a static mesh actor."""
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.StaticMeshActor,
        location,
        unreal.Rotator(0.0, 0.0, 0.0),
    )

    if actor is None:
        fail(f"Unable to spawn actor: {label}")

    actor.set_actor_label(label)

    static_mesh_component = actor.static_mesh_component
    static_mesh_component.set_static_mesh(mesh)

    actor.set_actor_scale3d(scale)

    return actor


def create_new_level() -> None:
    """Create or replace the AI test level."""
    if unreal.EditorAssetLibrary.does_asset_exist(MAP_PATH):
        log(f"Deleting existing test map: {MAP_PATH}")

        deleted = unreal.EditorAssetLibrary.delete_asset(MAP_PATH)

        if not deleted:
            fail(
                "The existing AI_TestMap could not be deleted. "
                "Make sure it is not currently open."
            )

    log(f"Creating level: {MAP_PATH}")

    created = unreal.EditorLevelLibrary.new_level(MAP_PATH)

    if not created:
        fail(f"Unable to create level: {MAP_PATH}")


def create_floor(cube_mesh: unreal.StaticMesh) -> None:
    """Create the playable floor."""
    spawn_static_mesh(
        label="AI_Floor",
        mesh=cube_mesh,
        location=unreal.Vector(
            0.0,
            0.0,
            -FLOOR_THICKNESS / 2.0,
        ),
        scale=unreal.Vector(
            FLOOR_SIZE_X / DEFAULT_CUBE_SIZE,
            FLOOR_SIZE_Y / DEFAULT_CUBE_SIZE,
            FLOOR_THICKNESS / DEFAULT_CUBE_SIZE,
        ),
    )


def create_walls(cube_mesh: unreal.StaticMesh) -> None:
    """Create four boundary walls."""
    half_floor_x = FLOOR_SIZE_X / 2.0
    half_floor_y = FLOOR_SIZE_Y / 2.0
    wall_z = WALL_HEIGHT / 2.0

    spawn_static_mesh(
        label="AI_Wall_North",
        mesh=cube_mesh,
        location=unreal.Vector(
            0.0,
            half_floor_y,
            wall_z,
        ),
        scale=unreal.Vector(
            FLOOR_SIZE_X / DEFAULT_CUBE_SIZE,
            WALL_THICKNESS / DEFAULT_CUBE_SIZE,
            WALL_HEIGHT / DEFAULT_CUBE_SIZE,
        ),
    )

    spawn_static_mesh(
        label="AI_Wall_South",
        mesh=cube_mesh,
        location=unreal.Vector(
            0.0,
            -half_floor_y,
            wall_z,
        ),
        scale=unreal.Vector(
            FLOOR_SIZE_X / DEFAULT_CUBE_SIZE,
            WALL_THICKNESS / DEFAULT_CUBE_SIZE,
            WALL_HEIGHT / DEFAULT_CUBE_SIZE,
        ),
    )

    spawn_static_mesh(
        label="AI_Wall_East",
        mesh=cube_mesh,
        location=unreal.Vector(
            half_floor_x,
            0.0,
            wall_z,
        ),
        scale=unreal.Vector(
            WALL_THICKNESS / DEFAULT_CUBE_SIZE,
            FLOOR_SIZE_Y / DEFAULT_CUBE_SIZE,
            WALL_HEIGHT / DEFAULT_CUBE_SIZE,
        ),
    )

    spawn_static_mesh(
        label="AI_Wall_West",
        mesh=cube_mesh,
        location=unreal.Vector(
            -half_floor_x,
            0.0,
            wall_z,
        ),
        scale=unreal.Vector(
            WALL_THICKNESS / DEFAULT_CUBE_SIZE,
            FLOOR_SIZE_Y / DEFAULT_CUBE_SIZE,
            WALL_HEIGHT / DEFAULT_CUBE_SIZE,
        ),
    )


def create_obstacles(
    cube_mesh: unreal.StaticMesh,
    sphere_mesh: unreal.StaticMesh,
) -> None:
    """Create simple gameplay obstacles for the generated test map."""
    obstacle_data = [
        (
            "AI_Obstacle_Center",
            cube_mesh,
            unreal.Vector(0.0, 0.0, 150.0),
            unreal.Vector(6.0, 6.0, 3.0),
        ),
        (
            "AI_Obstacle_NorthWest",
            cube_mesh,
            unreal.Vector(-1200.0, 1000.0, 150.0),
            unreal.Vector(5.0, 8.0, 3.0),
        ),
        (
            "AI_Obstacle_SouthEast",
            cube_mesh,
            unreal.Vector(1200.0, -1000.0, 150.0),
            unreal.Vector(5.0, 8.0, 3.0),
        ),
        (
            "AI_Obstacle_Sphere_West",
            sphere_mesh,
            unreal.Vector(-1200.0, -1000.0, 250.0),
            unreal.Vector(5.0, 5.0, 5.0),
        ),
        (
            "AI_Obstacle_Sphere_East",
            sphere_mesh,
            unreal.Vector(1200.0, 1000.0, 250.0),
            unreal.Vector(5.0, 5.0, 5.0),
        ),
    ]

    for label, mesh, location, scale in obstacle_data:
        spawn_static_mesh(
            label=label,
            mesh=mesh,
            location=location,
            scale=scale,
        )


def create_player_start() -> None:
    """Create the player spawn point."""
    player_start = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.PlayerStart,
        unreal.Vector(0.0, -1800.0, 150.0),
        unreal.Rotator(0.0, 0.0, 0.0),
    )

    if player_start is None:
        fail("Unable to create PlayerStart.")

    player_start.set_actor_label("AI_PlayerStart")


def create_directional_light() -> None:
    """Create the main directional light."""
    light = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.DirectionalLight,
        unreal.Vector(0.0, 0.0, 1500.0),
        unreal.Rotator(-45.0, -35.0, 0.0),
    )

    if light is None:
        fail("Unable to create DirectionalLight.")

    light.set_actor_label("AI_DirectionalLight")

    light_component = light.get_component_by_class(
        unreal.DirectionalLightComponent
    )

    if light_component is not None:
        light_component.set_editor_property("intensity", 8.0)


def create_sky_light() -> None:
    """Create ambient lighting."""
    sky_light = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.SkyLight,
        unreal.Vector(0.0, 0.0, 1000.0),
        unreal.Rotator(0.0, 0.0, 0.0),
    )

    if sky_light is None:
        fail("Unable to create SkyLight.")

    sky_light.set_actor_label("AI_SkyLight")

    sky_light_component = sky_light.get_component_by_class(
        unreal.SkyLightComponent
    )

    if sky_light_component is not None:
        sky_light_component.set_editor_property("intensity", 1.0)
        sky_light_component.set_editor_property(
            "real_time_capture",
            True,
        )


def create_nav_mesh_bounds() -> None:
    """Create a navigation bounds volume covering the test arena."""
    nav_mesh_bounds = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.NavMeshBoundsVolume,
        unreal.Vector(0.0, 0.0, 250.0),
        unreal.Rotator(0.0, 0.0, 0.0),
    )

    if nav_mesh_bounds is None:
        fail("Unable to create NavMeshBoundsVolume.")

    nav_mesh_bounds.set_actor_label("AI_NavMeshBounds")
    nav_mesh_bounds.set_actor_scale3d(
        unreal.Vector(
            FLOOR_SIZE_X / 200.0,
            FLOOR_SIZE_Y / 200.0,
            5.0,
        )
    )


def save_level() -> None:
    """Save the generated map."""
    log("Saving generated map.")

    saved = unreal.EditorLevelLibrary.save_current_level()

    if not saved:
        fail("The level could not be saved.")


def build_map() -> None:
    """Build the complete generated test map."""
    log("Generation started.")

    cube_mesh = load_required_asset(CUBE_MESH_PATH)
    sphere_mesh = load_required_asset(SPHERE_MESH_PATH)

    create_new_level()
    create_floor(cube_mesh)
    create_walls(cube_mesh)
    create_obstacles(cube_mesh, sphere_mesh)
    create_player_start()
    create_directional_light()
    create_sky_light()
    create_nav_mesh_bounds()
    save_level()

    log("Generation completed successfully.")

    unreal.EditorDialog.show_message(
        "ZombieSeasons AI Map",
        "La map AI_TestMap a été créée et enregistrée.",
        unreal.AppMsgType.OK,
    )


build_map()