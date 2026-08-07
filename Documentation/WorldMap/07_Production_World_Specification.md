# 07 — Production World Specification

## Status

This document freezes the production layout contract for the first complete ZombieSeasons world. It refines the high-level design in `01_Master_Level_Design.md` and `02_District_Specifications.md` into deterministic coordinates, dimensions, route rules, gameplay budgets, and generation boundaries.

The art placement may vary inside the bounds below, but generators must not change the topology, objective order, critical route widths, or district ownership without updating this document first.

## World envelope

All distances are Unreal centimeters.

| Item | Frozen value |
|---|---:|
| Playable world width | 180,000 cm |
| Playable world depth | 180,000 cm |
| World X bounds | -90,000 to +90,000 |
| World Y bounds | -90,000 to +90,000 |
| Hub center | `(0, 0, 0)` |
| Protected Hub inner radius | 6,000 cm |
| Hub circulation radius | 12,000 cm |
| Main radial road width | 1,200 cm |
| Secondary road width | 700 cm |
| Service road width | 500 cm |
| Standard alley width | 350–450 cm |
| Standard sidewalk | 200 cm per side |
| Minimum mandatory doorway | 140 cm |
| Minimum mandatory interior corridor | 200 cm |
| Minimum mandatory combat passage | 300 cm |

The world origin remains inside the Hub. The extraction dam is deliberately near the eastern edge so that the final sequence feels like an actual escape from the city.

## District ownership bounds

The central 30,000 × 30,000 cm square is reserved for the Hub, ring road, transition spaces, and shared infrastructure.

| District | X range | Y range | Primary terrain character |
|---|---:|---:|---|
| Spring | -85,000 to -15,000 | +15,000 to +85,000 | suburb / park / school |
| Summer | +15,000 to +85,000 | +15,000 to +85,000 | beachfront / motel / boardwalk |
| Autumn | -85,000 to -15,000 | -85,000 to -15,000 | dense civic center |
| Winter | +15,000 to +85,000 | -85,000 to -15,000 | industrial / power infrastructure |
| Hub / shared | -15,000 to +15,000 | -15,000 to +15,000 | safehouse / ring road / transitions |
| Extraction | +72,000 to +90,000 | -45,000 to -15,000 | dam / final escape route |

District transitions must visually blend over at least 4,000 cm. Seasonal identity may not change on a single hard line.

## Elevation bands

Large terrain cliffs are intentionally avoided because zombie navigation and FPS combat readability are higher priorities than terrain spectacle.

| Zone | Normal ground Z | Allowed production range |
|---|---:|---:|
| Hub | 0 | -100 to +300 |
| Spring | +200 | -100 to +800 |
| Summer | 0 | -200 to +500 |
| Autumn | +300 | 0 to +1,000 |
| Winter | +500 | +100 to +1,400 |
| Dam | +800 | -200 to +2,000 |
| Sewer floor | -700 | -1,200 to -500 |

Elevated traversal such as rooftops, fire escapes, catwalks, bridges, and galleries may exceed these values.

## Primary road graph

The road network is generated geometry using the approved AsphaltMat material, not a wildcard road-mesh system.

### Hub ring road

A rounded square / ring circulation route surrounds the protected Hub at approximately 9,000–12,000 cm from world origin.

The ring road connects four radial arterials:

- `R_SPRING`: Hub northwest toward Spring.
- `R_SUMMER`: Hub northeast toward Summer.
- `R_AUTUMN`: Hub southwest toward Autumn.
- `R_WINTER`: Hub southeast toward Winter.

Each radial arterial starts at 1,200 cm wide and may narrow to 900 cm where environmental pressure is intentional.

### Cross-city continuity

The world must also contain:

- one northern cross-route linking Spring and Summer without requiring Hub entry;
- one southern cross-route linking Autumn and Winter;
- one western service route between Spring and Autumn;
- one eastern service route between Summer and Winter;
- one emergency extraction road from Winter to the dam.

At least one cross-city route is blocked at the beginning and becomes usable only after a district objective.

## Frozen POI anchors

POI centers are placement anchors. Building footprints may move by at most ±2,500 cm unless a documented collision or asset-layout constraint requires more.

### Hub

| POI | Anchor |
|---|---|
| Safehouse core | `(0, 0, 0)` |
| North district gate | `(0, +10,500, 0)` |
| East district gate | `(+10,500, 0, 0)` |
| South district gate | `(0, -10,500, 0)` |
| West district gate | `(-10,500, 0, 0)` |
| Objective board / operations room | `(0, +2,000, 0)` |

Hub traversal from one exterior gate to the opposite gate must remain under 45 seconds during normal movement.

### Spring

