# ZombieSeasonsRuntime — Agent Guide

This plugin owns reusable ZombieSeasons runtime gameplay systems. Do not place
environment-art logic here or move runtime gameplay into level Blueprints merely
for convenience.

Inspect and extend existing implementations before adding systems. Existing
public runtime concepts include:

```text
ZSFPSCompatibilityRuntimeSubsystem
ZSGameplayRuntimeSubsystem
ZSPlayerAimRuntimeSubsystem
ZSSchoolHUDModel
ZSSchoolOverlay
ZSSchoolProgress
ZSSchoolScenario
```

Use C++ for mission state, runtime rules, reusable combat systems, validation,
and shared subsystems. Use Blueprint for asset references, assembly,
configuration, and simple per-level presentation.

Keep public APIs intentional, avoid hidden global state and duplicate sources
of truth, and make mission transitions explicit and testable. Protect invalid
state transitions and do not make gameplay depend on actor labels when a
stronger type or reference exists.

The target is Unreal Engine 5.5.4. Verify version-sensitive APIs before use.
Preserve and run focused runtime tests when changing progression or state rules.
Avoid broad refactors and unnecessary dependencies.
