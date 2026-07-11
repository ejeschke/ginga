#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.txt

import sys
from setuptools import setup
from setuptools.command.build_py import build_py as _build_py

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


class build_py(_build_py):
    """Compile the gettext translation catalogs (.po -> .mo) before building.

    The compiled .mo files are not stored in version control (only the .po
    sources are); they are generated here so that they get picked up by
    ``package_data`` and shipped in the wheel/sdist.  Requires Babel, which is
    declared in ``[build-system] requires`` (see pyproject.toml).
    """
    def run(self):
        try:
            self.run_command('compile_catalog')
        except Exception as exc:
            # Don't hard-fail the build if catalogs can't be compiled;
            # translations simply fall back to English at runtime.
            self.warn("could not compile translation catalogs: %s" % (exc,))
        super().run()


setup(use_scm_version={'write_to': 'ginga/version.py'},
      cmdclass={'build_py': build_py})
