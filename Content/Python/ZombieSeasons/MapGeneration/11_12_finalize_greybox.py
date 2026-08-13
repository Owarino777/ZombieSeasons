"""Accelerated checkpoint: create Stage 11 if missing, then run Stage 12."""
from __future__ import annotations

import hashlib
import importlib
import sys
import types
from pathlib import Path
from typing import Any

import unreal

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from zs_generation_common import actor_has_tag, fail, log, show_editor_message


STAGE12_REQUIRED_SOURCE_FRAGMENTS = (
    'if district == "Hub" and math.hypot(location.x, location.y) < HUB_PROTECTED_RADIUS:',
    "Hub-owned zombie spawn marker(s) are inside the 6000 cm protected Hub radius.",
)

STAGE12_FORBIDDEN_SOURCE_FRAGMENTS = (
    "zombie spawn marker(s) are inside the 6000 cm Hub radius.",
    "standard zombie spawn marker(s) are inside the protected 6000 cm Hub radius.",
)


def _read_source(filename: str) -> tuple[Path, str, str]:
    path = (SCRIPT_DIR / filename).resolve()
    if not path.is_file():
        fail(f"Required generation script does not exist: {path}")

    source = path.read_text(encoding="utf-8-sig")
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    return path, source, digest


def _validate_stage12_source(path: Path, source: str) -> None:
    missing = [
        fragment
        for fragment in STAGE12_REQUIRED_SOURCE_FRAGMENTS
        if fragment not in source
    ]
    forbidden = [
        fragment
        for fragment in STAGE12_FORBIDDEN_SOURCE_FRAGMENTS
        if fragment in source
    ]

    if missing or forbidden:
        details = []
        if missing:
            details.append(
                "missing required revision marker(s): "
                + " | ".join(repr(value) for value in missing)
            )
        if forbidden:
            details.append(
                "legacy validation marker(s) still present: "
                + " | ".join(repr(value) for value in forbidden)
            )

        fail(
            "Stage 12 source revision check failed before execution. "
            f"File: {path}. "
            + " ".join(details)
        )


def _load_source_module(
    module_name: str,
    filename: str,
    *,
    validate_source: bool = False,
) -> tuple[Any, Path, str]:
    path, source, digest = _read_source(filename)

    if validate_source:
        _validate_stage12_source(path, source)

    # Read and compile the current file contents directly.
    # This deliberately bypasses importlib bytecode/module caching.
    importlib.invalidate_caches()
    sys.modules.pop(module_name, None)

    module = types.ModuleType(module_name)
    module.__file__ = str(path)
    module.__package__ = None
    sys.modules[module_name] = module

    try:
        code = compile(source, str(path), "exec", dont_inherit=True)
        exec(code, module.__dict__)
    except Exception:
        sys.modules.pop(module_name, None)
        raise

    return module, path, digest


def main():
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    if actor_subsystem is None:
        fail("EditorActorSubsystem is unavailable.")

    actors = list(actor_subsystem.get_all_level_actors() or [])
    lighting_exists = any(
        actor_has_tag(actor, "ZS.Stage.LightingBaseline") for actor in actors
    )

    lighting, lighting_path, lighting_digest = _load_source_module(
        "zs_stage11_lighting_runtime",
        "11_create_lighting_baseline.py",
    )
    validation, validation_path, validation_digest = _load_source_module(
        "zs_stage12_validation_runtime",
        "12_validate_generated_world.py",
        validate_source=True,
    )

    log(
        "Greybox Final: source-locked scripts loaded directly from disk.  "
        f"Stage 11: {lighting_path} [sha256:{lighting_digest[:12]}]  "
        f"Stage 12: {validation_path} [sha256:{validation_digest[:12]}]"
    )

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
        f"Warnings: {len(validation_result.get('warnings', []))}\n"
        f"Stage 12 source: sha256:{validation_digest[:12]}\n\n"
        "Ready for production-world creation and the Spring final-quality vertical slice."
    )
    log(message.replace("\n", "  "))
    show_editor_message("ZombieSeasons — Greybox Final", message)


if __name__ == "__main__":
    main()
