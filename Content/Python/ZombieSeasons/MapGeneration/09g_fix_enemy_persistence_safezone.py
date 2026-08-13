"""Stage 9G - keep runtime zombies from vanishing at the Hub boundary.

The greybox gameplay runtime historically used the design SafeZoneRadius tag as a
hard kill radius. That made pursuing zombies disappear abruptly when crossing the
Hub boundary. For the production flow, the 6000 cm value remains preserved as a
design-only tag while the runtime kill radius is reduced to 1 cm.

Run with L_ZS_World_Greybox open and PIE stopped.
"""

import unreal

STAGE_TAG = "ZS.Stage.GameplayLayout"
SAFE_ZONE_ROLE_TAG = "ZS.MarkerType.SafeZoneContract"
RUNTIME_RADIUS_PREFIX = "ZS.SafeZoneRadius."
DESIGN_RADIUS_PREFIX = "ZS.DesignSafeZoneRadius."
RUNTIME_RADIUS_CM = 1.0


def _tag_strings(actor):
    return [str(tag) for tag in actor.get_editor_property("tags")]


def _has_tag(tags, expected):
    return expected in tags


def main():
    editor_subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    if not editor_subsystem:
        raise RuntimeError("UnrealEditorSubsystem is unavailable.")

    # UE 5.5's Python World wrapper does not expose a `world_type` property.
    # Ask the editor subsystem directly whether a PIE/game world exists instead.
    game_world = editor_subsystem.get_game_world()
    if game_world:
        raise RuntimeError("Stop PIE before running Stage 9G.")

    world = editor_subsystem.get_editor_world()
    if not world:
        raise RuntimeError("No editor world is currently open.")

    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    if not actor_subsystem:
        raise RuntimeError("EditorActorSubsystem is unavailable.")

    actors = actor_subsystem.get_all_level_actors()

    changed = 0
    found = 0

    for actor in actors:
        if not actor:
            continue

        tags = _tag_strings(actor)
        if not _has_tag(tags, STAGE_TAG) or not _has_tag(tags, SAFE_ZONE_ROLE_TAG):
            continue

        found += 1
        original_radius = None
        new_tags = []

        for tag in tags:
            if tag.startswith(RUNTIME_RADIUS_PREFIX):
                original_radius = tag[len(RUNTIME_RADIUS_PREFIX):]
                continue
            new_tags.append(tag)

        if original_radius is None:
            unreal.log_warning(
                "Stage 9G: SafeZoneContract found without a runtime radius tag: {}".format(
                    actor.get_actor_label()
                )
            )
            continue

        design_tag = DESIGN_RADIUS_PREFIX + original_radius
        if not any(tag.startswith(DESIGN_RADIUS_PREFIX) for tag in new_tags):
            new_tags.append(design_tag)

        runtime_radius_tag = RUNTIME_RADIUS_PREFIX + str(RUNTIME_RADIUS_CM).rstrip("0").rstrip(".")
        new_tags.append(runtime_radius_tag)
        actor.set_editor_property("tags", [unreal.Name(tag) for tag in new_tags])
        changed += 1

        unreal.log(
            "Stage 9G: {} runtime safe-zone radius {} cm -> {} cm; design radius preserved as {}".format(
                actor.get_actor_label(),
                original_radius,
                RUNTIME_RADIUS_CM,
                design_tag,
            )
        )

    if found == 0:
        raise RuntimeError(
            "Stage 9G: no loaded SafeZoneContract marker was found. Load the Hub/central World Partition cells and retry."
        )

    if changed == 0:
        unreal.log("Stage 9G PASS: no SafeZoneContract changes were required.")
        return

    if not unreal.EditorLevelLibrary.save_current_level():
        raise RuntimeError("Stage 9G changed the safe-zone marker but failed to save the current level.")

    unreal.log("Stage 9G PASS: {} SafeZoneContract actor(s) updated and level saved.".format(changed))


if __name__ == "__main__":
    main()
