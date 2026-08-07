"""Build the deterministic ZombieSeasons visual asset review plan.

This script runs with standard Python and never imports Unreal Engine modules.
It converts the production shortlist and Asphalt material variants into ordered
review batches consumed by the Unreal validation-gallery script.

Inputs:
- Documentation/WorldMap/GeneratedProductionShortlist/production_shortlist.csv
- Documentation/WorldMap/GeneratedNewPackDetails/AsphaltMat.csv

Outputs:
Documentation/WorldMap/GeneratedAssetReview/
- asset_review.csv
- batches.json
- summary.json
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve()
WORLD_MAP_DIRECTORY = SCRIPT_PATH.parents[1]
SHORTLIST_FILE = (
    WORLD_MAP_DIRECTORY
    / "GeneratedProductionShortlist"
    / "production_shortlist.csv"
)
ASPHALT_FILE = (
    WORLD_MAP_DIRECTORY
    / "GeneratedNewPackDetails"
    / "AsphaltMat.csv"
)
OUTPUT_DIRECTORY = WORLD_MAP_DIRECTORY / "GeneratedAssetReview"
OUTPUT_CSV = OUTPUT_DIRECTORY / "asset_review.csv"
OUTPUT_BATCHES = OUTPUT_DIRECTORY / "batches.json"
OUTPUT_SUMMARY = OUTPUT_DIRECTORY / "summary.json"

# Keep complete categories together whenever practical so visual comparison is
# immediate. Only the two 80-item City Sample categories are split to limit memory
# pressure and viewport clutter.
DEFAULT_MESH_BATCH_SIZE = 48
CATEGORY_BATCH_SIZES = {
    "wall_facade": 40,
    "architecture_general": 40,
}
ASPHALT_PREVIEW_CLASS = "MaterialInstanceConstant"

CATEGORY_ORDER = (
    "road_material",
    "barrier_fence",
    "street_prop",
    "debris_rubble",
    "ruin_general",
    "vehicle",
    "stairs_traversal",
    "door_window",
    "roof",
    "structural",
    "wall_facade",
    "architecture_general",
)

REVIEW_FIELDS = [
    "review_id",
    "kind",
    "category",
    "pack",
    "review_state",
    "asset_name",
    "asset_class",
    "object_path",
    "source_score",
    "source_score_reasons",
]


class ReviewPlanError(RuntimeError):
    """Raised when the visual review plan cannot be generated safely."""


def read_csv(path: Path, required: set[str]) -> list[dict[str, str]]:
    """Read a UTF-8/BOM CSV and verify its schema."""
    if not path.is_file():
        raise ReviewPlanError(f"Required input not found: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        actual = set(reader.fieldnames or ())
        missing = required - actual
        if missing:
            raise ReviewPlanError(
                f"{path.name} is missing columns: {', '.join(sorted(missing))}"
            )
        return [dict(row) for row in reader]


def clean_identifier(value: str) -> str:
    """Return an Unreal-package-safe identifier component."""
    parts = re.findall(r"[A-Za-z0-9]+", value)
    return "_".join(parts) or "Uncategorized"


def build_review_rows() -> list[dict[str, str]]:
    """Create stable review IDs for shortlisted meshes and asphalt variants."""
    shortlist = read_csv(
        SHORTLIST_FILE,
        {
            "pack",
            "category",
            "review_state",
            "score",
            "score_reasons",
            "asset_name",
            "asset_class",
            "object_path",
        },
    )
    asphalt = read_csv(
        ASPHALT_FILE,
        {"pack", "asset_name", "asset_class", "object_path"},
    )

    mesh_rows = sorted(
        shortlist,
        key=lambda row: (
            CATEGORY_ORDER.index(row["category"])
            if row["category"] in CATEGORY_ORDER
            else len(CATEGORY_ORDER),
            row["category"].casefold(),
            -int(row["score"]),
            row["pack"].casefold(),
            row["object_path"].casefold(),
        ),
    )

    output: list[dict[str, str]] = []
    for index, row in enumerate(mesh_rows, start=1):
        output.append(
            {
                "review_id": f"M{index:04d}",
                "kind": "MESH",
                "category": row["category"],
                "pack": row["pack"],
                "review_state": "PENDING",
                "asset_name": row["asset_name"],
                "asset_class": row["asset_class"],
                "object_path": row["object_path"],
                "source_score": row["score"],
                "source_score_reasons": row["score_reasons"],
            }
        )

    asphalt_instances = sorted(
        (
            row
            for row in asphalt
            if row["asset_class"] == ASPHALT_PREVIEW_CLASS
        ),
        key=lambda row: row["object_path"].casefold(),
    )

    for index, row in enumerate(asphalt_instances, start=1):
        output.append(
            {
                "review_id": f"A{index:03d}",
                "kind": "MATERIAL",
                "category": "road_material",
                "pack": row["pack"],
                "review_state": "PENDING",
                "asset_name": row["asset_name"],
                "asset_class": row["asset_class"],
                "object_path": row["object_path"],
                "source_score": "",
                "source_score_reasons": "asphalt_material_variant",
            }
        )

    if not mesh_rows:
        raise ReviewPlanError("Production shortlist contains no reviewable meshes.")
    if len(asphalt_instances) != 10:
        raise ReviewPlanError(
            "Expected exactly 10 AsphaltMat material instances, found "
            f"{len(asphalt_instances)}. Re-audit before visual validation."
        )

    return output


def build_batches(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    """Build ordered category batches with comparison-friendly sizes."""
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(row["kind"], row["category"])].append(row)

    batches: list[dict[str, object]] = []

    for category in CATEGORY_ORDER:
        kinds = ("MATERIAL",) if category == "road_material" else ("MESH",)
        for kind in kinds:
            group = grouped.get((kind, category), [])
            if not group:
                continue

            if kind == "MATERIAL":
                chunk_size = len(group)
            else:
                chunk_size = CATEGORY_BATCH_SIZES.get(
                    category,
                    DEFAULT_MESH_BATCH_SIZE,
                )

            chunks = [
                group[start : start + chunk_size]
                for start in range(0, len(group), chunk_size)
            ]
            for batch_index, chunk in enumerate(chunks, start=1):
                category_token = clean_identifier(category)
                kind_token = "Mat" if kind == "MATERIAL" else "Mesh"
                batch_id = f"{kind_token}_{category_token}_{batch_index:02d}"
                map_name = f"ZS_Validate_{batch_id}"
                batches.append(
                    {
                        "batch_id": batch_id,
                        "map_name": map_name,
                        "kind": kind,
                        "category": category,
                        "review_ids": [row["review_id"] for row in chunk],
                        "asset_count": len(chunk),
                    }
                )

    assigned = {
        review_id
        for batch in batches
        for review_id in batch["review_ids"]
    }
    expected = {row["review_id"] for row in rows}
    if assigned != expected:
        missing = sorted(expected - assigned)
        raise ReviewPlanError(
            "Some review rows were not assigned to batches: " + ", ".join(missing)
        )

    return batches


def write_review_csv(rows: list[dict[str, str]]) -> None:
    with OUTPUT_CSV.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=REVIEW_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: object) -> None:
    with path.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2, sort_keys=True)


def main() -> None:
    """Generate the complete deterministic visual review plan."""
    rows = build_review_rows()
    batches = build_batches(rows)

    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    write_review_csv(rows)
    write_json(
        OUTPUT_BATCHES,
        {
            "gallery_root": "/Game/ZombieSeasons/Validation/AssetGallery",
            "default_mesh_batch_size": DEFAULT_MESH_BATCH_SIZE,
            "category_batch_sizes": CATEGORY_BATCH_SIZES,
            "batches": batches,
        },
    )

    kind_counts = Counter(row["kind"] for row in rows)
    category_counts = Counter(row["category"] for row in rows)
    pack_counts = Counter(row["pack"] for row in rows)
    write_json(
        OUTPUT_SUMMARY,
        {
            "review_asset_count": len(rows),
            "batch_count": len(batches),
            "kind_counts": dict(sorted(kind_counts.items())),
            "category_counts": dict(sorted(category_counts.items())),
            "pack_counts": dict(sorted(pack_counts.items())),
            "default_mesh_batch_size": DEFAULT_MESH_BATCH_SIZE,
            "category_batch_sizes": CATEGORY_BATCH_SIZES,
            "policy": {
                "initial_state_is_pending": True,
                "approval_requires_visual_review": True,
                "generator_must_not_use_pending_assets": True,
                "generator_must_not_use_rejected_assets": True,
                "batch_maps_are_non_destructive": True,
                "keep_category_together_when_practical": True,
            },
        },
    )

    print(f"Review assets: {len(rows)}")
    print(f"Review batches: {len(batches)}")
    print(f"Mesh reviews: {kind_counts.get('MESH', 0)}")
    print(f"Material reviews: {kind_counts.get('MATERIAL', 0)}")
    print(f"CSV: {OUTPUT_CSV}")
    print(f"Batches: {OUTPUT_BATCHES}")
    print(f"Summary: {OUTPUT_SUMMARY}")


if __name__ == "__main__":
    main()
