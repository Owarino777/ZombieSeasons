"""Export a reproducible Unreal Editor audit for ZombieSeasons.

Required editor plugins:
- Python Editor Script Plugin
- Editor Scripting Utilities

Output:
Saved/ZombieSeasonsAudit/

The audit scans project content (/Game) and Fab-mounted content (/Fab).
It intentionally does not scan the complete /Engine mount.
"""

from __future__ import annotations

import csv
import json
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import unreal


AUDIT_DIRECTORY_NAME = "ZombieSeasonsAudit"
CONTENT_ROOTS = ("/Game", "/Fab")
BLUEPRINT_ASSET_CLASSES = {"Blueprint", "AnimBlueprint", "WidgetBlueprint"}


def log(message: str) -> None:
    """Write an informational message to the Unreal log."""
    unreal.log(f"[ZombieSeasonsAudit] {message}")


def log_warning(message: str) -> None:
    """Write a warning without aborting the audit."""
    unreal.log_warning(f"[ZombieSeasonsAudit] {message}")


def log_error(message: str) -> None:
    """Write an error to the Unreal log."""
    unreal.log_error(f"[ZombieSeasonsAudit] {message}")


def safe_string(value: Any) -> str:
    """Convert Unreal/Python values to text without raising."""
    if value is None:
        return ""

    try:
        return str(value)
    except Exception:
        return repr(value)


def get_project_root() -> Path:
    """Return the absolute project directory."""
    project_dir = unreal.Paths.convert_relative_path_to_full(
        unreal.Paths.project_dir()
    )
    return Path(project_dir).resolve()


def get_output_directory() -> Path:
    """Create and return the audit output directory."""
    output_directory = get_project_root() / "Saved" / AUDIT_DIRECTORY_NAME
    output_directory.mkdir(parents=True, exist_ok=True)
    return output_directory


def write_csv(
    path: Path,
    fieldnames: list[str],
    rows: Iterable[dict[str, Any]],
) -> None:
    """Write a UTF-8 CSV file with a BOM for spreadsheet compatibility."""
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()

        for row in rows:
            writer.writerow(
                {key: safe_string(row.get(key, "")) for key in fieldnames}
            )


def write_json(path: Path, payload: Any) -> None:
    """Write a deterministic readable JSON file."""
    with path.open("w", encoding="utf-8") as stream:
        json.dump(
            payload,
            stream,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )


def get_asset_registry() -> unreal.AssetRegistry:
    """Return Unreal's Asset Registry subsystem."""
    return unreal.AssetRegistryHelpers.get_asset_registry()


def infer_mount_point(package_name: str) -> str:
    """Return the configured content root containing a package."""
    for root in CONTENT_ROOTS:
        if package_name == root or package_name.startswith(f"{root}/"):
            return root

    return "UNKNOWN"


def get_asset_object_path(asset_data: unreal.AssetData) -> str:
    """Build a UE 5.5-compatible object path from AssetData metadata.

    Unreal Engine 5.5 Python AssetData does not expose get_soft_object_path().
    A regular asset object path is deterministically package_name.asset_name.
    """
    package_name = safe_string(asset_data.package_name)
    asset_name = safe_string(asset_data.asset_name)

    if not package_name or not asset_name:
        return ""

    return f"{package_name}.{asset_name}"


def get_all_relevant_assets() -> list[unreal.AssetData]:
    """Collect unique assets under /Game and /Fab."""
    registry = get_asset_registry()
    registry.search_all_assets(True)

    assets_by_object_path: dict[str, unreal.AssetData] = {}

    for root in CONTENT_ROOTS:
        try:
            root_assets = registry.get_assets_by_path(
                unreal.Name(root),
                recursive=True,
            )
        except Exception as error:
            log_warning(f"Unable to scan mount '{root}': {error}")
            continue

        log(f"Found {len(root_assets)} registry entries under {root}")

        for asset_data in root_assets:
            object_path = get_asset_object_path(asset_data)

            if not object_path:
                log_warning(
                    "Skipping AssetData with missing package/name: "
                    f"{safe_string(asset_data)}"
                )
                continue

            assets_by_object_path[object_path] = asset_data

    assets = list(assets_by_object_path.values())
    assets.sort(
        key=lambda item: (
            safe_string(item.package_name).lower(),
            safe_string(item.asset_name).lower(),
        )
    )
    return assets


def get_asset_class_name(asset_data: unreal.AssetData) -> str:
    """Return the asset class name across compatible Unreal API variants."""
    try:
        class_path = asset_data.asset_class_path
        return safe_string(class_path.asset_name)
    except Exception:
        try:
            return safe_string(asset_data.asset_class)
        except Exception:
            return "Unknown"


def get_asset_tags(asset_data: unreal.AssetData) -> dict[str, str]:
    """Export registry tags when the API exposes them."""
    result: dict[str, str] = {}

    try:
        tags_and_values = asset_data.tags_and_values

        for key in tags_and_values.keys():
            result[safe_string(key)] = safe_string(tags_and_values[key])
    except Exception as error:
        result["__audit_error__"] = safe_string(error)

    return result


