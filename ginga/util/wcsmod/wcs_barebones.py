#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.util.wcsmod import common

coord_types = ['pixel']


class BareBonesWCS(common.BaseWCS):
    """A dummy placeholder WCS.

    .. note::
        To get WCS functionality, please install one of the 3rd party python
        WCS modules referred to at the top of this module.

    """
    def __init__(self, logger):
        super(BareBonesWCS, self).__init__(logger)
        self.kind = 'barebones'

    def load_header(self, header, fobj=None):
        self.coordsys = 'pixel'

    def spectral_coord(self, idxs, coords='data'):
        raise common.WCSError("This feature not supported by BareBonesWCS")

    def pixtoradec(self, idxs, coords='data'):
        px_x, px_y = idxs[:2]
        px_x, px_y = px_x + 1.0, px_y + 1.0
        return (px_x, px_y)

    def radectopix(self, px_x, px_y, coords='data', naxispath=None):
        # px_x, px_y = px_x - 1.0, px_y - 1.0
        return (px_x, px_y)

    def pixtosystem(self, idxs, system=None, coords='data'):
        return self.pixtoradec(idxs, coords=coords)


# register our WCS with ginga
common.register_wcs('barebones', BareBonesWCS, coord_types)
