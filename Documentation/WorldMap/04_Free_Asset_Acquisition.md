# 04 — Free Asset Acquisition

## Rule

Only free assets may be used. Do not acquire a paid pack, subscription-only pack, or plugin with an unclear runtime license.

Prefer content packs over runtime plugins. A content pack adds meshes, materials, textures, sounds, or VFX without introducing code dependencies.

## Access Fab from Unreal Engine 5.5

1. Open `ZombieSeasons.uproject` in Unreal Engine 5.5.
2. Open `Window`.
3. In `Get Content`, select `Fab`.
4. Alternative: open the Content Drawer and press the `Fab` button beside `Add`.
5. If Fab is missing, open `Edit > Plugins`, search `Fab`, enable it, and restart Unreal Editor.
6. Sign in with the Epic Games account used by the Epic Games Launcher.

## Search filters

For every search:

- Set price to `Free`.
- Select compatibility with Unreal Engine.
- Prefer assets that explicitly support UE 5.5 or can be added to a UE 5.5 project.
- Prefer `Megascans` and content distributed by Epic or established publishers.
- Verify the license shown on the product page before adding it to the library.
- Avoid packs requiring an additional third-party plugin.

## Acquisition order

Do not download random packs. Acquire by production need.

### Shared city kit

Search terms:

```text
free modular urban environment
free abandoned city
free road asphalt street props
free construction barriers
free abandoned vehicles
```

Required content:

- modular walls, doors, windows, stairs, roofs;
- roads, pavements, curbs, markings;
- fences, barriers, bins, lamps, signs;
- damaged and abandoned vehicles;
- reusable debris.

### Spring

```text
free suburban house environment
free school environment
Megascans vegetation ivy moss
free greenhouse props
```

### Summer

```text
free motel environment
free gas station environment
free beach props
free boardwalk environment
free amusement park props
```

### Autumn

```text
free european town environment
free market props
free church environment
free apartment modular environment
free police station props
```

### Winter and industrial

```text
free industrial environment
free warehouse environment
free factory props
free pipes machinery
free snow materials
```

### Atmosphere

```text
free Niagara fog
free Niagara snow
free ambient city sounds
free horror ambience
free fire smoke VFX
```

## Selection checklist

Before adding an asset to the project, record:

- Fab listing name;
- publisher;
- listing URL in the local acquisition log;
- license displayed at acquisition time;
- supported Unreal versions;
- download size;
- whether Nanite meshes are included;
- texture resolutions;
- material count;
- whether collision is supplied;
- whether the pack contains Blueprints or code plugins.

## Import destination

Fab packs may create their own top-level folders. Do not move imported files immediately because this can break internal references. First add their exact paths to `AssetRegistry.csv`. Project-owned material instances and prefabs belong under `/Game/ZombieSeasons/`.

## Packs to reject

Reject a pack when:

- it requires payment;
- the license is unclear;
- it requires a proprietary runtime plugin;
- it has no UE 5.5-compatible delivery path;
- it contains only demonstration renders instead of usable assets;
- its style cannot be normalized with the selected environment;
- it creates a major performance problem with no acceptable optimization path.

## Current acquisition target

The first target is not all four final districts. Acquire enough coherent content to complete:

1. shared roads and debris;
2. the Hub exterior;
3. Spring suburb and school;
4. one complete horde arena.

After the Spring vertical slice is validated, freeze its art direction before downloading the remaining district packs.
