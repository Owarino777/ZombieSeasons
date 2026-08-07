# 08 — Generation Execution Plan

## Purpose

This document defines how the production world is generated without overwriting existing maps, silently substituting assets, or coupling runtime gameplay to editor Python.

The generator is intentionally modular. A failed district or stage must be rebuildable without rebuilding unrelated districts.

## Production maps

```text
/Game/ZombieSeasons/Maps/Development/L_ZS_World_Greybox
/Game/ZombieSeasons/Maps/L_ZS_World
```

The first generated target is always `L_ZS_World_Greybox`.

`L_ZS_World` is created only after the greybox acceptance gates pass.

Existing TopDownShooter, MainMap, AI_TestMap, and Black Tide maps are read-only references for this workflow.

## Generator root

Production Unreal Editor Python scripts belong under:

```text
Content/Python/ZombieSeasons/MapGeneration/
```

Required scripts:

```text
00_validate_environment.py
01_create_world_shell.py
02_create_hub.py
03_create_spring.py
04_create_summer.py
05_create_autumn.py
06_create_winter.py
07_create_sewers.py
08_create_extraction.py
09_create_gameplay_markers.py
10_create_navigation_setup.py
11_create_lighting_baseline.py
12_validate_generated_world.py
run_generation_stage.py
```

No single monolithic script is allowed to generate the entire production map.

## Stage contract

### Stage 0 — Environment validation

Validates before any map mutation:

- Unreal Engine version is compatible with the recorded production environment.
- project path is correct;
- required plugins are enabled;
- `r.VirtualTextures=True` is active;
- production manifest exists;
- all 201 generator-enabled asset paths resolve;
- required gameplay Blueprint paths resolve;
- no destination-map naming collision exists unless an explicit rebuild mode is requested;
- free disk space warning is emitted if local project drive is below the configured safety margin.

Failure aborts generation before creating actors.

### Stage 1 — World shell

Creates the new greybox world with:

- World Partition;
- One File Per Actor;
- configured runtime grid;
- Data Layers;
- world bounds markers;
- Hub reserved area;
- district bounds markers;
- extraction boundary;
- elevation baseline;
- generated road graph placeholders.

No final City Sample art is placed in this stage.

### Stage 2 — Hub

Creates:

- protected safehouse volume;
- Hub floor / walls greybox;
- four district exits;
- ring-road connections;
- operations room marker;
- objective board marker;
- initial player start marker;
- safe-zone marker;
- navigation exclusion for routine zombies.

### Stage 3 — Spring

Creates the frozen Spring POI footprints and route topology from `07_Production_World_Specification.md`.

### Stage 4 — Summer

Creates the frozen Summer POI footprints and route topology.

### Stage 5 — Autumn

Creates the frozen Autumn POI footprints and route topology.

### Stage 6 — Winter

Creates the frozen Winter POI footprints and route topology.

### Stage 7 — Sewers

Creates only the documented sewer junctions and interconnections. It does not generate a procedural maze.

### Stage 8 — Extraction

Creates the dam perimeter, moving-defense positions, final crossing, and extraction endpoint.

### Stage 9 — Gameplay markers

Places only project-owned adapter actors / marker actors with stable IDs.

This stage never assumes undocumented methods on existing binary Blueprints.

### Stage 10 — Navigation setup

Creates or configures navigation-support actors and validates intended traversal spaces. It may create Nav Link Proxies for documented transitions.

Navigation build itself may still require an editor-side build command depending on UE 5.5 Python exposure.

### Stage 11 — Lighting baseline

Adds only neutral production lighting required to evaluate the greybox. Seasonal final lighting belongs to the art-pass workflow.

### Stage 12 — Validation

Runs the complete validation gate and produces a machine-readable report under:

```text
Saved/ZombieSeasonsWorldGeneration/Validation/
```

## Determinism

Global production seed:

```text
24071996
```

Each district derives its own deterministic seed from the global seed and district identifier. Random choices may affect non-critical dressing only.

Randomness may never alter:

- objective positions;
- district bounds;
- critical roads;
- mandatory shortcuts;
- horde-arena exits;
- extraction topology;
- gameplay actor stable IDs.

## Rebuild modes

Every stage supports one of two explicit modes:

```text
CREATE
REBUILD_GENERATED
```

`CREATE` fails if generated actors for that stage already exist.

`REBUILD_GENERATED` removes only actors carrying both:

```text
ZS.Generated
ZS.Stage.<StageName>
```

and then recreates the stage.

A generator must never delete untagged actors.

## Save checkpoints

