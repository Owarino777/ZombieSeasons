# 00 — Current Project Audit

## Audit status

The local Unreal Editor audit was completed on Unreal Engine 5.5.4 and committed under `Documentation/WorldMap/GeneratedAudit/`.

| Item | Confirmed value |
|---|---|
| Working branch | `feat/unreal-ai-map-generation` |
| Unreal Engine | `5.5.4-40574608+++UE5+Release-5.5` |
| Project name | `ZombieSeasons` |
| Editor startup map | `/Game/TopDownShooter/Maps/MainMap` |
| Game default map | `/Game/TopDownShooter/Maps/MainMap` |
| Global default GameMode | `/Game/TopDownShooter/Core/BP_GameMode` |
| Scanned mounts | `/Game`, `/Fab` |
| Total audited assets | 779 |
| `/Game` assets | 698 |
| `/Fab` assets | 81 |
| Blueprints | 24 |
| Maps | 9 |
| Static meshes | 81 |
| Materials | 98 |
| Material instances | 11 |
| Textures | 142 |
| Sound waves | 32 |
| Sound cues | 17 |
| Object redirectors | 287 |
| Failed Blueprint loads | 0 |

## Confirmed production gameplay assets

The actual production gameplay is under `/Game/TopDownShooter/`, not the legacy First Person template paths.

### Player and gameplay

- `/Game/TopDownShooter/Core/BP_FPSCharacter`
- `/Game/TopDownShooter/Core/BP_Hero`
- `/Game/TopDownShooter/Core/BP_Character`
- `/Game/TopDownShooter/Core/BP_FPSGameMode`
- `/Game/TopDownShooter/Core/BP_GameMode`
- `/Game/TopDownShooter/Core/WBP_InGameHUD`
- `/Game/TopDownShooter/Core/BPI_Damageable`
- `/Game/TopDownShooter/Core/BPI_GameMode_MP`

### Enemy system

- `/Game/TopDownShooter/Core/BP_Enemy`
- `/Game/TopDownShooter/Core/BP_EnemySpawner`
- `/Game/TopDownShooter/Core/AIC_Enemy`
- `/Game/TopDownShooter/Core/Animation/ABP_Enemy`
- `/Game/TopDownShooter/Core/Animation/BS_Enemy_Walk`

`BP_Enemy` depends on the AI controller, enemy animation blueprint, damage interface and GameMode interface. `BP_EnemySpawner` depends directly on `BP_Enemy`, `BPI_GameMode_MP`, AIModule and NavigationSystem. This confirms that enemy spawning and navigation already exist and must be integrated rather than replaced.

### Weapons and input

- `/Game/TopDownShooter/Core/Weapon/BP_Gun`
- `/Game/TopDownShooter/Core/Weapon/BP_Projectile`
- `/Game/TopDownShooter/Core/Inputs/IMC_FPS`
- `/Game/TopDownShooter/Core/Inputs/IMC_TopDown`
- `/Game/TopDownShooter/Core/Inputs/INP_AutoFire`
- `/Game/TopDownShooter/Core/Inputs/INP_FireProjectile`
- `/Game/TopDownShooter/Core/Inputs/INP_LookAround`
- `/Game/TopDownShooter/Core/Inputs/INP_MoveAround`

`BP_FPSCharacter` already depends on the FPS gameplay assets, HUD/game-mode interfaces, weapon Blueprint and Enhanced Input.

## Confirmed maps

Project gameplay maps:

- `/Game/TopDownShooter/Maps/AI_TestMap`
- `/Game/TopDownShooter/Maps/MainMap`
- `/Game/TopDownShooter/Maps/MainMap1`
- `/Game/TopDownShooter/Maps/ZM_BlackTide_Greybox`
- `/Game/TopDownShooter/Maps/ZM_BlackTide_ArtPass`
- `/Game/TopDownShooter/Maps/ZM_BlackTide_ArtPass_V2`

Starter Content maps:

- `/Game/TopDownShooter/Ressources/StarterContent/Maps/Advanced_Lighting`
- `/Game/TopDownShooter/Ressources/StarterContent/Maps/Minimal_Default`
- `/Game/TopDownShooter/Ressources/StarterContent/Maps/StarterMap`

`ZM_BlackTide_*` already uses `BP_FPSGameMode` and NavigationSystem and is the reference implementation for non-destructive Python-assisted map generation. It is not the target final map.

## Existing environment content

The project contains Starter Content architecture, props, shapes, materials, audio and effects. These are enough for greyboxing and for a limited art pass, but not enough for the intended AAA-quality large seasonal map.

The `/Fab` mount currently contains 81 assets, but most belong to Fab/Megascans support materials, material functions and the Global Foliage Actor. They are not a complete city/environment pack.

A Megascans coconut asset is already referenced inside the project under `/Game/TopDownShooter/Ressources/Fab/Megascans/3D/...`, which confirms Fab/Megascans content has already been imported at least once.

## Rendering configuration

Confirmed in `Config/DefaultEngine.ini`:

- DirectX 12 / SM6;
- Lumen dynamic global illumination;
- Lumen reflections;
- Virtual Shadow Maps;
- ray tracing enabled;
- static lighting disabled;
- desktop / maximum graphics target.

These settings are appropriate for the intended visual direction but require strict environment and zombie-performance budgets.

## Plugin state

Declared in the project file:

- `ModelingToolsEditorMode` — enabled;
- `RawInput` — enabled.

Python Editor Script Plugin and Editor Scripting Utilities are enabled in the local editor for production tooling, even though they are not declared as project plugin entries in the `.uproject` audit output.

## Audit limitations that remain

The first audit successfully inventories assets and dependency relationships, but Unreal Engine 5.5 Python did not expose the old `AssetData.tags_and_values` interface and Blueprint asset properties such as `parent_class` through the attempted property access. Those fields therefore remain unavailable in the first CSV export.

This does not block level production because the dependency graph already confirms the major gameplay contracts. Before changing gameplay Blueprints, a second targeted Blueprint-introspection audit should be used instead of guessing graph internals.

## Repository hygiene

There are 287 ObjectRedirectors in the audited content. Do not bulk-delete or fix redirectors during map production without a dedicated backup and validation pass because existing maps and Blueprints may still depend on them.

Do not add API keys, Fab credentials, Epic account credentials or machine-specific secrets to the repository.

## Production gate

The project is ready for:

- full level-design documentation;
- final world measurements;
- deterministic greybox generation;
- gameplay placement using existing `BP_EnemySpawner` / `BP_FPSGameMode` contracts;
- acquisition of approved free environment content.

The project is not ready for the final art build until the approved free packs have been imported and re-audited so their exact Unreal object paths can be frozen in `AssetRegistry.csv`.