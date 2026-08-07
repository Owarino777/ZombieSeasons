"""Build complete ZombieSeasons production asset decisions automatically.

This standard-Python tool removes the need to manually approve hundreds of assets.
It preserves explicit human/visual decisions already present in review_decisions.csv,
then applies deterministic category quotas, source scores, family diversity and pack
semantics to every remaining review asset.

The output remains auditable: every decision records whether it came from visual
review or from the automatic production-selection policy.
"""

from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve()
WORLD_MAP_DIRECTORY = SCRIPT_PATH.parents[1]
REVIEW_DIRECTORY = WORLD_MAP_DIRECTORY / "GeneratedAssetReview"
REVIEW_CSV = REVIEW_DIRECTORY / "asset_review.csv"
DECISIONS_CSV = REVIEW_DIRECTORY / "review_decisions.csv"
SUMMARY_CSV = REVIEW_DIRECTORY / "review_decisions_summary.csv"

OUTPUT_FIELDS = [
    "review_id",
    "decision",
    "role",
    "asset_name",
    "object_path",
    "basis",
    "notes",
]

# Production-oriented targets. They deliberately keep broad visual variety without
# carrying every near-duplicate into the final generator manifest.
CATEGORY_TARGETS: dict[str, tuple[int, int]] = {
    # category: (APPROVED target, RESERVE target)
    "barrier_fence": (14, 8),
    "street_prop": (25, 9),
    "debris_rubble": (10, 5),
    "ruin_general": (18, 10),
    "vehicle": (12, 8),
    "stairs_traversal": (3, 0),
    "door_window": (20, 10),
    "roof": (14, 6),
    "structural": (20, 10),
    "wall_facade": (32, 24),
    "architecture_general": (32, 24),
}

CATEGORY_ROLES = {
    "barrier_fence": "BARRIER_FENCE",
    "street_prop": "STREET_PROP",
    "debris_rubble": "DEBRIS_RUBBLE",
    "ruin_general": "RUIN_MODULE",
    "vehicle": "VEHICLE",
    "stairs_traversal": "TRAVERSAL",
    "door_window": "DOOR_WINDOW",
    "roof": "ROOF_MODULE",
    "structural": "STRUCTURAL_MODULE",
    "wall_facade": "FACADE_MODULE",
    "architecture_general": "ARCHITECTURE_MODULE",
    "road_material": "ROAD_MATERIAL",
}

# Decisions made from the galleries already inspected in this conversation.
# They are treated as VISUAL and therefore outrank automatic policy.
VISUAL_OVERRIDES: dict[str, tuple[str, str, str]] = {
    "A010": (
        "APPROVED",
        "PRIMARY_ROAD",
        "Primary dark asphalt selected visually for the road network.",
    ),
    "A004": (
        "RESERVE",
        "DAMAGED_ROAD",
        "Visually selected for heavily damaged road zones.",
    ),
    "A007": (
        "RESERVE",
        "AGED_CRACKED_ROAD",
        "Visually selected for aged roads, parking areas and secondary streets.",
    ),

    # Street-prop gallery: strong reusable urban production set.
    "M0023": ("APPROVED", "STREET_PROP", "Bench selected visually."),
    "M0024": ("APPROVED", "STREET_PROP", "Bench variant selected visually."),
    "M0025": ("APPROVED", "STREET_SIGN", "Street sign selected visually."),
    "M0026": ("APPROVED", "STREET_SIGN", "Street sign selected visually."),
    "M0027": ("APPROVED", "STREET_SIGN", "Street sign selected visually."),
    "M0028": ("APPROVED", "STREET_SIGN", "Street sign selected visually."),
    "M0029": ("APPROVED", "STREET_SIGN", "Street sign selected visually."),
    "M0030": ("APPROVED", "STREET_SIGN", "Street sign selected visually."),
    "M0031": ("APPROVED", "STREET_SIGN", "Street sign selected visually."),
    "M0032": ("APPROVED", "STREET_SIGN", "Street sign selected visually."),
    "M0033": ("APPROVED", "STREET_SIGN", "Street sign selected visually."),
    "M0034": ("APPROVED", "BICYCLE_STAND", "Bicycle stand selected visually."),
    "M0035": ("APPROVED", "BICYCLE_STAND", "Bicycle stand variant selected visually."),
    "M0036": ("APPROVED", "BUS_STOP", "Bus stop selected visually."),
    "M0037": ("APPROVED", "BUS_STOP", "Bus stop variant selected visually."),
    "M0038": ("RESERVE", "FLOWER_POT", "Secondary dressing only."),
    "M0039": ("RESERVE", "FLOWER_POT", "Secondary dressing only."),
    "M0040": ("RESERVE", "FLOWER_POT", "Secondary dressing only."),
    "M0041": ("RESERVE", "FLOWER_POT", "Secondary dressing only."),
    "M0042": ("RESERVE", "LANTERN", "Atmospheric secondary dressing."),
    "M0043": ("APPROVED", "PALLET", "Useful urban clutter and gameplay dressing."),
    "M0044": ("RESERVE", "PIER", "Use only for waterfront-specific dressing."),
    "M0045": ("RESERVE", "PIER", "Use only for waterfront-specific dressing."),
    "M0046": ("RESERVE", "PIER", "Use only for waterfront-specific dressing."),
    "M0047": ("RESERVE", "PIER", "Use only for waterfront-specific dressing."),
    "M0048": ("APPROVED", "PYLON", "Useful traffic-control prop."),
    "M0049": ("APPROVED", "SPEED_BUMP", "Useful road gameplay/environment prop."),
    "M0050": ("APPROVED", "STREET_LAMP", "Strong urban lighting landmark."),
    "M0051": ("APPROVED", "STREET_SIGN", "City Sample sign selected visually."),
    "M0052": ("APPROVED", "STREET_SIGN", "City Sample sign selected visually."),
    "M0053": ("APPROVED", "STREET_SIGN", "City Sample sign selected visually."),
    "M0054": ("APPROVED", "STREET_SIGN", "City Sample sign selected visually."),
    "M0055": ("APPROVED", "STREET_SIGN", "City Sample sign selected visually."),
    "M0056": ("APPROVED", "STREET_LAMP", "Strong urban lighting landmark."),
}


