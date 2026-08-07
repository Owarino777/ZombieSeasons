"""Validate ZombieSeasons production-generation prerequisites without mutating maps.

Run from Unreal Editor:

py "C:/Users/malik/Documents/Unreal Projects/ZombieSeasons/Content/Python/ZombieSeasons/MapGeneration/00_validate_environment.py"

The validator intentionally avoids loading the 201 production assets. It checks exact
object-path existence through EditorAssetLibrary, project configuration, required
Blueprint paths, disk headroom, destination-map state, and the final manifest.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import unreal


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from zs_generation_common import (  # noqa: E402
    GREYBOX_MAP,
    MANIFEST_PATH,
    PROJECT_ROOT,
    approved_manifest_rows,
    editor_asset_exists,
    log,
    show_editor_message,
    warn,
    write_json_report,
)


DEFAULT_ENGINE = PROJECT_ROOT / "Config" / "DefaultEngine.ini"
UPROJECT = PROJECT_ROOT / "ZombieSeasons.uproject"
MIN_FREE_DISK_GB = 30.0
RECOMMENDED_FREE_DISK_GB = 60.0
EXPECTED_APPROVED_COUNT = 201
EXPECTED_ENGINE_PREFIX = "5.5"

REQUIRED_EXISTING_BLUEPRINTS = (
    "/Game/TopDownShooter/Core/BP_Enemy.BP_Enemy",
    "/Game/TopDownShooter/Core/BP_EnemySpawner.BP_EnemySpawner",
    "/Game/TopDownShooter/Core/BP_FPSCharacter.BP_FPSCharacter",
    "/Game/TopDownShooter/Core/BP_FPSGameMode.BP_FPSGameMode",
    "/Game/TopDownShooter/Core/BP_GameMode.BP_GameMode",
    "/Game/TopDownShooter/Core/BP_Hero.BP_Hero",
    "/Game/TopDownShooter/Core/Weapon/BP_Gun.BP_Gun",
    "/Game/TopDownShooter/Core/WBP_InGameHUD.WBP_InGameHUD",
)

PLANNED_ADAPTERS = (
    "/Game/ZombieSeasons/Blueprints/Encounters/BP_ZS_ZombieSpawnPoint.BP_ZS_ZombieSpawnPoint",
    "/Game/ZombieSeasons/Blueprints/Encounters/BP_ZS_SpawnGroup.BP_ZS_SpawnGroup",
    "/Game/ZombieSeasons/Blueprints/Encounters/BP_ZS_HordeTrigger.BP_ZS_HordeTrigger",
    "/Game/ZombieSeasons/Blueprints/Objectives/BP_ZS_ObjectiveTrigger.BP_ZS_ObjectiveTrigger",
    "/Game/ZombieSeasons/Blueprints/World/BP_ZS_DistrictGate.BP_ZS_DistrictGate",
    "/Game/ZombieSeasons/Blueprints/Loot/BP_ZS_LootPoint.BP_ZS_LootPoint",
    "/Game/ZombieSeasons/Blueprints/World/BP_ZS_SafeZoneVolume.BP_ZS_SafeZoneVolume",
    "/Game/ZombieSeasons/Blueprints/Objectives/BP_ZS_ExtractionController.BP_ZS_ExtractionController",
)


def check_configuration() -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if not DEFAULT_ENGINE.is_file():
        errors.append(f"Missing DefaultEngine.ini: {DEFAULT_ENGINE}")
    else:
        text = DEFAULT_ENGINE.read_text(encoding="utf-8-sig", errors="replace")
        compact = "".join(text.split()).lower()
        if "r.virtualtextures=true" not in compact:
            errors.append("DefaultEngine.ini does not enable r.VirtualTextures=True.")

    if not UPROJECT.is_file():
        errors.append(f"Missing .uproject file: {UPROJECT}")
    else:
        try:
            payload = json.loads(UPROJECT.read_text(encoding="utf-8-sig"))
            plugins = {
                str(item.get("Name")): bool(item.get("Enabled"))
                for item in payload.get("Plugins", [])
                if isinstance(item, dict)
            }
            if not plugins.get("ChaosVehiclesPlugin", False):
                warnings.append(
                    "ChaosVehiclesPlugin is not explicitly enabled in ZombieSeasons.uproject."
                )
        except Exception as error:
            errors.append(f"Unable to parse ZombieSeasons.uproject: {error}")

    return errors, warnings


def check_editor_python_capabilities() -> tuple[list[str], list[str]]:
    """Verify the editor Python API through symbols exposed by the embedded runtime.

    Unreal injects its ``unreal`` module into the embedded interpreter and, in UE 5.5,
    that module can legitimately have ``__spec__`` set to ``None``. Calling
    ``importlib.util.find_spec('unreal')`` in that state raises ``ValueError`` even
    though the module is loaded and fully usable. Reaching this function already
    proves the import succeeded, so capability checks must rely on API symbols only.
    """
    errors: list[str] = []
    warnings: list[str] = []

    required_symbols = (
        "EditorAssetLibrary",
        "EditorActorSubsystem",
        "LevelEditorSubsystem",
        "EditorDialog",
    )
    for symbol in required_symbols:
        if not hasattr(unreal, symbol):
            errors.append(f"Required Unreal Python symbol is unavailable: unreal.{symbol}")

    if sys.modules.get("unreal") is not unreal:
        warnings.append(
            "The embedded Unreal Python module is not registered in sys.modules as expected."
        )

    return errors, warnings


def check_manifest() -> tuple[list[str], list[str], dict[str, object]]:
    errors: list[str] = []
    warnings: list[str] = []
    details: dict[str, object] = {}

    try:
        rows = approved_manifest_rows()
    except Exception as error:
        return [str(error)], warnings, details

    details["manifest_path"] = str(MANIFEST_PATH)
    details["approved_generator_enabled_count"] = len(rows)

    if len(rows) != EXPECTED_APPROVED_COUNT:
        errors.append(
            f"Expected {EXPECTED_APPROVED_COUNT} generator-enabled APPROVED assets, "
            f"found {len(rows)}."
        )

    missing_paths: list[str] = []
    for row in rows:
        object_path = row["object_path"]
        if not editor_asset_exists(object_path):
            missing_paths.append(object_path)

    details["missing_approved_asset_count"] = len(missing_paths)
    details["missing_approved_asset_paths"] = missing_paths
    if missing_paths:
        errors.append(
            f"{len(missing_paths)} approved production asset paths do not exist in the editor."
        )

    return errors, warnings, details


def check_blueprints() -> tuple[list[str], list[str], dict[str, object]]:
    errors: list[str] = []
    warnings: list[str] = []

    missing_required = [
        path for path in REQUIRED_EXISTING_BLUEPRINTS if not editor_asset_exists(path)
    ]
    missing_adapters = [
        path for path in PLANNED_ADAPTERS if not editor_asset_exists(path)
    ]

    if missing_required:
        errors.append(
            f"{len(missing_required)} required existing gameplay Blueprint assets are missing."
        )

    if missing_adapters:
        warnings.append(
            f"{len(missing_adapters)} planned ZombieSeasons adapter Blueprints do not exist yet; "
            "greybox gameplay generation must use deterministic markers until adapters are built."
        )

    return errors, warnings, {
        "missing_required_blueprints": missing_required,
        "missing_planned_adapters": missing_adapters,
    }


def check_disk() -> tuple[list[str], list[str], dict[str, object]]:
    errors: list[str] = []
    warnings: list[str] = []
    usage = shutil.disk_usage(PROJECT_ROOT)
    free_gb = usage.free / (1024 ** 3)

    if free_gb < MIN_FREE_DISK_GB:
        errors.append(
            f"Only {free_gb:.1f} GB free on the project drive; at least "
            f"{MIN_FREE_DISK_GB:.0f} GB is required before generation."
        )
    elif free_gb < RECOMMENDED_FREE_DISK_GB:
        warnings.append(
            f"Only {free_gb:.1f} GB free on the project drive; "
            f"{RECOMMENDED_FREE_DISK_GB:.0f}+ GB is recommended."
        )

    return errors, warnings, {"free_disk_gb": round(free_gb, 2)}


def check_destination() -> tuple[list[str], list[str], dict[str, object]]:
    warnings: list[str] = []
    exists = editor_asset_exists(GREYBOX_MAP)
    if exists:
        warnings.append(
            "Greybox destination map already exists. CREATE mode must refuse to overwrite it; "
            "future REBUILD_GENERATED mode may operate only on tagged generated actors."
        )
    return [], warnings, {"greybox_destination_exists": exists, "greybox_map": GREYBOX_MAP}


def run() -> None:
    all_errors: list[str] = []
    all_warnings: list[str] = []
    details: dict[str, object] = {}

    engine_version = str(unreal.SystemLibrary.get_engine_version())
    details["engine_version"] = engine_version
    details["project_root"] = str(PROJECT_ROOT)

    if not engine_version.startswith(EXPECTED_ENGINE_PREFIX):
        all_warnings.append(
            f"Recorded production baseline is UE {EXPECTED_ENGINE_PREFIX}.x, "
            f"current editor reports {engine_version}."
        )

    checks = (
        ("configuration", check_configuration),
        ("python_capabilities", check_editor_python_capabilities),
        ("manifest", check_manifest),
        ("blueprints", check_blueprints),
        ("disk", check_disk),
        ("destination", check_destination),
    )

    for name, check in checks:
        result = check()
        if len(result) == 2:
            errors, warnings = result
            check_details: dict[str, object] = {}
        else:
            errors, warnings, check_details = result
        all_errors.extend(errors)
        all_warnings.extend(warnings)
        details[name] = check_details

    payload = {
        "status": "PASS" if not all_errors else "FAIL",
        "errors": all_errors,
        "warnings": all_warnings,
        "details": details,
        "mutates_maps": False,
        "loads_production_assets_intentionally": False,
    }
    report = write_json_report("environment_validation.json", payload)

    for message in all_warnings:
        warn(message)
    for message in all_errors:
        unreal.log_error(f"[ZombieSeasonsGeneration] {message}")

    if all_errors:
        summary = (
            f"Environment validation FAILED.\n\n"
            f"Errors: {len(all_errors)}\n"
            f"Warnings: {len(all_warnings)}\n\n"
            f"Report:\n{report}"
        )
    else:
        summary = (
            "Environment validation PASSED.\n\n"
            f"Approved assets verified: {EXPECTED_APPROVED_COUNT}\n"
            f"Warnings: {len(all_warnings)}\n\n"
            f"Report:\n{report}"
        )

    log(summary.replace("\n", " "))
    show_editor_message("ZombieSeasons World Generation", summary)


if __name__ == "__main__":
    run()
