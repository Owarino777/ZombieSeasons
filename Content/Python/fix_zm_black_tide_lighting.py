import unreal
from typing import Iterable, Optional, Tuple


# ============================================================================
# ZombieSeasons - ZM Black Tide lighting repair
# Safe, idempotent lighting patch for Unreal Engine 5.5.x
# ============================================================================

EXPECTED_MAP_NAMES = {
    "ZM_BlackTide_ArtPass_V2",
    "ZM_BlackTide_ArtPass",
    "ZM_BlackTide_Greybox",
}

FILL_LIGHT_PREFIX = "Lighting_Fill_"
LIGHTING_FOLDER = "ZM_BlackTide_ArtPass/Lighting/Fill"

# Large non-shadow-casting fill lights keep the map readable while local
# colored lights preserve the horror atmosphere.
FILL_LIGHTS = (
    (
        "Spawn",
        unreal.Vector(0.0, 0.0, 900.0),
        (125, 165, 255),
        6500.0,
        6200.0,
    ),
    (
        "Theatre",
        unreal.Vector(-9000.0, 3200.0, 900.0),
        (255, 135, 90),
        6000.0,
        5200.0,
    ),
    (
        "Clinic",
        unreal.Vector(9000.0, 3200.0, 900.0),
        (145, 205, 255),
        6000.0,
        5200.0,
    ),
    (
        "Market",
        unreal.Vector(0.0, 10000.0, 1000.0),
        (170, 125, 255),
        6500.0,
        6200.0,
    ),
    (
        "PowerStation",
        unreal.Vector(0.0, -10200.0, 900.0),
        (255, 145, 75),
        6500.0,
        6200.0,
    ),
    (
        "UndergroundLab",
        unreal.Vector(0.0, -16000.0, -700.0),
        (95, 175, 255),
        7500.0,
        6200.0,
    ),
    (
        "SecretChamber",
        unreal.Vector(6200.0, -16000.0, -700.0),
        (190, 85, 255),
        8500.0,
        5000.0,
    ),
)


class LightingRepairError(RuntimeError):
    """Raised when the lighting patch cannot continue safely."""


def log(message: str) -> None:
    """Write an informational message to the Unreal log."""
    unreal.log(f"[ZM Black Tide Lighting] {message}")


def warn(message: str) -> None:
    """Write a warning message to the Unreal log."""
    unreal.log_warning(f"[ZM Black Tide Lighting] {message}")


def fail(message: str) -> None:
    """Abort the patch with a visible error."""
    unreal.log_error(f"[ZM Black Tide Lighting] {message}")
    raise LightingRepairError(message)


def safe_set(
    unreal_object: unreal.Object,
    property_name: str,
    value: object,
) -> bool:
    """Set an editor property without aborting the complete patch."""
    try:
        unreal_object.set_editor_property(property_name, value)
        return True
    except Exception as error:
        warn(
            f"Unable to set '{property_name}' on "
            f"'{unreal_object.get_name()}': {error}"
        )
        return False


def current_map_name() -> str:
    """Return the current editor map name."""
    editor_subsystem = unreal.get_editor_subsystem(
        unreal.UnrealEditorSubsystem
    )
    world = editor_subsystem.get_editor_world()

    if world is None:
        fail("No editor world is currently open.")

    return world.get_name()


def actor_has_tag(actor: unreal.Actor, tag: str) -> bool:
    """Check whether an actor contains an exact Unreal tag."""
    try:
        return unreal.Name(tag) in actor.get_editor_property("tags")
    except Exception:
        return False


def get_component(
    actor: unreal.Actor,
    component_class: type,
) -> Optional[unreal.ActorComponent]:
    """Return the requested actor component when available."""
    try:
        return actor.get_component_by_class(component_class)
    except Exception:
        return None


def delete_previous_fill_lights(actors: Iterable[unreal.Actor]) -> None:
    """Delete only fill lights previously created by this patch."""
    for actor in actors:
        try:
            if actor.get_actor_label().startswith(FILL_LIGHT_PREFIX):
                unreal.EditorLevelLibrary.destroy_actor(actor)
        except Exception as error:
            warn(f"Unable to remove old fill light: {error}")


def repair_directional_lights(actors: Iterable[unreal.Actor]) -> int:
    """Increase the moon contribution without creating daylight."""
    updated = 0

    for actor in actors:
        if not isinstance(actor, unreal.DirectionalLight):
            continue

        component = get_component(actor, unreal.DirectionalLightComponent)
        if component is None:
            continue

        safe_set(component, "intensity", 5.0)
        safe_set(
            component,
            "light_color",
            unreal.Color(160, 185, 255, 255),
        )
        safe_set(component, "atmosphere_sun_light", True)
        safe_set(component, "cast_shadows", True)
        updated += 1

    return updated


