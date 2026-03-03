# vim: set expandtab shiftwidth=4 softtabstop=4:

"""Samsung XR backing window with 3D cursor, selection, and hover labels.

This module provides an enhanced backing window for vrto3d-driven
autostereo displays.  It extends the upstream XRBackingWindow concept
with:

- 3D cursor tracking at stereo depth (multiple styles, press C to cycle)
- 3D selection rectangle for ctrl+drag region selection
- 3D hover labels for atoms, residues, and bonds

The enable_samsung_xr_mouse_modes() entry point is called by the
monkey-patched _vrto3d_screen_setup in __init__.py.
"""

import time

from .cursor3d import Cursor3D, SelectionRect3D, CURSOR_STYLES, view_rotation


def enable_samsung_xr_mouse_modes(session):
    """Create a SamsungXRBackingWindow on the Samsung display.

    Called from the monkey-patched _vrto3d_screen_setup.
    Uses direct_pick coordinate mapping (vrto3d per-eye render is portrait,
    screen is landscape — standard mapping through the graphics pane loses
    accuracy due to aspect ratio mismatch).
    """
    screen = _find_samsung_screen(session)
    if screen is None:
        session.logger.warning(
            'ChimeraX-SamsungXR: Could not find Samsung display.')
        return False
    SamsungXRBackingWindow(session, screen)
    session.logger.info(
        f'ChimeraX-SamsungXR: Enabled 3D interaction on "{screen.model()}"')
    return True


_samsung_screen_models = ['Odyssey G90XF', 'Odyssey G90XH']


def _find_samsung_screen(session):
    """Find a Samsung Odyssey screen among connected displays."""
    # Also check upstream xr_screen_model_names in case more are added
    try:
        from chimerax.xr.xr_screens import xr_screen_model_names
        model_names = list(set(_samsung_screen_models + xr_screen_model_names))
    except ImportError:
        model_names = _samsung_screen_models

    screens = session.ui.screens()
    for screen in screens:
        if screen.model() in model_names:
            return screen
    found_names = [screen.model() for screen in screens]
    session.logger.warning(
        f'ChimeraX-SamsungXR: Screens found: {", ".join(found_names)}. '
        f'None match Samsung models: {", ".join(_samsung_screen_models)}')
    return None


