# ZombieSeasons — World Map Production Dossier

## Status

This directory is the source of truth for the production of the large ZombieSeasons map.

The current GitHub repository contains an Unreal Engine 5.5 project based on the First Person Blueprint template. The repository currently exposes one gameplay map (`/Game/FirstPerson/Maps/FirstPersonMap`), the first-person character and weapon assets, `BP_Zombie`, and `AIC_Zombie`. Unreal binary assets cannot be reliably inspected from GitHub alone, so all Blueprint variables, interfaces, event dispatchers, behavior trees, navigation settings, and asset dependencies must be exported from the local Unreal Editor before production scripts reference them.

## Production rule

No map-generation script may invent an Unreal asset path. Every referenced asset must exist in `AssetRegistry.csv` with a verified object path and compatibility status.

## Documents

- `00_Current_Project_Audit.md`: confirmed repository state and unresolved local-editor checks.
- `01_Master_Level_Design.md`: world structure, measurements, progression, and pacing.
- `02_District_Specifications.md`: detailed design of Spring, Summer, Autumn, and Winter.
- `03_Technical_Integration.md`: World Partition, Blueprints, navigation, spawning, loot, and naming rules.
- `04_Free_Asset_Acquisition.md`: required free Fab/Megascans content and installation procedure.
- `05_Performance_And_Test_Plan.md`: performance budgets and validation gates.
- `AssetRegistry.csv`: verified asset catalog. Initially contains repository-confirmed assets only.
- `BlueprintIntegrationMatrix.csv`: Blueprint contracts to complete after the local audit.
- `Tools/export_project_audit.py`: Unreal Editor Python audit script.

## Delivery stages

1. Export the local project audit.
2. Freeze the asset registry and Blueprint contracts.
3. Build the complete greybox map.
4. Validate traversal, combat, zombie navigation, and 60–90 minute pacing.
5. Replace greybox modules with approved free assets.
6. Add lighting, audio, VFX, HLOD, and optimization.
7. Package and perform a full playthrough.

## Non-negotiable safeguards

- Never modify the original `FirstPersonMap` directly.
- Create the production map under `/Game/ZombieSeasons/Maps/`.
- Keep each district independently rebuildable.
- Run validation before saving generated levels.
- Keep generated actors tagged by district and generation version.
- Do not enable a third-party runtime plugin unless it is necessary and verified for UE 5.5.
- Prefer built-in Unreal plugins and content-only Fab packs.