def get_dependencies(package_name: str) -> list[str]:
    """Return hard/soft package dependencies for an asset package."""
    try:
        dependency_options = unreal.AssetRegistryDependencyOptions(
            include_soft_package_references=True,
            include_hard_package_references=True,
            include_searchable_names=False,
            include_soft_management_references=True,
            include_hard_management_references=True,
        )
        dependencies = get_asset_registry().get_dependencies(
            unreal.Name(package_name),
            dependency_options,
        )
        return sorted(safe_string(item) for item in dependencies)
    except Exception as error:
        log_warning(
            f"Unable to resolve dependencies for {package_name}: {error}"
        )
        return []


def export_assets(
    output_directory: Path,
    assets: list[unreal.AssetData],
) -> list[dict[str, Any]]:
    """Export the complete asset registry required for map generation."""
    rows: list[dict[str, Any]] = []

    for index, asset_data in enumerate(assets, start=1):
        package_name = safe_string(asset_data.package_name)
        object_path = get_asset_object_path(asset_data)
        asset_class = get_asset_class_name(asset_data)
        tags = get_asset_tags(asset_data)

        rows.append(
            {
                "mount_point": infer_mount_point(package_name),
                "asset_name": safe_string(asset_data.asset_name),
                "asset_class": asset_class,
                "package_name": package_name,
                "package_path": safe_string(asset_data.package_path),
                "object_path": object_path,
                "is_redirector": asset_class == "ObjectRedirector",
                "dependencies": "|".join(get_dependencies(package_name)),
                "tags_json": json.dumps(
                    tags,
                    ensure_ascii=False,
                    sort_keys=True,
                ),
            }
        )

        if index % 1000 == 0:
            log(f"Processed {index}/{len(assets)} assets")

    write_csv(
        output_directory / "assets.csv",
        [
            "mount_point",
            "asset_name",
            "asset_class",
            "package_name",
            "package_path",
            "object_path",
            "is_redirector",
            "dependencies",
            "tags_json",
        ],
        rows,
    )
    return rows


def load_asset_safely(object_path: str) -> Any:
    """Load an editor asset without aborting the complete audit."""
    try:
        return unreal.EditorAssetLibrary.load_asset(object_path)
    except Exception as error:
        log_warning(f"Unable to load {object_path}: {error}")
        return None


def read_blueprint_property(
    blueprint: Any,
    property_name: str,
    errors: list[str],
) -> str:
    """Read one Blueprint editor property safely."""
    try:
        return safe_string(blueprint.get_editor_property(property_name))
    except Exception as error:
        errors.append(f"{property_name}: {error}")
        return ""


