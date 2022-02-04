#
# catalog.py -- image and star catalog interfaces for Ginga
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import os.path
import tempfile
import re
import time
import warnings
from urllib.request import Request, urlopen, urlretrieve
from urllib.error import URLError, HTTPError

from ginga.misc import Bunch
from ginga.util import wcs

from astropy import coordinates, units

# Do we have astroquery >=0.3.5 installed?
have_astroquery = False
try:
    from astroquery.vo_conesearch import conesearch

    have_astroquery = True
except ImportError:
    pass

# these are modifed at bottom of this module
default_image_sources = []
default_catalog_sources = []
default_name_sources = []


class SourceError(Exception):
    """For exceptions raised by the `~ginga.util.catalog` module."""
    pass


class Star(object):
    def __init__(self, **kwdargs):
        starInfo = {}
        starInfo.update(kwdargs)
        self.starInfo = starInfo

    def __getitem__(self, key):
        return self.starInfo[key]

    def __contains__(self, key):
        return key in self.starInfo

    def __setitem__(self, key, value):
        self.starInfo[key] = value

    # TODO: Should deprecate this and encourage __contains__ like Python dict
    def has_key(self, key):
        return key in self.starInfo


class AstroqueryCatalogServer(object):
    """For queries using the ``astroquery.catalog`` function."""

    kind = 'astroquery.catalog'

    @classmethod
    def get_params_metadata(cls):
        from ginga.misc.ParamSet import Param
        return [
            Param(name='ra', type=str, widget='entry',
                  description="Right ascension component of center"),
            Param(name='dec', type=str, widget='entry',
                  description="Declination component of center"),
            Param(name='r', type=float, default=5.0, widget='entry',
                  description="Radius from center in arcmin"),
        ]

    def __init__(self, logger, full_name, key, querymod, mapping,
                 description=None):
        super(AstroqueryCatalogServer, self).__init__()
        if not have_astroquery:
            raise ImportError("'astroquery' not found, please install it")

        self.logger = logger
        self.full_name = full_name
        self.short_name = key
        self.mapping = mapping
        self.querymod = querymod
        if description is None:
            description = full_name
        self.description = description

    def getParams(self):
        return self.get_params_metadata()

    def toStar(self, data, ext, magfield):
        try:
            mag = float(data[magfield])
        except Exception:
            mag = 0.0

        # Make sure we have at least these Ginga standard fields defined
        d = {'name': data[ext['id']],
             'ra_deg': float(data[ext['ra']]),
             'dec_deg': float(data[ext['dec']]),
             'mag': mag,
             'preference': 0.0,
             'priority': 0,
             'description': 'fake magnitude'}
        data.update(d)
        data['ra'] = wcs.ra_deg_to_str(data['ra_deg'])
        data['dec'] = wcs.dec_deg_to_str(data['dec_deg'])
        return Star(**data)

    def _search(self, center, radius, catalog, **kwargs):
        results = self.querymod.query_region(center, radius,
                                             catalog=catalog,
                                             **kwargs)
        if results is None:
            return results
        return results[0]

    def search(self, **params):
        """
        For compatibility with generic star catalog search.
        """

        self.logger.debug("search params=%s" % (str(params)))
        ra, dec = params['ra'], params['dec']
        if not (':' in ra):
            # Assume RA and DEC are in degrees
            ra_deg = float(ra)
            dec_deg = float(dec)
        else:
            # Assume RA and DEC are in standard string notation
            ra_deg = wcs.hmsStrToDeg(ra)
            dec_deg = wcs.dmsStrToDeg(dec)

        # Convert to degrees for search radius
        radius_deg = float(params['r']) / 60.0
        # radius_deg = float(params['r'])

        # Note requires astropy 0.3.x+
        c = coordinates.SkyCoord(ra_deg * units.degree,
                                 dec_deg * units.degree,
                                 frame='icrs')
        self.logger.info("Querying catalog: %s" % (self.full_name))
        time_start = time.time()
        with warnings.catch_warnings():  # Ignore VO warnings
            warnings.simplefilter('ignore')
            results = self._search(c, radius_deg * units.degree,
                                   self.full_name)

        time_elapsed = time.time() - time_start
        if results is None:
            self.logger.info("Null result in %.2f sec" % (
                time_elapsed))
            raise SourceError("Null result from query")
        else:
            numsources = len(results)
            self.logger.info("Found %d sources in %.2f sec" % (
                numsources, time_elapsed))

        # Scan the returned fields to find ones we need to extract
        # particulars from (ra, dec, id, magnitude)
        mags = []
        ext = {}
        fields = results.colnames
        #print("fields are", fields)
        for name in fields:
            if name == self.mapping['id']:
                ext['id'] = name
            elif name == self.mapping['ra']:
                ext['ra'] = name
            elif name == self.mapping['dec']:
                ext['dec'] = name
            if name in self.mapping.get('mag', []):
                mags.append(name)
        self.logger.debug("possible magnitude fields: %s" % str(mags))
        if len(mags) > 0:
            magfield = mags[0]
        else:
            magfield = None

        # prepare the result list
        starlist = []
        for i in range(numsources):
            source = dict(zip(fields, results[i]))
            starlist.append(self.toStar(source, ext, magfield))

        # metadata about the list
        columns = [('Name', 'name'),
                   ('RA', 'ra'),
                   ('DEC', 'dec'),
                   ('Mag', 'mag'),
                   ('Preference', 'preference'),
                   ('Priority', 'priority'),
                   ('Description', 'description'),
                   ]
        # Append extra columns returned by search to table header
        cols = list(fields)
        cols.remove(ext['ra'])
        cols.remove(ext['dec'])
        cols.remove(ext['id'])
        columns.extend(zip(cols, cols))

        # which column is the likely one to color source circles
        colorCode = 'Mag'

        info = Bunch.Bunch(columns=columns, color=colorCode)
        return starlist, info


