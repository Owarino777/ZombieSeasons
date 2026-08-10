"""Create the deterministic ZombieSeasons greybox gameplay-marker layout.

This stage deliberately does NOT guess the runtime contract of BP_EnemySpawner or the
existing GameModes. UE 5.5 exposed the relevant Blueprint EventGraphs but not their node
arrays through Python, so the runtime integration remains a separate adapter stage.

Run from Unreal Editor after Stage 8 and the Stage 9A/9A2 audits:

py "C:/Users/malik/Documents/Unreal Projects/ZombieSeasons/Content/Python/ZombieSeasons/MapGeneration/09b_create_gameplay_layout.py"

The generated actors are deterministic metadata markers carrying stable ZS.Id tags.
Stage 9C can later replace or consume them using project-owned BP_ZS_* adapters without
changing the frozen world topology or marker budgets.
"""

from __future__ import annotations

import math
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import unreal


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from zs_generation_common import (  # noqa: E402
    GLOBAL_SEED,
    GREYBOX_MAP,
    PLAYABLE_MAX_X,
    PLAYABLE_MAX_Y,
    PLAYABLE_MIN_X,
    PLAYABLE_MIN_Y,
    actor_has_tag,
    add_generation_tags,
    fail,
    log,
    show_editor_message,
    warn,
    write_json_report,
)


STAGE = "GameplayLayout"
STAGE_TAG = f"ZS.Stage.{STAGE}"
MODE = "CREATE"

HUB_PROTECTED_RADIUS = 6000.0
MARKER_Z_OFFSET = 120.0


@dataclass(frozen=True)
class ZoneSpec:
    name: str
    bounds: tuple[float, float, float, float]
    ground_z: float
    anchors: tuple[tuple[str, tuple[float, float, float]], ...]
    zombie_spawns: int
    spawn_groups: int
    horde_triggers: int
    general_loot: int
    high_value_loot: int
    objectives: tuple[tuple[str, tuple[float, float, float]], ...]


HUB_ANCHORS = (
    ("NorthGate", (0.0, 10500.0, 0.0)),
    ("EastGate", (10500.0, 0.0, 0.0)),
    ("SouthGate", (0.0, -10500.0, 0.0)),
    ("WestGate", (-10500.0, 0.0, 0.0)),
)

SPRING_ANCHORS = (
    ("Residential", (-31000.0, 67000.0, 200.0)),
    ("Park", (-34000.0, 38000.0, 100.0)),
    ("School", (-55000.0, 58000.0, 300.0)),
    ("Gym", (-60000.0, 52000.0, 300.0)),
    ("Greenhouses", (-71000.0, 31000.0, 100.0)),
    ("Relay", (-57000.0, 60000.0, 800.0)),
    ("Drainage", (-62000.0, 20000.0, -100.0)),
)

SUMMER_ANCHORS = (
    ("GasStation", (31000.0, 64000.0, 0.0)),
    ("Motel", (53000.0, 56000.0, 100.0)),
    ("ParkingArena", (63000.0, 34000.0, 0.0)),
    ("Boardwalk", (48000.0, 77000.0, 100.0)),
    ("BeachService", (68000.0, 69000.0, 0.0)),
    ("Pier", (76000.0, 82000.0, 100.0)),
    ("StormDrain", (24000.0, 31000.0, -100.0)),
)

AUTUMN_ANCHORS = (
    ("ChurchSquare", (-35000.0, -35000.0, 300.0)),
    ("MarketHall", (-54000.0, -43000.0, 300.0)),
    ("Apartments", (-69000.0, -61000.0, 500.0)),
    ("TownHall", (-41000.0, -66000.0, 400.0)),
    ("PoliceStation", (-66000.0, -29000.0, 300.0)),
    ("Clinic", (-23000.0, -48000.0, 200.0)),
    ("PoliceArena", (-62000.0, -24000.0, 300.0)),
)

