"""WSGI entry point for a free PythonAnywhere web app.

Clone the repository to ``~/Songtrove`` and paste this file into the WSGI
configuration file shown in PythonAnywhere's Web tab.
"""

import os
import sys

project_home = os.path.expanduser("~/Songtrove")
if project_home not in sys.path:
    sys.path.insert(0, project_home)

from app import app as application  # noqa: E402,F401
