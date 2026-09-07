# SchoolA1 — Astra Environment Context

This directory separates facts generated from Unreal from human-maintained
artistic intent.

## Files

`COUR_SCENE.json` is generated from the currently loaded
`L_ZS_School_Expedition` level by
`Scripts/Unreal/export_schoola1_scene.py`. It contains actor transforms, bounds,
meshes, materials, folders, protected-actor hints, and cameras. Do not manually
maintain transforms in it; regenerate it when the level changes.

`COUR_ART_SPEC.yaml` contains composition, priorities, storytelling, protected
gameplay rules, visual direction, and review criteria. Do not put discovered
actor coordinates there.

## Workflow

1. Open `L_ZS_School_Expedition` in Unreal Editor.
2. Ensure the intended level state is loaded.
3. Run `Scripts/Unreal/export_schoola1_scene.py` in the Unreal Python editor.
4. Verify that `COUR_SCENE.json` was regenerated.
5. Give Astra the manifest, art spec, relevant reference, and a focused task.

The manifest answers what exists, where it is, how large it is, and what may be
gameplay-sensitive. The art spec answers what the area should communicate and
what must remain clear. Screenshots are artistic evidence, not a replacement
for the generated spatial manifest.
