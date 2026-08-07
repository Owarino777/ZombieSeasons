"""Build a deterministic environment-asset catalog from the lightweight audit.

This script runs with standard Python. Unreal Editor is not required.

Input:
Documentation/WorldMap/GeneratedAuditLight/assets_light.csv

Output:
Documentation/WorldMap/GeneratedEnvironmentCatalog/
- environment_assets.csv
- environment_summary.json

The script never edits Unreal assets. It only classifies registry metadata already
exported by export_asset_inventory_light.py.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Iterable


SCRIPT_PATH = Path(__file__).resolve()
WORLD_MAP_DIRECTORY = SCRIPT_PATH.parents[1]
INPUT_FILE = WORLD_MAP_DIRECTORY / "GeneratedAuditLight" / "assets_light.csv"
OUTPUT_DIRECTORY = WORLD_MAP_DIRECTORY / "GeneratedEnvironmentCatalog"
OUTPUT_CSV = OUTPUT_DIRECTORY / "environment_assets.csv"
OUTPUT_JSON = OUTPUT_DIRECTORY / "environment_summary.json"

PACK_ROOTS = {
    "/Game/CitySampleBuildings": "CitySampleBuildings",
    "/Game/CitySampleVehicles": "CitySampleVehicles",
    "/Game/Scene_UnfinishedBuilding": "Scene_UnfinishedBuilding",
}

MESH_CLASSES = {"StaticMesh", "SkeletalMesh"}

CATEGORY_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "road",
        (
            "road",
            "street",
            "asphalt",
            "lane",
            "intersection",
            "crosswalk",
            "curb",
            "kerb",
            "sidewalk",
            "pavement",
        ),
    ),
    (
        "wall_facade",
        (
            "wall",
            "facade",
            "façade",
            "frontage",
            "exterior",
            "brick",
            "panel",
        ),
    ),
    (
        "door_window",
        (
            "door",
            "window",
            "shutter",
            "storefront",
            "entrance",
            "gate",
        ),
    ),
    (
        "roof",
        (
            "roof",
            "rooftop",
            "parapet",
            "cornice",
            "gutter",
        ),
    ),
    (
        "stairs_traversal",
        (
            "stair",
            "step",
            "ladder",
            "ramp",
            "walkway",
            "bridge",
            "fireescape",
            "fire_escape",
        ),
    ),
    (
        "structural",
        (
            "column",
            "pillar",
            "beam",
            "girder",
            "support",
            "foundation",
            "floor",
            "ceiling",
        ),
    ),
    (
        "street_prop",
        (
            "lamp",
            "lightpole",
            "light_pole",
            "traffic",
            "sign",
            "hydrant",
            "bollard",
            "bench",
            "mailbox",
            "phone",
            "parkingmeter",
            "parking_meter",
        ),
    ),
    (
        "barrier_fence",
        (
            "fence",
            "barrier",
            "barricade",
            "railing",
            "guardrail",
            "guard_rail",
            "concreteblock",
            "concrete_block",
        ),
    ),
    (
        "debris_rubble",
        (
            "debris",
            "rubble",
            "broken",
            "damage",
            "damaged",
            "destroyed",
            "ruin",
            "wreck",
            "trash",
            "garbage",
            "dumpster",
            "scrap",
        ),
    ),
    (
        "construction",
        (
            "scaffold",
            "construction",
            "rebar",
            "concrete",
            "plywood",
            "formwork",
            "worksite",
        ),
    ),
    (
        "vehicle",
        (
            "vehicle",
            "car",
            "truck",
            "taxi",
            "bus",
            "van",
            "suv",
            "pickup",
            "sedan",
            "hatchback",
        ),
    ),
)


class CatalogError(RuntimeError):
    """Raised when catalog generation cannot continue safely."""


def detect_pack(package_name: str) -> str | None:
    """Return the verified source pack for one package path."""
    for root, pack_name in PACK_ROOTS.items():
        if package_name == root or package_name.startswith(f"{root}/"):
            return pack_name
    return None


def infer_category(pack_name: str, searchable_text: str) -> str:
    """Infer a conservative production category from path/name metadata."""
    normalized = searchable_text.casefold().replace("-", "_").replace(" ", "_")

    if pack_name == "CitySampleVehicles":
        return "vehicle"

    for category, keywords in CATEGORY_KEYWORDS:
        if any(keyword.casefold() in normalized for keyword in keywords):
            return category

    if pack_name == "Scene_UnfinishedBuilding":
        return "ruin_general"

    return "architecture_general"


def initial_approval(asset_class: str, category: str) -> str:
    """Assign the initial review state without pretending visual approval exists."""
    if asset_class not in MESH_CLASSES:
        return "REFERENCE_ONLY"

    if category in {
        "road",
        "wall_facade",
        "door_window",
        "roof",
        "stairs_traversal",
        "structural",
        "street_prop",
        "barrier_fence",
        "debris_rubble",
        "construction",
        "vehicle",
        "ruin_general",
        "architecture_general",
    }:
        return "CANDIDATE"

    return "REVIEW"


def read_inventory(path: Path) -> list[dict[str, str]]:
    """Read the UTF-8 BOM-compatible lightweight inventory."""
    if not path.is_file():
        raise CatalogError(f"Inventory file not found: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {
            "mount_point",
            "asset_name",
            "asset_class",
            "package_name",
            "package_path",
            "object_path",
        }
        actual = set(reader.fieldnames or ())
        missing = required - actual
        if missing:
            raise CatalogError(
                "Inventory is missing required columns: "
                + ", ".join(sorted(missing))
            )
        return [dict(row) for row in reader]


def build_rows(inventory: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    """Filter installed production packs and add deterministic classifications."""
    output: list[dict[str, str]] = []

    for row in inventory:
        package_name = row["package_name"]
        pack_name = detect_pack(package_name)
        if pack_name is None:
            continue

        searchable_text = f"{row['asset_name']} {package_name}"
        category = infer_category(pack_name, searchable_text)
        approval = initial_approval(row["asset_class"], category)

        output.append(
            {
                "pack": pack_name,
                "category": category,
                "approval": approval,
                "asset_name": row["asset_name"],
                "asset_class": row["asset_class"],
                "package_name": package_name,
                "package_path": row["package_path"],
                "object_path": row["object_path"],
            }
        )

    output.sort(
        key=lambda item: (
            item["pack"].casefold(),
            item["category"].casefold(),
            item["object_path"].casefold(),
        )
    )
    return output


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    """Write the complete classified environment catalog."""
    fieldnames = [
        "pack",
        "category",
        "approval",
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
    """Write compact counts used to review catalog quality before generation."""
    pack_counts = Counter(row["pack"] for row in rows)
    class_counts = Counter(row["asset_class"] for row in rows)
    category_counts = Counter(row["category"] for row in rows)
    approval_counts = Counter(row["approval"] for row in rows)

    mesh_rows = [row for row in rows if row["asset_class"] in MESH_CLASSES]
    mesh_pack_counts = Counter(row["pack"] for row in mesh_rows)
    mesh_category_counts = Counter(row["category"] for row in mesh_rows)

    payload = {
        "source": str(INPUT_FILE.relative_to(WORLD_MAP_DIRECTORY)),
        "environment_asset_count": len(rows),
        "mesh_candidate_count": len(mesh_rows),
        "pack_counts": dict(sorted(pack_counts.items())),
        "mesh_pack_counts": dict(sorted(mesh_pack_counts.items())),
        "asset_class_counts": dict(sorted(class_counts.items())),
        "category_counts": dict(sorted(category_counts.items())),
        "mesh_category_counts": dict(sorted(mesh_category_counts.items())),
        "approval_counts": dict(sorted(approval_counts.items())),
        "policy": {
            "candidate_is_not_visual_approval": True,
            "final_generator_requires_approved_manifest": True,
            "runtime_wildcard_asset_discovery": False,
        },
    }

    with path.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2, sort_keys=True)


def main() -> None:
    """Generate the environment catalog from the committed lightweight audit."""
    inventory = read_inventory(INPUT_FILE)
    rows = build_rows(inventory)

    if not rows:
        raise CatalogError(
            "No installed environment-pack assets were found in the inventory."
        )

    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    write_csv(OUTPUT_CSV, rows)
    write_summary(OUTPUT_JSON, rows)

    mesh_count = sum(1 for row in rows if row["asset_class"] in MESH_CLASSES)
    print(f"Environment assets cataloged: {len(rows)}")
    print(f"Mesh candidates: {mesh_count}")
    print(f"CSV: {OUTPUT_CSV}")
    print(f"Summary: {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