WINTER_ANCHORS = (
    ("Warehouse", (32000.0, -33000.0, 500.0)),
    ("LoadingYard", (53000.0, -43000.0, 400.0)),
    ("Workshops", (35000.0, -66000.0, 500.0)),
    ("PowerStation", (65000.0, -66000.0, 700.0)),
    ("CoolingChannel", (78000.0, -56000.0, 300.0)),
    ("SewerControl", (25000.0, -78000.0, -500.0)),
    ("DamGate", (76000.0, -33000.0, 600.0)),
)

SEWER_ANCHORS = (
    ("Hub", (0.0, -6000.0, -700.0)),
    ("Spring", (-40000.0, 18000.0, -700.0)),
    ("Summer", (28000.0, 20000.0, -700.0)),
    ("Autumn", (-28000.0, -25000.0, -700.0)),
    ("Winter", (26000.0, -40000.0, -700.0)),
    ("Control", (25000.0, -78000.0, -500.0)),
)

EXTRACTION_ANCHORS = (
    ("Perimeter", (79000.0, -31000.0, 700.0)),
    ("ControlBuilding", (84000.0, -31000.0, 900.0)),
    ("DefenseA", (82000.0, -25000.0, 900.0)),
    ("DefenseB", (87000.0, -35000.0, 1000.0)),
    ("FinalCrossing", (84000.0, -21000.0, 1100.0)),
    ("Endpoint", (88000.0, -18000.0, 1200.0)),
)


ZONE_SPECS: tuple[ZoneSpec, ...] = (
    ZoneSpec(
        "Hub",
        (-15000.0, 15000.0, -15000.0, 15000.0),
        0.0,
        HUB_ANCHORS,
        8,
        2,
        0,
        8,
        2,
        (
            ("InitialEquipment", (0.0, -1800.0, 100.0)),
            ("ObjectiveBoard", (0.0, 2000.0, 100.0)),
            ("DistrictAccess", (1800.0, 0.0, 100.0)),
            ("ReturnStash", (-1800.0, 0.0, 100.0)),
        ),
    ),
    ZoneSpec(
        "Spring",
        (-85000.0, -15000.0, 15000.0, 85000.0),
        200.0,
        SPRING_ANCHORS,
        32,
        8,
        3,
        21,
        4,
        (
            ("RelayApproach", (-55000.0, 57500.0, 500.0)),
            ("RelayPower", (-57500.0, 59000.0, 650.0)),
            ("RelayRepair", (-57000.0, 60000.0, 900.0)),
            ("DistrictKey", (-55500.0, 60500.0, 450.0)),
            ("HubShortcutUnlock", (-50500.0, 47000.0, 350.0)),
        ),
    ),
    ZoneSpec(
        "Summer",
        (15000.0, 85000.0, 15000.0, 85000.0),
        0.0,
        SUMMER_ANCHORS,
        36,
        9,
        3,
        24,
        4,
        (
            ("FuelPickup", (31500.0, 64200.0, 150.0)),
            ("BatteryPickup", (53500.0, 56000.0, 250.0)),
            ("ServiceGateControl", (61000.0, 50000.0, 150.0)),
            ("MotelCache", (52000.0, 55000.0, 250.0)),
            ("BoardwalkPower", (48500.0, 76500.0, 250.0)),
            ("StormDrainUnlock", (24500.0, 31500.0, 50.0)),
        ),
    ),
    ZoneSpec(
        "Autumn",
        (-85000.0, -15000.0, -85000.0, -15000.0),
        300.0,
        AUTUMN_ANCHORS,
        40,
        10,
        4,
        27,
        5,
        (
            ("InfrastructureRecords", (-41000.0, -66000.0, 550.0)),
            ("ArmoryAccess", (-66000.0, -29000.0, 450.0)),
            ("PoliceDefenseStart", (-62000.0, -24000.0, 450.0)),
            ("PoliceDefenseComplete", (-61000.0, -25500.0, 450.0)),
            ("MarketShortcut", (-54000.0, -43000.0, 450.0)),
            ("RooftopBridge", (-65000.0, -56000.0, 1700.0)),
            ("SewerUnlock", (-30000.0, -27000.0, 100.0)),
        ),
    ),
    ZoneSpec(
        "Winter",
        (15000.0, 85000.0, -85000.0, -15000.0),
        500.0,
        WINTER_ANCHORS,
        46,
        11,
        4,
        28,
        5,
        (
            ("PowerStationEntry", (63000.0, -65000.0, 800.0)),
            ("PowerSwitchA", (64500.0, -67000.0, 900.0)),
            ("PowerSwitchB", (66500.0, -65500.0, 900.0)),
            ("MainBreaker", (65000.0, -66500.0, 1100.0)),
            ("DamControls", (76000.0, -33000.0, 800.0)),
            ("ServiceRoadGate", (75500.0, -34000.0, 750.0)),
            ("UtilityTunnel", (43000.0, -61000.0, 200.0)),
            ("SewerControl", (25000.0, -78000.0, -350.0)),
        ),
    ),
    ZoneSpec(
        "Sewers",
        (-65000.0, 30000.0, -80000.0, 22000.0),
        -700.0,
        SEWER_ANCHORS,
        21,
        6,
        2,
        10,
        2,
        (
            ("HubMaintenanceAccess", (0.0, -6000.0, -550.0)),
            ("DistrictJunctionControl", (-28000.0, -25000.0, -550.0)),
            ("ControlRoomAccess", (25000.0, -78000.0, -350.0)),
        ),
    ),
    ZoneSpec(
        "Extraction",
        (72000.0, 90000.0, -45000.0, -15000.0),
        800.0,
        EXTRACTION_ANCHORS,
        28,
        7,
        2,
        6,
        2,
        (
            ("PerimeterEntry", (79000.0, -31000.0, 900.0)),
            ("ControlBuilding", (84000.0, -31000.0, 1100.0)),
            ("DefenseA", (82000.0, -25000.0, 1100.0)),
            ("DefenseB", (87000.0, -35000.0, 1200.0)),
            ("FinalCrossing", (84000.0, -21000.0, 1300.0)),
        ),
    ),
)


