#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Regenerate build files without extracting, patching or signing APKs."""
import runpy
import sys
from pathlib import Path

sys.argv = [str(Path(__file__).with_name('extract-files.py')),
            '--regenerate_makefiles', *sys.argv[1:]]
runpy.run_path(sys.argv[0], run_name='__main__')