def repair_sky_lights(actors: Iterable[unreal.Actor]) -> int:
    """Raise ambient sky contribution and refresh real-time capture."""
    updated = 0

    for actor in actors:
        if not isinstance(actor, unreal.SkyLight):
            continue

        component = get_component(actor, unreal.SkyLightComponent)
        if component is None:
            continue

        safe_set(component, "intensity", 1.65)
        safe_set(component, "real_time_capture", True)
        safe_set(
            component,
            "light_color",
            unreal.Color(150, 175, 220, 255),
        )

        try:
            component.recapture_sky()
        except Exception as error:
            warn(f"Sky recapture could not be requested: {error}")

        updated += 1

    return updated


def repair_fog(actors: Iterable[unreal.Actor]) -> int:
    """Reduce excessive fog absorption while keeping volumetric depth."""
    updated = 0

    for actor in actors:
        if not isinstance(actor, unreal.ExponentialHeightFog):
            continue

        component = get_component(
            actor,
            unreal.ExponentialHeightFogComponent,
        )
        if component is None:
            continue

        safe_set(component, "fog_density", 0.010)
        safe_set(component, "fog_height_falloff", 0.28)
        safe_set(component, "volumetric_fog", True)
        safe_set(component, "volumetric_fog_extinction_scale", 0.65)
        safe_set(
            component,
            "fog_inscattering_color",
            unreal.LinearColor(0.065, 0.085, 0.14, 1.0),
        )
        updated += 1

    return updated


def repair_post_process(actors: Iterable[unreal.Actor]) -> int:
    """Restore readable exposure while preserving cinematic contrast."""
    updated = 0

    for actor in actors:
        if not isinstance(actor, unreal.PostProcessVolume):
            continue

        safe_set(actor, "unbound", True)
        safe_set(actor, "blend_weight", 1.0)

        try:
            settings = actor.get_editor_property("settings")

            safe_set(settings, "override_auto_exposure_method", True)
            safe_set(
                settings,
                "auto_exposure_method",
                unreal.AutoExposureMethod.AEM_HISTOGRAM,
            )

            safe_set(settings, "override_auto_exposure_bias", True)
            safe_set(settings, "auto_exposure_bias", 1.35)

            # Unreal changed some exposure property names between versions.
            # All assignments are attempted safely for UE 5.5 compatibility.
            safe_set(
                settings,
                "override_auto_exposure_min_brightness",
                True,
            )
            safe_set(settings, "auto_exposure_min_brightness", 0.65)
            safe_set(
                settings,
                "override_auto_exposure_max_brightness",
                True,
            )
            safe_set(settings, "auto_exposure_max_brightness", 2.5)

            safe_set(settings, "override_auto_exposure_min_ev100", True)
            safe_set(settings, "auto_exposure_min_ev100", -1.0)
            safe_set(settings, "override_auto_exposure_max_ev100", True)
            safe_set(settings, "auto_exposure_max_ev100", 4.0)

            safe_set(settings, "override_bloom_intensity", True)
            safe_set(settings, "bloom_intensity", 0.30)

            safe_set(settings, "override_vignette_intensity", True)
            safe_set(settings, "vignette_intensity", 0.22)

            safe_set(settings, "override_color_saturation", True)
            safe_set(
                settings,
                "color_saturation",
                unreal.Vector4(0.95, 0.97, 1.0, 1.0),
            )

            safe_set(actor, "settings", settings)
            updated += 1
        except Exception as error:
            warn(
                f"Post-process volume '{actor.get_actor_label()}' "
                f"could not be repaired: {error}"
            )

    return updated


def repair_existing_local_lights(
    actors: Iterable[unreal.Actor],
) -> Tuple[int, int]:
    """Boost existing art lights while retaining their original colors."""
    point_count = 0
    spot_count = 0

    for actor in actors:
        is_art_light = (
            actor_has_tag(actor, "ZS_ArtLight")
            or actor.get_actor_label().startswith("ZoneLight_")
            or actor.get_actor_label().startswith("Light_")
        )

        if not is_art_light:
            continue

        if isinstance(actor, unreal.PointLight):
            component = get_component(actor, unreal.PointLightComponent)
            if component is None:
                continue

            try:
                current_intensity = float(
                    component.get_editor_property("intensity")
                )
            except Exception:
                current_intensity = 5000.0

            try:
                current_radius = float(
                    component.get_editor_property("attenuation_radius")
                )
            except Exception:
                current_radius = 2000.0

            safe_set(
                component,
                "intensity",
                min(max(current_intensity * 2.25, 8000.0), 22000.0),
            )
            safe_set(
                component,
                "attenuation_radius",
                max(current_radius, 3400.0),
            )
            point_count += 1

        elif isinstance(actor, unreal.SpotLight):
            component = get_component(actor, unreal.SpotLightComponent)
            if component is None:
                continue

            try:
                current_intensity = float(
                    component.get_editor_property("intensity")
                )
            except Exception:
                current_intensity = 5000.0

            try:
                current_radius = float(
                    component.get_editor_property("attenuation_radius")
                )
            except Exception:
                current_radius = 2200.0

            safe_set(
                component,
                "intensity",
                min(max(current_intensity * 2.0, 9000.0), 24000.0),
            )
            safe_set(
                component,
                "attenuation_radius",
                max(current_radius, 3800.0),
            )
            spot_count += 1

    return point_count, spot_count