EXPECTED_TOTALS = {
    "zombie_spawns": sum(zone.zombie_spawns for zone in ZONE_SPECS),
    "spawn_groups": sum(zone.spawn_groups for zone in ZONE_SPECS),
    "horde_triggers": sum(zone.horde_triggers for zone in ZONE_SPECS),
    "general_loot": sum(zone.general_loot for zone in ZONE_SPECS),
    "high_value_loot": sum(zone.high_value_loot for zone in ZONE_SPECS),
    "objectives": sum(len(zone.objectives) for zone in ZONE_SPECS),
}


def get_level_subsystem() -> Any:
    subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if subsystem is None:
        fail("LevelEditorSubsystem is unavailable.")
    return subsystem


def get_actor_subsystem() -> Any:
    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    if subsystem is None:
        fail("EditorActorSubsystem is unavailable.")
    return subsystem


def current_level_path() -> str:
    try:
        return str(get_level_subsystem().get_current_level().get_outer().get_path_name())
    except Exception:
        return ""


def stage_actors() -> list[Any]:
    return [
        actor
        for actor in (get_actor_subsystem().get_all_level_actors() or [])
        if actor_has_tag(actor, STAGE_TAG)
    ]


def preflight() -> None:
    level_path = current_level_path()
    if GREYBOX_MAP not in level_path:
        fail(
            "Stage 9B must run with the ZombieSeasons greybox map loaded. "
            f"Current level: {level_path or '<unknown>'}"
        )

    existing = stage_actors()
    if existing:
        fail(
            f"Stage 9B already owns {len(existing)} actors in this map. "
            "Refusing to duplicate gameplay markers."
        )

    if not hasattr(unreal, "TargetPoint"):
        fail("unreal.TargetPoint is unavailable in this UE build.")


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def point_inside_hub_protected(x: float, y: float) -> bool:
    return math.hypot(x, y) < HUB_PROTECTED_RADIUS


