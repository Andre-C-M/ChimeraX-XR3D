# vim: set expandtab shiftwidth=4 softtabstop=4:
"""Persistent user preferences for ChimeraX-XR3D.

Only one preference so far: whether the 3D cursor casts a shadow.

Shadows make cursor depth much easier to read -- the shadow lands on the
molecule and tells you where the cursor actually is in the scene -- but they
force a shadow-map rebuild whenever the cursor moves, which is noticeable on
slower GPUs.  So the shipped default stays **off**, and users who want them pay
the cost knowingly.

Before this existed, `xr3d cursor shadows true` only affected the current
``Cursor3D`` object.  Every ``xr on`` built a fresh one with shadows off again,
so the preference could not be expressed durably -- it had to be re-typed every
session.  Now it is stored per user via ChimeraX's ``Settings``.

``AUTO_SAVE`` means assignment writes straight to disk; there is no explicit
``save()`` call and no ``save true`` keyword for the user to remember.
"""

from chimerax.core.settings import Settings


class _XR3DSettings(Settings):
    AUTO_SAVE = {
        # Shipped default is off -- see the module docstring for why.
        'cursor_shadows': False,
    }


_settings = None


def get_settings(session):
    """Return the singleton XR3D settings, creating it on first use.

    Deliberately lazy: constructing a Settings object touches the config file,
    and the bundle is initialised at ChimeraX startup on machines that may have
    no XR display at all.
    """
    global _settings
    if _settings is None:
        _settings = _XR3DSettings(session, "ChimeraX-XR3D")
    return _settings
