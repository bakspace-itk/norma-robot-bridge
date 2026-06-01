# -*- coding: utf-8 -*-
"""pytest-konfiguration der tilfoejer src/ til sys.path saa tests kan
importere pepper_bridge uden at pakken er installeret med pip install -e."""

from __future__ import print_function

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.normpath(os.path.join(_HERE, "..", "src"))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
