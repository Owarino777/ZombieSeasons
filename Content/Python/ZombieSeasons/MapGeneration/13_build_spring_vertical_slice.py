"""Stage 13: create/reuse the production world and build the Spring vertical slice art pass.

This stage is intentionally a single operator checkpoint. It preserves the validated
greybox gameplay/navigation topology, creates /Game/ZombieSeasons/Maps/L_ZS_World from
the accepted greybox when needed, and adds deterministic Spring production dressing
from the approved production manifest.

Generated art actors are non-blocking during this first production pass so the already
validated zombie navigation and traversal are not silently invalidated by decorative
content. Collision is promoted selectively only after the Spring performance/gameplay
gate.
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path
from typing import Any

import unreal

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from zs_generation_common import (  # noqa: E402
    GLOBAL_SEED,
    GREYBOX_MAP,
    PRODUCTION_MAP,
    VALIDATION_ROOT,
    actor_has_tag,
    add_generation_tags,
    approved_manifest_rows,
    editor_asset_exists,
    fail,
    log,
    show_editor_message,
    warn,
    write_json_report,
)


STAGE = "SpringVerticalSlice"
STAGE_TAG = f"ZS.Stage.{STAGE}"
GREYBOX_ACCEPTANCE_REPORT = VALIDATION_ROOT / "generated_world_validation.json"
ART_FOLDER = "ZombieSeasons/FinalArt/Spring"
FINAL_ART_LAYERS = ("DL_ZS_FinalArt", "DL_ZS_Spring")
REBUILD_GENERATED_STAGE_ART = True

# Art anchors keep production dressing inside the already validated Spring topology.
VEHICLE_PLACEMENTS = (
    (-22500.0, 23500.0, 225.0, 135.0),
    (-30500.0, 34000.0, 225.0, 45.0),
    (-39500.0, 43000.0, 225.0, 135.0),
    (-49200.0, 50000.0, 225.0, 130.0),
    (-52500.0, 55500.0, 225.0, 50.0),
    (-35000.0, 62500.0, 225.0, 15.0),
    (-29200.0, 65500.0, 225.0, 95.0),
    (-34000.0, 47000.0, 225.0, 165.0),
    (-46000.0, 45500.0, 225.0, 35.0),
    (-66500.0, 32500.0, 225.0, 12.0),
    (-70500.0, 28500.0, 225.0, 105.0),
    (-61000.0, 24000.0, 225.0, 175.0),
)

STREET_PROP_PLACEMENTS = (
    (-32200.0, 40500.0, 230.0, 0.0),
    (-35500.0, 39500.0, 230.0, 180.0),
    (-31500.0, 37000.0, 230.0, 90.0),
    (-36500.0, 36000.0, 230.0, -90.0),
    (-33500.0, 42000.0, 230.0, 45.0),
    (-36000.0, 62500.0, 230.0, 10.0),
    (-32500.0, 64000.0, 230.0, 95.0),
    (-28500.0, 69000.0, 230.0, 190.0),
    (-54200.0, 54500.0, 230.0, 0.0),
    (-56500.0, 62000.0, 230.0, 180.0),
    (-60200.0, 56000.0, 230.0, 90.0),
    (-62500.0, 50000.0, 230.0, -90.0),
    (-69000.0, 33500.0, 230.0, 25.0),
    (-72000.0, 30000.0, 230.0, 120.0),
    (-65500.0, 28500.0, 230.0, 205.0),
    (-60000.0, 22500.0, 230.0, 0.0),
)

BARRIER_PLACEMENTS = (
    (-50500.0, 52000.0, 235.0, 40.0),
    (-52000.0, 53000.0, 235.0, 40.0),
    (-57500.0, 54500.0, 235.0, 0.0),
    (-58500.0, 54500.0, 235.0, 0.0),
    (-61000.0, 49000.0, 235.0, 90.0),
    (-62000.0, 49000.0, 235.0, 90.0),
    (-67500.0, 30500.0, 235.0, 15.0),
    (-69000.0, 29500.0, 235.0, 15.0),
    (-61500.0, 21500.0, 235.0, 90.0),
    (-62500.0, 21500.0, 235.0, 90.0),
)

DEBRIS_PLACEMENTS = (
    (-25000.0, 27500.0, 220.0, 0.0),
    (-28700.0, 31500.0, 220.0, 35.0),
    (-33000.0, 35000.0, 220.0, 70.0),
    (-37000.0, 40500.0, 220.0, 105.0),
    (-42000.0, 43500.0, 220.0, 140.0),
    (-47500.0, 48500.0, 220.0, 175.0),
    (-53500.0, 53500.0, 220.0, 210.0),
    (-56000.0, 57000.0, 220.0, 245.0),
    (-58500.0, 55500.0, 220.0, 280.0),
    (-62000.0, 52000.0, 220.0, 315.0),
    (-33500.0, 61500.0, 220.0, 20.0),
    (-30500.0, 67500.0, 220.0, 65.0),
    (-35000.0, 39000.0, 220.0, 110.0),
    (-32500.0, 36500.0, 220.0, 155.0),
    (-65000.0, 35000.0, 220.0, 200.0),
    (-68500.0, 32000.0, 220.0, 245.0),
    (-71500.0, 29500.0, 220.0, 290.0),
    (-65000.0, 26000.0, 220.0, 335.0),
    (-62000.0, 22500.0, 220.0, 20.0),
    (-59000.0, 20500.0, 220.0, 65.0),
)

# Architecture remains non-colliding in this pass and overlays the validated shell.
FACADE_PLACEMENTS = (
    (-35000.0, 67050.0, 575.0, 180.0, 2200.0),
    (-30500.0, 70050.0, 540.0, 180.0, 2100.0),
    (-26000.0, 66050.0, 550.0, 180.0, 2200.0),
    (-30500.0, 62150.0, 520.0, 0.0, 2000.0),
    (-55000.0, 55550.0, 430.0, 0.0, 3600.0),
    (-60000.0, 49250.0, 450.0, 0.0, 3500.0),
)

ROOF_PLACEMENTS = (
    (-35000.0, 68000.0, 940.0, 0.0, 2600.0),
    (-30500.0, 71000.0, 880.0, 0.0, 2300.0),
    (-26000.0, 67000.0, 910.0, 0.0, 2500.0),
    (-30500.0, 63000.0, 840.0, 0.0, 2200.0),
)

ENTRANCE_PLACEMENTS = (
    (-55000.0, 55520.0, 430.0, 0.0, 1500.0),
    (-56500.0, 60500.0, 430.0, 180.0, 1300.0),
    (-60000.0, 49230.0, 450.0, 0.0, 1500.0),
    (-62000.0, 20000.0, 350.0, 0.0, 1100.0),
)

# These silhouettes add height without touching playable terrain or NavMesh.
LANDMARK_PLACEMENTS = (
    (-57000.0, 60000.0, 900.0, 0.0, 1800.0),
    (-57500.0, 58500.0, 750.0, 90.0, 1600.0),
    (-61000.0, 53500.0, 650.0, 0.0, 1600.0),
    (-72000.0, 33000.0, 500.0, 15.0, 1500.0),
)


def _level_subsystem() -> Any:
    value = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if value is None:
        fail("LevelEditorSubsystem is unavailable.")
    return value


def _actor_subsystem() -> Any:
    value = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    if value is None:
        fail("EditorActorSubsystem is unavailable.")
    return value


def _editor_subsystem() -> Any:
    value = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    if value is None:
        fail("UnrealEditorSubsystem is unavailable.")
    return value


def _current_world() -> Any:
    subsystem = _editor_subsystem()
    if subsystem.get_game_world():
        fail("Stop PIE before Stage 13.")
    world = subsystem.get_editor_world()
    if world is None:
        fail("No editor world is open.")
    return world


def _current_world_path() -> str:
    return str(_current_world().get_path_name()).split(".", 1)[0]


def _load_level(asset_path: str) -> None:
    if not _level_subsystem().load_level(asset_path):
        fail(f"Unable to load level: {asset_path}")


def _read_acceptance_report() -> dict[str, Any]:
    if not GREYBOX_ACCEPTANCE_REPORT.is_file():
        fail(
            "Greybox acceptance report is missing. Run 11_12_finalize_greybox.py "
            "and require Stage 12 PASS before Stage 13."
        )
    try:
        payload = json.loads(GREYBOX_ACCEPTANCE_REPORT.read_text(encoding="utf-8"))
    except Exception as error:
        fail(f"Unable to read greybox acceptance report: {error}")
    if payload.get("status") != "PASS":
        fail(
            "The latest generated_world_validation.json is not PASS. "
            "Stage 13 refuses to art-pass an unaccepted gameplay world."
        )
    if int(payload.get("gameplay_marker_count", 0)) != 470:
        fail("Greybox acceptance report does not certify all 470 gameplay markers.")
    return payload


def _check_dirty_maps_before_world_switch() -> None:
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
            "Unsaved map packages are open. Save them before creating/loading the "
            "production world: " + ", ".join(names)
        )


def _create_production_from_greybox() -> str:
    if editor_asset_exists(PRODUCTION_MAP):
        if _current_world_path() != PRODUCTION_MAP:
            _check_dirty_maps_before_world_switch()
            _load_level(PRODUCTION_MAP)
        return "EXISTING"

    if not editor_asset_exists(GREYBOX_MAP):
        fail(f"Accepted greybox map does not exist: {GREYBOX_MAP}")

    if _current_world_path() != GREYBOX_MAP:
        _check_dirty_maps_before_world_switch()
        _load_level(GREYBOX_MAP)

    level_subsystem = _level_subsystem()
    created = False
    creation_error = None

    # Preferred route: create the production world from the accepted WP world template.
    method = getattr(level_subsystem, "new_level_from_template", None)
    if method is not None:
        try:
            created = bool(method(PRODUCTION_MAP, GREYBOX_MAP))
        except Exception as error:
            creation_error = error

    # Compatibility fallback for builds exposing the call on EditorLevelLibrary.
    if not created:
        library = getattr(unreal, "EditorLevelLibrary", None)
        fallback = getattr(library, "new_level_from_template", None) if library else None
        if fallback is not None:
            try:
                created = bool(fallback(PRODUCTION_MAP, GREYBOX_MAP))
                creation_error = None
            except Exception as error:
                creation_error = error

    if not created:
        detail = f" Last error: {creation_error}" if creation_error else ""
        fail(
            "This UE 5.5 editor build could not create L_ZS_World from the accepted "
            "greybox template using the exposed level APIs." + detail
        )

    if _current_world_path() != PRODUCTION_MAP:
        _load_level(PRODUCTION_MAP)
    return "CREATED_FROM_GREYBOX"


def _all_actors() -> list[Any]:
    return list(_actor_subsystem().get_all_level_actors() or [])


def _validate_production_copy() -> dict[str, int]:
    actors = _all_actors()
    gameplay = [actor for actor in actors if actor_has_tag(actor, "ZS.Stage.GameplayLayout")]
    lighting = [actor for actor in actors if actor_has_tag(actor, "ZS.Stage.LightingBaseline")]
    navigation = [actor for actor in actors if actor_has_tag(actor, "ZS.Stage.NavigationSetup")]
    spring = [actor for actor in actors if actor_has_tag(actor, "ZS.Stage.Spring")]

    if len(gameplay) != 470:
        fail(
            "Production map copy is incomplete: expected 470 gameplay markers, "
            f"found {len(gameplay)}."
        )
    if len(lighting) != 4:
        fail(
            "Production map copy is incomplete: expected 4 baseline lighting actors, "
            f"found {len(lighting)}."
        )
    if len(navigation) != 1:
        fail(
            "Production map copy is incomplete: expected one NavigationSetup actor, "
            f"found {len(navigation)}."
        )
    if not spring:
        fail("Production map copy contains no Stage-3 Spring geometry.")

    return {
        "actors": len(actors),
        "gameplay": len(gameplay),
        "lighting": len(lighting),
        "navigation": len(navigation),
        "spring": len(spring),
    }


def _actor_label(actor: Any) -> str:
    try:
        return str(actor.get_actor_label())
    except Exception:
        return str(actor.get_name())


def _stage_art_actors() -> list[Any]:
    return [actor for actor in _all_actors() if actor_has_tag(actor, STAGE_TAG)]


def _rebuild_previous_stage_art() -> int:
    existing = _stage_art_actors()
    if not existing:
        return 0
    if not REBUILD_GENERATED_STAGE_ART:
        fail(f"Stage 13 already owns {len(existing)} actor(s); refusing duplicates.")

    destroyed = 0
    subsystem = _actor_subsystem()
    for actor in existing:
        try:
            if subsystem.destroy_actor(actor):
                destroyed += 1
        except Exception as error:
            fail(f"Unable to rebuild Stage 13 actor {_actor_label(actor)}: {error}")
    log(f"Stage 13 rebuild removed {destroyed} previously generated art actor(s).")
    return destroyed


def _manifest_rows_for_spring() -> list[dict[str, str]]:
    rows = []
    for row in approved_manifest_rows():
        districts = {
            value.strip().upper()
            for value in (row.get("district_pool") or "").split(";")
            if value.strip()
        }
        if "SPRING" in districts:
            rows.append(row)
    if not rows:
        fail("Approved production manifest has no Spring-enabled assets.")
    return rows


def _row_weight(row: dict[str, str]) -> float:
    try:
        return float(row.get("selection_weight") or 0.0)
    except Exception:
        return 0.0


def _build_asset_pools(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    pools: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        category = (row.get("category") or "").strip()
        if category:
            pools.setdefault(category, []).append(row)

    for category_rows in pools.values():
        category_rows.sort(
            key=lambda row: (
                -_row_weight(row),
                row.get("review_id", ""),
                row.get("asset_name", ""),
            )
        )
    return pools


def _require_pool(
    pools: dict[str, list[dict[str, str]]],
    category: str,
    *,
    asset_class: str | None = None,
) -> list[dict[str, str]]:
    rows = list(pools.get(category, ()))
    if asset_class:
        rows = [row for row in rows if row.get("asset_class") == asset_class]
    if not rows:
        suffix = f" ({asset_class})" if asset_class else ""
        fail(f"Spring production manifest is missing required pool: {category}{suffix}")
    return rows


def _optional_pool(
    pools: dict[str, list[dict[str, str]]],
    category: str,
    *,
    asset_class: str | None = None,
) -> list[dict[str, str]]:
    rows = list(pools.get(category, ()))
    if asset_class:
        rows = [row for row in rows if row.get("asset_class") == asset_class]
    return rows


_ASSET_CACHE: dict[str, Any] = {}


def _load_manifest_asset(row: dict[str, str]) -> Any:
    object_path = row["object_path"]
    if object_path in _ASSET_CACHE:
        return _ASSET_CACHE[object_path]
    if not editor_asset_exists(object_path):
        fail(
            "Approved manifest asset no longer resolves in Unreal: "
            f"{row.get('review_id')} -> {object_path}"
        )
    asset = unreal.load_asset(object_path)
    if asset is None:
        fail(f"Unable to load approved production asset: {object_path}")
    _ASSET_CACHE[object_path] = asset
    return asset


def _choose_row(rows: list[dict[str, str]], index: int, salt: int = 0) -> dict[str, str]:
    if not rows:
        fail("Internal error: attempted deterministic selection from an empty pool.")
    rng = random.Random(GLOBAL_SEED + salt * 1009 + index * 7919)
    total = sum(max(0.01, _row_weight(row)) for row in rows)
    value = rng.random() * total
    for row in rows:
        value -= max(0.01, _row_weight(row))
        if value <= 0.0:
            return row
    return rows[-1]


def _set_editor_layers(actor: Any) -> None:
    try:
        actor.set_editor_property("layers", [unreal.Name(name) for name in FINAL_ART_LAYERS])
    except Exception as error:
        warn(f"Unable to assign final-art Editor Layers to {_actor_label(actor)}: {error}")


def _set_collision(component: Any, enabled: bool) -> None:
    try:
        component.set_collision_enabled(
            unreal.CollisionEnabled.QUERY_AND_PHYSICS
            if enabled
            else unreal.CollisionEnabled.NO_COLLISION
        )
    except Exception as error:
        warn(f"Unable to configure art collision: {error}")


def _mesh_size_cm(mesh: Any) -> tuple[float, float, float] | None:
    method = getattr(mesh, "get_bounding_box", None)
    if method is None:
        return None
    try:
        box = method()
        minimum = box.min
        maximum = box.max
        return (
            max(1.0, float(maximum.x - minimum.x)),
            max(1.0, float(maximum.y - minimum.y)),
            max(1.0, float(maximum.z - minimum.z)),
        )
    except Exception:
        return None


def _fit_uniform_scale(mesh: Any, target_max_dimension_cm: float) -> float:
    size = _mesh_size_cm(mesh)
    if size is None:
        return 1.0
    native_max = max(size)
    if native_max <= 1.0:
        return 1.0
    return max(0.25, min(2.5, target_max_dimension_cm / native_max))


def _spawn_static_mesh(
    row: dict[str, str],
    *,
    label: str,
    stable_id: str,
    location: tuple[float, float, float],
    yaw: float,
    target_max_dimension_cm: float | None = None,
    collision: bool = False,
) -> Any:
    mesh = _load_manifest_asset(row)
    actor = _actor_subsystem().spawn_actor_from_class(
        unreal.StaticMeshActor,
        unreal.Vector(*location),
        unreal.Rotator(roll=0.0, pitch=0.0, yaw=yaw),
        transient=False,
    )
    if actor is None:
        fail(f"Unable to spawn Spring production actor: {label}")

    component = actor.get_editor_property("static_mesh_component")
    if component is None or not component.set_static_mesh(mesh):
        fail(f"Unable to assign {row['object_path']} to {label}")

    if target_max_dimension_cm is not None:
        scale = _fit_uniform_scale(mesh, target_max_dimension_cm)
        actor.set_actor_scale3d(unreal.Vector(scale, scale, scale))

    _set_collision(component, collision)
    actor.set_actor_label(label, mark_dirty=True)
    actor.set_folder_path(unreal.Name(ART_FOLDER))
    add_generation_tags(actor, stage=STAGE, district="Spring", stable_id=stable_id)
    _set_editor_layers(actor)
    try:
        actor.set_editor_property("is_spatially_loaded", True)
    except Exception as error:
        warn(f"Unable to configure spatial loading for {label}: {error}")
    return actor


def _apply_spring_road_material(road_material: Any) -> int:
    changed = 0
    for actor in _all_actors():
        if not actor_has_tag(actor, "ZS.Stage.Spring"):
            continue
        label = _actor_label(actor)
        if not (
            label.startswith("ZS_Spring_Road_")
            or label.startswith("ZS_Spring_Shortcut_")
        ):
            continue
        try:
            component = actor.get_editor_property("static_mesh_component")
        except Exception:
            component = None
        if component is None:
            continue
        try:
            component.set_material(0, road_material)
            changed += 1
        except Exception as error:
            warn(f"Unable to apply Spring asphalt to {label}: {error}")
    if changed <= 0:
        fail("Stage 13 found no Spring road/shortcut mesh to surface.")
    return changed


def _spawn_placement_series(
    rows: list[dict[str, str]],
    placements: tuple[tuple[float, float, float, float], ...],
    *,
    prefix: str,
    salt: int,
    target_max_dimension_cm: float | None = None,
) -> int:
    count = 0
    for index, (x, y, z, yaw) in enumerate(placements, start=1):
        row = _choose_row(rows, index, salt)
        _spawn_static_mesh(
            row,
            label=f"ZS_Art_Spring_{prefix}_{index:02d}",
            stable_id=f"Art.Spring.{prefix}.{index:02d}",
            location=(x, y, z),
            yaw=yaw,
            target_max_dimension_cm=target_max_dimension_cm,
            collision=False,
        )
        count += 1
    return count


def _spawn_scaled_architecture_series(
    rows: list[dict[str, str]],
    placements: tuple[tuple[float, float, float, float, float], ...],
    *,
    prefix: str,
    salt: int,
) -> int:
    if not rows:
        return 0
    count = 0
    for index, (x, y, z, yaw, target_size) in enumerate(placements, start=1):
        row = _choose_row(rows, index, salt)
        _spawn_static_mesh(
            row,
            label=f"ZS_Art_Spring_{prefix}_{index:02d}",
            stable_id=f"Art.Spring.{prefix}.{index:02d}",
            location=(x, y, z),
            yaw=yaw,
            target_max_dimension_cm=target_size,
            collision=False,
        )
        count += 1
    return count


def _set_property(obj: Any, name: str, value: Any) -> bool:
    if obj is None:
        return False
    try:
        obj.set_editor_property(name, value)
        return True
    except Exception:
        return False


def _spring_lighting_pass() -> dict[str, int]:
    sun_count = skylight_count = fog_count = atmosphere_count = 0

    for actor in _all_actors():
        if not actor_has_tag(actor, "ZS.Stage.LightingBaseline"):
            continue
        class_name = str(actor.get_class().get_name())

        if "DirectionalLight" in class_name:
            sun_count += 1
            actor.set_actor_rotation(unreal.Rotator(roll=0.0, pitch=-34.0, yaw=-24.0), False)
            try:
                component = actor.get_editor_property("directional_light_component")
            except Exception:
                component = None
            _set_property(component, "intensity", 6.5)
            _set_property(component, "light_color", unreal.Color(r=246, g=252, b=232, a=255))
            _set_property(component, "cast_shadows", True)

        elif "SkyLight" in class_name:
            skylight_count += 1
            try:
                component = actor.get_editor_property("light_component")
            except Exception:
                component = None
            _set_property(component, "intensity", 1.15)
            _set_property(component, "real_time_capture", True)

        elif "ExponentialHeightFog" in class_name:
            fog_count += 1
            try:
                component = actor.get_editor_property("component")
            except Exception:
                component = None
            if component is None:
                try:
                    values = actor.get_components_by_class(unreal.ExponentialHeightFogComponent) or []
                    component = values[0] if values else None
                except Exception:
                    component = None
            _set_property(component, "fog_density", 0.0065)
            _set_property(component, "fog_height_falloff", 0.18)
            _set_property(component, "fog_max_opacity", 0.42)
            _set_property(component, "enable_volumetric_fog", True)
            _set_property(component, "volumetric_fog_extinction_scale", 0.45)
            _set_property(
                component,
                "fog_inscattering_color",
                unreal.LinearColor(r=0.74, g=0.83, b=0.69, a=1.0),
            )

        elif "SkyAtmosphere" in class_name:
            atmosphere_count += 1

    if sun_count != 1 or skylight_count != 1 or fog_count != 1 or atmosphere_count != 1:
        warn(
            "Spring lighting pass expected one Sun/SkyLight/Fog/SkyAtmosphere; "
            f"found sun={sun_count}, skylight={skylight_count}, "
            f"fog={fog_count}, atmosphere={atmosphere_count}."
        )

    return {
        "sun": sun_count,
        "skylight": skylight_count,
        "fog": fog_count,
        "atmosphere": atmosphere_count,
    }


def _save_current_level() -> None:
    if not _level_subsystem().save_current_level():
        fail("Stage 13 generated production art but could not save L_ZS_World.")


def _position_viewport() -> None:
    try:
        _editor_subsystem().set_level_viewport_camera_info(
            unreal.Vector(-40500.0, 47500.0, 10500.0),
            unreal.Rotator(roll=0.0, pitch=-24.0, yaw=132.0),
        )
    except Exception as error:
        warn(f"Unable to position viewport for Spring production review: {error}")


def main():
    acceptance = _read_acceptance_report()
    creation_mode = _create_production_from_greybox()
    production_copy = _validate_production_copy()
    removed_previous = _rebuild_previous_stage_art()

    spring_rows = _manifest_rows_for_spring()
    pools = _build_asset_pools(spring_rows)

    road_rows = _require_pool(pools, "road_material", asset_class="MaterialInstanceConstant")
    vehicle_rows = _require_pool(pools, "vehicle", asset_class="StaticMesh")
    street_rows = _require_pool(pools, "street_prop", asset_class="StaticMesh")
    barrier_rows = _require_pool(pools, "barrier_fence", asset_class="StaticMesh")
    debris_rows = _require_pool(pools, "debris_rubble", asset_class="StaticMesh")

    facade_rows = _optional_pool(pools, "wall_facade", asset_class="StaticMesh")
    roof_rows = _optional_pool(pools, "roof", asset_class="StaticMesh")
    entrance_rows = _optional_pool(pools, "door_window", asset_class="StaticMesh")
    architecture_rows = _optional_pool(pools, "architecture_general", asset_class="StaticMesh")
    if not architecture_rows:
        architecture_rows = _optional_pool(pools, "structural", asset_class="StaticMesh")

    road_material = _load_manifest_asset(road_rows[0])
    surfaced_roads = _apply_spring_road_material(road_material)

    counts = {
        "vehicles": _spawn_placement_series(
            vehicle_rows, VEHICLE_PLACEMENTS, prefix="Vehicle", salt=11, target_max_dimension_cm=1200.0
        ),
        "street_props": _spawn_placement_series(
            street_rows, STREET_PROP_PLACEMENTS, prefix="StreetProp", salt=23, target_max_dimension_cm=550.0
        ),
        "barriers": _spawn_placement_series(
            barrier_rows, BARRIER_PLACEMENTS, prefix="Barrier", salt=37, target_max_dimension_cm=500.0
        ),
        "debris": _spawn_placement_series(
            debris_rows, DEBRIS_PLACEMENTS, prefix="Debris", salt=41, target_max_dimension_cm=650.0
        ),
        "facades": _spawn_scaled_architecture_series(
            facade_rows, FACADE_PLACEMENTS, prefix="Facade", salt=53
        ),
        "roofs": _spawn_scaled_architecture_series(
            roof_rows, ROOF_PLACEMENTS, prefix="Roof", salt=67
        ),
        "entrances": _spawn_scaled_architecture_series(
            entrance_rows, ENTRANCE_PLACEMENTS, prefix="Entrance", salt=79
        ),
        "landmarks": _spawn_scaled_architecture_series(
            architecture_rows, LANDMARK_PLACEMENTS, prefix="Landmark", salt=97
        ),
    }

    lighting = _spring_lighting_pass()
    _save_current_level()
    _position_viewport()

    generated_count = len(_stage_art_actors())
    missing_art_pools = []
    if not facade_rows:
        missing_art_pools.append("wall_facade")
    if not roof_rows:
        missing_art_pools.append("roof")
    if not entrance_rows:
        missing_art_pools.append("door_window")
    if not architecture_rows:
        missing_art_pools.append("architecture_general/structural")

    vegetation_categories = ("vegetation", "foliage", "tree", "bush", "ivy", "moss", "grass")
    available_vegetation = [category for category in vegetation_categories if pools.get(category)]
    vegetation_gap = not available_vegetation

    report = write_json_report(
        "spring_vertical_slice_stage13.json",
        {
            "stage": "13_SPRING_VERTICAL_SLICE",
            "status": "PASS",
            "production_map": PRODUCTION_MAP,
            "creation_mode": creation_mode,
            "greybox_acceptance_status": acceptance.get("status"),
            "production_copy_validation": production_copy,
            "removed_previous_stage_art": removed_previous,
            "surfaced_spring_roads": surfaced_roads,
            "generated_stage_art_actor_count": generated_count,
            "generated_by_category": counts,
            "lighting": lighting,
            "approved_spring_manifest_rows": len(spring_rows),
            "missing_optional_art_pools": missing_art_pools,
            "vegetation_pool_present": not vegetation_gap,
            "available_vegetation_categories": available_vegetation,
            "collision_policy": (
                "Stage-13 production dressing is non-blocking; validated greybox collision "
                "and navigation remain authoritative until Spring gameplay/performance QA."
            ),
            "next_gate": (
                "Spring final foliage/VFX/audio + horde performance validation"
                if vegetation_gap
                else "Spring VFX/audio + horde performance validation"
            ),
        },
    )

    total_dressing = sum(counts.values())
    message = (
        "STAGE 13 PASS — SPRING PRODUCTION VERTICAL SLICE CREATED.\n\n"
        f"Map: {PRODUCTION_MAP}\n"
        f"Base: {creation_mode}\n"
        f"Spring roads surfaced: {surfaced_roads}\n"
        f"Production dressing actors: {total_dressing}\n"
        f"Stage-13 tagged actors: {generated_count}\n"
        f"Vehicles: {counts['vehicles']} | Props: {counts['street_props']} | "
        f"Barriers: {counts['barriers']} | Debris: {counts['debris']}\n"
        f"Facades: {counts['facades']} | Roofs: {counts['roofs']} | "
        f"Entrances: {counts['entrances']} | Landmarks: {counts['landmarks']}\n"
        f"Vegetation pool approved: {'NO' if vegetation_gap else 'YES'}\n\n"
        "Gameplay/NavMesh topology was preserved.\n"
        f"Report: {report}"
    )
    if vegetation_gap:
        message += (
            "\n\nNOTE: The approved manifest still has no dedicated Spring vegetation/"
            "ivy/moss pool. The map is now materially dressed, but dense overgrowth remains "
            "the next visual-content gap; unrelated meshes were intentionally not substituted."
        )

    log(message.replace("\n", "  "))
    show_editor_message("ZombieSeasons — Spring Production Slice", message)
    return {
        "status": "PASS",
        "report": str(report),
        "vegetation_gap": vegetation_gap,
        "generated_actor_count": generated_count,
    }


if __name__ == "__main__":
    main()
