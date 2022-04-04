import logging
import warnings

import numpy as np
import pytest
from numpy.testing import assert_allclose

from ginga import AstroImage
from ginga.util import wcsmod

# TODO: Add a test for native GWCS object.

_logger = logging.getLogger("TestWCS")
_wcsmods = ('kapteyn', 'starlink', 'astlib', 'astropy', 'astropy_ape14')
_hdr = {'2d': {'ADC-END': 6.28,
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
               'ZD-STR': 17.858},
        '3d': {'SIMPLE': True,
               'BITPIX': 16,
               'NAXIS': 3,
               'NAXIS1': 100,
               'NAXIS2': 100,
               'NAXIS3': 101,
               'BLOCKED': True,
               'CDELT1': -7.165998823E-03,
               'CRPIX1': 5.1E+01,
               'CRVAL1': -5.12820847959E+01,
               'CTYPE1': 'RA---NCP',
               'CUNIT1': 'deg',
               'CDELT2': 7.165998823E-03,
               'CRPIX2': 5.1E+01,
               'CRVAL2': 6.01538880206E+01,
               'CTYPE2': 'DEC--NCP',
               'CUNIT2': 'deg',
               'CDELT3': 4.199999809,
               'CRPIX3': -2.0E+01,
               'CRVAL3': -2.43E+02,
               'CTYPE3': 'VOPT',
               'CUNIT3': 'km/s',
               'EPOCH': 2.0E+03,
               'FREQ0': 1.420405758370E+09,
               'BUNIT': 'JY/BEAM ',
               'BMAJ': 1.82215739042E-02,
               'BMIN': 1.76625289023E-02,
               'BTYPE': 'intensity',
               'BPA': -7.41641769409E+01,
               'NITERS': 2626643,
               'LWIDTH': 4.19999980927E+00,
               'LSTEP': 4.19999980927E+00,
               'LSTART': -2.43E+02,
               'VOBS': -1.95447368244E+00,
               'LTYPE': 'velocity',
               'SPECSYS': 'BARYCENT'}}
img_dict = {}


def setup_module():
    """Create objects once and re-use throughout this module."""
    global img_dict

    img_dict = {}
    for modname in _wcsmods:
        if not wcsmod.use(modname, raise_err=False):
            continue
        img_dict[modname] = {}
        for dim in _hdr.keys():
            w = wcsmod.WCS(_logger)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                w.load_header(_hdr[dim])
            img = AstroImage.AstroImage(logger=_logger)
            img.wcs = w
            if dim == '2d':
                img.revnaxis = []
                img.naxispath = []
            else:  # 3d
                img.revnaxis = [0]
                img.naxispath = [0]
            img_dict[modname][dim] = img


@pytest.mark.parametrize('modname', _wcsmods)
def test_scalar_2d(modname):
    if modname not in img_dict:
        pytest.skip("WCS '{}' not available".format(modname))

    img = img_dict[modname]['2d']

    xy_v1 = (120, 100)
    radec_deg_v1 = (300.2308791294835, 22.691653517073615)

    # If this works here, should already work for other cases.
    assert img.wcs.has_valid_wcs()

    # 0.01% agreement is good enough across different libraries.
    radec = img.pixtoradec(*xy_v1)
    assert_allclose(radec, radec_deg_v1, rtol=1e-4)

    xy = img.radectopix(*radec_deg_v1)
    if modname == 'astropy_ape14':
        # TODO: Remove rtol when load_header is fixed.
        assert_allclose(xy, xy_v1, rtol=0.01)
    else:
        assert_allclose(xy, xy_v1)

    gal = img.wcs.pixtosystem(xy_v1, system='galactic')
    assert_allclose(gal, (60.97030081935234, -3.9706229385605307), rtol=1e-4)


