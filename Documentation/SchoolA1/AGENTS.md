# SchoolA1 — Agent Guide

This guide applies to the SchoolA1 environment, mission, level art, lighting,
and School expedition. The main level is `L_ZS_School_Expedition`.

## Scope and strategy

Keep work small and reviewable: the target is 8–12 excellent minutes rather
than several hours of medium-quality content. Do not expand scope merely
because other areas are documented.

Read only the source needed for the task:

- `ZOMBIESEASONS_BIBLE_V1.md` for world rules and tone
- `EXPEDITION_01_SECTEUR_B.md` for mission progression and storytelling
- `PREMIER_LOT_UNREAL.md` for the current Unreal implementation
- `ESSAI_ECOLE_A1.md` for prototype history
- `ECOLE_A2_LIVRAISON.md` only for SchoolA2 work

## World and visual direction

SchoolA1 is a modest French municipal school abandoned weeks ago during late
autumn rain. Prefer mud, wet surfaces, leaves, barriers, cases, paperwork,
technical equipment, and interrupted evacuation. Avoid decades of overgrowth,
universal heavy rust, major collapse, excessive gore, jungle dressing, and
random prop scatter.

The courtyard reads as a school plus a temporary evacuation point. Keep roughly
60–70% of the central playable area clear. The entrance is the primary focal
point; the radio point is secondary. Storage stays near walls.

Use cold, diffuse exterior light and restrained warmer interior accents explained
by visible practical lights. Wetness belongs near drains, wall bases, downpipes,
low points, and protected corners; never make the whole floor a mirror.

## Gameplay protection

Preserve the established route: courtyard → radio → entrance → reception →
radio response → corridors → gymnasium → service passage → delivery yard.
Do not move mission actors, spawns, objectives, or navigation casually. Inspect
actor class/type rather than relying only on labels.

Reuse existing folders:

```text
00_Lighting
10_StartArea_Architecture
20_StartArea_Props
30_StartArea_Story
40_StartArea_Decals
90_StartArea_Review
```

Review at player height and in PIE. Check visual hierarchy, clear space,
entrance access, collision, navigation when affected, objective flow, material
repetition, lighting regressions, and performance when relevant.

For generated spatial facts and artistic constraints, read
`Documentation/SchoolA1/Astra/README.md`.
