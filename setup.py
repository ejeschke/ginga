#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.txt

import sys
from setuptools import setup

TEST_HELP = """
Note: running tests is no longer done using 'python setup.py test'. Instead
you will need to run:
    pip install -e .
    pytest
For more information, see:
  https://docs.astropy.org/en/latest/development/testguide.html#running-tests
"""

if 'test' in sys.argv:
    print(TEST_HELP)
    sys.exit(1)

DOCS_HELP = """
Note: building the documentation is no longer done using
'python setup.py build_docs'. Instead you will need to run:
    cd doc
    make html
For more information, see:
  https://docs.astropy.org/en/latest/install.html#builddocs
"""

if 'build_docs' in sys.argv or 'build_sphinx' in sys.argv:
    print(DOCS_HELP)
    sys.exit(1)

setup(use_scm_version={'write_to': 'ginga/version.py'})
