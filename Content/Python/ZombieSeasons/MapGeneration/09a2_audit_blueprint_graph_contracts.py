"""Deep, read-only Blueprint graph audit for ZombieSeasons Stage 9.

Run from Unreal Editor after 09a_audit_gameplay_contracts.py:

py "C:/Users/malik/Documents/Unreal Projects/ZombieSeasons/Content/Python/ZombieSeasons/MapGeneration/09a2_audit_blueprint_graph_contracts.py"

UE 5.5 does not expose the newer high-level Blueprint graph listing helpers available in
later engine versions. This audit therefore uses the UE 5.5 BlueprintEditorLibrary entry
points plus conservative reflected-property probes to inspect the actual Blueprint graphs
without modifying or compiling any project asset.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import unreal


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from zs_generation_common import (  # noqa: E402
    editor_asset_exists,
    fail,
    log,
    show_editor_message,
    warn,
    write_json_report,
)


STAGE = "BlueprintGraphContractAudit"

TARGETS: tuple[tuple[str, str], ...] = (
    ("enemy_spawner", "/Game/TopDownShooter/Core/BP_EnemySpawner"),
    ("game_mode", "/Game/TopDownShooter/Core/BP_GameMode"),
    ("fps_game_mode", "/Game/TopDownShooter/Core/BP_FPSGameMode"),
    ("enemy", "/Game/TopDownShooter/Core/BP_Enemy"),
    ("enemy_controller", "/Game/TopDownShooter/Core/AIC_Enemy"),
    ("game_mode_interface", "/Game/TopDownShooter/Core/BPI_GameMode_MP"),
    ("damage_interface", "/Game/TopDownShooter/Core/BPI_Damageable"),
)

GRAPH_PROPERTY_NAMES: tuple[str, ...] = (
    "ubergraph_pages",
    "function_graphs",
    "macro_graphs",
    "delegate_signature_graphs",
    "intermediate_generated_graphs",
)

NODE_REFERENCE_PROPERTIES: tuple[str, ...] = (
    "function_reference",
    "event_reference",
    "variable_reference",
    "delegate_reference",
    "custom_function_name",
    "function_name",
    "event_name",
    "proxy_factory_function_name",
)

CONTRACT_TOKENS: tuple[str, ...] = (
    "enemy",
    "spawn",
    "wave",
    "round",
    "remaining",
    "alive",
    "killed",
    "dead",
    "death",
    "damage",
    "health",
    "player",
    "hud",
    "ui",
    "start",
    "stop",
    "complete",
    "finished",
    "timer",
    "count",
    "navigation",
    "move",
    "target",
    "game_mode",
    "gamemode",
    "interface",
)


def safe_text(value: Any, limit: int = 800) -> str:
    try:
        text = str(value)
    except Exception as error:
        text = f"<unprintable:{type(error).__name__}>"
    if len(text) > limit:
        return text[: limit - 3] + "..."
    return text


def object_name(obj: Any) -> str:
    for method_name in ("get_name", "get_path_name"):
        method = getattr(obj, method_name, None)
        if callable(method):
            try:
                value = method()
                if value:
                    return safe_text(value)
            except Exception:
                pass
    return safe_text(obj)


def object_class_name(obj: Any) -> str:
    getter = getattr(obj, "get_class", None)
    if callable(getter):
        try:
            cls = getter()
            if cls is not None:
                path_getter = getattr(cls, "get_path_name", None)
                if callable(path_getter):
                    return safe_text(path_getter())
                return safe_text(cls)
        except Exception:
            pass
    return type(obj).__name__


def get_editor_property_if_available(obj: Any, name: str) -> tuple[bool, Any]:
    getter = getattr(obj, "get_editor_property", None)
    if not callable(getter):
        return False, None
    try:
        return True, getter(name)
    except Exception:
        return False, None


def load_blueprint(asset_path: str) -> Any:
    if not editor_asset_exists(asset_path):
        fail(f"Required Blueprint asset is missing: {asset_path}")
    asset = unreal.load_asset(asset_path)
    if asset is None:
        fail(f"Unable to load Blueprint asset: {asset_path}")
    return asset


def add_graph_unique(graphs: list[Any], seen: set[str], graph: Any) -> None:
    if graph is None:
        return
    key = object_name(graph)
    if key in seen:
        return
    seen.add(key)
    graphs.append(graph)


def discover_graphs(blueprint: Any) -> tuple[list[Any], dict[str, Any]]:
    graphs: list[Any] = []
    seen: set[str] = set()
    diagnostics: dict[str, Any] = {
        "event_graph_found": False,
        "reflected_graph_properties": {},
    }

    library = getattr(unreal, "BlueprintEditorLibrary", None)
    if library is None:
        fail("BlueprintEditorLibrary is unavailable. Enable the required editor plugin/module.")

    finder = getattr(library, "find_event_graph", None)
    if callable(finder):
        try:
            event_graph = finder(blueprint)
        except Exception as error:
            diagnostics["event_graph_error"] = safe_text(error)
        else:
            if event_graph is not None:
                diagnostics["event_graph_found"] = True
                add_graph_unique(graphs, seen, event_graph)

    for property_name in GRAPH_PROPERTY_NAMES:
        ok, value = get_editor_property_if_available(blueprint, property_name)
        if not ok:
            diagnostics["reflected_graph_properties"][property_name] = "UNAVAILABLE"
            continue
        try:
            entries = list(value or [])
        except Exception:
            entries = []
        diagnostics["reflected_graph_properties"][property_name] = len(entries)
        for graph in entries:
            add_graph_unique(graphs, seen, graph)

    return graphs, diagnostics


def read_node_reference_properties(node: Any) -> dict[str, str]:
    values: dict[str, str] = {}
    for property_name in NODE_REFERENCE_PROPERTIES:
        ok, value = get_editor_property_if_available(node, property_name)
        if ok:
            values[property_name] = safe_text(value)
    return values


def relevant_attribute_names(node: Any) -> list[str]:
    try:
        names = dir(node)
    except Exception:
        return []
    result: list[str] = []
    for name in names:
        lowered = name.lower()
        if name.startswith("_"):
            continue
        if any(token in lowered for token in CONTRACT_TOKENS):
            result.append(name)
    return sorted(set(result))


def inspect_node(node: Any) -> dict[str, Any]:
    name = object_name(node)
    class_name = object_class_name(node)
    refs = read_node_reference_properties(node)

    ok_comment, comment = get_editor_property_if_available(node, "node_comment")
    ok_enabled, enabled_state = get_editor_property_if_available(node, "enabled_state")

    text_blob = " ".join(
        [name, class_name, *refs.keys(), *refs.values(), safe_text(comment) if ok_comment else ""]
    ).lower()
    matched_tokens = sorted(token for token in CONTRACT_TOKENS if token in text_blob)

    return {
        "name": name,
        "class": class_name,
        "reference_properties": refs,
        "comment": safe_text(comment) if ok_comment and comment else "",
        "enabled_state": safe_text(enabled_state) if ok_enabled else None,
        "relevant_attribute_names": relevant_attribute_names(node),
        "matched_contract_tokens": matched_tokens,
        "contract_candidate": bool(matched_tokens),
    }


def inspect_graph(graph: Any) -> dict[str, Any]:
    result: dict[str, Any] = {
        "name": object_name(graph),
        "class": object_class_name(graph),
        "node_property_available": False,
        "node_count": 0,
        "contract_candidate_count": 0,
        "nodes": [],
        "warnings": [],
    }

    ok, nodes_value = get_editor_property_if_available(graph, "nodes")
    if not ok:
        result["warnings"].append("Graph 'nodes' property is not exposed to Python in this UE build.")
        return result

    result["node_property_available"] = True
    try:
        nodes = list(nodes_value or [])
    except Exception as error:
        result["warnings"].append(f"Unable to enumerate graph nodes: {safe_text(error)}")
        return result

    inspected = [inspect_node(node) for node in nodes if node is not None]
    result["nodes"] = inspected
    result["node_count"] = len(inspected)
    result["contract_candidate_count"] = sum(1 for row in inspected if row["contract_candidate"])
    return result


def inspect_target(key: str, asset_path: str) -> dict[str, Any]:
    blueprint = load_blueprint(asset_path)
    graphs, diagnostics = discover_graphs(blueprint)
    graph_rows = [inspect_graph(graph) for graph in graphs]

    return {
        "key": key,
        "asset_path": asset_path,
        "asset_type": type(blueprint).__name__,
        "graph_discovery": diagnostics,
        "graph_count": len(graph_rows),
        "total_node_count": sum(row["node_count"] for row in graph_rows),
        "contract_candidate_count": sum(row["contract_candidate_count"] for row in graph_rows),
        "graphs": graph_rows,
    }


def summarize(targets: dict[str, dict[str, Any]]) -> dict[str, Any]:
    graph_count = sum(row["graph_count"] for row in targets.values())
    node_count = sum(row["total_node_count"] for row in targets.values())
    candidate_count = sum(row["contract_candidate_count"] for row in targets.values())
    targets_with_nodes = [key for key, row in targets.items() if row["total_node_count"] > 0]
    targets_with_candidates = [
        key for key, row in targets.items() if row["contract_candidate_count"] > 0
    ]

    spawner = targets.get("enemy_spawner", {})
    spawner_nodes = int(spawner.get("total_node_count", 0))
    spawner_candidates = int(spawner.get("contract_candidate_count", 0))

    return {
        "target_count": len(targets),
        "graph_count": graph_count,
        "node_count": node_count,
        "contract_candidate_count": candidate_count,
        "targets_with_nodes": targets_with_nodes,
        "targets_with_contract_candidates": targets_with_candidates,
        "enemy_spawner_node_count": spawner_nodes,
        "enemy_spawner_contract_candidate_count": spawner_candidates,
        "graph_introspection_usable": node_count > 0,
        "ready_for_stage_9b_contract_decision": spawner_nodes > 0 and spawner_candidates > 0,
    }


def run() -> None:
    if not hasattr(unreal, "BlueprintEditorLibrary"):
        fail("BlueprintEditorLibrary is unavailable in this Unreal Editor session.")

    log("Stage 9A2 Blueprint graph audit started. No Blueprint or map will be modified.")

    targets: dict[str, dict[str, Any]] = {}
    for key, asset_path in TARGETS:
        log(f"Inspecting Blueprint graph contract: {key} -> {asset_path}")
        targets[key] = inspect_target(key, asset_path)

    summary = summarize(targets)
    status = "PASS" if summary["graph_introspection_usable"] else "WARN"
    report = write_json_report(
        "gameplay_blueprint_graph_audit.json",
        {
            "status": status,
            "stage": STAGE,
            "read_only": True,
            "targets": targets,
            "summary": summary,
        },
    )

    if not summary["graph_introspection_usable"]:
        warn(
            "UE 5.5 did not expose graph nodes through the reflected graph properties. "
            "Do not infer the EnemySpawner contract from inherited wrapper symbols."
        )

    message = (
        "Blueprint graph contract audit completed.\n\n"
        f"Status: {status}\n"
        f"Targets: {summary['target_count']}\n"
        f"Graphs discovered: {summary['graph_count']}\n"
        f"Nodes inspected: {summary['node_count']}\n"
        f"Contract candidates: {summary['contract_candidate_count']}\n"
        f"EnemySpawner nodes: {summary['enemy_spawner_node_count']}\n"
        f"EnemySpawner contract candidates: {summary['enemy_spawner_contract_candidate_count']}\n"
        f"Ready for Stage 9B contract decision: {summary['ready_for_stage_9b_contract_decision']}\n\n"
        "No map or Blueprint was modified.\n\n"
        f"Report: {report}"
    )
    log(message.replace("\n", " "))
    show_editor_message(
        "ZombieSeasons World Generation — Stage 9A2",
        message,
    )


try:
    run()
except Exception as error:
    unreal.log_error(f"[ZombieSeasonsGeneration] Stage 9A2 failed: {error}")
    raise
