"""Create a separate non-WP school A1. CREATE only; never overwrite a map."""
from __future__ import annotations

import json
from pathlib import Path
import unreal

MAP = "/Game/ZombieSeasons/Maps/Development/L_ZS_School_Expedition"
ROOT = "/Game/ZombieSeasons/SchoolA1"
REPORT = Path(unreal.Paths.project_saved_dir()) / "SchoolA1" / "generation.json"
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
worlds = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
made = []
seen_boxes = set()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def spawn(cls, name, pos, yaw=0):
    unreal.log(f"SCHOOL_A1_SPAWN {name}")
    actor = actors.spawn_actor_from_class(cls, unreal.Vector(*pos), unreal.Rotator(roll=0, pitch=0, yaw=yaw))
    require(actor is not None, f"Cannot create {name}")
    actor.set_actor_label(name)
    actor.set_folder_path("SchoolA1")
    actor.set_editor_property("tags", [unreal.Name("ZS.School.A1")])
    made.append(actor)
    return actor


def material(name, color, glass=False):
    path = f"{ROOT}/Materials/{name}"
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        return unreal.load_asset(path)
    mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, f"{ROOT}/Materials", unreal.Material, unreal.MaterialFactoryNew())
    require(mat, f"Material creation failed: {name}")
    lib = unreal.MaterialEditingLibrary
    node = lib.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector)
    node.set_editor_property("constant", unreal.LinearColor(*color, 1.0))
    lib.connect_material_property(node, "", unreal.MaterialProperty.MP_BASE_COLOR)
    rough = lib.create_material_expression(mat, unreal.MaterialExpressionConstant)
    rough.set_editor_property("r", 0.25 if glass else 0.8)
    lib.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    if glass:
        mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
        opacity = lib.create_material_expression(mat, unreal.MaterialExpressionConstant)
        opacity.set_editor_property("r", 0.12)
        lib.connect_material_property(opacity, "", unreal.MaterialProperty.MP_OPACITY)
    lib.recompile_material(mat)
    unreal.EditorAssetLibrary.save_loaded_asset(mat)
    return mat


def box(name, pos, size, mat, collision=True, movable=False):
    actor = spawn(unreal.StaticMeshActor, name, pos)
    component = actor.static_mesh_component
    component.set_static_mesh(cube)
    if movable:
        component.set_mobility(unreal.ComponentMobility.MOVABLE)
    component.set_material(0, mat)
    component.set_collision_profile_name("BlockAll" if collision else "NoCollision")
    actor.set_actor_scale3d(unreal.Vector(*(n / 100 for n in size)))
    return actor


def wall(name, axis, fixed, start, end, holes=(), height=340):
    cursor = start
    for low, high in sorted(holes) + [(end, end)]:
        require(start <= low <= high <= end, f"Bad opening {name}: {low}, {high}")
        if low > cursor:
            center = (cursor + low) / 2
            pos = (fixed, center, height / 2) if axis == "x" else (center, fixed, height / 2)
            size = (20, low - cursor, height) if axis == "x" else (low - cursor, 20, height)
            key = tuple(pos) + tuple(size)
            if key not in seen_boxes:
                box(f"{name}_{int(cursor)}", pos, size, wall_mat)
                seen_boxes.add(key)
        if high > low and height > 300:
            center = (low + high) / 2
            pos = (fixed, center, (300 + height) / 2) if axis == "x" else (center, fixed, (300 + height) / 2)
            size = (20, high - low, height - 300) if axis == "x" else (high - low, 20, height - 300)
            box(f"{name}_Lintel_{int(low)}", pos, size, wall_mat)
        cursor = high


def label(name, text, pos, yaw=180, size=22):
    actor = spawn(unreal.TextRenderActor, name, pos, yaw)
    component = actor.get_component_by_class(unreal.TextRenderComponent)
    component.set_text(text)
    component.set_world_size(size)
    component.set_text_render_color(unreal.Color(18, 25, 28, 255))
    return actor


def point_light(name, pos, power, color, active=True):
    actor = spawn(unreal.PointLight, name, pos)
    light = actor.get_component_by_class(unreal.PointLightComponent)
    light.set_mobility(unreal.ComponentMobility.MOVABLE)
    light.set_intensity(power)
    light.set_editor_property("attenuation_radius", 2200)
    light.set_light_color(unreal.LinearColor(*color, 1))
    light.set_visibility(active)
    return actor