class AstroqueryVOCatalogServer(AstroqueryCatalogServer):
    """For queries using the `astroquery.vo.conesearch` function."""

    kind = 'astroquery.vo_conesearch'

    def __init__(self, logger, full_name, key, mapping, description=None):
        super(AstroqueryVOCatalogServer, self).__init__(logger, full_name,
                                                        key, None, mapping,
                                                        description=description)

    def _search(self, center, radius, catalog):
        # override this methid to pass some special kwargs to the search
        results = conesearch.conesearch(center, radius, catalog_db=catalog,
                                        verbose=False,
                                        return_astropy_table=True,
                                        use_names_over_ids=False)
        return results


class AstroqueryImageServer(object):
    """For queries using the ``astroquery.vo_conesearch`` function."""

    kind = 'astroquery.image'

    @classmethod
    def get_params_metadata(cls):
        from ginga.misc.ParamSet import Param
        return [
            Param(name='ra', type=str, default='', widget='entry',
                  description="Right ascension component of center"),
            Param(name='dec', type=str, widget='entry',
                  description="Declination component of center"),
            Param(name='width', type=float, default=1, widget='entry',
                  description="Width of box in degrees"),
            Param(name='height', type=float, default=1, widget='entry',
                  description="Height of box in degrees"),
        ]

    def __init__(self, logger, full_name, key, querymod, description=None):
        super(AstroqueryImageServer, self).__init__()
        if not have_astroquery:
            raise ImportError('astroquery not found, please install astroquery')

        self.logger = logger
        self.full_name = full_name
        self.short_name = key
        if isinstance(querymod, str) and querymod.lower() == 'skyview':
            from astroquery.skyview import SkyView
            self.querymod = SkyView
        else:
            self.querymod = querymod
        if description is None:
            description = full_name
        self.description = description

    def getParams(self):
        return self.get_params_metadata()

    def _search(self, center, wd_deg, ht_deg):
        survey = [self.short_name]

        results = self.querymod.get_image_list(center, survey,
                                               width=wd_deg * units.degree,
                                               height=ht_deg * units.degree)
        return results

    # TODO: dstpath provides the pathname for storing the image
    def search(self, dstpath, **params):
        """
        For compatibility with generic image catalog search.
        """

        self.logger.debug("search params=%s" % (str(params)))
        ra, dec = params['ra'], params['dec']
        if not (':' in ra):
            # Assume RA and DEC are in degrees
            ra_deg = float(ra)
            dec_deg = float(dec)
        else:
            # Assume RA and DEC are in standard string notation
            ra_deg = wcs.hmsStrToDeg(ra)
            dec_deg = wcs.dmsStrToDeg(dec)

        # Convert to degrees for search
        wd_deg = float(params['width']) / 60.0
        ht_deg = float(params['height']) / 60.0

        # Note requires astropy 3.x+
        c = coordinates.SkyCoord(ra_deg * units.degree,
                                 dec_deg * units.degree,
                                 frame='icrs')
        self.logger.info("Querying image source: %s" % (self.full_name))
        time_start = time.time()
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            results = self._search(c, wd_deg, ht_deg)

        time_elapsed = time.time() - time_start
        if results is None:
            self.logger.info("Null result in %.2f sec" % (
                time_elapsed))
            return None
        else:
            numsources = len(results)
            self.logger.info("Found %d images in %.2f sec" % (
                numsources, time_elapsed))
            if numsources == 0:
                self.logger.warning("Found no images in this area" % len(results))
                return None

        # For now, we pick the first one found
        urls = list(results)
        # fitspath = results[0].make_dataset_filename(dir=tempfile.gettempdir())

        # file will be downloaded
        fitspath = urls[0]

        # explicit return
        return fitspath


