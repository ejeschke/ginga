#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#

from ginga.util.wcsmod import common

coord_types = ['pixel']

class ImgWCS(common.BaseWCS):
    """Use an image (or images) to provide a pseudo-WCS.
    """
    def __init__(self, logger): #, shape):
        super(ImgWCS, self).__init__(logger)
        self.kind = 'imgwcs'
        self.coordsys = 'pixel'

    def load_header(self, header, fobj=None):
        self.header = {}
        self.header.update(header.items())
        # Load WCS x-image
        if 'WCS-XIMG' in self.header.keys():
            from astropy.io import fits as pyfits
            hdu = pyfits.open(self.header['WCS-XIMG'])
            head0 = hdu[0].header
            # Error check
            if (head0['NAXIS1'] == header['NAXIS1']) & (head0['NAXIS2'] == header['NAXIS2']):
                self.wcs_ximage = hdu[0].data
                return
        # Set dummy image if we get here
        import numpy as np
        try:
            shape = self.header['NAXIS2'], self.header['NAXIS1']
        except:
            self.wcs_ximage = None
        else:
            self.wcs_ximage = np.outer(np.linspace(4000.,8000.,num=shape[0]), np.ones(shape[1]))

    def pixtoradec(self, idxs, coords='data'):
        """Convert a (x, y) pixel coordinate on the image to a (ra, dec)
        coordinate in space.

        Parameter (coords):
        - if 'data' then x, y coordinates are interpreted as 0-based
        - otherwise coordinates are interpreted as 1-based (traditional FITS)
        """
        if self.wcs_ximage is None:
            return 0., 0.
        x, y = idxs[:2]

        # account for DATA->FITS coordinate space
        if coords == 'data':
            x, y = int(round(x)), int(round(y))

        ra_deg = self.wcs_ximage[y,x]
        dec_deg = 0.

        return ra_deg, dec_deg

    def pixtosystem(self, idxs, system=None, coords='data'):
        return self.pixtoradec(idxs, coords=coords)


# register our WCS with ginga
common.register_wcs('imgwcs', ImgWCS, coord_types)