def camera(name, pos, pitch, yaw, tag):
    actor = spawn(unreal.CameraActor, name, pos, yaw)
    actor.set_actor_rotation(unreal.Rotator(roll=0, pitch=pitch, yaw=yaw), False)
    actor.set_editor_property("tags", [unreal.Name(tag)])
    actor.get_component_by_class(unreal.CameraComponent).set_field_of_view(85)
    return actor


require(not levels.is_in_play_in_editor(), "Stop PIE before generation")
require(not unreal.EditorAssetLibrary.does_asset_exist(MAP), "Map already exists: CREATE refuses to overwrite it")
require(not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages(), "Save open maps before generation")
cube = unreal.load_asset("/Engine/BasicShapes/Cube.Cube")
scenario_cls = unreal.load_class(None, "/Script/ZombieSeasonsRuntime.ZSSchoolScenario")
game_mode = unreal.load_class(None, "/Game/TopDownShooter/Core/BP_FPSGameMode.BP_FPSGameMode_C")
enemy_cls = unreal.load_class(None, "/Game/TopDownShooter/Core/BP_Enemy.BP_Enemy_C")
enemy_ai = unreal.load_class(None, "/Game/TopDownShooter/Core/AIC_Enemy.AIC_Enemy_C")
require(all([cube, scenario_cls, game_mode, enemy_cls, enemy_ai]), "Required school/FPS/enemy classes missing; compile first")
require(levels.new_level(MAP), "Cannot create school level")
world = worlds.get_editor_world()
settings = world.get_world_settings()
settings.set_editor_property("default_game_mode", game_mode)
settings.set_editor_property("tags", [unreal.Name("ZS.Scenario.School")])
wall_mat = material("M_A1_Wall", (0.42, 0.43, 0.4))
floor_mat = material("M_A1_Floor", (0.19, 0.21, 0.2))
wood = material("M_A1_Gym", (0.3, 0.21, 0.12))
blue = material("M_A1_Blue", (0.055, 0.16, 0.23))
amber = material("M_A1_Amber", (0.62, 0.34, 0.055))
glass = material("M_A1_Glass", (0.55, 0.67, 0.65), True)

# Ground is intentionally compact; distances in centimeters.
box("A1_Ground", (600, 0, -25), (9200, 5600, 50), floor_mat)
box("Gym_Floor", (1600, 1000, 2), (3200, 2000, 4), wood)
# Initial courtyard, kitchen, service, loge, preparation room.
wall("Cour_W", "x", -3600, -2200, 400, height=280)
wall("Cour_N", "y", 400, -3600, -1600, height=280)
wall("Cour_E", "x", -1600, -2200, 400, [(-1000, -600)], height=340)
wall("Cour_S", "y", -2200, -3600, -1600, [(-3000, -2600)], height=280)
wall("Cuisine_S", "y", -1400, -1600, -400)
wall("Cuisine_N", "y", -200, -1600, -400)
wall("Service_W", "x", -400, -1400, 1200, [(-1000, -600)])
wall("Service_S", "y", -1400, -400, 0)
wall("Service_E", "x", 0, -1400, 1200, [(-1100, -700), (200, 600)])
wall("Loge_S", "y", -1400, 0, 800)
wall("Loge_E", "x", 800, -1400, 0)
wall("Loge_WindowWall", "y", 0, 0, 800, [(200, 650)])
box("Observation_Sill", (425, 0, 45), (450, 20, 90), wall_mat)
box("Observation_Glass", (425, 0, 195), (450, 8, 210), glass)
wall("Preparation_S", "y", 1200, -800, 0, [(-350, -50)])
wall("Preparation_W", "x", -800, 1200, 2000)
wall("Preparation_N", "y", 2000, -800, 0)
wall("Preparation_E", "x", 0, 1200, 2000, [(1400, 1800)])
# Gym has two independent western approaches and an eastern exit.
wall("Gym_S", "y", 0, 800, 3200, height=700)
wall("Gym_N", "y", 2000, 0, 3200, height=700)
wall("Gym_E", "x", 3200, 0, 2000, [(800, 1200)], height=700)
box("Gym_W_Upper", (0, 1000, 520), (20, 2000, 360), wall_mat)
# Roof and service ceilings are hidden only for the automated cutaway screenshot.
for name, pos, size in [
    ("Gym_Roof", (1600, 1000, 710), (3240, 2040, 20)),
    ("Kitchen_Roof", (-1000, -800, 350), (1200, 1200, 20)),
    ("Loge_Roof", (400, -700, 350), (800, 1400, 20)),
    ("Service_Roof", (-200, -100, 350), (400, 2600, 20)),
    ("Preparation_Roof", (-400, 1600, 350), (800, 800, 20)),
]:
    roof = box(name, pos, size, wall_mat)
    roof.set_editor_property("tags", [unreal.Name("ZS.School.Roof")])
