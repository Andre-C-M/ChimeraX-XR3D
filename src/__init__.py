# vim: set expandtab shiftwidth=4 softtabstop=4:

from chimerax.core.toolshed import BundleAPI


class _SamsungXRAPI(BundleAPI):
    """Bundle API for Samsung XR 3D interaction features.

    On initialize(), monkey-patches the vrto3d screen setup in
    chimerax.xr.xr_screens to use our enhanced backing window with
    3D cursor, selection rectangle, and hover labels.

    When the upstream registration hook API lands, this will switch
    to the clean register_xr_screen_setup() call instead.
    """
    api_version = 1

    @staticmethod
    def initialize(session, bi):
        """Called at ChimeraX startup (customInit=true).
        Patches _vrto3d_screen_setup to use our enhanced version."""
        _install_vrto3d_hook(session)

    @staticmethod
    def finish(session, bi):
        """Called at ChimeraX shutdown. Restore original setup if needed."""
        _remove_vrto3d_hook()


# ---------------------------------------------------------------------------
# Monkey-patching infrastructure
# ---------------------------------------------------------------------------

_original_vrto3d_setup = None


def _install_vrto3d_hook(session):
    """Replace _vrto3d_screen_setup in xr_screens with our enhanced version."""
    global _original_vrto3d_setup
    try:
        from chimerax.xr import xr_screens
    except ImportError:
        session.logger.warning(
            'ChimeraX-SamsungXR: chimerax.xr.xr_screens not found. '
            'Need ChimeraX daily build 2026-02-27 or newer.')
        return

    # Save the original so we can restore it later
    _original_vrto3d_setup = getattr(xr_screens, '_vrto3d_screen_setup', None)

    # Also add Samsung models if not already present
    for model in ('Odyssey G90XF', 'Odyssey G90XH'):
        if model not in xr_screens.xr_screen_model_names:
            xr_screens.xr_screen_model_names.append(model)

    # Replace with our enhanced setup
    xr_screens._vrto3d_screen_setup = _enhanced_vrto3d_setup

    session.logger.info('ChimeraX-SamsungXR: 3D interaction features loaded')


def _remove_vrto3d_hook():
    """Restore original _vrto3d_screen_setup."""
    global _original_vrto3d_setup
    if _original_vrto3d_setup is not None:
        try:
            from chimerax.xr import xr_screens
            xr_screens._vrto3d_screen_setup = _original_vrto3d_setup
        except ImportError:
            pass
        _original_vrto3d_setup = None


def _enhanced_vrto3d_setup(openxr_camera):
    """Enhanced vrto3d screen setup with 3D cursor, selection, and hover.

    Replaces the upstream _vrto3d_screen_setup which only enables basic
    mouse modes. Our version creates a SamsungXRBackingWindow with full
    3D interaction support.
    """
    from .backing_window import enable_samsung_xr_mouse_modes
    enable_samsung_xr_mouse_modes(openxr_camera._session)


bundle_api = _SamsungXRAPI()
