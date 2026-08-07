# ZombieSeasons — World Map Production Dossier

## Status

This directory is the source of truth for the production of the large ZombieSeasons map on branch `feat/unreal-ai-map-generation`.

The active branch is significantly more advanced than the historical `master` state. It contains the existing TopDownShooter gameplay content, the current gameplay maps, and the previous automated Black Tide map-generation work. The Black Tide work is retained as technical reference only; the production world described in this dossier is a larger, independently rebuildable ZombieSeasons map.

Unreal binary assets cannot be reliably inspected from GitHub alone. Therefore Blueprint internals, runtime contracts, navigation settings, material compatibility, map dependencies, and exact asset paths must be exported from the local Unreal Editor before final production scripts reference them.

## Production rule

No production map-generation script may invent an Unreal asset path. Every referenced asset must be confirmed by the generated local audit or explicitly added to `AssetRegistry.csv` after validation in Unreal Editor.

The audit scans:

- `/Game` for project-owned content;
- `/Fab` for currently mounted Fab content.

The complete `/Engine` mount is intentionally excluded because it would add thousands of irrelevant engine assets.

## Existing automation reference

The branch already contains the previous Black Tide generation work under `Content/Python/`, including:

- `ZM_Black_Tide_design.md`;
- `build_zm_black_tide_artpass.py`;
- `build_zm_black_tide_artpass_v2_safe.py`;
- `fix_zm_black_tide_lighting.py`.

These files must not be deleted. Their safe-generation patterns, asset loading, deterministic placement, actor tagging, non-destructive destination-map workflow, lighting helpers, and error handling can be reused where appropriate. Their level design and dimensions are not the target for the new large map.

## Documents

- `00_Current_Project_Audit.md`: confirmed repository state and unresolved local-editor checks.
- `01_Master_Level_Design.md`: world structure, measurements, progression, and pacing.
- `02_District_Specifications.md`: detailed design of Spring, Summer, Autumn, and Winter.
- `03_Technical_Integration.md`: World Partition, Blueprints, navigation, spawning, loot, and naming rules.
- `04_Free_Asset_Acquisition.md`: required free Fab/Megascans content and installation procedure.
- `05_Performance_And_Test_Plan.md`: performance budgets and validation gates.
- `AssetRegistry.csv`: verified asset catalog.
- `BlueprintIntegrationMatrix.csv`: Blueprint contracts to complete after the local audit.
- `Tools/export_project_audit.py`: Unreal Editor Python audit script.

## Delivery stages

1. Export the local project and Fab audit.
2. Commit the generated audit results on `feat/unreal-ai-map-generation`.
3. Freeze the asset registry and Blueprint contracts.
4. Build the complete greybox map in a new production map, without modifying the existing gameplay maps.
5. Validate traversal, combat, zombie navigation, and 60–90 minute pacing.
6. Select and add only approved free Fab/Megascans content.
7. Replace greybox modules with approved assets district by district.
8. Add lighting, audio, VFX, HLOD, and optimization.
9. Package and perform a full playthrough.

## Non-negotiable safeguards

- Never overwrite an existing gameplay map as part of generation.
- Create the new production map under a dedicated ZombieSeasons map path.
- Keep each district independently rebuildable.
- Use deterministic seeds for procedural dressing.
- Run validation before saving generated levels.
- Keep generated actors tagged by district, generation stage, and generation version.
- Never silently fall back to a different asset when a required production asset is missing.
- Do not enable a third-party runtime plugin unless it is necessary, free, and verified for UE 5.5.
- Prefer built-in Unreal plugins and content-only Fab packs.
- Preserve the existing Black Tide maps and scripts as rollback/reference material.
