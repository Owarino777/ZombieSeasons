# 01 — Master Level Design

## Vision

ZombieSeasons is a large, interconnected first-person zombie survival map built around four seasonal districts surrounding a fortified central safehouse. The intended first complete playthrough is 60–90 minutes, while optional exploration, hidden rooms, side objectives, and higher difficulty can extend the session.

The map must not behave like four disconnected demo arenas. It must feel like one city with continuous roads, sightlines, shortcuts, service tunnels, rooftops, and environmental transitions.

## World dimensions

Initial production envelope:

| Measurement | Target |
|---|---:|
| World playable footprint | 1,800 m × 1,800 m |
| Effective playable surface | approximately 2.5–3.2 km² |
| Direct edge-to-edge traversal | 8–12 minutes |
| Hub to district objective | 2–4 minutes |
| Main route width | 8–14 m |
| Secondary street width | 5–8 m |
| Interior corridor minimum | 1.8 m |
| Standard doorway clearance | 1.2–1.6 m |
| Primary combat arena | 45–90 m across |
| Horde arena capacity | 30–60 active zombies, subject to profiling |

All Unreal distances use centimeters.

## Coordinate plan

The central safehouse is located around world origin.

| Zone | Approximate center |
|---|---|
| Hub | `(0, 0, 0)` |
| Spring | `(-45000, 45000, variable Z)` |
| Summer | `(45000, 45000, variable Z)` |
| Autumn | `(-45000, -45000, variable Z)` |
| Winter | `(45000, -45000, variable Z)` |
| Extraction dam | `(85000, -30000, variable Z)` |

These coordinates are blockout anchors, not immutable art positions.

## Required world topology

- Central safehouse connected to every district.
- One primary route per district.
- At least two secondary return paths per district.
- At least one unlockable shortcut per district.
- Rooftop or elevated traversal in Summer, Autumn, and Winter.
- Sewer network connecting at least three districts.
- No critical objective in a dead end without a defensive fallback.
- Every major horde arena must have at least two player escape routes.
- Zombie spawn points must remain outside immediate player visibility.

## Progression

Recommended first-playthrough sequence:

1. Start and tutorial inside the Hub.
2. Spring: acquire basic resources and restore a communication relay.
3. Summer: obtain fuel and a vehicle battery from the beachfront district.
4. Autumn: recover police armory access and municipal records.
5. Winter: restart the power station and unlock the extraction route.
6. Return through a compressed high-pressure route.
7. Reach the river dam and survive the final extraction event.

Districts remain physically explorable before their main objective, but gates, hazards, power states, or key items prevent sequence-breaking of critical progression.

## Core gameplay loop

```text
Explore -> Read the environment -> Loot -> Open a route -> Trigger pressure -> Survive -> Secure reward -> Unlock shortcut -> Return or progress
```

## Pacing model

| Segment | Target duration |
|---|---:|
| Hub onboarding | 5–8 min |
| Spring | 12–18 min |
| Summer | 12–18 min |
| Autumn | 12–18 min |
| Winter | 15–20 min |
| Extraction finale | 8–12 min |

Optional interiors and secrets can add 15–30 minutes.

## Major POIs

- Hub Safehouse.
- School.
- Overgrown park and greenhouses.
- Motel.
- Gas station.
- Boardwalk and beach parking.
- Church square.
- Market.
- Apartments.
- Town hall.
- Hospital or clinic.
- Police station.
- Warehouse.
- Loading yard.
- Power station.
- Sewer control room.
- River dam extraction zone.

## Encounter language

- Quiet exploration spaces use long sightlines, ambient storytelling, and sparse isolated threats.
- Chokepoints use barricades, stalled vehicles, collapsed floors, and narrow service routes.
- Horde arenas provide circular movement, vertical options, readable landmarks, and controlled spawn occlusion.
- Interior fights use sound pressure and short sightlines rather than raw zombie counts.
- Final extraction combines defense, movement, and timed route opening instead of requiring the player to stand in one place for the entire event.

## Greybox acceptance criteria

The complete greybox is accepted only when:

- all districts are traversable;
- every critical route is readable without debug arrows;
- the full objective path is completable;
- navigation covers all required zombie spaces;
- no mandatory jump requires precision platforming;
- traversal times match the pacing model;
- all horde arenas support circling and retreat;
- a complete playtest lasts at least 60 minutes without artificial waiting.
