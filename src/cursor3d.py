# vim: set expandtab shiftwidth=4 softtabstop=4:

"""3D cursor for autostereo displays.

Renders a small shape in the scene at the depth of whatever is under
the mouse, so it appears at the correct stereo depth instead of being
flat on the screen.  Press C to cycle styles.

Orientation is baked into vertex positions each frame via set_geometry()
so it stays screen-fixed in XR rendering.  model.position handles
translation only — using Place(axes=R) does NOT work in the XR
rendering pipeline (cursors rotate with the molecule).
"""

import numpy as np

CURSOR_STYLES = ('sphere', 'crosshair', 'diamond', 'arrow', 'pointer')


# ---------------------------------------------------------------------------
# Geometry generators
# ---------------------------------------------------------------------------

def _crosshair_geometry(size):
    """Three orthogonal thin rectangular prisms forming a 3D crosshair."""
    arm = size
    t = size * 0.1
    verts = []
    norms = []
    tris = []
    for axis in range(3):
        ext = [t, t, t]
        ext[axis] = arm
        hx, hy, hz = ext
        o = len(verts)
        v = [[-hx,-hy,-hz], [hx,-hy,-hz], [hx,hy,-hz], [-hx,hy,-hz],
             [-hx,-hy, hz], [hx,-hy, hz], [hx,hy, hz], [-hx,hy, hz]]
        verts.extend(v)
        for p in v:
            n = np.array(p, dtype=np.float32)
            mag = np.linalg.norm(n)
            norms.append(n / mag if mag > 0 else np.array([0,1,0], dtype=np.float32))
        tris.extend([
            [o+0,o+2,o+1], [o+0,o+3,o+2],
            [o+4,o+5,o+6], [o+4,o+6,o+7],
            [o+0,o+1,o+5], [o+0,o+5,o+4],
            [o+2,o+3,o+7], [o+2,o+7,o+6],
            [o+0,o+4,o+7], [o+0,o+7,o+3],
            [o+1,o+2,o+6], [o+1,o+6,o+5],
        ])
    return np.array(verts, np.float32), np.array(norms, np.float32), np.array(tris, np.int32)


def _diamond_geometry(size):
    """Octahedron (diamond) shape."""
    s = size
    verts = np.array([
        [ s, 0, 0], [-s, 0, 0],
        [ 0, s, 0], [ 0,-s, 0],
        [ 0, 0, s], [ 0, 0,-s],
    ], dtype=np.float32)
    norms = np.array([
        [1,0,0], [-1,0,0], [0,1,0], [0,-1,0], [0,0,1], [0,0,-1],
    ], dtype=np.float32)
    tris = np.array([
        [0,2,4], [2,1,4], [1,3,4], [3,0,4],
        [2,0,5], [1,2,5], [3,1,5], [0,3,5],
    ], dtype=np.int32)
    return verts, norms, tris


def _arrow_geometry(size):
    """3D cone pointer -- tip at origin, base extends in +Y.
    Tip sits on the surface; base points toward the camera."""
    length = size * 5
    base_r = size * 0.6
    n_seg = 16
    verts = [[0, 0, 0]]
    norms = [[0, -1, 0]]
    angles = np.linspace(0, 2 * np.pi, n_seg, endpoint=False)
    slope = base_r / length
    for a in angles:
        ca, sa = np.cos(a), np.sin(a)
        verts.append([base_r * ca, length, base_r * sa])
        nx, nz = ca, sa
        ny = -slope
        mag = np.sqrt(nx*nx + ny*ny + nz*nz)
        norms.append([nx/mag, ny/mag, nz/mag])
    bc = len(verts)
    verts.append([0, length, 0])
    norms.append([0, 1, 0])
    tris = []
    for i in range(n_seg):
        tris.append([0, 1 + (i + 1) % n_seg, 1 + i])
    for i in range(n_seg):
        tris.append([bc, 1 + i, 1 + (i + 1) % n_seg])
    return np.array(verts, np.float32), np.array(norms, np.float32), np.array(tris, np.int32)


