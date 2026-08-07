# 03 — Technical Integration

## Production maps

```text
/Game/ZombieSeasons/Maps/L_ZS_World
/Game/ZombieSeasons/Maps/Development/L_ZS_World_Greybox
```

Never modify `/Game/FirstPerson/Maps/FirstPersonMap` directly.

## World architecture

Recommended systems for the production world:

- World Partition.
- One File Per Actor.
- Runtime spatial loading.
- HLOD for district-scale streaming.
- Data Layers separating greybox, gameplay, final art, and districts.

Initial Data Layers:

```text
DL_ZS_Greybox
DL_ZS_Gameplay
DL_ZS_FinalArt
DL_ZS_Spring
DL_ZS_Summer
DL_ZS_Autumn
DL_ZS_Winter
DL_ZS_Extraction
```

## Required built-in editor plugins

- `PythonScriptPlugin` — required for project audit and map generation.
- `EditorScriptingUtilities` — required for reliable editor automation.
- `ModelingToolsEditorMode` — already enabled.
- `Fab` — required only for acquiring content.
- `PCG` — optional; enable only when the vegetation/dressing workflow is approved.

Python is editor-only. No packaged gameplay may require Python.

## Content structure

```text
/Game/ZombieSeasons/
├── Maps/
├── Blueprints/
│   ├── World/
│   ├── Encounters/
│   ├── Objectives/
│   ├── Loot/
│   └── Interactions/
├── Data/
├── Environment/
│   ├── Shared/
│   ├── Spring/
│   ├── Summer/
│   ├── Autumn/
│   └── Winter/
├── Materials/
├── VFX/
├── Audio/
└── Developer/
```

## Naming

| Type | Prefix | Example |
|---|---|---|
| Level | `L_` | `L_ZS_World` |
| Blueprint Actor | `BP_` | `BP_ZS_HordeTrigger` |
| Blueprint Interface | `BPI_` | `BPI_ZS_Interactable` |
| Actor Component | `BPC_` | `BPC_ZS_DistrictState` |
| Data Asset | `DA_` | `DA_ZS_District_Spring` |
| Data Table | `DT_` | `DT_ZS_LootTables` |
| Static Mesh | `SM_` | `SM_ZS_Barricade_01` |
| Material | `M_` | `M_ZS_Master_Surface` |
| Material Instance | `MI_` | `MI_ZS_Winter_Concrete` |
| Texture | `T_` | `T_ZS_Asphalt_D` |
| Niagara System | `NS_` | `NS_ZS_Snow` |

## Level integration adapters

The existing zombie Blueprints are binary assets and their callable contracts are not yet verified. Level design must therefore use project-owned adapters:

- `BP_ZS_ZombieSpawnPoint`
- `BP_ZS_SpawnGroup`
- `BP_ZS_HordeTrigger`
- `BP_ZS_ObjectiveTrigger`
- `BP_ZS_DistrictGate`
- `BP_ZS_LootPoint`
- `BP_ZS_SafeZoneVolume`
- `BP_ZS_ExtractionController`

Adapters may reference `BP_Zombie` only after the audit confirms its class path and required initialization.

## Navigation

- Cover only intended zombie traversal areas with navigation.
- Validate doors, stairs, ramps, debris, and catwalks against the real zombie capsule.
- Use Nav Link Proxies for explicit drops and broken transitions.
- Keep zombie spawns on valid navigation and outside player line of sight.
- Do not include the protected Hub interior in standard zombie navigation.

## Generation strategy

```text
Tools/MapGeneration/
├── build_world.py
├── create_hub.py
├── create_spring.py
├── create_summer.py
├── create_autumn.py
├── create_winter.py
├── create_sewers.py
├── create_extraction.py
├── create_gameplay_markers.py
├── create_navigation.py
└── validate_world.py
```

Every generator must be idempotent and operate only on actors carrying its tags:

```text
ZS.Generated
ZS.District.Spring
ZS.GenerationVersion.001
```

## Asset-reference rule

A generation script may load an asset only when its exact Unreal object path exists in `AssetRegistry.csv` and its status is `VERIFIED`. Missing assets must fail validation with an explicit error; scripts must never silently replace them with unrelated content.

## Texture and material rules

- Default environment textures: 2K.
- 4K only for justified hero assets.
- Keep imported pack masters unchanged where possible.
- Create project-owned material instances under `/Game/ZombieSeasons/Materials/Instances/`.
- Do not mix incompatible art packs inside one visible POI without a material-normalization pass.
