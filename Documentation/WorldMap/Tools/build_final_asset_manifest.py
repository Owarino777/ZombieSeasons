"""Build the final ZombieSeasons production asset manifest.

This script is standard Python only. It joins the review inventory with finalized
APPROVED/RESERVE/REJECTED decisions and emits the explicit manifest consumed by
future Unreal world-generation scripts.

Only APPROVED assets are generator-enabled by default. RESERVE assets remain in the
manifest for controlled fallback use, and REJECTED assets are excluded entirely.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve()
WORLD_MAP_DIRECTORY = SCRIPT_PATH.parents[1]
REVIEW_DIRECTORY = WORLD_MAP_DIRECTORY / "GeneratedAssetReview"
REVIEW_CSV = REVIEW_DIRECTORY / "asset_review.csv"
DECISIONS_CSV = REVIEW_DIRECTORY / "review_decisions.csv"
OUTPUT_DIRECTORY = WORLD_MAP_DIRECTORY / "GeneratedProductionManifest"
OUTPUT_CSV = OUTPUT_DIRECTORY / "production_asset_manifest.csv"
OUTPUT_PATHS = OUTPUT_DIRECTORY / "approved_asset_paths.txt"
OUTPUT_SUMMARY = OUTPUT_DIRECTORY / "summary.json"

MANIFEST_FIELDS = [
    "review_id",
    "decision",
    "basis",
    "generator_enabled",
    "usage_class",
    "district_pool",
    "season_pool",
    "selection_weight",
    "category",
    "role",
    "pack",
    "asset_name",
    "asset_class",
    "object_path",
    "source_score",
    "notes",
]

ALL_DISTRICTS = "HUB;SPRING;SUMMER;AUTUMN;WINTER"
ALL_SEASONS = "SPRING;SUMMER;AUTUMN;WINTER"

CATEGORY_POLICY = {
    "road_material": ("ROAD_SURFACE", ALL_DISTRICTS, ALL_SEASONS),
    "barrier_fence": ("GAMEPLAY_OBSTACLE", ALL_DISTRICTS, ALL_SEASONS),
    "street_prop": ("STREET_DRESSING", ALL_DISTRICTS, ALL_SEASONS),
    "debris_rubble": ("DESTRUCTION_DRESSING", ALL_DISTRICTS, ALL_SEASONS),
    "ruin_general": ("RUIN_MODULE", "SUMMER;AUTUMN;WINTER", "SUMMER;AUTUMN;WINTER"),
    "vehicle": ("VEHICLE_DRESSING", ALL_DISTRICTS, ALL_SEASONS),
    "stairs_traversal": ("TRAVERSAL_MODULE", ALL_DISTRICTS, ALL_SEASONS),
    "door_window": ("ARCHITECTURE_SECONDARY", ALL_DISTRICTS, ALL_SEASONS),
    "roof": ("ARCHITECTURE_SECONDARY", ALL_DISTRICTS, ALL_SEASONS),
    "structural": ("ARCHITECTURE_PRIMARY", ALL_DISTRICTS, ALL_SEASONS),
    "wall_facade": ("ARCHITECTURE_PRIMARY", ALL_DISTRICTS, ALL_SEASONS),
    "architecture_general": ("ARCHITECTURE_PRIMARY", ALL_DISTRICTS, ALL_SEASONS),
}


class ManifestError(RuntimeError):
    """Raised when the final manifest cannot be built safely."""


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise ManifestError(f"Required file not found: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return [dict(row) for row in csv.DictReader(stream)]


def parse_score(value: str) -> int:
    try:
        return int(value or 0)
    except ValueError:
        return 0


def selection_weight(decision: str, basis: str, score: int) -> str:
    """Return a deterministic relative selection weight for future generators."""
    if decision == "RESERVE":
        return "0.35"

    base = 1.00 if basis == "VISUAL" else 0.85
    score_bonus = max(0.0, min(0.15, score / 1000.0))
    return f"{base + score_bonus:.2f}"


def main() -> None:
    review_rows = read_csv(REVIEW_CSV)
    decision_rows = read_csv(DECISIONS_CSV)

    review_by_id = {row.get("review_id", ""): row for row in review_rows}
    decisions_by_id = {row.get("review_id", ""): row for row in decision_rows}

    if not review_by_id:
        raise ManifestError("asset_review.csv contains no review rows.")
    if len(decisions_by_id) != len(review_by_id):
        raise ManifestError(
            "Decision count does not match review count: "
            f"{len(decisions_by_id)} decisions vs {len(review_by_id)} review rows."
        )

    unresolved = sorted(set(review_by_id) - set(decisions_by_id))
    if unresolved:
        raise ManifestError(
            "Review IDs without final decision: " + ", ".join(unresolved)
        )

    manifest_rows: list[dict[str, str]] = []

    for review_id in sorted(review_by_id):
        review = review_by_id[review_id]
        decision = decisions_by_id[review_id]
        final_decision = decision.get("decision", "").upper()
        if final_decision == "REJECTED":
            continue
        if final_decision not in {"APPROVED", "RESERVE"}:
            raise ManifestError(
                f"Unsupported final decision for {review_id}: {final_decision}"
            )

        category = review.get("category", "")
        usage_class, district_pool, season_pool = CATEGORY_POLICY.get(
            category,
            ("ENVIRONMENT_ASSET", ALL_DISTRICTS, ALL_SEASONS),
        )
        score = parse_score(review.get("source_score", ""))
        basis = decision.get("basis", "AUTO_POLICY") or "AUTO_POLICY"

        manifest_rows.append(
            {
                "review_id": review_id,
                "decision": final_decision,
                "basis": basis,
                "generator_enabled": "true" if final_decision == "APPROVED" else "false",
                "usage_class": usage_class,
                "district_pool": district_pool,
                "season_pool": season_pool,
                "selection_weight": selection_weight(final_decision, basis, score),
                "category": category,
                "role": decision.get("role", ""),
                "pack": review.get("pack", ""),
                "asset_name": review.get("asset_name", ""),
                "asset_class": review.get("asset_class", ""),
                "object_path": review.get("object_path", ""),
                "source_score": str(score),
                "notes": decision.get("notes", ""),
            }
        )

    approved_rows = [
        row for row in manifest_rows if row["decision"] == "APPROVED"
    ]
    reserve_rows = [
        row for row in manifest_rows if row["decision"] == "RESERVE"
    ]

    if len(approved_rows) != 201:
        raise ManifestError(
            f"Expected 201 APPROVED production assets, found {len(approved_rows)}."
        )

    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    with OUTPUT_CSV.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=MANIFEST_FIELDS, extrasaction="raise")
        writer.writeheader()
        writer.writerows(manifest_rows)

    with OUTPUT_PATHS.open("w", encoding="utf-8") as stream:
        for row in approved_rows:
            stream.write(row["object_path"] + "\n")

    summary = {
        "manifest_asset_count": len(manifest_rows),
        "approved_count": len(approved_rows),
        "reserve_count": len(reserve_rows),
        "rejected_excluded_count": len(review_rows) - len(manifest_rows),
        "generator_enabled_count": len(approved_rows),
        "decision_counts": dict(sorted(Counter(row["decision"] for row in manifest_rows).items())),
        "basis_counts": dict(sorted(Counter(row["basis"] for row in manifest_rows).items())),
        "category_counts_approved": dict(sorted(Counter(row["category"] for row in approved_rows).items())),
        "pack_counts_approved": dict(sorted(Counter(row["pack"] for row in approved_rows).items())),
        "policy": {
            "generator_uses_explicit_paths_only": True,
            "approved_enabled_by_default": True,
            "reserve_disabled_by_default": True,
            "rejected_assets_excluded": True,
            "wildcard_runtime_asset_discovery": False,
            "district_pool_is_policy_not_visual_claim": True,
        },
    }
    with OUTPUT_SUMMARY.open("w", encoding="utf-8") as stream:
        json.dump(summary, stream, ensure_ascii=False, indent=2, sort_keys=True)

    print(f"Manifest assets: {len(manifest_rows)}")
    print(f"Generator-enabled approved assets: {len(approved_rows)}")
    print(f"Reserve assets: {len(reserve_rows)}")
    print(f"Rejected assets excluded: {len(review_rows) - len(manifest_rows)}")
    print(f"CSV: {OUTPUT_CSV}")
    print(f"Approved paths: {OUTPUT_PATHS}")
    print(f"Summary: {OUTPUT_SUMMARY}")


if __name__ == "__main__":
    main()
