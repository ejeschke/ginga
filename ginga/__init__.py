# Licensed under a 3-clause BSD style license - see LICENSE.txt
"""See LONG_DESC.txt"""

# Packages may add whatever they like to this file, but
# should keep this content at the top.
# ----------------------------------------------------------------------------
from ._astropy_init import *  # noqa
# ----------------------------------------------------------------------------

try:
    # As long as we're using setuptools/distribute, we need to do this the
    # setuptools way or else pkg_resources will throw up unnecessary and
    # annoying warnings (even though the namespace mechanism will still
    # otherwise work without it).
    __import__('pkg_resources').declare_namespace(__name__)
except ImportError:
    pass

__path__ = __import__('pkgutil').extend_path(__path__, __name__)  # noqa

# END