| POI | Anchor |
|---|---|
| Residential block | `(-31,000, +67,000, +200)` |
| Public park | `(-34,000, +38,000, +100)` |
| School | `(-55,000, +58,000, +300)` |
| Gym horde arena | `(-60,000, +52,000, +300)` |
| Greenhouses | `(-71,000, +31,000, +100)` |
| Relay objective | `(-57,000, +60,000, +800)` |
| Sewer / drainage entrance | `(-62,000, +20,000, -100)` |

### Summer

| POI | Anchor |
|---|---|
| Gas station | `(+31,000, +64,000, 0)` |
| Motel | `(+53,000, +56,000, +100)` |
| Large parking arena | `(+63,000, +34,000, 0)` |
| Boardwalk | `(+48,000, +77,000, +100)` |
| Beach service buildings | `(+68,000, +69,000, 0)` |
| Amusement pier | `(+76,000, +82,000, +100)` |
| Storm-drain entrance | `(+24,000, +31,000, -100)` |

### Autumn

| POI | Anchor |
|---|---|
| Church square | `(-35,000, -35,000, +300)` |
| Market hall | `(-54,000, -43,000, +300)` |
| Apartment block | `(-69,000, -61,000, +500)` |
| Town hall | `(-41,000, -66,000, +400)` |
| Police station | `(-66,000, -29,000, +300)` |
| Clinic | `(-23,000, -48,000, +200)` |
| Police horde arena / garage | `(-62,000, -24,000, +300)` |

### Winter

| POI | Anchor |
|---|---|
| Warehouse | `(+32,000, -33,000, +500)` |
| Loading yard arena | `(+53,000, -43,000, +400)` |
| Maintenance workshops | `(+35,000, -66,000, +500)` |
| Power station | `(+65,000, -66,000, +700)` |
| Cooling channel | `(+78,000, -56,000, +300)` |
| Sewer control room | `(+25,000, -78,000, -500)` |
| Dam service-road gate | `(+76,000, -33,000, +600)` |

### Extraction dam

| POI | Anchor |
|---|---|
| Dam perimeter entry | `(+79,000, -31,000, +700)` |
| Control building | `(+84,000, -31,000, +900)` |
| Defense position A | `(+82,000, -25,000, +900)` |
| Defense position B | `(+87,000, -35,000, +1,000)` |
| Final crossing start | `(+84,000, -21,000, +1,100)` |
| Extraction endpoint | `(+88,000, -18,000, +1,200)` |

## Sewer topology

The sewer is a traversal and shortcut network, not a second full district.

Frozen junctions:

- `SWR_HUB`: `(0, -6,000, -700)`
- `SWR_SPRING`: `(-40,000, +18,000, -700)`
- `SWR_SUMMER`: `(+28,000, +20,000, -700)`
- `SWR_AUTUMN`: `(-28,000, -25,000, -700)`
- `SWR_WINTER`: `(+26,000, -40,000, -700)`
- `SWR_CONTROL`: `(+25,000, -78,000, -500)`

At least three district connections must be usable in the final map. Initially, only the Hub maintenance segment is accessible. District objective or shortcut progression unlocks the remaining connections.

Main sewer corridors are 500–700 cm wide. Combat chambers are 1,200–2,000 cm wide. No mandatory sewer path may be a single-entry dead end longer than 3,500 cm.

## Objective chain

The canonical first-playthrough order is frozen:

1. Hub onboarding and initial equipment.
2. Spring: restore the school communication relay.
3. Spring reward: district access key + Hub shortcut.
4. Summer: retrieve fuel.
5. Summer: retrieve compatible vehicle battery.
6. Summer: activate service-road gate.
7. Autumn: obtain municipal infrastructure records.
8. Autumn: unlock police armory access.
9. Autumn: complete police-station defense.
10. Winter: reach the power station.
11. Winter: restore power in staged interactions.
12. Winter: activate dam controls.
13. Open extraction service road.
14. Return / pressure route toward the dam.
15. Extraction: two changing defense positions.
16. Cross final dam route and reach extraction endpoint.

Critical objectives are sequential even if some districts can be physically entered earlier.

## Shortcut contract

Each district must expose at least three topology improvements by the time its primary objective is complete:

- one direct return shortcut to the Hub or ring road;
- one local shortcut reducing traversal inside the district;
- one sewer / rooftop / service-route alternate path.

A shortcut may be a gate, broken wall, fire escape, bridge, maintenance door, collapsed fence, powered shutter, or utility tunnel.

## Combat-arena requirements

| Arena | Target footprint | Required exits | Initial active-zombie target |
|---|---:|---:|---:|
| Spring gym | 50–65 m | 2 + 1 unlockable | 25–40 |
| Summer parking | 70–90 m | 3 | 30–50 |
| Summer boardwalk | 45–70 m long pressure route | 2 lateral + retreat | 25–45 |
| Autumn church square | 55–70 m | 3 | 30–50 |
| Autumn police station | mixed interior / garage | 2 | 30–45 |
| Winter loading yard | 80–90 m | 3 | 40–60 |
| Winter power station | multi-stage | 2 per stage | 35–60 |
| Dam finale | moving defense | 2 until final lock | 40–60 |

