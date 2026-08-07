"""Shared helpers for ZombieSeasons production map-generation scripts.

This module is editor-only and must never become a packaged runtime dependency.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import unreal


GENERATION_VERSION = "001"
GLOBAL_SEED = 24071996

PROJECT_ROOT = Path(
    unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
).resolve()
WORLD_MAP_DIRECTORY = PROJECT_ROOT / "Documentation" / "WorldMap"
MANIFEST_PATH = (
    WORLD_MAP_DIRECTORY
    / "GeneratedProductionManifest"
    / "production_asset_manifest.csv"
)
SAVED_ROOT = PROJECT_ROOT / "Saved" / "ZombieSeasonsWorldGeneration"
VALIDATION_ROOT = SAVED_ROOT / "Validation"

GREYBOX_MAP = "/Game/ZombieSeasons/Maps/Development/L_ZS_World_Greybox"
PRODUCTION_MAP = "/Game/ZombieSeasons/Maps/L_ZS_World"

PLAYABLE_MIN_X = -90000.0
PLAYABLE_MAX_X = 90000.0
PLAYABLE_MIN_Y = -90000.0
PLAYABLE_MAX_Y = 90000.0

BASE_TAGS = (
    "ZS.Generated",
    f"ZS.GenerationVersion.{GENERATION_VERSION}",
)


class ZSGenerationError(RuntimeError):
    """Raised when a generation stage cannot continue safely."""


def log(message: str) -> None:
    unreal.log(f"[ZombieSeasonsGeneration] {message}")


def warn(message: str) -> None:
    unreal.log_warning(f"[ZombieSeasonsGeneration] {message}")


def fail(message: str) -> None:
    unreal.log_error(f"[ZombieSeasonsGeneration] {message}")
    raise ZSGenerationError(message)


def ensure_saved_directories() -> None:
    VALIDATION_ROOT.mkdir(parents=True, exist_ok=True)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        fail(f"Required CSV file not found: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return [dict(row) for row in csv.DictReader(stream)]


def read_production_manifest() -> list[dict[str, str]]:
    rows = read_csv(MANIFEST_PATH)
    required = {
        "review_id",
        "decision",
        "generator_enabled",
        "category",
        "pack",
        "asset_name",
        "asset_class",
        "object_path",
    }
    actual = set(rows[0]) if rows else set()
    missing = required - actual
    if missing:
        fail(
            "Production manifest is missing required columns: "
            + ", ".join(sorted(missing))
        )
    return rows


def approved_manifest_rows() -> list[dict[str, str]]:
    rows = [
        row
        for row in read_production_manifest()
        if row["decision"] == "APPROVED"
        and row["generator_enabled"].strip().lower() == "true"
    ]
    if not rows:
        fail("Production manifest contains no generator-enabled APPROVED assets.")
    return rows


def editor_asset_exists(object_path: str) -> bool:
    """Check an exact Unreal object path without intentionally loading the asset."""
    return bool(unreal.EditorAssetLibrary.does_asset_exist(object_path))


def add_generation_tags(
    actor: Any,
    *,
    stage: str,
    district: str,
    stable_id: str | None = None,
) -> None:
    tags = [
        unreal.Name(tag)
        for tag in (
            *BASE_TAGS,
            f"ZS.Stage.{stage}",
            f"ZS.District.{district}",
            *((f"ZS.Id.{stable_id}",) if stable_id else ()),
        )
    ]
    actor.set_editor_property("tags", tags)


def actor_has_tag(actor: Any, tag: str) -> bool:
    try:
        tags = actor.get_editor_property("tags") or []
        return any(str(item) == tag for item in tags)
    except Exception:
        return False


def write_json_report(filename: str, payload: object) -> Path:
    ensure_saved_directories()
    destination = VALIDATION_ROOT / filename
    with destination.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2, sort_keys=True)
    return destination


def show_editor_message(title: str, message: str) -> None:
    unreal.EditorDialog.show_message(title, message, unreal.AppMsgType.OK)