The editor saves after every successful stage.

Expected checkpoints:

```text
WorldShell
Hub
Spring
Summer
Autumn
Winter
Sewers
Extraction
GameplayMarkers
NavigationSetup
LightingBaseline
ValidationPassed
```

If a stage fails, the previously saved stage remains the rollback point.

## Asset use

The generator reads:

```text
Documentation/WorldMap/GeneratedProductionManifest/production_asset_manifest.csv
```

First production pass rules:

- `APPROVED` + `generator_enabled=true`: selectable.
- `RESERVE`: not selectable.
- `REJECTED`: absent from final manifest.
- exact Unreal `object_path` only.
- no runtime wildcard folder search.
- no fallback to a visually unrelated asset.

Generated roads use the approved primary asphalt material. Secondary damaged/aged asphalt variants remain reserve-only until explicitly promoted.

## Greybox versus art pass

Greybox generation uses primitive or project-owned temporary geometry for topology-critical structures.

Final production assets are introduced only after the greybox traversal and gameplay gates pass.

This prevents asset dimensions from dictating level design and keeps navigation / pacing testable before expensive art placement.

## Art-pass replacement rules

A greybox module may be replaced by production art only when:

- replacement preserves required gameplay clearance;
- collision is validated;
- navigation remains valid;
- objective / spawn markers remain unchanged;
- no critical sightline is unintentionally blocked;
- the replacement asset is generator-enabled in the manifest;
- performance budget remains within the current gate.

## Gameplay adapter dependencies

The following project-owned adapters remain the intended integration boundary:

```text
BP_ZS_ZombieSpawnPoint
BP_ZS_SpawnGroup
BP_ZS_HordeTrigger
BP_ZS_ObjectiveTrigger
BP_ZS_DistrictGate
BP_ZS_LootPoint
BP_ZS_SafeZoneVolume
BP_ZS_ExtractionController
```

If any do not yet exist, the greybox generator places deterministic marker actors using the same stable IDs and records the missing adapter as a blocker rather than inventing gameplay behavior.

## Known blockers to close before complete playable greybox

### BP_GameMode event warning

The existing `BP_GameMode` warning involving `UpdateUI_PlayerHealth` must be resolved or explicitly proven unrelated to the production flow before final gameplay certification.

### Navigation serialization warning

The earlier Black Tide greybox reported a serialized NavMesh max-tiles mismatch. The new production map must create navigation from clean settings rather than copying that navigation data.

### Nanite / vendor material warning

The Fab base material warning about `bUsedWithNanite` must be tested only if an approved production asset actually depends on that material in the production map. Vendor masters should not be modified pre-emptively.

### Existing Blueprint contracts

Binary Blueprint event graphs still require targeted editor verification wherever the adapters need to invoke existing game systems.

## Validation report requirements

`12_validate_generated_world.py` must report at minimum:

- world bounds;
- generated actor count by stage and district;
- duplicate stable IDs;
- missing required stage tags;
- missing required POIs;
- missing required shortcuts;
- unresolved asset paths;
- unexpected reserve / rejected asset usage;
- objective-marker count;
- spawn-marker count by district;
- gameplay markers outside their owning district;
- actors outside playable bounds;
- Hub zombie-spawn violations;
- horde arena exit-count violations;
- navigation-support coverage warnings;
- maps modified outside `/Game/ZombieSeasons/Maps/`;
- save failures.

A validation failure blocks the next production stage.

## Performance checkpoints

Generation execution follows the performance gates from `05_Performance_And_Test_Plan.md`:

1. empty-world baseline;
2. complete greybox;
3. Spring vertical slice;
4. complete art pass;
5. packaged build.

No full-city final-art generation is allowed before the Spring vertical slice establishes a real cost baseline.

## Version-control boundaries

Recommended commit separation:

```text
gen: add world-generation validation framework
gen: create ZombieSeasons world shell
gen: add Hub greybox
gen: add Spring greybox
gen: add Summer greybox
gen: add Autumn greybox
gen: add Winter greybox
gen: add sewer and extraction greybox
gen: add gameplay marker layer
gen: add generated-world validator
```

Binary generated `.umap` commits should remain isolated from unrelated documentation or script changes whenever practical.

## Permission to begin generation

Actual `L_ZS_World_Greybox` generation begins only when:

- `07_Production_World_Specification.md` is committed;
- the final production manifest is committed;
- environment validation script exists;
- destination-map safety checks exist;
- no generator writes to the historical reference maps;
- the user has reopened Unreal after project configuration changes that require restart.
