"""Build a compact production shortlist from the classified environment catalog.

This is the hardened v2 implementation used by ZombieSeasons. It runs with
standard Python and never loads Unreal assets.
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()
WORLD_MAP_DIRECTORY = SCRIPT_PATH.parents[1]
INPUT_FILE = WORLD_MAP_DIRECTORY / "GeneratedEnvironmentCatalog" / "environment_assets.csv"
OUTPUT_DIRECTORY = WORLD_MAP_DIRECTORY / "GeneratedProductionShortlist"
OUTPUT_CSV = OUTPUT_DIRECTORY / "production_shortlist.csv"
OUTPUT_JSON = OUTPUT_DIRECTORY / "production_shortlist_summary.json"

MESH_CLASSES = {"StaticMesh", "SkeletalMesh"}

CATEGORY_QUOTAS: dict[str, int] = {
    "road": 12,
    "wall_facade": 80,
    "door_window": 36,
    "roof": 24,
    "stairs_traversal": 12,
    "structural": 36,
    "street_prop": 24,
    "barrier_fence": 24,
    "debris_rubble": 36,
    "construction": 16,
    "vehicle": 40,
    "ruin_general": 32,
    "architecture_general": 80,
}

PACK_MINIMUMS: dict[str, int] = {
    "CitySampleBuildings": 120,
    "CitySampleVehicles": 24,
    "Scene_UnfinishedBuilding": 48,
}

POSITIVE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "road": ("road", "street", "asphalt", "sidewalk", "curb", "intersection", "crosswalk"),
    "wall_facade": ("facade", "wall", "storefront", "brick", "exterior", "building"),
    "door_window": ("door", "window", "entrance", "storefront", "gate"),
    "roof": ("roof", "rooftop", "parapet", "cornice"),
    "stairs_traversal": ("stair", "stairs", "step", "ramp", "walkway", "bridge", "fireescape"),
    "structural": ("column", "pillar", "beam", "floor", "ceiling", "support"),
    "street_prop": ("lamp", "traffic", "sign", "hydrant", "bollard", "bench", "mailbox"),
    "barrier_fence": ("fence", "barrier", "barricade", "railing", "guardrail"),
    "debris_rubble": ("debris", "rubble", "broken", "damaged", "destroyed", "wreck", "trash", "garbage"),
    "construction": ("construction", "scaffold", "rebar", "concrete", "plywood"),
    "vehicle": ("car", "truck", "taxi", "bus", "van", "suv", "pickup", "sedan", "vehicle"),
    "ruin_general": ("ruin", "broken", "damaged", "destroyed", "unfinished", "concrete", "wall", "floor"),
    "architecture_general": ("building", "module", "corner", "floor", "shop", "store", "house", "office"),
}

HARD_REJECT_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"(^|[/_.-])lod[0-9]*($|[/_.-])",
        r"(^|[/_.-])hlod($|[/_.-])",
        r"(^|[/_.-])proxy($|[/_.-])",
        r"(^|[/_.-])collision($|[/_.-])",
        r"(^|[/_.-])collider($|[/_.-])",
        r"(^|[/_.-])test($|[/_.-])",
        r"(^|[/_.-])debug($|[/_.-])",
        r"(^|[/_.-])preview($|[/_.-])",
        r"(^|[/_.-])thumbnail($|[/_.-])",
        r"(^|[/_.-])guideline($|[/_.-])",
        r"(^|[/_.-])icon($|[/_.-])",
        r"(^|[/_.-])helper($|[/_.-])",
        r"(^|[/_.-])socket($|[/_.-])",
        r"(^|[/_.-])physics($|[/_.-])",
    )
)

SOFT_PENALTY_KEYWORDS = ("variant", "temp", "old", "deprecated", "sample", "demo", "guide")

OUTPUT_FIELDS = [
    "pack",
    "category",
    "review_state",
    "score",
    "score_reasons",
    "asset_name",
    "asset_class",
    "package_name",
    "package_path",
    "object_path",
]


class ShortlistError(RuntimeError):
    """Raised when shortlist generation cannot continue safely."""


def normalize(value: str) -> str:
    return value.casefold().replace("-", "_").replace(" ", "_")


def read_catalog(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise ShortlistError(f"Catalog file not found: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {
            "pack", "category", "approval", "asset_name", "asset_class",
            "package_name", "package_path", "object_path",
        }
        missing = required - set(reader.fieldnames or ())
        if missing:
            raise ShortlistError("Catalog is missing required columns: " + ", ".join(sorted(missing)))
        return [dict(row) for row in reader]


def hard_reject(row: dict[str, str]) -> tuple[bool, str]:
    searchable = normalize(f"{row['asset_name']} {row['package_name']}")
    for pattern in HARD_REJECT_PATTERNS:
        if pattern.search(searchable):
            return True, f"technical_pattern:{pattern.pattern}"

    if row["pack"] == "CitySampleVehicles":
        internal_tokens = (
            "wheel", "tire", "brake", "suspension", "steering", "engine",
            "drivetrain", "chassis", "door_fl", "door_fr", "door_rl",
            "door_rr", "seat", "interior",
        )
        if any(token in searchable for token in internal_tokens):
            return True, "vehicle_internal_component"

    return False, ""


def score_row(row: dict[str, str]) -> tuple[int, list[str]]:
    searchable = normalize(f"{row['asset_name']} {row['package_name']} {row['package_path']}")
    category = row["category"]
    score = 0
    reasons: list[str] = []

    for keyword in POSITIVE_KEYWORDS.get(category, ()):
        if keyword in searchable:
            score += 8
            reasons.append(f"keyword:{keyword}")

    if row["asset_class"] == "StaticMesh":
        score += 6
        reasons.append("static_mesh")
    elif row["asset_class"] == "SkeletalMesh" and category == "vehicle":
        score += 4
        reasons.append("vehicle_skeletal_mesh")

    if row["pack"] == "Scene_UnfinishedBuilding" and category in {
        "ruin_general", "debris_rubble", "construction", "structural"
    }:
        score += 20
        reasons.append("preferred_ruin_pack")

    if row["pack"] == "CitySampleVehicles" and category == "vehicle":
        score += 16
        reasons.append("preferred_vehicle_pack")

    if row["pack"] == "CitySampleBuildings" and category in {
        "wall_facade", "door_window", "roof", "structural", "architecture_general"
    }:
        score += 10
        reasons.append("preferred_city_pack")

    asset_name = normalize(row["asset_name"])
    if asset_name.startswith(("sm_", "s_", "mesh_")):
        score += 5
        reasons.append("mesh_naming")

    for keyword in SOFT_PENALTY_KEYWORDS:
        if keyword in searchable:
            score -= 6
            reasons.append(f"penalty:{keyword}")

    depth = len([part for part in row["package_name"].split("/") if part])
    if 4 <= depth <= 9:
        score += 3
        reasons.append("normal_path_depth")

    return score, reasons


def build_scored_candidates(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], Counter[str]]:
    rejected: Counter[str] = Counter()
    output: list[dict[str, str]] = []

    for row in rows:
        if row["approval"] != "CANDIDATE" or row["asset_class"] not in MESH_CLASSES:
            continue

        rejected_asset, rejection_reason = hard_reject(row)
        if rejected_asset:
            rejected[rejection_reason] += 1
            continue

        score, reasons = score_row(row)
        output.append({
            "pack": row["pack"],
            "category": row["category"],
            "review_state": "SHORTLISTED",
            "score": str(score),
            "score_reasons": ";".join(reasons),
            "asset_name": row["asset_name"],
            "asset_class": row["asset_class"],
            "package_name": row["package_name"],
            "package_path": row["package_path"],
            "object_path": row["object_path"],
        })

    output.sort(key=lambda row: (-int(row["score"]), row["category"].casefold(), row["pack"].casefold(), row["object_path"].casefold()))
    return output, rejected


def apply_quotas(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["category"]].append(row)

    selected: list[dict[str, str]] = []
    selected_paths: set[str] = set()

    for category, quota in CATEGORY_QUOTAS.items():
        group = sorted(
            grouped.get(category, []),
            key=lambda row: (-int(row["score"]), row["pack"].casefold(), row["object_path"].casefold()),
        )
        for row in group[:quota]:
            selected.append(row)
            selected_paths.add(row["object_path"])

    for pack, minimum in PACK_MINIMUMS.items():
        current = sum(1 for row in selected if row["pack"] == pack)
        if current >= minimum:
            continue

        additions = sorted(
            (row for row in rows if row["pack"] == pack and row["object_path"] not in selected_paths),
            key=lambda row: (-int(row["score"]), row["object_path"].casefold()),
        )
        for row in additions[: max(0, minimum - current)]:
            selected.append(row)
            selected_paths.add(row["object_path"])

    selected.sort(key=lambda row: (row["category"].casefold(), -int(row["score"]), row["pack"].casefold(), row["object_path"].casefold()))
    return selected


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=OUTPUT_FIELDS, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def write_summary(path: Path, source_count: int, scored_count: int, rows: list[dict[str, str]], rejected: Counter[str]) -> None:
    payload = {
        "source": str(INPUT_FILE.relative_to(WORLD_MAP_DIRECTORY)),
        "source_candidate_count": source_count,
        "scored_candidate_count": scored_count,
        "shortlist_count": len(rows),
        "pack_counts": dict(sorted(Counter(row["pack"] for row in rows).items())),
        "category_counts": dict(sorted(Counter(row["category"] for row in rows).items())),
        "asset_class_counts": dict(sorted(Counter(row["asset_class"] for row in rows).items())),
        "hard_reject_counts": dict(sorted(rejected.items())),
        "category_quotas": CATEGORY_QUOTAS,
        "pack_minimums": PACK_MINIMUMS,
        "policy": {
            "metadata_only": True,
            "loads_unreal_assets": False,
            "shortlisted_is_not_approved": True,
            "visual_review_required_before_generator_use": True,
            "generator_may_only_use_explicit_approved_manifest": True,
        },
    }
    with path.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2, sort_keys=True)


def main() -> None:
    rows = read_catalog(INPUT_FILE)
    source_candidates = [
        row for row in rows
        if row["approval"] == "CANDIDATE" and row["asset_class"] in MESH_CLASSES
    ]

    scored, rejected = build_scored_candidates(rows)
    shortlist = apply_quotas(scored)
    if not shortlist:
        raise ShortlistError("No production assets survived shortlist filtering.")

    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    write_csv(OUTPUT_CSV, shortlist)
    write_summary(OUTPUT_JSON, len(source_candidates), len(scored), shortlist, rejected)

    print(f"Source mesh candidates: {len(source_candidates)}")
    print(f"After technical filtering: {len(scored)}")
    print(f"Production shortlist: {len(shortlist)}")
    print(f"CSV: {OUTPUT_CSV}")
    print(f"Summary: {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
