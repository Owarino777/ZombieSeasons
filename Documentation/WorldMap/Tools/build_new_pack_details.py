"""Export compact details for the newly installed Street Props and Asphalt packs.

This script runs with standard Python and reads only the committed lightweight
Asset Registry CSV. Unreal Editor is not required and no Unreal asset is loaded.

Input:
Documentation/WorldMap/GeneratedAuditLight/assets_light.csv

Output:
Documentation/WorldMap/GeneratedNewPackDetails/
- AsphaltMat.csv
- Street_Props_Pack_V1.csv
- summary.json
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve()
WORLD_MAP_DIRECTORY = SCRIPT_PATH.parents[1]
INPUT_FILE = WORLD_MAP_DIRECTORY / "GeneratedAuditLight" / "assets_light.csv"
OUTPUT_DIRECTORY = WORLD_MAP_DIRECTORY / "GeneratedNewPackDetails"
OUTPUT_JSON = OUTPUT_DIRECTORY / "summary.json"

PACK_ROOTS = {
    "/Game/AsphaltMat": "AsphaltMat",
    "/Game/Street_Props_Pack_V1": "Street_Props_Pack_V1",
}

FIELDNAMES = [
    "pack",
    "asset_name",
    "asset_class",
    "package_name",
    "package_path",
    "object_path",
]


class PackDetailsError(RuntimeError):
    """Raised when compact pack-detail generation cannot continue."""


def detect_pack(package_name: str) -> str | None:
    for root, pack_name in PACK_ROOTS.items():
        if package_name == root or package_name.startswith(f"{root}/"):
            return pack_name
    return None


def read_inventory() -> list[dict[str, str]]:
    if not INPUT_FILE.is_file():
        raise PackDetailsError(f"Inventory file not found: {INPUT_FILE}")

    with INPUT_FILE.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {
            "asset_name",
            "asset_class",
            "package_name",
            "package_path",
            "object_path",
        }
        missing = required - set(reader.fieldnames or ())
        if missing:
            raise PackDetailsError(
                "Inventory is missing required columns: " + ", ".join(sorted(missing))
            )
        return [dict(row) for row in reader]


def build_rows(inventory: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped = {pack_name: [] for pack_name in PACK_ROOTS.values()}

    for row in inventory:
        pack_name = detect_pack(row["package_name"])
        if pack_name is None:
            continue

        grouped[pack_name].append(
            {
                "pack": pack_name,
                "asset_name": row["asset_name"],
                "asset_class": row["asset_class"],
                "package_name": row["package_name"],
                "package_path": row["package_path"],
                "object_path": row["object_path"],
            }
        )

    for rows in grouped.values():
        rows.sort(key=lambda row: (row["asset_class"].casefold(), row["object_path"].casefold()))

    return grouped


def write_pack_csv(pack_name: str, rows: list[dict[str, str]]) -> Path:
    path = OUTPUT_DIRECTORY / f"{pack_name}.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    return path


def write_summary(grouped: dict[str, list[dict[str, str]]]) -> None:
    packs: dict[str, object] = {}

    for pack_name, rows in sorted(grouped.items()):
        class_counts = Counter(row["asset_class"] for row in rows)
        material_like_paths = [
            row["object_path"]
            for row in rows
            if row["asset_class"] in {"Material", "MaterialInstanceConstant"}
        ]
        static_mesh_paths = [
            row["object_path"]
            for row in rows
            if row["asset_class"] == "StaticMesh"
        ]

        packs[pack_name] = {
            "asset_count": len(rows),
            "asset_class_counts": dict(sorted(class_counts.items())),
            "material_like_count": len(material_like_paths),
            "static_mesh_count": len(static_mesh_paths),
            "material_like_object_paths": material_like_paths,
        }

    payload = {
        "source": str(INPUT_FILE.relative_to(WORLD_MAP_DIRECTORY)),
        "packs": packs,
        "safety": {
            "standard_python_only": True,
            "loads_unreal_assets": False,
            "modifies_unreal_assets": False,
        },
    }

    with OUTPUT_JSON.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2, sort_keys=True)


def main() -> None:
    grouped = build_rows(read_inventory())

    missing_packs = [pack_name for pack_name, rows in grouped.items() if not rows]
    if missing_packs:
        raise PackDetailsError(
            "No assets found for installed pack(s): " + ", ".join(sorted(missing_packs))
        )

    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    for pack_name, rows in sorted(grouped.items()):
        path = write_pack_csv(pack_name, rows)
        print(f"{pack_name}: {len(rows)} assets -> {path}")

    write_summary(grouped)
    print(f"Summary: {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