def spawn_fill_light(
    suffix: str,
    location: unreal.Vector,
    color: Tuple[int, int, int],
    intensity: float,
    radius: float,
) -> unreal.PointLight:
    """Create one broad non-shadow-casting navigation fill light."""
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.PointLight,
        location,
        unreal.Rotator(0.0, 0.0, 0.0),
    )

    if actor is None:
        fail(f"Unable to create fill light '{suffix}'.")

    actor.set_actor_label(f"{FILL_LIGHT_PREFIX}{suffix}")
    actor.set_folder_path(unreal.Name(LIGHTING_FOLDER))
    actor.set_editor_property(
        "tags",
        [
            unreal.Name("ZS_LightingRepair"),
            unreal.Name("ZS_FillLight"),
        ],
    )

    component = get_component(actor, unreal.PointLightComponent)

    if component is not None:
        safe_set(component, "light_color", unreal.Color(*color, 255))
        safe_set(component, "intensity", intensity)
        safe_set(component, "attenuation_radius", radius)
        safe_set(component, "cast_shadows", False)
        safe_set(component, "source_radius", 100.0)
        safe_set(component, "soft_source_radius", 250.0)

    return actor


def save_level() -> None:
    """Save the repaired map."""
    if not unreal.EditorLevelLibrary.save_current_level():
        fail("The lighting changes could not be saved.")


def repair_lighting() -> None:
    """Apply the complete non-destructive lighting repair."""
    map_name = current_map_name()

    if map_name not in EXPECTED_MAP_NAMES:
        fail(
            "Open ZM_BlackTide_ArtPass_V2 before running this script.\n"
            f"Current map: {map_name}"
        )

    actors = unreal.EditorLevelLibrary.get_all_level_actors()
    delete_previous_fill_lights(actors)

    # Refresh the actor list after removing previous fill lights.
    actors = unreal.EditorLevelLibrary.get_all_level_actors()

    directional_count = repair_directional_lights(actors)
    sky_count = repair_sky_lights(actors)
    fog_count = repair_fog(actors)
    post_process_count = repair_post_process(actors)
    point_count, spot_count = repair_existing_local_lights(actors)

    for suffix, location, color, intensity, radius in FILL_LIGHTS:
        spawn_fill_light(
            suffix,
            location,
            color,
            intensity,
            radius,
        )

    save_level()

    log(
        "Lighting repaired successfully: "
        f"{directional_count} directional, "
        f"{sky_count} sky, "
        f"{fog_count} fog, "
        f"{post_process_count} post-process, "
        f"{point_count} point lights, "
        f"{spot_count} spot lights."
    )

    unreal.EditorDialog.show_message(
        "ZombieSeasons - Lighting repaired",
        (
            "L'éclairage de ZM Black Tide a été corrigé.\n\n"
            "- exposition augmentée\n"
            "- clair de lune renforcé\n"
            "- lumière ambiante restaurée\n"
            "- brouillard moins absorbant\n"
            "- lumières locales renforcées\n"
            "- sept lumières de remplissage ajoutées\n\n"
            "La map reste nocturne, mais elle doit maintenant être lisible."
        ),
        unreal.AppMsgType.OK,
    )


try:
    repair_lighting()
except LightingRepairError as error:
    unreal.EditorDialog.show_message(
        "ZombieSeasons - Lighting repair stopped",
        str(error),
        unreal.AppMsgType.OK,
    )
except Exception as error:
    unreal.log_error(
        f"[ZM Black Tide Lighting] Unexpected error: {error}"
    )
    unreal.EditorDialog.show_message(
        "ZombieSeasons - Unexpected lighting error",
        (
            "La correction de lumière a rencontré une erreur inattendue.\n\n"
            f"{error}\n\n"
            "Consulte le Journal de sortie pour la ligne exacte."
        ),
        unreal.AppMsgType.OK,
    )