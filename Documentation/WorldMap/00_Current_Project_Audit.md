# 00 — Current Project Audit

## Confirmed repository facts

| Item | Confirmed value |
|---|---|
| Repository | `Owarino777/ZombieSeasons` |
| Default branch | `master` |
| Unreal association | `5.5` |
| Project type | First Person Blueprint template |
| Startup map | `/Game/FirstPerson/Maps/FirstPersonMap` |
| Default map | `/Game/FirstPerson/Maps/FirstPersonMap` |
| Default game mode | `/Game/FirstPerson/Blueprints/BP_FirstPersonGameMode` |
| Graphics API | DirectX 12 / Shader Model 6 |
| Dynamic GI | Lumen enabled |
| Reflections | Lumen reflection method enabled |
| Virtual Shadow Maps | Enabled |
| Ray tracing | Enabled in configuration |
| Static lighting | Disabled |
| Modeling Tools Editor Mode | Enabled |

## Confirmed gameplay assets

- `/Game/FirstPerson/Blueprints/BP_FirstPersonCharacter`
- `/Game/FirstPerson/Blueprints/BP_FirstPersonGameMode`
- `/Game/FirstPerson/Blueprints/BP_FirstPersonProjectile`
- `/Game/FirstPerson/Blueprints/BP_Pickup_Rifle`
- `/Game/FirstPerson/Blueprints/BP_Weapon_Component`
- `/Game/FirstPerson/Blueprints/AIC_Zombie`
- `/Game/FirstPerson/Blueprints/Enemies/BP_Zombie`
- Enhanced Input actions for movement, look, jump, and shoot.
- First-person arms, rifle animations, projectile, and starter content.
- Level-prototyping meshes and materials suitable for greyboxing.

## Confirmed current map inventory

- `/Game/FirstPerson/Maps/FirstPersonMap`
- Starter Content demonstration maps.

There is no confirmed production map for ZombieSeasons in the visible repository state.

## Current limitations

GitHub can confirm that `.uasset` and `.umap` files exist, but it cannot safely expose their Blueprint graph contents. The following data must be exported by Unreal Editor before automated integration:

- Blueprint parent classes.
- Public variables and types.
- Interfaces implemented.
- Event dispatchers.
- Callable functions.
- Behavior Tree and Blackboard references.
- Spawn logic and wave-management contracts.
- Health and damage interfaces.
- Loot and pickup interfaces.
- Save-game integration.
- Collision presets used by zombies and interactables.
- Navigation agent radius, height, and step limits.
- Asset dependencies and redirectors.

## Required local audit output

Run `Tools/export_project_audit.py` from Unreal Editor. The audit must produce:

```text
Saved/ZombieSeasonsAudit/
├── assets.csv
├── blueprints.csv
├── maps.csv
├── plugins.csv
└── project_summary.json
```

These files must then be committed under:

```text
Documentation/WorldMap/GeneratedAudit/
```

## Security and repository hygiene

The current `DefaultEngine.ini` includes an Android File Server security token. It is not intended as a gameplay secret, but environment-specific tokens should not be relied on as stable credentials. Do not add API keys, Fab credentials, Epic account information, or local file-system paths to the repository.

## Audit gate

The project is ready for documentation and greybox planning now. It is not ready for a one-shot final art build until the local audit and free asset acquisition are complete.