# Courtyard and return route, blocked by the shortcut from its far side.
wall("Interieur_N", "y", 2400, 3200, 4800, height=280)
wall("Interieur_E", "x", 4800, -2600, 2400, height=280)
wall("Interieur_W_N", "x", 3200, 2000, 2400, height=280)
wall("Interieur_W_S", "x", 3200, -2200, 0, height=280)
wall("Raccourci_Frame", "y", -1200, 3200, 4800, [(3800, 4200)])
wall("Retour_S", "y", -2600, -3600, 4800, height=280)
wall("Retour_W", "x", -3600, -2600, -2200, height=280)
wall("Retour_N", "y", -2200, -1600, 3200, height=280)
prep_door = box("Passage_Lateral", (0, 1600, 145), (20, 395, 290), blue, movable=True)
shortcut_door = box("Raccourci", (4000, -1200, 145), (395, 20, 290), blue, movable=True)

# Large readable obstacles, not detailed dressing. Two clear gym routes remain.
box("Gradins_Replies", (1500, 1050, 90), (650, 350, 180), blue)
box("Materiel_Accueil", (2450, 700, 70), (300, 300, 140), wall_mat)
box("Comptoir_Cuisine", (-1000, -400, 50), (650, 140, 100), wall_mat)
for index, x in enumerate((700, 1250, 2100, 2650)):
    box(f"Barriere_Mobile_B_{index}", (x, 1550, 55), (300, 35, 110), amber)
for index, x in enumerate((800, 1500, 2300)):
    box(f"Attente_B_Volume_{index}", (x, 1870, 30), (180, 70, 60), blue)

relay = box("Commande_Liaison", (760, -900, 125), (50, 100, 130), blue)
prep_control = box("Commande_Passage", (-100, 1380, 125), (40, 40, 90), amber)
shortcut_control = box("Commande_Raccourci", (4250, -1080, 125), (40, 40, 90), amber)
return_point = box("Poste_Retour", (-3250, -1550, 125), (100, 50, 100), blue)
label("Livraison", "LIVRAISONS  /  ACCUEIL", (-1625, -650, 240), 180, 23)
label("Loge", "LOGE  /  COMMUNICATIONS", (-22, -700, 245), 180, 17)
label("Consigne", "COMMUNICATIONS SEULES\nLAISSER B INHIBE", (726, -930, 225), 180, 15)
label("Secteur_B", "B  /  ATTENTE TRANSFERT", (1600, 1975, 260), -90, 32)
label("Sortie", "SORTIE  >", (3175, 1250, 260), 180, 27)
label("Passage", "PASSAGE LATERAL\nDEVERROUILLAGE MANUEL", (-30, 1720, 235), 180, 15)
label("Retour", "RETOUR  /  COUR LIVRAISON", (3800, -1175, 265), 90, 22)
label("Fin_A1", "POSTE D'ENTREE\nFIN DU PARCOURS A1", (-3250, -1505, 240), 90, 19)
spawn(unreal.PlayerStart, "Depart_Joueur", (-2800, -1400, 110), 35)