The 80-zombie value remains a profiling-only stress ceiling, not a default encounter target.

## Spawn-marker budgets

These are marker budgets, not simultaneously active zombies.

| Zone | Zombie spawn markers | Spawn groups | Horde triggers |
|---|---:|---:|---:|
| Hub exterior | 8 | 2 | 0 |
| Spring | 28–36 | 7–9 | 2–3 |
| Summer | 32–42 | 8–10 | 2–3 |
| Autumn | 36–46 | 9–11 | 3–4 |
| Winter | 40–52 | 10–12 | 3–4 |
| Sewers | 18–24 | 5–6 | 1–2 |
| Extraction | 24–32 | 6–8 | 2 |

No standard zombie spawn marker may be placed inside the protected Hub interior.

## Loot and interaction budgets

For the greybox phase, generators place gameplay markers rather than final loot meshes.

| District | General loot points | Weapon / high-value points | Required objective interactions |
|---|---:|---:|---:|
| Hub | 6–10 | 2 | 3–5 |
| Spring | 18–24 | 3–4 | 4–6 |
| Summer | 20–28 | 3–5 | 5–7 |
| Autumn | 24–30 | 4–5 | 5–8 |
| Winter | 24–32 | 4–6 | 6–9 |
| Sewers | 8–12 | 1–2 | 2–3 |
| Extraction | 4–8 | 1–2 | 4–6 |

## Navigation contract

- Hub protected interior: no standard zombie NavMesh.
- Every mandatory player combat route: zombie navigation unless explicitly documented as player-only traversal.
- Stairs and ramps: minimum 200 cm clear width for mandatory zombie routes.
- Zombie-only drops: explicit Nav Link Proxy, never accidental falling.
- Spawn markers: projection to valid NavMesh required during validation.
- Locked doors: navigation state must match gameplay gate state.
- Rooftop player shortcuts do not automatically require zombie navigation.

## World Partition production defaults

These are the initial production values and may be tuned only through the performance gates without changing level topology.

| Setting | Initial value |
|---|---:|
| Runtime grid cell size | 12,800 cm |
| Default loading range | 38,400 cm |
| One File Per Actor | enabled |
| Runtime spatial loading | enabled for environment actors |
| Critical gameplay controllers | always loaded |
| HLOD | enabled before full art pass |

Required Data Layers:

```text
DL_ZS_Greybox
DL_ZS_Gameplay
DL_ZS_FinalArt
DL_ZS_Hub
DL_ZS_Spring
DL_ZS_Summer
DL_ZS_Autumn
DL_ZS_Winter
DL_ZS_Sewers
DL_ZS_Extraction
```

## Asset-manifest contract

The production generator may use only assets whose final manifest row has:

```text
decision = APPROVED
generator_enabled = true
```

Current approved production set: 201 assets.

`RESERVE` assets are never selected automatically by the first production pass. A reserve asset may be promoted only by an explicit manifest update.

Asset selection must use exact `object_path` values. Wildcard searches and runtime folder scans are forbidden in production generation.

## District asset intent

The same City Sample building family should not be blindly repeated in every quadrant.

- Spring: lower-density residential / civic modules, limited heavy ruin dressing.
- Summer: commercial frontage, motel-like modules, parking and street props, vehicles.
- Autumn: densest facades, civic architecture, alleys, market / police / apartment composition.
- Winter: industrial-looking structural modules, unfinished-building assets, debris, vehicles, barriers.
- Hub: cleanest reusable architecture subset, strong defensive barriers, minimal ruin assets.

Seasonal identity is primarily created through district dressing, lighting, decals, foliage, atmospheric VFX, surface treatment, and composition; the generator must not rely on one mesh pack to provide the season itself.

## Generation ownership tags

Every generated actor must receive:

```text
ZS.Generated
ZS.GenerationVersion.001
ZS.Stage.<StageName>
ZS.District.<DistrictName>
```

Gameplay markers additionally receive a stable identifier tag such as:

```text
ZS.Id.Spring.Spawn.001
ZS.Id.Autumn.Objective.PoliceDefense
```

No production cleanup script may delete an actor lacking `ZS.Generated`.

## Acceptance before art pass

The world shell / greybox is not approved until all of the following are true:

- all four districts, Hub, sewers, and extraction route exist;
- POI anchors are recognizable in spatial layout;
- all primary and secondary routes are traversable;
- each district has the required shortcut topology;
- the canonical objective path is completable using project-owned gameplay adapters;
- mandatory zombie areas have valid navigation;
- horde arenas satisfy exit requirements;
- direct traversal remains in the 8–12 minute envelope;
- a complete objective playthrough reaches at least 60 minutes without artificial waiting;
- no generation or validation step writes to existing TopDownShooter or Black Tide maps.
