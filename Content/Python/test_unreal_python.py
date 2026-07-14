import unreal


def main() -> None:
    """Verify that Unreal Python scripting is available."""

    unreal.log("ZombieSeasons: Python scripting started.")

    editor_subsystem = unreal.get_editor_subsystem(
        unreal.UnrealEditorSubsystem
    )

    world = editor_subsystem.get_editor_world()

    if world is None:
        unreal.log_error("ZombieSeasons: No editor world is currently loaded.")
        return

    unreal.log(
        f"ZombieSeasons: Current world is '{world.get_name()}'."
    )

    unreal.EditorDialog.show_message(
        "ZombieSeasons",
        "Python fonctionne correctement dans Unreal Engine.",
        unreal.AppMsgType.OK,
    )


main()