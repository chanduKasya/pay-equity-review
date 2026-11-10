"""Lets the tests import the modules in the src folder."""

import os
import sys

SRC_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
sys.path.insert(0, SRC_FOLDER)