sun = spawn(unreal.DirectionalLight, "Jour_Diffus", (0, 0, 1500))
sun.set_actor_rotation(unreal.Rotator(roll=0, pitch=-40, yaw=35), False)
sun_light = sun.get_component_by_class(unreal.DirectionalLightComponent)
sun_light.set_mobility(unreal.ComponentMobility.MOVABLE)
sun_light.set_editor_property("atmosphere_sun_light", True)
sun_light.set_intensity(2000)
spawn(unreal.SkyAtmosphere, "Atmosphere", (0, 0, 0))
sky = spawn(unreal.SkyLight, "Ciel", (0, 0, 1200))
sky.get_component_by_class(unreal.SkyLightComponent).set_mobility(unreal.ComponentMobility.MOVABLE)
sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("real_time_capture", True)
for i, (x, y, z) in enumerate([(-1000, -800, 280), (-200, -200, 290), (400, -900, 280), (-400, 1600, 290), (650, 600, 590), (2200, 1200, 590)]):
    point_light(f"Ambiance_{i}", (x, y, z), 4500 if i < 4 else 18000, (0.7, 0.8, 1.0))
incident = [point_light(f"Services_B_{i}", (x, 1500, 480), 22000, (1.0, 0.65, 0.25), False) for i, x in enumerate((700, 1700, 2700))]

nav = spawn(unreal.NavMeshBoundsVolume, "Navigation_Ecole", (600, -100, 350))
_, extent = nav.get_actor_bounds(False)
require(min(extent.x, extent.y, extent.z) > 0, "Invalid nav bounds brush")
nav.set_actor_scale3d(unreal.Vector(4700 / extent.x, 2900 / extent.y, 650 / extent.z))
recast = spawn(unreal.RecastNavMesh, "Recast_Ecole", (0, 0, 0))
recast.set_editor_property("runtime_generation", unreal.RuntimeGenerationType.DYNAMIC)
recast.set_editor_property("force_rebuild_on_load", True)
# Keep the supported-agent dimensions; changing them here makes Unreal discard this nav data on reload.


waiting = []
for index, pos in enumerate([(-1000, -900, 110), (-1150, -500, 110), (600, 1850, 110), (1100, 1800, 110), (1800, 1850, 110), (2400, 1800, 110), (2900, 1700, 110)]):
    enemy = spawn(enemy_cls, f"Infecte_{index}", pos, -90)
    enemy.set_editor_property("ai_controller_class", enemy_ai)
    enemy.set_editor_property("auto_possess_ai", unreal.AutoPossessAI.PLACED_IN_WORLD_OR_SPAWNED)
    if index >= 2:
        waiting.append(enemy)

scenario = spawn(scenario_cls, "Scenario_Ecole_B", (0, 0, 0))
for key, value in dict(relay=relay, preparation_control=prep_control, preparation_door=prep_door, shortcut_control=shortcut_control, shortcut_door=shortcut_door, return_point=return_point, waiting_enemies=waiting, incident_lights=incident).items():
    scenario.set_editor_property(key, value)
route = [(-2800,-1400,0),(-1000,-800,0),(-200,-800,0),(400,-900,0),(-200,400,0),(400,400,0),(1600,400,0),(3500,1000,0),(2800,1350,0),(400,1300,0),(-400,1600,0),(-200,700,0),(3500,1000,0),(4000,-1000,0),(4000,-2400,0),(-2800,-2400,0),(-2800,-1400,0)]
scenario.set_editor_property("test_route", [unreal.Vector(*p) for p in route])
camera("Vue_Avant", (400, 240, 180), -2, 48, "ZS.School.Camera.Before")
camera("Vue_Apres", (400, 240, 180), -2, 48, "ZS.School.Camera.After")
camera("Vue_Routes", (600, -450, 6800), -88, 90, "ZS.School.Camera.Routes")
worlds.set_level_viewport_camera_info(unreal.Vector(400, 240, 180), unreal.Rotator(roll=0,pitch=-2,yaw=48))
require(levels.save_current_level(), "Cannot save school map")
REPORT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text(json.dumps(dict(status="GENERATED_NOT_PLAYTESTED", map=MAP, actor_count=len(made), scenario="School A1", region="France fictive", waiting_enemies=len(waiting), nav="dynamic; runtime verification required", existing_maps_modified=False), indent=2), encoding="utf-8")
unreal.log(f"SCHOOL_A1_GENERATED {REPORT}")
