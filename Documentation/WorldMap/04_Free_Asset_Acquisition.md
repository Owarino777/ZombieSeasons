# 04 — Free Asset Acquisition

## Rule

Only assets that are displayed as **Free** on Fab at acquisition time may be used. Do not acquire a paid pack, subscription-only pack, reference-only pack unsuitable for local UE use, or a plugin with an unclear runtime dependency.

Prefer content packs over runtime plugins. A content pack adds meshes, materials, textures, sounds or VFX without creating a new code dependency.

The listing price and license must be rechecked immediately before acquisition because Fab listings can change.

## Current project gap after audit

The Unreal audit found 779 assets, including 81 under the `/Fab` mount. Those `/Fab` assets are primarily Fab/Megascans support materials, material functions, textures and the Global Foliage Actor. They do **not** provide the large modular environment kit required for the final map.

The project already contains one imported Megascans coconut asset under `/Game/TopDownShooter/Ressources/Fab/Megascans/...`, but the existing environment inventory remains insufficient for the intended city-scale art pass.

## Access Fab from Unreal Engine 5.5

1. Open `ZombieSeasons.uproject` in Unreal Engine 5.5.4.
2. Open `Window`.
3. In `Get Content`, select `Fab`.
4. Alternative: open the Content Drawer and use the `Fab` button beside `Add`.
5. Sign in with the Epic Games account used by Epic Games Launcher.
6. Search the exact pack names below rather than downloading random results.

## Verified free acquisition set — checked 2026-08-07

### Priority A — City Sample Buildings

Publisher: Epic Games
Fab listing ID: `008fe959-5511-428e-93bd-f99b1179f6d5`
Price status checked: **Free**
Format: Unreal Engine
Use: primary modular city architecture.

The listing contains more than 2,000 individual modular building pieces with modern and classic styles. Modules are split into ground levels, corners, walls, entrances and additional architectural pieces. This is the main shared architecture kit for the Hub, Autumn city core, urban edges of Spring and portions of Summer.

Acquisition status: `REQUIRED_NOT_IMPORTED`

### Priority A — City Sample Vehicles

Publisher: Epic Games
Fab listing ID: `2909157b-ddfa-4cef-a925-69dc2467021f`
Price status checked: **Free**
Format: Unreal Engine
Use: abandoned street dressing, roadblocks and landmark vehicles.

The listing includes 13 vehicle types including sedans, SUVs, pickups, trucks, taxi, bus and delivery van. For ZombieSeasons they should initially be used as static environment dressing; do not introduce Chaos vehicle gameplay into the first map production pass.

Acquisition status: `REQUIRED_NOT_IMPORTED`

### Priority B — Unfinished Building

Publisher: listing currently available on Fab
Fab listing ID: `25f2e7e5-5cca-48a5-99a3-35c38b8240ac`
Price status checked: **Free**
Formats include Unreal Engine / FBX delivery
Compatibility stated by listing: UE 5.4–5.6
Use: damaged structures, exposed concrete, rubble and post-apocalyptic building shells.

The listing advertises 78 assets and is useful for breaking the clean City Sample silhouette. Use primarily in Autumn, Winter and transition zones.

Acquisition status: `RECOMMENDED_NOT_IMPORTED`

### Priority B — Soul: City

Publisher: Epic Games
Fab listing ID: `dd77fee6-0ad2-41ce-b32c-09300c24c9f3`
Price status checked: **Free**
Format: Unreal Engine
Use: lightweight urban props, materials and background dressing.

Soul: City is older mobile-oriented content, so do not use it as the visual hero kit. It is useful for secondary props and distant/background dressing where a lower asset cost is desirable.

Acquisition status: `OPTIONAL_NOT_IMPORTED`

### Priority C — Electric Dreams Env

Publisher: Epic Games
Fab listing ID: `d79688f5-29be-4fb2-a650-2d4a813f5306`
Price status checked: **Free**
Format: Unreal Engine
Use: high-quality natural dressing reference and vegetation/PCG study material.

The sample is significantly heavier and includes PCG-focused content. Do not migrate the complete project or enable its experimental systems blindly. Only evaluate specific environment assets after the base greybox and core city kit are stable.

Acquisition status: `OPTIONAL_LATE_PASS`

## Do not download the complete City Sample yet

The full `City Sample` project is also free, but it includes World Partition, Mass AI, crowds, vehicles, Niagara, MetaHumans and other systems that are unnecessary for the first ZombieSeasons map pass.

Prefer the extracted `City Sample Buildings` and `City Sample Vehicles` packs. This reduces project size and avoids importing systems unrelated to the existing ZombieSeasons gameplay architecture.

## AI / license safeguard

Some Fab listings expose an `Allows usage with AI` / `NoAI` state. Treat this conservatively:

- do not upload purchased/downloaded source meshes, textures or source files into generative-AI services;
- do not use Fab assets as training data or generative-AI input datasets;
- automated Unreal Editor scripts may reference already imported assets by their local Unreal object paths without sending the asset source data to an external model;
- retain the acquisition record and Fab license information in the project documentation;
- never redistribute standalone Fab source assets from the public Git repository if the applicable license forbids standalone redistribution.

## Import policy

Do not move imported Fab content immediately after adding it to the project. Packs may depend on their original package paths.

After every acquisition batch:

1. open the project and allow shader/asset compilation to finish;
2. run `Documentation/WorldMap/Tools/export_project_audit.py` again;
3. replace `Documentation/WorldMap/GeneratedAudit/*` with the new results;
4. commit the new audit;
5. update `AssetRegistry.csv` only with exact object paths returned by Unreal;
6. only then allow map-generation scripts to reference the new assets.

## First acquisition batch

Download only these first:

1. `City Sample Buildings`;
2. `City Sample Vehicles`;
3. `Unfinished Building` if Fab still displays it as Free when you open the listing.

Do **not** acquire additional packs yet. This first batch should provide enough architecture, vehicles, ruins and shared city dressing to build a serious vertical slice before we decide whether dedicated free Spring/Summer/Winter packs are still necessary.

## Pack rejection rules

Reject an asset when:

- Fab no longer displays it as Free;
- its license cannot be verified;
- it requires a proprietary runtime plugin;
- the Unreal delivery cannot be used with UE 5.5.4;
- it contains only renders and no usable asset source/delivery;
- it introduces a major performance problem without an acceptable optimization path;
- it forces replacement of the existing ZombieSeasons gameplay systems.