def export_blueprints(
    output_directory: Path,
    asset_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Export loadable Blueprint metadata."""
    blueprint_rows: list[dict[str, Any]] = []

    candidates = [
        row
        for row in asset_rows
        if row["asset_class"] in BLUEPRINT_ASSET_CLASSES
    ]

    for asset_row in candidates:
        object_path = safe_string(asset_row["object_path"])
        blueprint = load_asset_safely(object_path)
        errors: list[str] = []

        parent_class = ""
        generated_class = ""
        skeleton_generated_class = ""
        blueprint_type = ""

        if blueprint is not None:
            parent_class = read_blueprint_property(
                blueprint,
                "parent_class",
                errors,
            )
            generated_class = read_blueprint_property(
                blueprint,
                "generated_class",
                errors,
            )
            skeleton_generated_class = read_blueprint_property(
                blueprint,
                "skeleton_generated_class",
                errors,
            )
            blueprint_type = read_blueprint_property(
                blueprint,
                "blueprint_type",
                errors,
            )

        blueprint_rows.append(
            {
                "mount_point": asset_row["mount_point"],
                "asset_name": asset_row["asset_name"],
                "object_path": object_path,
                "blueprint_asset_class": asset_row["asset_class"],
                "parent_class": parent_class,
                "generated_class": generated_class,
                "skeleton_generated_class": skeleton_generated_class,
                "blueprint_type": blueprint_type,
                "load_status": "LOADED" if blueprint is not None else "FAILED",
                "audit_notes": "; ".join(errors),
            }
        )

    write_csv(
        output_directory / "blueprints.csv",
        [
            "mount_point",
            "asset_name",
            "object_path",
            "blueprint_asset_class",
            "parent_class",
            "generated_class",
            "skeleton_generated_class",
            "blueprint_type",
            "load_status",
            "audit_notes",
        ],
        blueprint_rows,
    )
    return blueprint_rows


def export_maps(
    output_directory: Path,
    asset_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Export World assets and their dependencies."""
    map_rows: list[dict[str, Any]] = []

    for asset_row in asset_rows:
        if asset_row["asset_class"] != "World":
            continue

        map_rows.append(
            {
                "mount_point": asset_row["mount_point"],
                "asset_name": asset_row["asset_name"],
                "package_name": asset_row["package_name"],
                "object_path": asset_row["object_path"],
                "dependencies": asset_row["dependencies"],
            }
        )

    write_csv(
        output_directory / "maps.csv",
        [
            "mount_point",
            "asset_name",
            "package_name",
            "object_path",
            "dependencies",
        ],
        map_rows,
    )
    return map_rows


def read_uproject() -> dict[str, Any]:
    """Read the current .uproject descriptor."""
    uproject_path = Path(
        unreal.Paths.convert_relative_path_to_full(
            unreal.Paths.get_project_file_path()
        )
    ).resolve()

    with uproject_path.open("r", encoding="utf-8-sig") as stream:
        return json.load(stream)


def export_plugins(
    output_directory: Path,
    uproject_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    """Export plugins explicitly declared by the .uproject file."""
    rows: list[dict[str, Any]] = []

    for plugin in uproject_payload.get("Plugins", []):
        rows.append(
            {
                "name": plugin.get("Name", ""),
                "enabled": plugin.get("Enabled", ""),
                "target_allow_list": "|".join(
                    plugin.get("TargetAllowList", [])
                ),
                "platform_allow_list": "|".join(
                    plugin.get("PlatformAllowList", [])
                ),
                "raw_json": json.dumps(
                    plugin,
                    ensure_ascii=False,
                    sort_keys=True,
                ),
            }
        )

    rows.sort(key=lambda item: safe_string(item["name"]).lower())

    write_csv(
        output_directory / "plugins.csv",
        [
            "name",
            "enabled",
            "target_allow_list",
            "platform_allow_list",
            "raw_json",
        ],
        rows,
    )
    return rows


def export_summary(
    output_directory: Path,
    uproject_payload: dict[str, Any],
    asset_rows: list[dict[str, Any]],
    blueprint_rows: list[dict[str, Any]],
    map_rows: list[dict[str, Any]],
    plugin_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Write high-level statistics for the complete audit."""
    class_counts: dict[str, int] = {}
    mount_counts: dict[str, int] = {}

    for row in asset_rows:
        asset_class = safe_string(row["asset_class"])
        mount_point = safe_string(row["mount_point"])
        class_counts[asset_class] = class_counts.get(asset_class, 0) + 1
        mount_counts[mount_point] = mount_counts.get(mount_point, 0) + 1

    failed_blueprints = sum(
        1
        for row in blueprint_rows
        if row["load_status"] != "LOADED"
    )

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "project_root": safe_string(get_project_root()),
        "project_name": safe_string(unreal.SystemLibrary.get_game_name()),
        "engine_version": safe_string(
            unreal.SystemLibrary.get_engine_version()
        ),
        "uproject_file_version": uproject_payload.get("FileVersion"),
        "engine_association": uproject_payload.get("EngineAssociation"),
        "scanned_mount_points": list(CONTENT_ROOTS),
        "asset_count": len(asset_rows),
        "blueprint_count": len(blueprint_rows),
        "failed_blueprint_load_count": failed_blueprints,
        "map_count": len(map_rows),
        "declared_plugin_count": len(plugin_rows),
        "asset_mount_counts": dict(sorted(mount_counts.items())),
        "asset_class_counts": dict(sorted(class_counts.items())),
        "required_generation_plugins": {
            "PythonScriptPlugin": (
                "Must be enabled while running audit/generation tools"
            ),
            "EditorScriptingUtilities": (
                "Must be enabled while running audit/generation tools"
            ),
            "ModelingToolsEditorMode": (
                "Expected from current project configuration"
            ),
            "Fab": "Needed only for acquiring content",
        },
    }

    write_json(output_directory / "project_summary.json", summary)
    return summary


def run_audit() -> None:
    """Run every audit stage and report the generated output."""
    output_directory = get_output_directory()
    log(f"Writing audit to {output_directory}")
    log(f"Scanning mounts: {', '.join(CONTENT_ROOTS)}")

    uproject_payload = read_uproject()
    assets = get_all_relevant_assets()

    log(f"Collected {len(assets)} unique assets")

    asset_rows = export_assets(output_directory, assets)
    blueprint_rows = export_blueprints(output_directory, asset_rows)
    map_rows = export_maps(output_directory, asset_rows)
    plugin_rows = export_plugins(output_directory, uproject_payload)
    summary = export_summary(
        output_directory,
        uproject_payload,
        asset_rows,
        blueprint_rows,
        map_rows,
        plugin_rows,
    )

    log(
        "Audit complete: "
        f"{summary['asset_count']} assets, "
        f"{summary['blueprint_count']} Blueprints, "
        f"{summary['map_count']} maps"
    )

    unreal.EditorDialog.show_message(
        "ZombieSeasons Audit",
        (
            "Audit complete.\n\n"
            f"Assets: {summary['asset_count']}\n"
            f"Blueprints: {summary['blueprint_count']}\n"
            f"Maps: {summary['map_count']}\n\n"
            f"Output:\n{output_directory}"
        ),
        unreal.AppMsgType.OK,
    )


if __name__ == "__main__":
    try:
        run_audit()
    except Exception as audit_error:
        details = traceback.format_exc()
        log_error(f"Audit failed: {audit_error}\n{details}")
        unreal.EditorDialog.show_message(
            "ZombieSeasons Audit Failed",
            f"{audit_error}\n\nSee Output Log for details.",
            unreal.AppMsgType.OK,
        )
        raise