def deterministic_points(zone: ZoneSpec, count: int, role: str) -> list[tuple[float, float, float]]:
    if count <= 0:
        return []

    seed = GLOBAL_SEED + sum(ord(char) for char in f"{zone.name}:{role}") * 97
    rng = random.Random(seed)
    anchors = zone.anchors
    xmin, xmax, ymin, ymax = zone.bounds
    margin = 900.0
    points: list[tuple[float, float, float]] = []
    golden_angle = math.radians(137.507764)

    for index in range(count):
        _anchor_name, anchor = anchors[index % len(anchors)]
        ring = 1 + (index // len(anchors))
        radius = 1800.0 + ring * 900.0 + rng.uniform(-350.0, 350.0)
        angle = golden_angle * index + rng.uniform(-0.22, 0.22)
        x = anchor[0] + math.cos(angle) * radius
        y = anchor[1] + math.sin(angle) * radius
        z = anchor[2] + MARKER_Z_OFFSET

        x = clamp(x, xmin + margin, xmax - margin)
        y = clamp(y, ymin + margin, ymax - margin)

        if zone.name == "Hub" and point_inside_hub_protected(x, y):
            base_angle = math.atan2(y, x)
            safe_radius = 8200.0 + (index % 3) * 900.0
            x = math.cos(base_angle) * safe_radius
            y = math.sin(base_angle) * safe_radius
            z = MARKER_Z_OFFSET

        if not (PLAYABLE_MIN_X <= x <= PLAYABLE_MAX_X and PLAYABLE_MIN_Y <= y <= PLAYABLE_MAX_Y):
            fail(f"Generated {zone.name} {role} point outside world bounds: {(x, y, z)}")
        points.append((x, y, z))

    return points


def spawn_marker(
    *,
    zone: str,
    role: str,
    stable_id: str,
    location: tuple[float, float, float],
    folder_suffix: str,
    extra_tags: tuple[str, ...] = (),
    persistent: bool = False,
) -> Any:
    actor = get_actor_subsystem().spawn_actor_from_class(
        unreal.TargetPoint,
        unreal.Vector(*location),
        unreal.Rotator(roll=0.0, pitch=0.0, yaw=0.0),
        transient=False,
    )
    if actor is None:
        fail(f"Unable to spawn marker {stable_id}.")

    label = "ZS_" + stable_id.replace(".", "_")
    actor.set_actor_label(label, mark_dirty=True)
    actor.set_folder_path(f"ZombieSeasons/Gameplay/{zone}/{folder_suffix}")
    add_generation_tags(actor, stage=STAGE, district=zone, stable_id=stable_id)

    tags = list(actor.get_editor_property("tags") or [])
    tags.extend(
        unreal.Name(tag)
        for tag in (
            f"ZS.MarkerType.{role}",
            *extra_tags,
        )
    )
    actor.set_editor_property("tags", tags)

    try:
        actor.set_editor_property("is_spatially_loaded", not persistent)
    except Exception as error:
        warn(f"Could not set spatial-loading state for {stable_id}: {error}")
    return actor


def create_zone_markers(zone: ZoneSpec) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []

    spawn_positions = deterministic_points(zone, zone.zombie_spawns, "Spawn")
    for index, position in enumerate(spawn_positions, start=1):
        group_index = ((index - 1) % max(1, zone.spawn_groups)) + 1
        stable_id = f"{zone.name}.Spawn.{index:03d}"
        spawn_marker(
            zone=zone.name,
            role="ZombieSpawnCandidate",
            stable_id=stable_id,
            location=position,
            folder_suffix="Spawns",
            extra_tags=(
                f"ZS.SpawnGroup.{zone.name}.{group_index:02d}",
                "ZS.AdapterTarget.BP_ZS_ZombieSpawnPoint",
                "ZS.NavProjection.Required",
            ),
        )
        rows.append({"id": stable_id, "role": "zombie_spawn", "location": position})

    group_positions = deterministic_points(zone, zone.spawn_groups, "SpawnGroup")
    for index, position in enumerate(group_positions, start=1):
        stable_id = f"{zone.name}.SpawnGroup.{index:02d}"
        spawn_marker(
            zone=zone.name,
            role="SpawnGroup",
            stable_id=stable_id,
            location=position,
            folder_suffix="SpawnGroups",
            extra_tags=("ZS.AdapterTarget.BP_ZS_SpawnGroup",),
            persistent=True,
        )
        rows.append({"id": stable_id, "role": "spawn_group", "location": position})

    horde_positions = deterministic_points(zone, zone.horde_triggers, "Horde")
    for index, position in enumerate(horde_positions, start=1):
        stable_id = f"{zone.name}.Horde.{index:02d}"
        spawn_marker(
            zone=zone.name,
            role="HordeTrigger",
            stable_id=stable_id,
            location=position,
            folder_suffix="HordeTriggers",
            extra_tags=("ZS.AdapterTarget.BP_ZS_HordeTrigger",),
            persistent=True,
        )
        rows.append({"id": stable_id, "role": "horde_trigger", "location": position})

    loot_positions = deterministic_points(zone, zone.general_loot, "Loot")
    for index, position in enumerate(loot_positions, start=1):
        stable_id = f"{zone.name}.Loot.{index:03d}"
        spawn_marker(
            zone=zone.name,
            role="LootPoint",
            stable_id=stable_id,
            location=position,
            folder_suffix="Loot/General",
            extra_tags=("ZS.AdapterTarget.BP_ZS_LootPoint", "ZS.LootTier.General"),
        )
        rows.append({"id": stable_id, "role": "general_loot", "location": position})

    high_positions = deterministic_points(zone, zone.high_value_loot, "HighValue")
    for index, position in enumerate(high_positions, start=1):
        stable_id = f"{zone.name}.HighValue.{index:02d}"
        spawn_marker(
            zone=zone.name,
            role="LootPoint",
            stable_id=stable_id,
            location=position,
            folder_suffix="Loot/HighValue",
            extra_tags=("ZS.AdapterTarget.BP_ZS_LootPoint", "ZS.LootTier.HighValue"),
        )
        rows.append({"id": stable_id, "role": "high_value_loot", "location": position})

    for objective_name, position in zone.objectives:
        stable_id = f"{zone.name}.Objective.{objective_name}"
        spawn_marker(
            zone=zone.name,
            role="Objective",
            stable_id=stable_id,
            location=position,
            folder_suffix="Objectives",
            extra_tags=("ZS.AdapterTarget.BP_ZS_ObjectiveTrigger", "ZS.Objective.Canonical"),
            persistent=True,
        )
        rows.append({"id": stable_id, "role": "objective", "location": position})

    return {
        "zone": zone.name,
        "counts": {
            "zombie_spawns": zone.zombie_spawns,
            "spawn_groups": zone.spawn_groups,
            "horde_triggers": zone.horde_triggers,
            "general_loot": zone.general_loot,
            "high_value_loot": zone.high_value_loot,
            "objectives": len(zone.objectives),
        },
        "markers": rows,
    }


def create_safe_zone_contract_marker() -> dict[str, Any]:
    stable_id = "Hub.SafeZone.Contract"
    spawn_marker(
        zone="Hub",
        role="SafeZoneContract",
        stable_id=stable_id,
        location=(0.0, 0.0, 150.0),
        folder_suffix="SafeZone",
        extra_tags=(
            "ZS.AdapterTarget.BP_ZS_SafeZoneVolume",
            f"ZS.SafeZoneRadius.{int(HUB_PROTECTED_RADIUS)}",
            "ZS.NoStandardZombieSpawn",
        ),
        persistent=True,
    )
    return {"id": stable_id, "radius_cm": HUB_PROTECTED_RADIUS}


def create_extraction_controller_contract_marker() -> dict[str, Any]:
    stable_id = "Extraction.Controller.Contract"
    spawn_marker(
        zone="Extraction",
        role="ExtractionControllerContract",
        stable_id=stable_id,
        location=(84000.0, -31000.0, 1600.0),
        folder_suffix="Controller",
        extra_tags=("ZS.AdapterTarget.BP_ZS_ExtractionController",),
        persistent=True,
    )
    return {"id": stable_id}


def validate_layout(zone_reports: list[dict[str, Any]]) -> dict[str, Any]:
    actual = {
        key: sum(report["counts"][key] for report in zone_reports)
        for key in EXPECTED_TOTALS
    }
    if actual != EXPECTED_TOTALS:
        fail(f"Stage 9B budget mismatch. Expected {EXPECTED_TOTALS}, got {actual}")

    hub_report = next(report for report in zone_reports if report["zone"] == "Hub")
    illegal_hub_spawns = []
    for marker in hub_report["markers"]:
        if marker["role"] != "zombie_spawn":
            continue
        x, y, _z = marker["location"]
        if point_inside_hub_protected(x, y):
            illegal_hub_spawns.append(marker["id"])
    if illegal_hub_spawns:
        fail("Hub zombie spawns entered protected radius: " + ", ".join(illegal_hub_spawns))

    return {
        "totals": actual,
        "hub_standard_spawns_inside_protected_radius": 0,
        "nav_projection_status": "DEFERRED_TO_STAGE_10",
        "runtime_adapter_binding_status": "DEFERRED_TO_STAGE_9C",
    }


def save_level() -> None:
    if not get_level_subsystem().save_current_level():
        fail("Gameplay markers were generated but the greybox level could not be saved.")


def position_viewport() -> None:
    try:
        subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        if subsystem is not None:
            subsystem.set_level_viewport_camera_info(
                unreal.Vector(0.0, -105000.0, 125000.0),
                unreal.Rotator(roll=0.0, pitch=-55.0, yaw=90.0),
            )
    except Exception as error:
        warn(f"Unable to position viewport for Stage 9B review: {error}")


def run() -> None:
    preflight()
    log("Stage 9B preflight passed. Creating deterministic gameplay-marker layout.")

    zone_reports = [create_zone_markers(zone) for zone in ZONE_SPECS]
    safe_zone = create_safe_zone_contract_marker()
    extraction_controller = create_extraction_controller_contract_marker()
    validation = validate_layout(zone_reports)

    save_level()
    position_viewport()

    report_path = write_json_report(
        "gameplay_layout_generation.json",
        {
            "status": "PASS",
            "stage": STAGE,
            "mode": MODE,
            "map": GREYBOX_MAP,
            "runtime_contract_note": (
                "Markers intentionally remain adapter-neutral because UE 5.5 Python did not expose "
                "Blueprint graph nodes for BP_EnemySpawner/GameMode inspection."
            ),
            "safe_zone": safe_zone,
            "extraction_controller": extraction_controller,
            "zones": zone_reports,
            "validation": validation,
        },
    )

    total_marker_actors = sum(
        sum(report["counts"].values()) for report in zone_reports
    ) + 2
    message = (
        "Stage 9B gameplay layout generation PASSED.\n\n"
        f"Generated gameplay markers: {total_marker_actors}\n"
        f"Zombie spawn candidates: {EXPECTED_TOTALS['zombie_spawns']}\n"
        f"Spawn groups: {EXPECTED_TOTALS['spawn_groups']}\n"
        f"Horde triggers: {EXPECTED_TOTALS['horde_triggers']}\n"
        f"General loot points: {EXPECTED_TOTALS['general_loot']}\n"
        f"High-value points: {EXPECTED_TOTALS['high_value_loot']}\n"
        f"Canonical objective markers: {EXPECTED_TOTALS['objectives']}\n"
        "Hub protected-radius violations: 0\n\n"
        "Runtime adapter binding: deferred to Stage 9C.\n"
        "NavMesh projection: deferred to Stage 10.\n\n"
        f"Report: {report_path}"
    )
    log(message.replace("\n", " "))
    show_editor_message("ZombieSeasons World Generation — Stage 9B", message)


if __name__ == "__main__":
    run()