def _pointer_geometry(size):
    """Classic mouse pointer cursor, extruded with side walls for
    real 3D depth.  Tip at origin so it sits on the surface;
    body extends in -Y (toward camera after rotation)."""
    s = size
    t = s * 0.15
    tip_y = s * 1.2
    pts = [
        [0, 0],
        [-s*0.40, -s*0.05 - tip_y],
        [-s*0.12,  s*0.15 - tip_y],
        [-s*0.12, -s*0.55 - tip_y],
        [ s*0.12, -s*0.55 - tip_y],
        [ s*0.12,  s*0.15 - tip_y],
        [ s*0.40, -s*0.05 - tip_y],
    ]
    faces_2d = [
        [0, 1, 2], [0, 2, 5], [0, 5, 6],
        [2, 3, 4], [2, 4, 5],
    ]
    verts = []
    norms = []
    tris = []
    n = len(pts)
    for p in pts:
        verts.append([p[0], p[1], t])
        norms.append([0, 0, 1])
    for f in faces_2d:
        tris.append(f)
    for p in pts:
        verts.append([p[0], p[1], -t])
        norms.append([0, 0, -1])
    for f in faces_2d:
        tris.append([n + f[0], n + f[2], n + f[1]])
    edges = [(0,1), (1,2), (2,3), (3,4), (4,5), (5,6), (6,0)]
    base = 2 * n
    for i, (a, b) in enumerate(edges):
        pa, pb = pts[a], pts[b]
        dx, dy = pb[0] - pa[0], pb[1] - pa[1]
        nx, ny = dy, -dx
        mag = np.sqrt(nx*nx + ny*ny)
        if mag > 0:
            nx, ny = nx/mag, ny/mag
        vi = base + i * 4
        verts.extend([
            [pa[0], pa[1],  t],
            [pb[0], pb[1],  t],
            [pb[0], pb[1], -t],
            [pa[0], pa[1], -t],
        ])
        norms.extend([[nx, ny, 0]] * 4)
        tris.append([vi, vi+1, vi+2])
        tris.append([vi, vi+2, vi+3])
    return np.array(verts, np.float32), np.array(norms, np.float32), np.array(tris, np.int32)


# ---------------------------------------------------------------------------
# View rotation helpers (screen-fixed orientation)
# ---------------------------------------------------------------------------

def view_rotation(camera):
    """Return 3x3 rotation whose columns are camera right / up / -forward
    expressed in scene coordinates.  This is the TRANSPOSE of the view
    matrix rotation (view maps scene->camera; we need camera->scene).
    Screen-fixed overlays use this so they do not rotate with the molecule."""
    try:
        vp = camera.view(camera.position, 0)
        return vp.zero_translation().remove_scale().axes().T.copy()
    except Exception:
        return camera.position.zero_translation().remove_scale().axes().T.copy()


def arrow_view_rotation(R):
    """Modify view rotation so arrow cone tip points diagonally into
    screen (between camera forward and down)."""
    from numpy.linalg import norm
    cam_fwd = -R[:, 2]
    cam_down = -R[:, 1]
    tip_dir = cam_fwd + cam_down
    td_len = norm(tip_dir)
    tip_dir = tip_dir / td_len if td_len > 0 else cam_fwd
    y_ax = -tip_dir
    x_ax = R[:, 0].copy()
    z_ax = np.cross(x_ax, y_ax)
    zl = norm(z_ax)
    if zl > 0:
        z_ax /= zl
    x_ax = np.cross(y_ax, z_ax)
    return np.column_stack([x_ax, y_ax, z_ax])


def pointer_view_rotation(R):
    """Tilt pointer into screen and lean sideways like a real cursor.
    1) Lean 20 deg clockwise (tip toward upper-left, classic cursor pose)
    2) Tilt 25 deg into screen so the face is partly visible."""
    import math
    from numpy.linalg import norm
    right = R[:, 0].copy()
    up = R[:, 1].copy()
    fwd = -R[:, 2]
    lean = math.radians(-20)
    cl, sl = math.cos(lean), math.sin(lean)
    right2 = cl * right + sl * up
    up2 = -sl * right + cl * up
    tilt = math.radians(25)
    ct, st = math.cos(tilt), math.sin(tilt)
    y_ax = ct * up2 + st * fwd
    x_ax = right2.copy()
    z_ax = np.cross(x_ax, y_ax)
    zl = norm(z_ax)
    if zl > 0:
        z_ax /= zl
    x_ax = np.cross(y_ax, z_ax)
    return np.column_stack([x_ax, y_ax, z_ax])


# ---------------------------------------------------------------------------
# Cursor3D
# ---------------------------------------------------------------------------

