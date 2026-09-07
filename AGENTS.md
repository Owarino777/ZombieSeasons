# ZombieSeasons — Agent Guide

## Purpose

Navigation and execution contract for AI coding agents working on ZombieSeasons.
Read only the documentation relevant to the current task and preserve local
modifications.

## Project

- Unreal Engine 5.5.4 (`5.5` association)
- Primary platform: Windows
- Runtime plugin: `Plugins/ZombieSeasonsRuntime`
- Current vertical slice: SchoolA1 / `L_ZS_School_Expedition`

Before writing, inspect the worktree with `git status --short --branch`.
Do not commit or push unless explicitly requested.

## Sources of truth

1. Existing implementation
2. Applicable `AGENTS.md`
3. Project documentation
4. Unreal Engine 5.5 documentation

For SchoolA1 work, start with `Documentation/SchoolA1/AGENTS.md`.

## Unreal asset safety

Never edit `.uasset` or `.umap` files as text or raw binary data. Modify Unreal
assets only through Unreal Editor, Unreal Python, Editor Scripting, or supported
Editor Utility APIs. Never replace binary assets with generated placeholders.

## Architecture

Prefer C++ for reusable runtime/gameplay systems and Blueprint for assembly,
configuration, asset references, and simple presentation. Inspect and extend
existing systems before creating parallel `V2`, `New`, or `Better` systems.

Gameplay systems live primarily under `Plugins/ZombieSeasonsRuntime/`; read its
agent guide before changing runtime behavior.

## Gameplay protection

Environment-art changes must preserve mission flow, spawn points, objectives,
navigation, and interactions. Treat labels beginning with `Scenario`,
`Commande`, `Attente`, `Trigger`, `PlayerStart`, `Objective`, `Spawn`, `Nav`,
`Interaction`, or `Compteur` as potentially protected and inspect their class
and references before changing them.

## Level art

Use intentional clusters for storytelling, navigation, composition, scale, or
physical plausibility. Keep playable routes clear. Validate collision and
navigation after meaningful dressing changes.

## Validation

Gameplay changes normally require a build, relevant tests, and PIE validation.
Level-art changes require a player-height review plus collision/navigation checks
when affected. Report changed files, decisions, validation, and remaining
problems concisely.
