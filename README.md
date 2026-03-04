# ChimeraX-XR3D

3D cursor, selection, and hover labels for OpenXR autostereo displays in UCSF ChimeraX.

## Features

- **3D cursor** at correct stereo depth (5 styles: sphere, crosshair, diamond, arrow, pointer — press C to cycle)
- **3D selection rectangle** for ctrl+drag region-based selection visible in stereo
- **3D hover labels** for atoms, residues, and bonds at proper scene depth

Works on all OpenXR autostereo displays: Sony Spatial Reality, Acer SpatialLabs, Samsung Odyssey 3D (via vrto3d).

## Requirements

- UCSF ChimeraX daily build **2026-02-27 or newer** (includes vrto3d base support from [PR #223](https://github.com/RBVI/ChimeraX/pull/223))
- A supported OpenXR autostereo display:
  - Sony Spatial Reality (15.6" or 27")
  - Acer SpatialLabs
  - Samsung Odyssey 3D (G90XF 27" 4K or G90XH 32" 6K) via [vrto3d](https://github.com/oneup03/VRto3D) + SteamVR

## Install

From ChimeraX command line:

```
devel install /path/to/ChimeraX-XR3D
```

## Usage

1. Start ChimeraX, load a molecule (`open 1a0s`)
2. `xr on` — display shows stereo with 3D cursor
3. Move mouse over molecule — cursor appears at atom depth in 3D
4. Press **C** to cycle cursor styles
5. **Ctrl+drag** for 3D selection rectangle
6. Hover on atoms/residues for 3D labels
7. `xr off` — clean up, OS cursor returns

## Architecture

ChimeraX Toolshed plugin that monkey-patches `_enable_xr_mouse_modes` in
`xr_screens` to use an enhanced backing window with 3D interaction features
on all XR displays.

```
src/
  __init__.py         # Bundle API — patches _enable_xr_mouse_modes on load
  cursor3d.py         # Cursor3D, SelectionRect3D, geometry generators
  backing_window.py   # XR3DBackingWindow (mouse, hover, coordination)
```

When the upstream registration hook API lands (discussed in [PR #224](https://github.com/RBVI/ChimeraX/pull/224)),
the monkey-patching will be replaced with a clean registration call.

## Technical Details

- **Vertex baking**: Cursor rotation is baked into vertex positions via `set_geometry()` each frame. Using `model.position = Place(axes=R)` does NOT work in ChimeraX's XR rendering pipeline — cursors rotate with the molecule instead of staying screen-fixed.
- **View rotation transpose**: `camera.view().axes()` gives scene-to-camera. We need camera-to-scene = `.axes().T` (transpose).
- **Direct pick** (vrto3d only): Per-eye render is portrait (1920x2160) while the screen is landscape. Standard coordinate mapping through the graphics pane loses accuracy. `_backing_to_render_coordinates` maps backing window coordinates to the XR render texture via inverted texture coordinates, falling back to standard mapping on other displays.

## Known Issues

- **Samsung Hub**: 3D overlay (Ctrl+Shift+2) conflicts with vrto3d SBS. Keep it OFF.
- **Auto-convert**: Samsung Hub auto-convert must be OFF — causes window focus issues.
- **Molecule position on xr start**: Molecule may appear below the view on vrto3d. Zoom out and adjust manually.

## References

- [ChimeraX Bundle Development Guide](https://www.cgl.ucsf.edu/chimerax/docs/devel/writing_bundles.html)
- [PR #223 — vrto3d base support (merged)](https://github.com/RBVI/ChimeraX/pull/223)
- [PR #224 — 3D cursor/selection discussion](https://github.com/RBVI/ChimeraX/pull/224)

## Author

[Andre-C-M](https://github.com/Andre-C-M)
