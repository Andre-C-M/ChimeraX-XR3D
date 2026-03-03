# ChimeraX-SamsungXR

3D cursor, selection, and hover labels for Samsung Odyssey 3D displays in UCSF ChimeraX.

## Features

- **3D cursor** at correct stereo depth (5 styles: sphere, crosshair, diamond, arrow, pointer — press C to cycle)
- **3D selection rectangle** for ctrl+drag region-based selection visible in stereo
- **3D hover labels** for atoms, residues, and bonds at proper scene depth
- **Direct pick** coordinate mapping optimized for vrto3d's portrait-render / landscape-screen geometry

## Requirements

- ChimeraX daily build **2026-02-27 or newer** (includes vrto3d base support from [PR #223](https://github.com/RBVI/ChimeraX/pull/223))
- Samsung Odyssey 3D display (G90XF 27" 4K or G90XH 32" 6K)
- [vrto3d](https://github.com/oneup03/VRto3D) SteamVR driver
- SteamVR

## Install

From ChimeraX command line:

```
devel install /path/to/ChimeraX-SamsungXR
```

For development (editable — changes take effect after restart):

```
devel install /path/to/ChimeraX-SamsungXR editable true
```

## Usage

1. Start ChimeraX, load a molecule (`open 1a0s`)
2. `xr on` — Samsung display shows stereo with 3D cursor
3. Move mouse over molecule — cursor appears at atom depth in 3D
4. Press **C** to cycle cursor styles
5. **Ctrl+drag** for 3D selection rectangle
6. Hover on atoms/residues for 3D labels
7. `xr off` — clean up, OS cursor returns

## Architecture

This is a ChimeraX Toolshed plugin that monkey-patches the vrto3d screen setup
to use an enhanced backing window with 3D interaction features.

```
src/
  __init__.py         # Bundle API — patches _vrto3d_screen_setup on load
  cursor3d.py         # Cursor3D, SelectionRect3D, geometry generators
  backing_window.py   # SamsungXRBackingWindow (mouse, hover, coordination)
```

When the upstream registration hook API lands (discussed in PR #224), the
monkey-patching will be replaced with a clean `register_xr_screen_setup()` call.

## Key Technical Details

- **Vertex baking**: Cursor rotation is baked into vertex positions via `set_geometry()` each frame. Using `model.position = Place(axes=R)` does NOT work in ChimeraX's XR rendering pipeline — cursors rotate with the molecule instead of staying screen-fixed.
- **View rotation transpose**: `camera.view().axes()` gives scene-to-camera. We need camera-to-scene = `.axes().T` (transpose).
- **Direct pick**: vrto3d per-eye render is portrait (1920x2160) while the screen is landscape. Standard coordinate mapping through the graphics pane loses accuracy. Direct pick maps backing window coordinates to the XR render texture via inverted texture coordinates.

## Related Resources

- `../Development/` — Original upstream patch approach (deploy_fix.py, pre-plugin)
- `../Documentation/chimerax_manual_complete.md` — Full ChimeraX manual (scraped)
- `../Example_Sessions/` — Example .cxs session files
- `../_backup/` — Old autostart scripts and ChimeraX config notes
- [ChimeraX Bundle Development Guide](https://www.cgl.ucsf.edu/chimerax/docs/devel/writing_bundles.html)
- [PR #223 (vrto3d base support, merged)](https://github.com/RBVI/ChimeraX/pull/223)
- [PR #224 (3D cursor/selection, → plugin)](https://github.com/RBVI/ChimeraX/pull/224)

## Known Issues

- **Samsung Hub**: 3D overlay (Ctrl+Shift+2) conflicts with vrto3d SBS. Keep it OFF.
- **Auto-convert**: Samsung Hub auto-convert must be OFF — causes window focus issues.
- **Molecule position on xr start**: Molecule may appear below the view. Zoom out and adjust manually. (Upstream fit_view_to_room doesn't apply to vrto3d.)

## Author

André Michaelis — Max Planck Institute of Biochemistry
