# vim: set expandtab shiftwidth=4 softtabstop=4:

"""Install ChimeraX-SamsungXR plugin for local development.

Run this script inside ChimeraX:
    runscript /path/to/ChimeraX-SamsungXR/install_dev.py

Or from the ChimeraX command line:
    devel install /path/to/ChimeraX-SamsungXR editable true
"""

import os
bundle_dir = os.path.dirname(os.path.abspath(__file__))
from chimerax.core.commands import run
run(session, f'devel install "{bundle_dir}" editable true')
