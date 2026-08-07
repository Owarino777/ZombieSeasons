# 06 — Installed Environment Inventory

## Purpose

This document freezes the environment content currently available to the ZombieSeasons world-map production pipeline. It is generated from the lightweight Unreal Asset Registry inventory and must be treated as the source of truth for installed environment packs.

## Verified project state

The lightweight inventory was generated with Unreal Engine 5.5.4 without loading assets, resolving dependencies, compiling materials, building meshes, or opening maps.

| Root | Asset count | Status |
|---|---:|---|
| `/Game/CitySampleBuildings` | 10,779 | Installed and available |
| `/Game/CitySampleVehicles` | 1,405 | Installed and available |
| `/Game/Scene_UnfinishedBuilding` | 382 | Installed and available |
| `/Game/TopDownShooter` | 411 | Existing gameplay/project content |
| `/Game/StarterContent` | 287 | Existing utility/prototyping content |
| `/Fab` | 81 | Fab integration/material support content |

Total inventory: 13,345 assets.

## Asset-class capacity

The complete inventory currently contains, among other classes:

- 2,684 `StaticMesh` assets;
- 2,993 `Texture2D` assets;
- 6,458 `MaterialInstanceConstant` assets;
- 148 `Blueprint` assets;
- 14 `SkeletalMesh` assets;
- 108 `World` assets.

This is enough content to stop using Starter Content as the primary visual language of the production map.

## Production policy

The map generator must not reference an environment asset merely because it belongs to one of the installed packs.

Every environment mesh used by production generation must first appear in the generated environment catalog with:

- exact package path;
- exact object path;
- source pack;
- Unreal asset class;
- inferred production category;
- explicit approval status.

The generator must use exact object paths from that catalog. Runtime wildcard discovery is not allowed in the final production build because changes to imported packs could otherwise silently change generated geometry.

## Source-pack roles

### City Sample Buildings

Primary source for:

- city architecture;
- facade modules;
- structural building pieces;
- roofs and architectural detail;
- urban street dressing when suitable;
- large-scale skyline/background dressing.

It must not be used blindly. High-detail modules and large assemblies must be profiled before repetition across the full world.

### City Sample Vehicles

Primary source for:

- abandoned road vehicles;
- roadblocks;
- parking areas;
- environmental storytelling;
- traffic remnants.

Production generation should prefer static visual use unless an existing gameplay requirement explicitly needs a driveable Chaos vehicle.

### Scene Unfinished Building

Primary source for:

- damaged concrete;
- exposed construction structures;
- rubble and debris;
- ruined interiors;
- collapsed or unfinished areas;
- post-apocalyptic variation that prevents City Sample architecture from looking pristine.

## Technical settings confirmed for the installed packs

The project has been restarted after enabling the requested project support for the newly imported content. Production must keep the required renderer/plugin settings committed with the project before map generation is considered final.

## Known warning

The editor has reported that `/Fab/Materials/Standard/M_MS_Base` needs the Nanite usage flag. Do not modify the Fab base material merely to silence the warning unless a production asset actually depends on it and the issue reproduces in the packaged build. Project-owned material instances are preferred over modifying vendor content.

## Next gate

Run `Tools/build_environment_catalog.py` against `GeneratedAuditLight/assets_light.csv`.

The resulting catalog is the input to the world-map asset-selection phase. No final art-generation script should be authored before that catalog exists.