class SamsungXRBackingWindow:
    """Backing window for Samsung Odyssey 3D displays with full 3D interaction.

    Creates a transparent fullscreen Qt window on the Samsung display to
    capture mouse/keyboard events, with:
    - 3D cursor at correct stereo depth
    - 3D selection rectangle for ctrl+drag
    - 3D hover labels for atoms/residues/bonds
    - Direct pick coordinate mapping for vrto3d
    """

    def __init__(self, session, screen):
        self._session = session
        self._screen = screen
        self._cursor = None
        self._sel_rect = None
        self._sel_start = None

        # Create fullscreen backing Qt window on Samsung screen
        from Qt.QtWidgets import QWidget
        self._widget = w = QWidget()

        # Transparent, always on top (vrto3d composites underneath)
        self._make_transparent_in_front(w)

        w.move(screen.geometry().topLeft())
        w.showFullScreen()
        w.raise_()
        w.activateWindow()

        # Hover label state
        self._hover_pos = None
        self._hover_time = 0
        self._hover_active = False

        # 3D cursor: hide OS cursor, render 3D shape at scene depth
        self._cursor_styles = list(CURSOR_STYLES)
        self._cursor_style_index = 0
        from Qt.QtCore import Qt
        w.setCursor(Qt.BlankCursor)
        w.setMouseTracking(True)
        self._cursor = Cursor3D(session)

        self._register_mouse_handlers()

        # Forward key press events, intercepting C for cursor style toggle
        def key_press(event):
            from Qt.QtCore import Qt
            if event.key() == Qt.Key_C and not event.modifiers():
                self._cycle_cursor_style()
            else:
                session.ui.forward_keystroke(event)
        w.keyPressEvent = key_press

        # Clean up when XR stops
        session.triggers.add_handler('vr stopped', self._xr_quit)

        # Hover labels via graphics update polling
        session.triggers.add_handler('graphics update',
                                     self._check_for_mouse_hover)

    def _make_transparent_in_front(self, w):
        """Make the backing window transparent and always-on-top.
        vrto3d/SteamVR composites the stereo view underneath this window."""
        from Qt.QtCore import Qt
        w.setAttribute(Qt.WA_TranslucentBackground)
        w.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)

        # Translucent frameless windows don't capture mouse events without
        # a child frame that has a tiny bit of opacity.
        from Qt.QtWidgets import QFrame, QVBoxLayout
        self._f = f = QFrame(w)
        f.setStyleSheet("background: rgba(2, 2, 2, 2);")
        layout = QVBoxLayout(w)
        w.setLayout(layout)
        layout.addWidget(f)

    def _cycle_cursor_style(self):
        """Cycle 3D cursor style: sphere -> crosshair -> diamond -> arrow -> pointer."""
        self._cursor_style_index = (
            (self._cursor_style_index + 1) % len(self._cursor_styles))
        style = self._cursor_styles[self._cursor_style_index]
        if self._cursor is not None:
            self._cursor.set_style(style)
        self._session.logger.info(f'3D cursor: {style}')

    # -------------------------------------------------------------------
    # Mouse event handling
    # -------------------------------------------------------------------

    def _register_mouse_handlers(self):
        w = self._widget
        w.mousePressEvent = self._mouse_down
        w.mouseMoveEvent = self._mouse_drag
        w.mouseReleaseEvent = self._mouse_up
        w.mouseDoubleClickEvent = self._mouse_double_click
        w.wheelEvent = self._wheel

    def _mouse_down(self, event):
        from Qt.QtCore import Qt
        if (event.button() == Qt.LeftButton
                and event.modifiers() & Qt.ControlModifier):
            p = event.position()
            gx, gy = self._backing_to_render_coordinates(p.x(), p.y())
            self._sel_start = (gx, gy)
            if self._sel_rect is None:
                self._sel_rect = SelectionRect3D(self._session)
        self._dispatch_mouse_event(event, "mouse_down")

    def _mouse_drag(self, event):
        if event.buttons():
            from Qt.QtCore import Qt
            if (self._sel_start is not None
                    and event.buttons() & Qt.LeftButton):
                p = event.position()
                gx, gy = self._backing_to_render_coordinates(p.x(), p.y())
                self._sel_rect.update(
                    self._sel_start[0], self._sel_start[1], gx, gy)
            self._dispatch_mouse_event(event, "mouse_drag")

    def _mouse_up(self, event):
        if self._sel_start is not None:
            self._sel_start = None
            if self._sel_rect is not None:
                self._sel_rect.hide()
        self._dispatch_mouse_event(event, "mouse_up")

    def _mouse_double_click(self, event):
        self._dispatch_mouse_event(event, "mouse_double_click")

    def _wheel(self, event):
        self._dispatch_wheel_event(event)

    def _dispatch_mouse_event(self, event, action):
        """Convert mouse event from backing window to render coordinates
        and dispatch to ChimeraX mouse modes."""
        p = event.position()
        gx, gy = self._backing_to_render_coordinates(p.x(), p.y())
        e = self._repositioned_event(event, gx, gy)
        mm = self._session.ui.mouse_modes
        mm._dispatch_mouse_event(e, action)

    def _dispatch_wheel_event(self, event):
        """Convert wheel event and dispatch."""
        p = event.position()
        gx, gy = self._backing_to_graphics_coordinates(p.x(), p.y())
        e = self._repositioned_event(event, gx, gy)
        mm = self._session.ui.mouse_modes
        mm._wheel_event(e)

    # -------------------------------------------------------------------
    # Coordinate mapping
    # -------------------------------------------------------------------

    def _backing_to_graphics_coordinates(self, x, y):
        """Convert backing window pixel coordinates to main graphics
        window coordinates, handling different aspect ratios."""
        w3d = self._widget
        w, h = w3d.width(), w3d.height()
        gw, gh = self._session.main_view.window_size
        if w == 0 or h == 0 or gw == 0 or gh == 0:
            return x, y
        fx, fy = x/w, y/h
        af = w*gh/(h*gw)
        if af > 1:
            afx = 0.5 + af * (fx - 0.5)
            afy = fy
        else:
            afx = fx
            afy = 0.5 + (1/af) * (fy - 0.5)
        gx, gy = afx * gw, afy * gh
        return gx, gy

    def _backing_to_render_coordinates(self, x, y):
        """Map backing window coordinates directly to the XR per-eye
        render texture, bypassing the graphics pane aspect ratio
        correction.  Needed for vrto3d where per-eye render is portrait
        (e.g. 1920x2160) but the graphics pane is landscape."""
        w3d = self._widget
        w, h = w3d.width(), w3d.height()
        if w == 0 or h == 0:
            return x, y
        cam = self._session.main_view.camera
        td = getattr(cam, '_texture_drawing', None)
        if td is None or td.texture is None:
            return self._backing_to_graphics_coordinates(x, y)
        fx, fy = x / w, y / h
        tc = td.texture_coordinates
        (xmin, ymin), (xmax, ymax) = tc[0], tc[2]
        gw, gh = self._session.main_view.window_size
        if (xmax - xmin) == 0 or (ymax - ymin) == 0:
            return self._backing_to_graphics_coordinates(x, y)
        gx = (fx - xmin) / (xmax - xmin) * gw
        gy = (fy - ymin) / (ymax - ymin) * gh
        return gx, gy

    def _repositioned_event(self, event, x, y):
        """Create a new Qt event with repositioned coordinates."""
        from Qt.QtGui import QMouseEvent, QWheelEvent
        from Qt.QtCore import QPointF
        pos = QPointF(x, y)
        if isinstance(event, QMouseEvent):
            return QMouseEvent(
                event.type(), pos, event.globalPosition(),
                event.button(), event.buttons(), event.modifiers(),
                event.device())
        elif isinstance(event, QWheelEvent):
            return QWheelEvent(
                pos, event.globalPosition(), event.pixelDelta(),
                event.angleDelta(), event.buttons(), event.modifiers(),
                event.phase(), event.inverted(), device=event.device())
        raise RuntimeError(f'Unexpected event type: {event}')

    def _graphics_cursor_position(self):
        """Return cursor position in graphics coordinates if on our window."""
        from Qt.QtGui import QCursor
        cp = QCursor.pos()
        if self._session.ui.topLevelAt(cp) == self._widget:
            p = self._widget.mapFromGlobal(cp)
            x, y = self._backing_to_graphics_coordinates(p.x(), p.y())
            return (int(x), int(y))
        mm = self._session.ui.mouse_modes
        return mm._graphics_cursor_position_original()

    # -------------------------------------------------------------------
    # Hover labels
    # -------------------------------------------------------------------

    def _check_for_mouse_hover(self, *args):
        """Called each graphics frame.  Updates 3D cursor and checks for
        mouse pause to show hover labels."""
        if self._widget is None:
            return 'delete handler'
        from Qt.QtGui import QCursor
        cp = QCursor.pos()
        if self._session.ui.topLevelAt(cp) != self._widget:
            if self._cursor is not None:
                self._cursor.hide()
            return

        bp = self._widget.mapFromGlobal(cp)
        x, y = self._backing_to_render_coordinates(bp.x(), bp.y())

        # Update 3D cursor position (once per frame)
        if self._cursor is not None:
            self._cursor.update(x, y)

        # Hover labels: detect pause (0.7s threshold)
        ix, iy = int(x), int(y)
        now = time.time()
        if self._hover_pos != (ix, iy):
            self._hover_pos = (ix, iy)
            self._hover_time = now
            if self._hover_active:
                self._hover_active = False
                self._hide_hover_label()
        elif not self._hover_active and (now - self._hover_time) > 0.7:
            self._hover_active = True
            pick, obj, label_type = self._hover_pick(x, y)
            if pick is None:
                self._hide_hover_label()
            else:
                self._show_hover_label(pick, obj, label_type)

    def _show_hover_label(self, pick, obj, label_type):
        text = pick.description()
        from chimerax.label.label3d import label
        label(self._session, obj, label_type,
              text=text, bg_color=(0, 0, 0, 255))
        self._hover_label_object = obj, label_type

    def _hide_hover_label(self):
        if hasattr(self, '_hover_label_object'):
            obj, label_type = self._hover_label_object
            if obj:
                from chimerax.label.label3d import label_delete
                label_delete(self._session, obj, label_type)
                self._hover_label_object = None, None

    def _hover_pick(self, x, y):
        pick = self._session.main_view.picked_object(x, y)
        from chimerax.atomic import PickedAtom, PickedResidue, PickedBond
        from chimerax.core.objects import Objects
        if isinstance(pick, PickedAtom):
            from chimerax.atomic import Atoms
            obj = Objects(atoms=Atoms([pick.atom]))
            label_type = 'atoms'
        elif isinstance(pick, PickedResidue):
            obj = Objects(atoms=pick.residue.atoms)
            label_type = 'residues'
        elif isinstance(pick, PickedBond):
            from chimerax.atomic import Bonds
            obj = Objects(bonds=Bonds([pick.bond]))
            label_type = 'bonds'
        else:
            return None, None, None
        return pick, obj, label_type

    # -------------------------------------------------------------------
    # Cleanup
    # -------------------------------------------------------------------

    def _xr_quit(self, *args):
        self._hide_hover_label()
        if self._cursor is not None:
            self._cursor.delete()
            self._cursor = None
        if self._sel_rect is not None:
            self._sel_rect.delete()
            self._sel_rect = None
        self._widget.deleteLater()
        self._widget = None
        return 'delete handler'
