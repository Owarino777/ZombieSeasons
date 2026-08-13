"""Stage 11: neutral always-loaded lighting for L_ZS_World_Greybox."""
from __future__ import annotations
import sys
from pathlib import Path
from typing import Any
import unreal

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from zs_generation_common import (
    GREYBOX_MAP, actor_has_tag, add_generation_tags, fail, log,
    show_editor_message, write_json_report,
)

STAGE = "LightingBaseline"
STAGE_TAG = "ZS.Stage.LightingBaseline"
FOLDER = "ZombieSeasons/Lighting/Baseline"


def _editor_subsystem():
    value = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    if value is None:
        fail("UnrealEditorSubsystem is unavailable.")
    return value


def _level_subsystem():
    value = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if value is None:
        fail("LevelEditorSubsystem is unavailable.")
    return value


def _actor_subsystem():
    value = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    if value is None:
        fail("EditorActorSubsystem is unavailable.")
    return value


def _world():
    subsystem = _editor_subsystem()
    if subsystem.get_game_world():
        fail("Stop PIE before Stage 11.")
    value = subsystem.get_editor_world()
    if value is None:
        fail("No editor world is open.")
    return value


def _set(obj: Any, name: str, value: Any) -> bool:
    if obj is None:
        return False
    try:
        obj.set_editor_property(name, value)
        return True
    except Exception:
        return False


def _mark(actor: Any, label: str, stable_id: str) -> None:
    try:
        actor.set_actor_label(label, mark_dirty=True)
    except TypeError:
        actor.set_actor_label(label)
    actor.set_folder_path(unreal.Name(FOLDER))
    add_generation_tags(actor, stage=STAGE, district="Shared", stable_id=stable_id)
    _set(actor, "is_spatially_loaded", False)
    _set(actor, "is_main_world_only", True)


def _spawn(actor_class: Any, label: str, stable_id: str, location, rotation):
    actor = _actor_subsystem().spawn_actor_from_class(
        actor_class, location, rotation, transient=False
    )
    if actor is None:
        fail(f"Unable to spawn {label}.")
    _mark(actor, label, stable_id)
    return actor


def _fog_component(actor: Any):
    try:
        value = actor.get_editor_property("component")
        if value is not None:
            return value
    except Exception:
        pass
    try:
        values = actor.get_components_by_class(unreal.ExponentialHeightFogComponent) or []
        return values[0] if values else None
    except Exception:
        return None


def main(show_dialog: bool = True):
    current_world = _world()
    path = str(current_world.get_path_name())
    if not (path == GREYBOX_MAP or path.startswith(GREYBOX_MAP + ".")):
        fail("L_ZS_World_Greybox must be open for Stage 11.")

    loaded = list(_actor_subsystem().get_all_level_actors() or [])
    existing = [actor for actor in loaded if actor_has_tag(actor, STAGE_TAG)]
    if existing:
        fail(f"Stage 11 already exists ({len(existing)} actors); refusing duplicates.")

    required = ("DirectionalLight", "SkyAtmosphere", "SkyLight", "ExponentialHeightFog")
    missing = [name for name in required if not hasattr(unreal, name)]
    if missing:
        fail("Missing UE lighting classes: " + ", ".join(missing))

    sun = _spawn(
        unreal.DirectionalLight, "ZS_Lighting_Sun", "Lighting.Sun",
        unreal.Vector(0.0, 0.0, 12000.0),
        unreal.Rotator(roll=0.0, pitch=-42.0, yaw=-32.0),
    )
    atmosphere = _spawn(
        unreal.SkyAtmosphere, "ZS_Lighting_SkyAtmosphere", "Lighting.SkyAtmosphere",
        unreal.Vector(0.0, 0.0, 0.0),
        unreal.Rotator(roll=0.0, pitch=0.0, yaw=0.0),
    )
    skylight = _spawn(
        unreal.SkyLight, "ZS_Lighting_SkyLight", "Lighting.SkyLight",
        unreal.Vector(0.0, 0.0, 1000.0),
        unreal.Rotator(roll=0.0, pitch=0.0, yaw=0.0),
    )
    fog = _spawn(
        unreal.ExponentialHeightFog, "ZS_Lighting_Fog", "Lighting.Fog",
        unreal.Vector(0.0, 0.0, 0.0),
        unreal.Rotator(roll=0.0, pitch=0.0, yaw=0.0),
    )

    sun_component = sun.get_editor_property("directional_light_component")
    _set(sun_component, "mobility", unreal.ComponentMobility.MOVABLE)
    _set(sun_component, "intensity", 8.0)
    _set(sun_component, "light_color", unreal.Color(r=255, g=244, b=230, a=255))
    _set(sun_component, "cast_shadows", True)
    atmosphere_ok = _set(sun_component, "atmosphere_sun_light", True)
    if not atmosphere_ok and hasattr(sun_component, "set_atmosphere_sun_light"):
        try:
            sun_component.set_atmosphere_sun_light(True)
            atmosphere_ok = True
        except Exception:
            pass
    if not atmosphere_ok:
        fail("Unable to configure the DirectionalLight as the atmosphere sun.")

    sky_component = skylight.get_editor_property("light_component")
    _set(sky_component, "mobility", unreal.ComponentMobility.MOVABLE)
    _set(sky_component, "intensity", 0.8)
    capture_ok = _set(sky_component, "real_time_capture", True)
    if not capture_ok and hasattr(sky_component, "set_real_time_capture"):
        try:
            sky_component.set_real_time_capture(True)
        except Exception:
            pass

    fog_comp = _fog_component(fog)
    if fog_comp is not None:
        _set(fog_comp, "fog_density", 0.0025)
        _set(fog_comp, "fog_height_falloff", 0.25)
        _set(fog_comp, "fog_max_opacity", 0.18)
        _set(fog_comp, "enable_volumetric_fog", False)

    if not _level_subsystem().save_current_level():
        fail("Stage 11 failed to save the current level.")

    actor_paths = [str(actor.get_path_name()) for actor in (sun, atmosphere, skylight, fog)]
    report = write_json_report("lighting_baseline.json", {
        "stage": "11_LIGHTING_BASELINE",
        "status": "PASS",
        "map": path,
        "actor_count": len(actor_paths),
        "actors": actor_paths,
        "intent": "neutral greybox evaluation only",
        "final_seasonal_lighting": "DEFERRED_TO_ART_PASS",
    })
    message = f"Stage 11 PASS: neutral lighting created and saved.\nReport: {report}"
    log(message.replace("\n", "  "))
    if show_dialog:
        show_editor_message("ZombieSeasons — Stage 11", message)
    return {"status": "PASS", "report": str(report)}


if __name__ == "__main__":
    main()