@pytest.mark.parametrize('modname', _wcsmods)
def test_vectorized_2d(modname):
    if modname not in img_dict:
        pytest.skip("WCS '{}' not available".format(modname))

    img = img_dict[modname]['2d']

    xy_v1 = [(0, 0), (120, 100)]
    radec_deg_v1 = np.array([(300.2381639, 22.68602823),
                             (300.2308791294835, 22.691653517073615)])
    gal_v1 = np.array([(60.96903325, -3.97929572),
                       (60.97030081935234, -3.9706229385605307)])

    # 0.01% agreement is good enough across different libraries.
    radec = img.wcs.datapt_to_wcspt(xy_v1)
    assert_allclose(radec, radec_deg_v1, rtol=1e-4)

    xy = img.wcs.wcspt_to_datapt(radec_deg_v1)
    assert_allclose(xy, xy_v1, atol=7e-5)

    if modname == 'astlib':
        with pytest.raises(NotImplementedError):
            img.wcs.datapt_to_system(xy_v1, system='galactic')
    else:
        gal = img.wcs.datapt_to_system(xy_v1, system='galactic')
        if modname in ('astropy', 'astropy_ape14'):
            assert_allclose(gal.l.degree, gal_v1[:, 0])
            assert_allclose(gal.b.degree, gal_v1[:, 1])
        else:
            assert_allclose(gal, gal_v1, rtol=1e-4)


@pytest.mark.parametrize('modname', _wcsmods)
def test_scalar_3d(modname):
    if modname not in img_dict:
        pytest.skip("WCS '{}' not available".format(modname))

    img = img_dict[modname]['3d']
    idxs = (0, 0, 0)
    ra_deg_v1 = -50.569931842112965
    dec_deg_v1 = 59.79236398619401
    vel_v1 = -159000.00382

    if modname == 'astlib':
        with pytest.raises(wcsmod.common.WCSError):
            img.spectral_coord(idxs)
    else:
        c = img.spectral_coord(idxs)
        if modname == 'starlink':
            assert_allclose(c, vel_v1 * 1e-3)
        elif modname == 'astropy_ape14':
            # TODO: Remove rtol with load_header() is fixed.
            assert_allclose(c, vel_v1, rtol=0.03)
        else:
            assert_allclose(c, vel_v1)

    # 0.01% agreement is good enough across different libraries.
    # RA can be off by 360 degrees and still be valid.
    c = img.pixtoradec(*idxs[:2])
    assert (np.allclose(c, (ra_deg_v1, dec_deg_v1), rtol=1e-4) or
            np.allclose(c, (ra_deg_v1 + 360, dec_deg_v1), rtol=1e-4))

    px = img.radectopix(*c)
    assert_allclose(px, idxs[:2], atol=1e-3)

    c = img.wcs.pixtosystem(idxs, system='galactic')
    assert_allclose(c, (95.62934261967311, 11.172927294480449), rtol=1e-4)


