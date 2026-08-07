# 05 — Performance and Test Plan

## Initial target

| Metric | Target |
|---|---:|
| Resolution | 1920 × 1080 |
| Frame rate | 60 FPS gameplay target |
| Frame budget | 16.67 ms |
| Active zombies | 30–60 initially |
| Absolute active-zombie ceiling | determined by profiling; initial test cap 80 |
| Environment textures | 2K by default |
| Hero textures | 4K only when justified |
| Direct traversal | 8–12 min edge-to-edge |
| Full main path | 60–90 min |

The current project enables Lumen, Virtual Shadow Maps, DX12/SM6, and ray tracing. Hardware ray tracing must be treated as optional until profiling proves it can remain enabled on the minimum target hardware.

## Performance gates

### Gate 1 — Empty-world baseline

- Record editor and packaged-build frame time.
- Record GPU, game thread, render thread, and memory baselines.

### Gate 2 — Complete greybox

- All districts present.
- Navigation enabled.
- Representative zombie count active.
- No final art.

### Gate 3 — Spring vertical slice

- Final-quality environment assets.
- Lighting, foliage, VFX, audio, gameplay, and one horde event.
- Establish real cost per district.

### Gate 4 — Complete art pass

- World Partition and HLOD active.
- Texture and mesh budgets enforced.
- Worst-case horde profiled in every major arena.

### Gate 5 — Packaged build

- Full 60–90 minute playthrough.
- No editor-only dependency.
- No missing assets, redirectors, or runtime load errors.

## Automated validation

The map validator must report:

- missing asset references;
- missing required gameplay actors;
- actors outside world bounds;
- generated actors without generation tags;
- spawn points outside navigation;
- spawn points visible from protected player test locations;
- horde arenas with fewer than two exits;
- objective paths with unreachable stages;
- duplicate actor identifiers;
- invalid district tags;
- external actors that fail to save.

## Gameplay tests

- Player can finish the main route without developer commands.
- Every district can be entered and exited through at least two routes after its shortcut is unlocked.
- Zombies can reach the player in all mandatory combat spaces.
- Zombies cannot spawn inside the Hub.
- No critical pickup can fall permanently outside the playable area.
- No objective can become impossible after saving and loading.
- Horde triggers cannot fire twice unless explicitly configured as repeatable.
- Extraction completes correctly after every valid district order allowed by the design.

## Art and readability tests

- Each district is identifiable from the Hub by silhouette and color temperature.
- Critical doors and interactables remain readable during combat.
- Navigation signage does not rely on color alone.
- Foliage does not hide required pickups or zombie attack animations.
- Snow, fog, smoke, and post-processing do not destroy target visibility.

## Version-control safety

- Generated map work must remain outside `master` until reviewed.
- Never overwrite the tutorial map.
- Commit documentation, audit outputs, generators, greybox, and final art separately.
- Do not commit `Saved`, `Intermediate`, `DerivedDataCache`, or local Fab credentials.