class AstroqueryNameServer(object):
    """For object name lookups using `astroquery`"""

    kind = 'astroquery.names'

    def __init__(self, logger, full_name, key, mapping, description=None):
        super(AstroqueryNameServer, self).__init__()
        if not have_astroquery:
            raise ImportError("'astroquery' not found, please install it")

        self.logger = logger
        self.full_name = full_name
        self.short_name = key
        self.mapping = mapping
        if description is None:
            description = full_name
        self.description = description

    def search(self, name, **kwargs):
        if self.short_name == 'SIMBAD':
            from astroquery.simbad import Simbad
            results = Simbad.query_object(name, **kwargs)
            if results is None:
                raise SourceError("No results found for name '{}'".format(name))

            # from SIMBAD, coords come formatted as a string
            ra = ':'.join(results['RA'][0].split())
            dec = ':'.join(results['DEC'][0].split())

        elif self.short_name == 'NED':
            from astroquery.ned import Ned
            results = Ned.query_object(name, **kwargs)
            if results is None:
                # Ned usually returns an exception for non-found objects
                # but lets put this test just in case
                raise SourceError("No results found for name '{}'".format(name))

            # from NED, coords come as degrees in float
            ra = wcs.ra_deg_to_str(results['RA'][0])
            dec = wcs.dec_deg_to_str(results['DEC'][0])

        else:
            raise SourceError("Don't know how to query source '{}'".format(self.short_name))

        return ra, dec


class URLServer(object):

    kind = 'url'

    def __init__(self, logger, full_name, key, url, description):
        self.logger = logger
        self.full_name = full_name
        self.short_name = key
        self.base_url = url
        self.reqtype = 'get'
        self.description = description

        self.params = self._parse_params(url)

    def _parse_params(self, url):
        params = {}
        regex = r'^.*?\%\((\w+)\)([sfd])(.*)$'
        match = re.match(regex, url)
        count = 0
        while match:
            key, typ, sfx = match.groups()
            idx = ['s', 'd', 'f'].index(typ)
            cvt = (str, int, float)[idx]
            params[key] = Bunch.Bunch(name=key, convert=cvt, order=count)
            count += 1
            match = re.match(regex, sfx)

        return params

    def getParams(self):
        return self.params

    def convertParams(self, params):
        d = {}
        for key, bnch in self.params.items():
            d[key] = bnch.convert(params[key])
        return d

    def fetch(self, url, filepath=None):
        data = ""

        req = Request(url)

        try:
            self.logger.info("Opening url=%s" % (url))
            try:
                response = urlopen(req)  # nosec

            except HTTPError as e:
                self.logger.error("Server returned error code %s" % (e.code))
                raise e
            except URLError as e:
                self.logger.error("Server URL failure: %s" % (str(e.reason)))
                raise e
            except Exception as e:
                self.logger.error("URL fetch failure: %s" % (str(e)))
                raise e

            self.logger.debug("getting HTTP headers")
            info = response.info()  # noqa

            self.logger.debug("getting data")
            data = response.read()
            self.logger.debug("fetched %d bytes" % (len(data)))
            # data = data.decode('ascii')

        except Exception as e:
            self.logger.error("Error reading data from '%s': %s" % (
                url, str(e)))
            raise e

        if filepath:
            with open(filepath, 'wb') as out_f:
                out_f.write(data)
            return None

        else:
            return data

    def retrieve(self, url, filepath=None, cb_fn=None):
        ofilepath = filepath
        if (filepath is None) or os.path.isdir(filepath):
            with tempfile.NamedTemporaryFile(dir=filepath,
                                             delete=False) as out_f:
                filepath = out_f.name

        try:
            self.logger.info("Opening url=%s" % (url))

            if cb_fn is not None:
                localpath, info = urlretrieve(url, filepath, cb_fn)  # nosec
            else:
                localpath, info = urlretrieve(url, filepath)  # nosec

        except Exception as e:
            self.logger.error("URL fetch failure: %s" % (str(e)))
            raise e

        if ofilepath is not None:
            return localpath

        with open(filepath, 'r') as in_f:
            return in_f.read()

    def search(self, filepath, **params):
        url = self.base_url % params

        self.fetch(url, filepath=filepath)
        return filepath


