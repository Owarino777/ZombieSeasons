# ZombieSeasons — World Map Production Dossier

## Status

This directory is the source of truth for the production of the large ZombieSeasons map on branch `feat/unreal-ai-map-generation`.

The active branch is significantly more advanced than the historical `master` state. It contains the existing TopDownShooter gameplay content, the current gameplay maps, and the previous automated Black Tide map-generation work. The Black Tide work is retained as technical reference only; the production world described in this dossier is a larger, independently rebuildable ZombieSeasons map.

The environment inventory and production asset selection phase is now complete. The committed final production manifest contains 317 usable production entries: 201 generator-enabled `APPROVED` assets and 116 disabled `RESERVE` assets. The 82 rejected review assets are excluded from that manifest. Production generation must use exact object paths from the manifest and may not perform wildcard runtime asset discovery.

Unreal binary assets cannot be reliably inspected from GitHub alone. Blueprint internals, runtime contracts, navigation settings, material compatibility, and map behavior that depend on binary assets still require targeted validation in the local Unreal Editor.

## Production rule

No production map-generation script may invent an Unreal asset path. Every referenced production asset must come from the committed final manifest or from an explicitly versioned project-owned dependency.

The final generator input is:

```text
Documentation/WorldMap/GeneratedProductionManifest/production_asset_manifest.csv
```

Only rows with:

```text
decision = APPROVED
generator_enabled = true
```

are selectable by the default generator.

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
- `04_Free_Asset_Acquisition.md`: approved free Fab content and installation procedure.
- `05_Performance_And_Test_Plan.md`: performance budgets and validation gates.
- `06_Installed_Environment_Inventory.md`: installed environment-pack inventory state.
- `07_Production_World_Specification.md`: frozen production bounds, coordinates, POI anchors, roads, sewers, gameplay budgets, World Partition defaults, and topology contract.
- `08_Generation_Execution_Plan.md`: modular generator architecture, safety rules, stage ordering, rollback, validation, and blockers.
- `GeneratedProductionManifest/production_asset_manifest.csv`: final 317-entry production manifest.
- `GeneratedProductionManifest/approved_asset_paths.txt`: exact 201 generator-enabled Unreal object paths.
- `BlueprintIntegrationMatrix.csv`: Blueprint contracts and targeted integration checks.
- `Tools/`: audit, classification, shortlist, review, decision, and manifest-generation tools.

## Delivery stages

1. Export the local project and Fab audit. — complete.
2. Commit the generated audit results. — complete.
3. Freeze the production asset set. — complete.
4. Freeze the production world topology and generation contract. — complete.
5. Build the modular environment validator and greybox generators.
6. Generate the complete greybox map in a new ZombieSeasons production map.
7. Validate traversal, combat topology, zombie navigation, and 60–90 minute pacing.
8. Build the Spring vertical slice using approved final-quality assets.
9. Profile the vertical slice and lock art/performance budgets.
10. Replace remaining greybox modules district by district.
11. Add final lighting, audio, VFX, HLOD, and optimization.
12. Package and perform a complete playthrough.

## Non-negotiable safeguards

- Never overwrite an existing gameplay map as part of generation.
- Create the new production map under `/Game/ZombieSeasons/Maps/`.
- Keep each district independently rebuildable.
- Use deterministic seeds for procedural dressing.
- Run validation before advancing generation stages.
- Keep generated actors tagged by district, generation stage, and generation version.
- Never silently fall back to a different asset when a required production asset is missing.
- Do not enable a third-party runtime plugin unless it is necessary, free, and verified for UE 5.5.
- Prefer built-in Unreal plugins and content-only Fab packs.
- Preserve the existing Black Tide maps and scripts as rollback/reference material.
- Keep `RESERVE` assets disabled until explicitly promoted in the production manifest.
- Do not run full-city final-art generation before the Spring vertical slice establishes the real performance cost.