class DecisionError(RuntimeError):
    """Raised when the automatic decision pass cannot continue safely."""


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise DecisionError(f"Required file not found: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return [dict(row) for row in csv.DictReader(stream)]


def numeric_score(row: dict[str, str]) -> int:
    try:
        return int(row.get("source_score") or 0)
    except ValueError:
        return 0


def family_key(asset_name: str) -> str:
    """Create a conservative variant-family key for diversity-first selection."""
    value = asset_name.casefold()
    value = re.sub(r"^(sm_|sk_|mesh_)", "", value)
    value = re.sub(r"_n\d+$", "", value)
    value = re.sub(r"_[abc]$", "", value)
    value = re.sub(r"_\d+$", "", value)
    value = re.sub(r"_l\d+", "_l", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or asset_name.casefold()


def diversity_order(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Prefer high-scoring assets while sampling different variant families first."""
    ordered = sorted(
        rows,
        key=lambda row: (
            -numeric_score(row),
            row.get("pack", "").casefold(),
            row.get("object_path", "").casefold(),
        ),
    )

    first_pass: list[dict[str, str]] = []
    duplicates: list[dict[str, str]] = []
    seen_families: set[str] = set()

    for row in ordered:
        key = family_key(row.get("asset_name", ""))
        if key not in seen_families:
            seen_families.add(key)
            first_pass.append(row)
        else:
            duplicates.append(row)

    return first_pass + duplicates


def load_existing_visual_decisions() -> dict[str, dict[str, str]]:
    """Preserve any explicit decisions already committed by the project."""
    if not DECISIONS_CSV.is_file():
        return {}

    existing: dict[str, dict[str, str]] = {}
    for row in read_csv(DECISIONS_CSV):
        review_id = row.get("review_id", "").strip()
        decision = row.get("decision", "").strip().upper()
        if not review_id or decision not in {"APPROVED", "RESERVE", "REJECTED"}:
            continue
        existing[review_id] = row
    return existing


def decision_row(
    source: dict[str, str],
    decision: str,
    role: str,
    basis: str,
    notes: str,
) -> dict[str, str]:
    return {
        "review_id": source["review_id"],
        "decision": decision,
        "role": role,
        "asset_name": source["asset_name"],
        "object_path": source["object_path"],
        "basis": basis,
        "notes": notes,
    }


def build_decisions(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    by_id = {row["review_id"]: row for row in rows}
    output: dict[str, dict[str, str]] = {}

    # Hard-coded visual decisions are authoritative.
    for review_id, (decision, role, notes) in VISUAL_OVERRIDES.items():
        source = by_id.get(review_id)
        if source is not None:
            output[review_id] = decision_row(
                source, decision, role, "VISUAL", notes
            )

    # Preserve any other committed explicit decisions that predate this tool.
    for review_id, existing in load_existing_visual_decisions().items():
        source = by_id.get(review_id)
        if source is None or review_id in output:
            continue
        output[review_id] = decision_row(
            source,
            existing["decision"].upper(),
            existing.get("role") or CATEGORY_ROLES.get(source["category"], "PRODUCTION_ASSET"),
            existing.get("basis") or "VISUAL",
            existing.get("notes") or "Preserved explicit project decision.",
        )

    # Asphalt variants not explicitly selected are rejected so the road material
    # palette stays controlled and intentional.
    asphalt_rows = [row for row in rows if row["category"] == "road_material"]
    for source in asphalt_rows:
        if source["review_id"] in output:
            continue
        output[source["review_id"]] = decision_row(
            source,
            "REJECTED",
            "ROAD_MATERIAL",
            "AUTO_POLICY",
            "Not selected among the visually reviewed asphalt production variants.",
        )

    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row["category"] != "road_material":
            grouped[row["category"]].append(row)

    for category, category_rows in grouped.items():
        approved_target, reserve_target = CATEGORY_TARGETS.get(
            category,
            (max(1, len(category_rows) // 2), max(0, len(category_rows) // 4)),
        )

        fixed_approved = sum(
            1
            for row in category_rows
            if output.get(row["review_id"], {}).get("decision") == "APPROVED"
        )
        fixed_reserve = sum(
            1
            for row in category_rows
            if output.get(row["review_id"], {}).get("decision") == "RESERVE"
        )

        remaining = [
            row for row in category_rows if row["review_id"] not in output
        ]
        ordered = diversity_order(remaining)

        approve_slots = max(0, approved_target - fixed_approved)
        reserve_slots = max(0, reserve_target - fixed_reserve)

        approved_rows = ordered[:approve_slots]
        reserve_rows = ordered[approve_slots : approve_slots + reserve_slots]
        rejected_rows = ordered[approve_slots + reserve_slots :]

        role = CATEGORY_ROLES.get(category, "PRODUCTION_ASSET")

        for source in approved_rows:
            output[source["review_id"]] = decision_row(
                source,
                "APPROVED",
                role,
                "AUTO_POLICY",
                "Selected by deterministic production policy: high source score and variant-family diversity.",
            )
        for source in reserve_rows:
            output[source["review_id"]] = decision_row(
                source,
                "RESERVE",
                role,
                "AUTO_POLICY",
                "Kept as deterministic reserve for visual variety or district-specific dressing.",
            )
        for source in rejected_rows:
            output[source["review_id"]] = decision_row(
                source,
                "REJECTED",
                role,
                "AUTO_POLICY",
                "Excluded from the production set to limit redundant variants and generator complexity.",
            )

    missing = sorted(set(by_id) - set(output))
    if missing:
        raise DecisionError(
            "Decision pass left review IDs unresolved: " + ", ".join(missing)
        )

    return [output[review_id] for review_id in sorted(output)]


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def write_summary(rows: list[dict[str, str]]) -> None:
    decision_counts = Counter(row["decision"] for row in rows)
    basis_counts = Counter(row["basis"] for row in rows)

    summary_rows = [
        {"metric": "TOTAL", "value": str(len(rows))},
        *(
            {"metric": f"DECISION_{key}", "value": str(value)}
            for key, value in sorted(decision_counts.items())
        ),
        *(
            {"metric": f"BASIS_{key}", "value": str(value)}
            for key, value in sorted(basis_counts.items())
        ),
    ]
    write_csv(SUMMARY_CSV, summary_rows, ["metric", "value"])


def main() -> None:
    rows = read_csv(REVIEW_CSV)
    required = {
        "review_id",
        "category",
        "pack",
        "asset_name",
        "asset_class",
        "object_path",
        "source_score",
    }
    actual = set(rows[0]) if rows else set()
    missing = required - actual
    if missing:
        raise DecisionError(
            "asset_review.csv is missing columns: " + ", ".join(sorted(missing))
        )

    decisions = build_decisions(rows)
    write_csv(DECISIONS_CSV, decisions, OUTPUT_FIELDS)
    write_summary(decisions)

    counts = Counter(row["decision"] for row in decisions)
    basis = Counter(row["basis"] for row in decisions)
    print(f"Total decisions: {len(decisions)}")
    print(f"Approved: {counts.get('APPROVED', 0)}")
    print(f"Reserve: {counts.get('RESERVE', 0)}")
    print(f"Rejected: {counts.get('REJECTED', 0)}")
    print(f"Visual decisions: {basis.get('VISUAL', 0)}")
    print(f"Automatic decisions: {basis.get('AUTO_POLICY', 0)}")
    print(f"CSV: {DECISIONS_CSV}")
    print(f"Summary: {SUMMARY_CSV}")


if __name__ == "__main__":
    main()