class ImageServer(URLServer):

    kind = 'ginga.image'

    @classmethod
    def get_params_metadata(cls):
        from ginga.misc.ParamSet import Param
        return [
            Param(name='ra', type=str, default='', widget='entry',
                  description="Right ascension component of center"),
            Param(name='dec', type=str, widget='entry',
                  description="Declination component of center"),
            Param(name='width', type=float, default=1, widget='entry',
                  description="Width of box in degrees"),
            Param(name='height', type=float, default=1, widget='entry',
                  description="Height of box in degrees"),
        ]

    def __init__(self, logger, full_name, key, url, description):
        super(ImageServer, self).__init__(logger, full_name, key, url,
                                          description)


class CatalogServer(URLServer):

    kind = 'ginga.catalog'

    @classmethod
    def get_params_metadata(cls):
        from ginga.misc.ParamSet import Param
        return [
            Param(name='ra', type=str, widget='entry',
                  description="Right ascension component of center"),
            Param(name='dec', type=str, widget='entry',
                  description="Declination component of center"),
            Param(name='r', type=float, default=1.0, widget='entry',
                  description="Radius from center in arcmin"),
            Param(name='r2', type=float, default=2.0, widget='entry',
                  description="Outer radius from center in arcmin"),
        ]

    def __init__(self, logger, full_name, key, url, description):
        super(CatalogServer, self).__init__(logger, full_name, key, url,
                                            description)
        self.index = {'name': 0, 'ra': 1, 'dec': 2, 'mag': 10}
        self.format = 'str'
        self.equinox = 2000.0

    def set_index(self, **kwdargs):
        self.index.update(kwdargs)

    def search(self, **params):
        self.logger.debug("search params=%s" % (str(params)))
        url = self.base_url % params

        data = self.fetch(url, filepath=None)
        data = data.decode("utf8")

        lines = data.split('\n')
        offset = 0
        while offset < len(lines):
            line = lines[offset].strip()
            # print(line)
            offset += 1
            if line.startswith('-'):
                break
        self.logger.debug("offset=%d" % (offset))

        results = []
        table = [lines[offset - 2]]

        for line in lines[offset:]:
            line = line.strip()
            # print(line)
            if (len(line) == 0) or line.startswith('#'):
                continue
            elts = line.split()
            if (len(elts) < 3):
                continue
            table.append(line)

            try:
                name = elts[self.index['name']]
                ra = elts[self.index['ra']]
                dec = elts[self.index['dec']]
                mag = float(elts[self.index['mag']])
                # print(name)

                if (self.format == 'deg') or not (':' in ra):
                    # Assume RA and DEC are in degrees
                    ra_deg = float(ra)
                    dec_deg = float(dec)
                else:
                    # Assume RA and DEC are in standard string notation
                    ra_deg = wcs.hmsStrToDeg(ra)
                    dec_deg = wcs.dmsStrToDeg(dec)

                # convert ra/dec via EQUINOX change if catalog EQUINOX is
                # not the same as our default one (2000)
                if self.equinox != 2000.0:
                    ra_deg, dec_deg = wcs.eqToEq2000(ra_deg, dec_deg,
                                                     self.equinox)

                ra_txt = wcs.ra_deg_to_str(ra_deg)
                dec_txt = wcs.dec_deg_to_str(dec_deg)
                self.logger.debug("STAR %s AT ra=%s dec=%s mag=%f" % (
                    name, ra_txt, dec_txt, mag))

                results.append(Star(name=name, ra_deg=ra_deg, dec_deg=dec_deg,
                                    ra=ra_txt, dec=dec_txt, mag=mag,
                                    preference=0.0, priority=0,
                                    description=''))

            except Exception as e:
                self.logger.error("Error parsing catalog query results: %s" % (
                    str(e)))

        # metadata about the list
        columns = [('Name', 'name'),
                   ('RA', 'ra'),
                   ('DEC', 'dec'),
                   ('Mag', 'mag'),
                   ('Preference', 'preference'),
                   ('Priority', 'priority'),
                   ('Description', 'description'),
                   ]
        info = Bunch.Bunch(columns=columns, color='Mag')

        return (results, info)


