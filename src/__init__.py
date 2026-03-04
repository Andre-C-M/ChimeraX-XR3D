# vim: set expandtab shiftwidth=4 softtabstop=4:

from chimerax.core.toolshed import BundleAPI


class _XR3DInteractionAPI(BundleAPI):
    """Bundle API for 3D cursor, selection, and hover on XR displays.

    On initialize(), monkey-patches _enable_xr_mouse_modes in
    xr_screens to create our enhanced backing window with 3D cursor,
    selection rectangle, and hover labels on ALL XR displays
    (Sony, Acer, Samsung).

    When the upstream registration hook API lands, this will switch
    to the clean registration call instead.
    """
    api_version = 1

    @staticmethod
    def initialize(session, bi):
        """Called at ChimeraX startup (customInit=true)."""
        _install_hook(session)

    @staticmethod
    def finish(session, bi):
        """Called at ChimeraX shutdown."""
        _remove_hook()


# ---------------------------------------------------------------------------
# Monkey-patching infrastructure
# ---------------------------------------------------------------------------

_original_enable_xr_mouse_modes = None


def _get_xr_screens():
    """Import xr_screens from the correct location.
    Older builds have it at chimerax.vive, newer at chimerax.xr."""
    try:
        from chimerax.xr import xr_screens
        return xr_screens
    except ImportError:
        pass
    try:
        from chimerax.vive import xr_screens
        return xr_screens
    except ImportError:
        pass
    return None


def _install_hook(session):
    """Patch _enable_xr_mouse_modes to use our enhanced backing window
    with 3D cursor on ALL XR displays (Sony, Acer, Samsung)."""
    global _original_enable_xr_mouse_modes
    xr_screens = _get_xr_screens()
    if xr_screens is None:
        session.logger.warning(
            'ChimeraX-SamsungXR: xr_screens module not found.')
        return

    # Save the original
    _original_enable_xr_mouse_modes = xr_screens._enable_xr_mouse_modes

    # Add Samsung models if not already present
    for model in ('Odyssey G90XF', 'Odyssey G90XH'):
        if model not in xr_screens.xr_screen_model_names:
            xr_screens.xr_screen_model_names.append(model)

    # Replace with our enhanced version
    xr_screens._enable_xr_mouse_modes = _enhanced_enable_xr_mouse_modes

    session.logger.info(
        'ChimeraX-SamsungXR: 3D cursor enabled for all XR displays')


def _remove_hook():
    """Restore original _enable_xr_mouse_modes."""
    global _original_enable_xr_mouse_modes
    if _original_enable_xr_mouse_modes is not None:
        xr_screens = _get_xr_screens()
        if xr_screens is not None:
            xr_screens._enable_xr_mouse_modes = _original_enable_xr_mouse_modes
        _original_enable_xr_mouse_modes = None


def _enhanced_enable_xr_mouse_modes(session, screen_model_name=None,
                                     openxr_window_captures_events=False,
                                     direct_pick=False, **kwargs):
    """Enhanced _enable_xr_mouse_modes that creates our 3D-capable
    backing window instead of the vanilla XRBackingWindow.

    Called by all display setup functions (Sony, Acer, Samsung).
    Passes through direct_pick and openxr_window_captures_events
    from the original caller.
    """
    from .backing_window import enable_xr3d_mouse_modes
    return enable_xr3d_mouse_modes(
        session,
        screen_model_name=screen_model_name,
        openxr_window_captures_events=openxr_window_captures_events,
        direct_pick=direct_pick)


bundle_api = _XR3DInteractionAPI()
