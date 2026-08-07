# 07 — Asset Visual Validation Workflow

## Purpose

The final ZombieSeasons world generator must never choose arbitrary assets at runtime.
Every production asset must progress through explicit states:

`CANDIDATE -> SHORTLISTED -> PENDING VISUAL REVIEW -> APPROVED or REJECTED`

Only `APPROVED` assets may enter the final production manifest.

The current metadata pipeline is useful for narrowing thousands of assets, but names
and paths cannot prove appearance, physical scale, pivot quality, collision quality,
material health, silhouette, or suitability for zombie-FPS traversal. Those properties
require targeted Unreal Editor inspection.

## Current review scope

The visual-review plan is generated from:

- `GeneratedProductionShortlist/production_shortlist.csv`;
- the 10 `MaterialInstanceConstant` asphalt variants in `GeneratedNewPackDetails/AsphaltMat.csv`.

The plan does not review every texture/material dependency independently. A mesh is
reviewed with its authored material setup as loaded by Unreal. Asphalt variants are
reviewed independently because one or more will become explicit road-surface materials.

## Step 1 — Build the deterministic review plan

Run from PowerShell at the project root:

```powershell
py "Documentation\WorldMap\Tools\build_asset_review_plan.py"
```

Generated files:

- `Documentation/WorldMap/GeneratedAssetReview/asset_review.csv`;
- `Documentation/WorldMap/GeneratedAssetReview/batches.json`;
- `Documentation/WorldMap/GeneratedAssetReview/summary.json`.

The plan uses stable review IDs:

- `M####` for mesh reviews;
- `A###` for AsphaltMat material reviews.

The initial state is always `PENDING`.

## Step 2 — Build one safe Unreal gallery batch

Run inside Unreal Editor:

```text
py "C:/Users/malik/Documents/Unreal Projects/ZombieSeasons/Content/Python/build_asset_validation_gallery.py"
```

Each invocation creates only the next missing gallery map under:

`/Game/ZombieSeasons/Validation/AssetGallery/`

The script intentionally processes one batch at a time. This is a memory-safety rule
following the earlier City Sample out-of-memory incident. Do not increase the batch
count globally before validating editor memory and virtual-memory stability.

Existing gallery maps are never overwritten. Source Epic/Fab assets are never edited.

## Step 3 — Review inside Unreal

Each preview actor is named in the World Outliner using its review ID and source name,
for example:

`M0042__SM_Fence_3`

During review inspect at minimum:

1. visual suitability for the intended district and zombie-FPS tone;
2. real-world scale relative to the player;
3. pivot/origin behavior for procedural placement;
4. collision and whether zombies/player navigation will be blocked correctly;
5. visible material or texture failures;
6. Nanite/rendering warnings;
7. whether modular pieces align cleanly with neighboring pieces;
8. whether the asset causes unreasonable editor/runtime cost;
9. whether it is a useful production piece rather than a reference/helper variant.

For AsphaltMat, compare the ten `A###` planes and choose only the road-surface variants
that fit ZombieSeasons. The master material itself is not directly selected for the
production manifest; the approved material instance paths are.

## Step 4 — Record decisions

Do not rename or move third-party source assets.

Review decisions will be recorded against the stable `review_id`, not against an
informal screenshot name. Valid final states will be:

- `APPROVED` — allowed in production generator manifests;
- `RESERVE` — visually valid but not required in the first production pass;
- `REJECTED` — forbidden from automatic production placement.

A later tool will convert reviewed IDs into an explicit production manifest containing
exact `/Game/...` object paths.

## Safety gates before final world generation

Final world-generation scripts remain blocked until all of the following are true:

- selected environment meshes have explicit review states;
- road material instances have explicit approval;
- Blueprint gameplay integration blockers are resolved or intentionally adapted;
- NavMesh serialization warning is resolved/revalidated;
- required Virtual Textures project setting is enabled;
- Chaos Vehicles dependency is enabled where required;
- known Nanite material warnings are resolved or confirmed irrelevant to approved assets;
- world layout, district bounds, routes, POIs, objective chain, streaming/HLOD policy,
  navigation budgets, spawn budgets and performance budgets are frozen in documentation.