class Cursor3D:
    """3D cursor for autostereo displays.

    Renders a small shape in the scene at the depth of whatever is under
    the mouse.  Press C to cycle styles: sphere, crosshair, diamond,
    arrow, pointer.
    """

    def __init__(self, session, style='sphere', radius=0.4):
        self._session = session
        self._radius = radius
        self._style = style
        from chimerax.core.models import Surface
        self._model = m = Surface('3D Cursor', session)
        m.color = (255, 150, 0, 180)
        m.pickable = False
        m.display = False
        self._apply_style(style)
        session.models.add([m])

    @property
    def style(self):
        return self._style

    def set_style(self, style):
        self._style = style
        self._apply_style(style)

    def _apply_style(self, style):
        r = self._radius
        if style == 'sphere':
            from chimerax.surface import sphere_geometry2
            va, na, ta = sphere_geometry2(80)
            va = r * va
        elif style == 'crosshair':
            va, na, ta = _crosshair_geometry(r)
        elif style == 'diamond':
            va, na, ta = _diamond_geometry(r)
        elif style == 'arrow':
            va, na, ta = _arrow_geometry(r)
        elif style == 'pointer':
            va, na, ta = _pointer_geometry(r * 2.5)
        else:
            return
        self._base_va = np.array(va, dtype=np.float64)
        self._base_na = np.array(na, dtype=np.float64)
        self._base_ta = np.array(ta, dtype=np.int32)
        self._model.set_geometry(
            np.array(va, dtype=np.float32),
            np.array(na, dtype=np.float32),
            self._base_ta)

    def update(self, x, y):
        view = self._session.main_view
        pick = view.picked_object(int(x), int(y))
        pos = None
        if pick is not None and hasattr(pick, 'position') and pick.position is not None:
            pos = pick.position
            cam_origin = view.camera.position.origin()
            from numpy.linalg import norm
            to_cam = cam_origin - pos
            dist = norm(to_cam)
            if dist > 0:
                pos = pos + 0.3 * (to_cam / dist)
        else:
            cam = view.camera
            origin, direction = cam.ray(int(x), int(y), view.window_size)
            if origin is not None:
                cofr = view.center_of_rotation
                from numpy.linalg import norm
                dist = norm(cofr - cam.position.origin())
                pos = origin + dist * 0.97 * direction

        if pos is not None:
            self._place_geometry(pos, view.camera)
            self._model.display = True
        else:
            self._model.display = False

    def _place_geometry(self, pos, camera):
        """Place cursor at pos with screen-fixed orientation.
        Rotation is baked into vertex positions via set_geometry();
        model.position handles translation only."""
        from chimerax.geometry import Place
        if self._style == 'sphere':
            va = self._base_va.astype(np.float32)
            na = self._base_na.astype(np.float32)
        else:
            R = view_rotation(camera)
            if self._style == 'arrow':
                R = arrow_view_rotation(R)
            elif self._style == 'pointer':
                R = pointer_view_rotation(R)
            va = (R @ self._base_va.T).T.astype(np.float32)
            na = (R @ self._base_na.T).T.astype(np.float32)
        self._model.set_geometry(va, na, self._base_ta)
        self._model.position = Place(origin=pos)

    def hide(self):
        if self._model is not None:
            self._model.display = False

    def delete(self):
        if self._model is not None:
            self._session.models.remove([self._model])
            self._model = None


class SelectionRect3D:
    """3D selection rectangle for autostereo displays.
    Renders a semi-transparent quad at the center-of-rotation depth
    so the ctrl-drag selection area is visible in stereo."""

    def __init__(self, session):
        self._session = session
        from chimerax.core.models import Surface
        self._model = m = Surface('3D Selection', session)
        m.color = (100, 180, 255, 60)
        m.pickable = False
        m.display = False
        m.use_lighting = False
        session.models.add([m])

    def update(self, x0, y0, x1, y1):
        """Update rectangle corners from graphics coordinates."""
        view = self._session.main_view
        cam = view.camera
        cofr = view.center_of_rotation
        view_dir = -view_rotation(cam)[:, 2]
        ws = view.window_size
        corners_3d = []
        for cx, cy in [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]:
            origin, direction = cam.ray(int(cx), int(cy), ws)
            if origin is None:
                self._model.display = False
                return
            denom = np.dot(direction, view_dir)
            if abs(denom) < 1e-10:
                self._model.display = False
                return
            t = np.dot(cofr - origin, view_dir) / denom
            corners_3d.append(origin + t * direction)
        verts = np.array(corners_3d, dtype=np.float32)
        norms = np.tile(view_dir.astype(np.float32), (4, 1))
        tris = np.array([
            [0, 1, 2], [0, 2, 3],
            [0, 2, 1], [0, 3, 2],
        ], dtype=np.int32)
        from chimerax.geometry import identity
        self._model.position = identity()
        self._model.set_geometry(verts, norms, tris)
        self._model.display = True

    def hide(self):
        if self._model is not None:
            self._model.display = False

    def delete(self):
        if self._model is not None:
            self._session.models.remove([self._model])
            self._model = None
