"""Export a lightweight Unreal asset inventory without loading project assets.

This script is designed for large UE 5.5 projects containing City Sample content.
It only queries the Asset Registry and does not resolve dependencies, load meshes,
compile materials, load Blueprints, or touch maps.

Output:
Saved/ZombieSeasonsAuditLight/
- assets_light.csv
- summary_light.json
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import unreal


OUTPUT_DIRECTORY_NAME = "ZombieSeasonsAuditLight"
ROOTS = (
    "/Game",
    "/Fab",
)


def log(message: str) -> None:
    unreal.log(f"[ZombieSeasonsAuditLight] {message}")


def warn(message: str) -> None:
    unreal.log_warning(f"[ZombieSeasonsAuditLight] {message}")


def safe_string(value: object) -> str:
    if value is None:
        return ""
    try:
        return str(value)
    except Exception:
        return repr(value)


def project_root() -> Path:
    return Path(
        unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
    ).resolve()


def output_directory() -> Path:
    path = project_root() / "Saved" / OUTPUT_DIRECTORY_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def asset_class_name(asset_data: unreal.AssetData) -> str:
    try:
        return safe_string(asset_data.asset_class_path.asset_name)
    except Exception:
        try:
            return safe_string(asset_data.asset_class)
        except Exception:
            return "Unknown"


def object_path(asset_data: unreal.AssetData) -> str:
    package_name = safe_string(asset_data.package_name)
    asset_name = safe_string(asset_data.asset_name)
    return f"{package_name}.{asset_name}" if package_name and asset_name else package_name


def mount_point(package_name: str) -> str:
    for root in ROOTS:
        if package_name == root or package_name.startswith(f"{root}/"):
            return root
    return "UNKNOWN"


def inventory_assets() -> list[dict[str, str]]:
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    registry.search_all_assets(True)

    rows_by_path: dict[str, dict[str, str]] = {}

    for root in ROOTS:
        try:
            entries = registry.get_assets_by_path(unreal.Name(root), recursive=True)
        except Exception as error:
            warn(f"Unable to scan {root}: {error}")
            continue

        log(f"Registry entries under {root}: {len(entries)}")

        for entry in entries:
            package_name = safe_string(entry.package_name)
            path = object_path(entry)
            rows_by_path[path] = {
                "mount_point": mount_point(package_name),
                "asset_name": safe_string(entry.asset_name),
                "asset_class": asset_class_name(entry),
                "package_name": package_name,
                "package_path": safe_string(entry.package_path),
                "object_path": path,
            }

    rows = list(rows_by_path.values())
    rows.sort(key=lambda row: row["object_path"].lower())
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = [
        "mount_point",
        "asset_name",
        "asset_class",
        "package_name",
        "package_path",
        "object_path",
    ]

    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_summary(path: Path, rows: list[dict[str, str]]) -> None:
    class_counts = Counter(row["asset_class"] for row in rows)
    mount_counts = Counter(row["mount_point"] for row in rows)

    top_level_game_folders = Counter()
    for row in rows:
        package_name = row["package_name"]
        if package_name.startswith("/Game/"):
            remainder = package_name[len("/Game/"):]
            first_segment = remainder.split("/", 1)[0]
            if first_segment:
                top_level_game_folders[first_segment] += 1

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "engine_version": safe_string(unreal.SystemLibrary.get_engine_version()),
        "project_name": safe_string(unreal.SystemLibrary.get_game_name()),
        "asset_count": len(rows),
        "mount_counts": dict(sorted(mount_counts.items())),
        "asset_class_counts": dict(sorted(class_counts.items())),
        "game_top_level_folder_counts": dict(
            sorted(top_level_game_folders.items(), key=lambda item: (-item[1], item[0]))
        ),
        "safety": {
            "loads_assets": False,
            "resolves_dependencies": False,
            "compiles_materials": False,
            "builds_static_meshes": False,
            "opens_maps": False,
        },
    }

    with path.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2, sort_keys=True)


def run() -> None:
    destination = output_directory()
    log(f"Writing lightweight inventory to {destination}")

    rows = inventory_assets()
    write_csv(destination / "assets_light.csv", rows)
    write_summary(destination / "summary_light.json", rows)

    log(f"Inventory complete: {len(rows)} assets")
    unreal.EditorDialog.show_message(
        "ZombieSeasons Lightweight Inventory",
        (
            f"Inventory complete.\n\nAssets: {len(rows)}\n\n"
            f"Output:\n{destination}"
        ),
        unreal.AppMsgType.OK,
    )


if __name__ == "__main__":
    run()