class ServerBank(object):

    def __init__(self, logger):
        self.logger = logger

        self.clear()

    def clear(self):
        self.imbank = {}
        self.ctbank = {}
        self.nmbank = {}

    def add_image_server(self, srvobj):
        self.imbank[srvobj.short_name] = srvobj

    def add_catalog_server(self, srvobj):
        self.ctbank[srvobj.short_name] = srvobj

    def add_name_server(self, srvobj):
        self.nmbank[srvobj.short_name] = srvobj

    def get_image_server(self, key):
        return self.imbank[key]

    def get_catalog_server(self, key):
        return self.ctbank[key]

    def get_name_server(self, key):
        return self.nmbank[key]

    def get_server_names(self, kind='image'):
        if kind == 'image':
            keys = self.imbank.keys()
        elif kind == 'name':
            keys = self.nmbank.keys()
        else:
            keys = self.ctbank.keys()
        keys = list(keys)
        keys.sort()
        return keys

    def get_image(self, key, filepath, **params):
        obj = self.imbank[key]

        return obj.search(filepath, **params)

    def get_catalog(self, key, filepath, **params):
        obj = self.ctbank[key]

        return obj.search(**params)

    # TO BE DEPRECATED
    addImageServer = add_image_server
    addCatalogServer = add_catalog_server
    getImageServer = get_image_server
    getCatalogServer = get_catalog_server
    getServerNames = get_server_names
    getImage = get_image
    getCatalog = get_catalog


# ---- SET UP DEFAULT SOURCES ----

if have_astroquery:
    # set up default name sources, catalog sources and image sources

    default_name_sources.extend([
        {'shortname': "SIMBAD", 'fullname': "SIMBAD",
         'type': 'astroquery.names'},
        {'shortname': "NED", 'fullname': "NED",
         'type': 'astroquery.names'},
    ])

    default_catalog_sources.extend([
        {'shortname': "GSC 2.3",
         'fullname': "Guide Star Catalog 2.3 Cone Search 1",
         'type': 'astroquery.vo_conesearch',
         'mapping': {'id': 'objID', 'ra': 'ra', 'dec': 'dec', 'mag': ['Mag']}},
        {'shortname': "USNO-A2.0 1",
         'fullname': "The USNO-A2.0 Catalogue 1",
         'type': 'astroquery.vo_conesearch',
         'mapping': {'id': 'USNO-A2.0', 'ra': 'RAJ2000', 'dec': 'DEJ2000',
                     'mag': ['Bmag', 'Rmag']}},
        {'shortname': "2MASS 1",
         'fullname': "Two Micron All Sky Survey (2MASS) 1",
         'type': 'astroquery.vo_conesearch',
         'mapping': {'id': 'htmID', 'ra': 'ra', 'dec': 'dec',
                     'mag': ['h_m', 'j_m', 'k_m']}},
    ])

    default_image_sources.extend([
        {'shortname': "DSS",
         'fullname': "Digital Sky Survey 1",
         'type': 'astroquery.image',
         'source': 'skyview'},
        {'shortname': "DSS1 Blue",
         'fullname': "Digital Sky Survey 1 Blue",
         'type': 'astroquery.image',
         'source': 'skyview'},
        {'shortname': "DSS1 Red",
         'fullname': "Digital Sky Survey 1 Red",
         'type': 'astroquery.image',
         'source': 'skyview'},
        {'shortname': "DSS2 Red",
         'fullname': "Digital Sky Survey 2 Red",
         'type': 'astroquery.image',
         'source': 'skyview'},
        {'shortname': "DSS2 Blue",
         'fullname': "Digital Sky Survey 2 Blue",
         'type': 'astroquery.image',
         'source': 'skyview'},
        {'shortname': "DSS2 IR",
         'fullname': "Digital Sky Survey 2 Infrared",
         'type': 'astroquery.image',
         'source': 'skyview'},
    ])
