# Licensed under a 3-clause BSD style license - see LICENSE.txt
import os
from warnings import warn

from astropy.config.configuration import (
    update_default_config, ConfigurationDefaultMissingError,
    ConfigurationDefaultMissingWarning)
from astropy.tests.runner import TestRunner

try:
    from .version import version as __version__
except ImportError:
    __version__ = ''

# Create the test function for self test
test = TestRunner.make_test_runner_in(os.path.dirname(__file__))
test.__test__ = False

__all__ = ['__version__', 'test']

# add these here so we only need to cleanup the namespace at the end
config_dir = None

if not os.environ.get('ASTROPY_SKIP_CONFIG_UPDATE', False):
    config_dir = os.path.dirname(__file__)
    config_template = os.path.join(config_dir, __package__ + ".cfg")
    if os.path.isfile(config_template):
        try:
            update_default_config(
                __package__, config_dir, version=__version__)
        except TypeError as orig_error:
            try:
                update_default_config(__package__, config_dir)
            except ConfigurationDefaultMissingError as e:
                wmsg = (e.args[0] + " Cannot install default profile. If "
                        "you are importing from source, this is expected.")
                warn(ConfigurationDefaultMissingWarning(wmsg))
                del e
            except Exception:
                raise orig_error
