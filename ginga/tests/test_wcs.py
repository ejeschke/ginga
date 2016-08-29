from __future__ import print_function
import unittest
import logging
import numpy

from ginga import AstroImage
from ginga.util import wcsmod

class TestImageView(unittest.TestCase):

    def setUp(self):
        self.logger = logging.getLogger("TestWCS")
        self.header = {'ADC-END': 6.28,
                       'ADC-STR': 6.16,
                       'ADC-TYPE': 'IN',
                       'AIRMASS': 1.0526,
                       'ALTITUDE': 72.142,
                       'AUTOGUID': 'ON',
                       'AZIMUTH': 282.679,
                       'BIN-FCT1': 1,
                       'BIN-FCT2': 1,
                       'BITPIX': -32,
                       'BLANK': -32768,
                       'BUNIT': 'ADU',
                       'CD1_1': -5.611e-05,
                       'CD1_2': 0.0,
                       'CD2_1': 0.0,
                       'CD2_2': 5.611e-05,
                       'CDELT1': -5.611e-05,
                       'CDELT2': 5.611e-05,
                       'COADD': 1,
                       'CRPIX1': 5276.0,
                       'CRPIX2': 25.0,
                       'CRVAL1': 299.91736667,
                       'CRVAL2': 22.68769444,
                       'CTYPE1': 'RA---TAN',
                       'CTYPE2': 'DEC--TAN',
                       'CUNIT1': 'degree',
                       'CUNIT2': 'degree',
                       'DATA-TYP': 'OBJECT',
                       'DATASET': 'DS000',
                       'DATE-OBS': '2009-08-22',
                       'DEC': '+22:41:15.70',
                       'DEC2000': '+22:41:15.70',
                       'DET-A01': 90.0,
                       'DET-ID': 6,
                       'DET-P101': -79.14,
                       'DET-P201': -0.375,
                       'DET-TMAX': 0.0,
                       'DET-TMED': 0.0,
                       'DET-TMIN': 0.0,
                       'DET-TMP': 172.74,
                       'DET-VER': 'spcam20080721',
                       'DETECTOR': 'chihiro',
                       'DOM-HUM': 12.4,
                       'DOM-PRS': 622.3,
                       'DOM-TMP': 276.35,
                       'DOM-WND': 0.6,
                       'EFP-MIN1': 9,
                       'EFP-MIN2': 49,
                       'EFP-RNG1': 2256,
                       'EFP-RNG2': 4177,
                       'EQUINOX': 2000.0,
                       'EXP-ID': 'SUPE01118760',
                       'EXP1TIME': 90.0,
                       'EXPTIME': 90.0,
                       'EXTEND': False,
                       'FILTER01': 'W-J-B',
                       'FOC-POS': 'Prime',
                       'FOC-VAL': 7.14,
                       'FRAMEID': 'SUPA01118766',
                       'GAIN': 3.73,
                       'HST': '23:34:25.911',
                       'HST-END': '23:35:55.010',
                       'HST-STR': '23:34:25.911',
                       'INR-END': -174.487,
                       'INR-STR': -174.239,
                       'INS-VER': 'Messia5/sup080721',
                       'INST-PA': 90.0,
                       'INSTRUME': 'SuprimeCam',
                       'LONGPOLE': 180.0,
                       'LST': '21:15:48.968',
                       'LST-END': '21:17:18.311',
                       'LST-STR': '21:15:48.968',
                       'M2-ANG1': 1.5,
                       'M2-ANG2': -0.0,
                       'M2-ANG3': 0.0,
                       'M2-POS1': -0.753,
                       'M2-POS2': -2.1,
                       'M2-POS3': 8.205,
                       'MJD': 55065.398914,
                       'MJD-END': 55065.399945,
                       'MJD-STR': 55065.398914,
                       'NAXIS': 2,
                       'NAXIS1': 2272,
                       'NAXIS2': 4273,
                       'OBJECT': 'M27',
                       'OBS-ALOC': 'Observation',
                       'OBS-MOD': 'IMAG_N_VGW',
                       'OBSERVAT': 'NAOJ',
                       'OBSERVER': 'Jeschke, Inagaki, Streeper, Yagi, Nakata',
                       'OUT-HUM': 13.1,
                       'OUT-PRS': 622.3,
                       'OUT-TMP': 275.95,
                       'OUT-WND': 6.0,
                       'PRD-MIN1': 1,
                       'PRD-MIN2': 1,
                       'PRD-RNG1': 2272,
                       'PRD-RNG2': 4273,
                       'PROP-ID': 'o99005',
                       'RA': '19:59:40.168',
                       'RA2000': '19:59:40.168',
                       'RADECSYS': 'FK5',
                       'SECZ-END': 1.053,
                       'SECZ-STR': 1.051,
                       'SEEING': 0.29,
                       'SIMPLE': True,
                       'S_AG-DEC': 'N/A',
                       'S_AG-EQN': 2000.0,
                       'S_AG-OBJ': 'N/A',
                       'S_AG-R': 999.99,
                       'S_AG-RA': 'N/A',
                       'S_AG-TH': 999.99,
                       'S_AG-X': 109.97,
                       'S_AG-Y': 19.3,
                       'S_BCTAVE': 999.999,
                       'S_BCTSD': 999.999,
                       'S_DELTAD': 0.0,
                       'S_DELTAZ': 0.0,
                       'S_EFMN11': 9,
                       'S_EFMN12': 49,
                       'S_EFMN21': 617,
                       'S_EFMN22': 49,
                       'S_EFMN31': 1145,
                       'S_EFMN32': 49,
                       'S_EFMN41': 1753,
                       'S_EFMN42': 49,
                       'S_EFMX11': 520,
                       'S_EFMX12': 4225,
                       'S_EFMX21': 1128,
                       'S_EFMX22': 4225,
                       'S_EFMX31': 1656,
                       'S_EFMX32': 4225,
                       'S_EFMX41': 2264,
                       'S_EFMX42': 4225,
                       'S_ETMAX': 0.0,
                       'S_ETMED': 273.15,
                       'S_ETMIN': 0.0,
                       'S_FRMPOS': '0001',
                       'S_GAIN1': 3.73,
                       'S_GAIN2': 2.95,
                       'S_GAIN3': 3.1,
                       'S_GAIN4': 3.17,
                       'S_M2OFF1': 0.0,
                       'S_M2OFF2': 0.0,
                       'S_M2OFF3': 7.14,
                       'S_OSMN11': 521,
                       'S_OSMN12': 1,
                       'S_OSMN21': 569,
                       'S_OSMN22': 1,
                       'S_OSMN31': 1657,
                       'S_OSMN32': 1,
                       'S_OSMN41': 1705,
                       'S_OSMN42': 1,
                       'S_OSMX11': 568,
                       'S_OSMX12': 48,
                       'S_OSMX21': 616,
                       'S_OSMX22': 48,
                       'S_OSMX31': 1704,
                       'S_OSMX32': 48,
                       'S_OSMX41': 1752,
                       'S_OSMX42': 48,
                       'S_SENT': False,
                       'S_UFNAME': 'object060_chihiro.fits',
                       'S_XFLIP': False,
                       'S_YFLIP': True,
                       'TELESCOP': 'Subaru',
                       'TELFOCUS': 'P_OPT',
                       'TIMESYS': 'UTC',
                       'UT': '09:34:25.911',
                       'UT-END': '09:35:55.010',
                       'UT-STR': '09:34:25.911',
                       'WCS-ORIG': 'SUBARU Toolkit',
                       'WEATHER': 'Fine',
                       'ZD-END': 18.2,
                       'ZD-STR': 17.858}


    def pixtoradec_scalar_runtest(self, modname):
        if not wcsmod.use(modname, raise_err=False):
            return False
        wcs = wcsmod.WCS(self.logger)
        if wcs.wcs is None:
            return False
        wcs.load_header(self.header)
        img = AstroImage.AstroImage(logger=self.logger)
        img.wcs = wcs
        img.revnaxis = []

        ra_deg_v1 = 300.2308791294835
        dec_deg_v1 = 22.691653517073615

        ra_deg, dec_deg = img.pixtoradec(120, 100)
        assert numpy.isclose(ra_deg, ra_deg_v1), \
               ValueError("RA deg does not match (%f != %f)" % (ra_deg,
                                                                ra_deg_v1))
        assert numpy.isclose(dec_deg, dec_deg_v1), \
               ValueError("DEC deg does not match (%f != %f)" % (dec_deg,
                                                                 dec_deg_v1))
        return True

    def test_pixtoradec_scalar_kapteyn(self):
        if not self.pixtoradec_scalar_runtest('kapteyn'):
            print("WCS '%s' not available--skipping test" % ('kapteyn'))

    def test_pixtoradec_scalar_starlink(self):
        if not self.pixtoradec_scalar_runtest('starlink'):
            print("WCS '%s' not available--skipping test" % ('starlink'))

    def test_pixtoradec_scalar_astlib(self):
        if not self.pixtoradec_scalar_runtest('astlib'):
            print("WCS '%s' not available--skipping test" % ('astlib'))

    def test_pixtoradec_scalar_astropy(self):
        if not self.pixtoradec_scalar_runtest('astropy'):
            print("WCS '%s' not available--skipping test" % ('astropy'))

    def radectopix_scalar_runtest(self, modname):
        if not wcsmod.use(modname, raise_err=False):
            return False
        wcs = wcsmod.WCS(self.logger)
        if wcs.wcs is None:
            return False
        wcs.load_header(self.header)
        img = AstroImage.AstroImage(logger=self.logger)
        img.wcs = wcs
        img.naxispath = []

        x_v1 = 120
        y_v1 = 100

        x, y = img.radectopix(300.2308791294835, 22.691653517073615)
        assert numpy.isclose(x, x_v1), \
               ValueError("x does not match (%f != %f)" % (x, x_v1))
        assert numpy.isclose(y, y_v1), \
               ValueError("y does not match (%f != %f)" % (y, y_v1))
        return True

    def test_radectopix_scalar_kapteyn(self):
        if not self.radectopix_scalar_runtest('kapteyn'):
            print("WCS '%s' not available--skipping test" % ('kapteyn'))

    def test_radectopix_scalar_starlink(self):
        if not self.radectopix_scalar_runtest('starlink'):
            print("WCS '%s' not available--skipping test" % ('starlink'))

    def test_radectopix_scalar_astlib(self):
        if not self.radectopix_scalar_runtest('astlib'):
            print("WCS '%s' not available--skipping test" % ('astlib'))

    def test_radectopix_scalar_astropy(self):
        if not self.radectopix_scalar_runtest('astropy'):
            print("WCS '%s' not available--skipping test" % ('astropy'))

    def tearDown(self):
        pass


if __name__ == '__main__':
    unittest.main()

#END
