import numpy as np

from astropy import nddata
from astropy.io import fits
from astropy.wcs import WCS

from ginga import AstroImage
from ginga.misc import log
from ginga.util import wcs, wcsmod
wcsmod.use('astropy')


class TestAstroImage(object):
    def setup_class(self):
        self.logger = log.get_logger("TestAstroImage", null=True)
        self.image = AstroImage.AstroImage(logger=self.logger)

    def _get_hdu(self):
        data = np.random.randint(0, 10000, (10, 10))
        ra_deg, dec_deg = 10.0, -10.0
        px_scale_deg_px = 0.000026044
        rot_deg = 90.0
        ht, wd = data.shape
        kwds = wcs.simple_wcs(wd / 2.0, ht / 2.0, ra_deg, dec_deg,
                              px_scale_deg_px, rot_deg)
        hdu = fits.PrimaryHDU(data)
        hdu.header.update(kwds)
        assert isinstance(hdu, fits.PrimaryHDU)
        return hdu

    def test_to_nddata(self):
        """Test that we can convert an AstroImage to an NDData object.
        """
        hdu = self._get_hdu()

        self.image.load_hdu(hdu)
        # make sure we have a valid astropy wcs
        assert isinstance(self.image.wcs.wcs, WCS)

        # convert to NDData
        ndd = self.image.as_nddata()
        assert isinstance(ndd, nddata.NDData)

        # this should also work
        ndd = self.image.astype('nddata')
        assert isinstance(ndd, nddata.NDData)

    def test_from_nddata(self):
        """Test that we can load a NDData object into an AstroImage object.
        """
        hdu = self._get_hdu()

        ndd = nddata.NDData(hdu.data, wcs=WCS(hdu.header))
        # make sure we have a valid NDData
        assert isinstance(ndd, nddata.NDData)

        self.image.load_nddata(ndd)
        # make sure we have a valid astropy wcs and numpy data
        assert isinstance(self.image.wcs.wcs, WCS)
        assert isinstance(self.image.get_data(), np.ndarray)

    def test_from_ccddata(self):
        """Test that we can load a NDData object into an AstroImage object.
        """
        hdu = self._get_hdu()

        ccdd = nddata.CCDData(hdu.data, unit='adu', wcs=WCS(hdu.header))
        # make sure we have a valid CCDData
        assert isinstance(ccdd, nddata.CCDData)

        self.image.load_nddata(ccdd)
        # make sure we have a valid astropy wcs and numpy data
        assert isinstance(self.image.wcs.wcs, WCS)
        assert isinstance(self.image.get_data(), np.ndarray)

    def test_to_hdu(self):
        """Test that we can convert an AstroImage to an astropy HDU.
        """
        hdu = self._get_hdu()

        self.image.load_hdu(hdu)
        # make sure we have a valid astropy wcs
        assert isinstance(self.image.wcs.wcs, WCS)

        hdu2 = self.image.as_hdu()
        assert isinstance(hdu2, fits.PrimaryHDU)

# END