@pytest.mark.parametrize('modname', _wcsmods)
def test_vectorized_3d(modname):
    if modname not in img_dict:
        pytest.skip("WCS '{}' not available".format(modname))

    img = img_dict[modname]['3d']

    xy_v1 = [(0, 0), (120, 100)]
    nxp = [0]
    radec_deg_v1 = np.array([[-50.5699318, 59.7923640],
                             [-52.3010162, 60.5064254]])
    gal_v1 = np.array([(95.62934262, 11.17292729),
                       (95.72174081, 12.28825976)])

    if modname == 'kapteyn':
        vel_v1 = -159000.00382
    else:
        vel_v1 = -154800.004

    # 0.01% agreement is good enough across different libraries.
    # RA can be off by 360 degrees and still be valid.
    if modname == 'astlib':
        with pytest.raises(NotImplementedError):
            img.wcs.datapt_to_wcspt(xy_v1, naxispath=nxp)
    else:
        radec = img.wcs.datapt_to_wcspt(xy_v1, naxispath=nxp)
        assert (np.allclose(radec[:, 0], radec_deg_v1[:, 0]) or
                np.allclose(radec[:, 0], radec_deg_v1[:, 0] + 360))
        assert_allclose(radec[:, 1], radec_deg_v1[:, 1], rtol=1e-4)
        if modname == 'starlink':
            with pytest.raises(IndexError):
                radec[:, 2]
        else:
            assert_allclose(radec[:, 2], vel_v1, rtol=1e-4)

    if modname == 'astlib':
        with pytest.raises(NotImplementedError):
            img.wcs.wcspt_to_datapt(radec_deg_v1, naxispath=nxp)
    else:
        xy = img.wcs.wcspt_to_datapt(radec_deg_v1, naxispath=nxp)
        assert_allclose(xy[:, :2], xy_v1, atol=3e-6)
        if modname == 'kapteyn':
            assert_allclose(xy[:, 2], 36.85715, atol=3e-6)

    if modname == 'astlib':
        with pytest.raises(NotImplementedError):
            img.wcs.datapt_to_system([(0, 0, 0), (120, 100, 0)],
                                     system='galactic')
    elif modname == 'kapteyn':
        with pytest.raises(Exception):
            img.wcs.datapt_to_system([(0, 0, 0), (120, 100, 0)],
                                     system='galactic')
    else:
        gal = img.wcs.datapt_to_system([(0, 0, 0), (120, 100, 0)],
                                       system='galactic')
        if modname in ('astropy', 'astropy_ape14'):
            assert_allclose(gal.l.degree, gal_v1[:, 0])
            assert_allclose(gal.b.degree, gal_v1[:, 1])
        else:
            assert_allclose(gal, gal_v1, rtol=1e-4)


def test_fixheader():
    w = wcsmod.common.BaseWCS(_logger)
    w.header = {'SIMPLE': True, 'CUNIT1': 'degree', 'CUNIT2': 'Degree'}
    w.fix_bad_headers()
    assert w.get_keyword('SIMPLE')
    assert w.get_keywords('CUNIT1', 'CUNIT2') == ['deg', 'deg']

    with pytest.raises(wcsmod.common.WCSError):
        w.datapt_to_system((0, 0))


@pytest.mark.parametrize('val', ['degr', 'blah'])
def test_choose_coord_units(val):
    assert wcsmod.common.choose_coord_units({'CUNIT1': val}) == 'degree'


@pytest.mark.parametrize(
    ('hdr', 'val'),
    [({'RA': 0, 'EQUINOX': 1983.9}, 'fk4'),
     ({'RA': 0, 'EQUINOX': 1984.0}, 'fk5'),
     ({'RA': 0}, 'icrs'),
     ({}, 'raw'),
     ({'CTYPE1': 'GLON-TAN'}, 'galactic'),
     ({'CTYPE1': 'ELON-TAN'}, 'ecliptic'),
     ({'CTYPE1': 'RA---TAN', 'EQUINOX': 1983.9}, 'fk4'),
     ({'CTYPE1': 'RA---TAN', 'EQUINOX': 1984.0}, 'fk5'),
     ({'CTYPE1': 'RA---TAN'}, 'icrs'),
     ({'CTYPE1': 'RA---TAN', 'RADECSYS': 'foo'}, 'foo'),
     ({'CTYPE1': 'RA---TAN', 'RADESYS': 'bar'}, 'bar'),
     ({'CTYPE1': 'HPLN-TAN'}, 'helioprojective'),
     ({'CTYPE1': 'HGLT-TAN'}, 'heliographicstonyhurst'),
     ({'CTYPE1': 'PIXEL'}, 'pixel'),
     ({'CTYPE1': 'LINEAR'}, 'pixel'),
     ({'CTYPE1': 'foo'}, 'icrs')])
def test_get_coord_sys_name(hdr, val):
    assert wcsmod.common.get_coord_system_name(hdr) == val

# END
