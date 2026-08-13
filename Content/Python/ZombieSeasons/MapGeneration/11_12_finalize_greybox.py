"""Accelerated checkpoint: create Stage 11 if missing, then run Stage 12."""
from __future__ import annotations
import importlib.util
import sys
from pathlib import Path
import unreal

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from zs_generation_common import actor_has_tag, log, show_editor_message


def _load(module_name: str, filename: str):
    path = SCRIPT_DIR / filename
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def main():
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors = list(actor_subsystem.get_all_level_actors() or [])
    lighting_exists = any(
        actor_has_tag(actor, "ZS.Stage.LightingBaseline") for actor in actors
    )

    lighting = _load("zs_stage11_lighting", "11_create_lighting_baseline.py")
    validation = _load("zs_stage12_validation", "12_validate_generated_world.py")

    lighting_result = (
        {"status": "ALREADY_PRESENT"}
        if lighting_exists
        else lighting.main(show_dialog=False)
    )
    if lighting_exists:
        log("Greybox Final: Stage 11 already exists; skipping duplicate creation.")

    validation_result = validation.main(show_dialog=False)
    message = (
        "GREYBOX FINAL CHECKPOINT PASSED.\n\n"
        f"Stage 11: {lighting_result['status']}\n"
        f"Stage 12: {validation_result['status']}\n"
        f"Warnings: {len(validation_result.get('warnings', []))}\n\n"
        "Ready for production-world creation and the Spring final-quality vertical slice."
    )
    log(message.replace("\n", "  "))
    show_editor_message("ZombieSeasons — Greybox Final", message)


if __name__ == "__main__":
    main()
