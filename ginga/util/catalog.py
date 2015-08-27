#
# catalog.py -- DSS and star catalog interfaces for the Ginga fits viewer
#
# Eric Jeschke (eric@naoj.org)
# Raymond Plante -- pyvo interfaces
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from __future__ import print_function
import os.path
import tempfile
import re
import urllib
import ginga.util.six as six
if six.PY2:
    from urllib2 import Request, urlopen, URLError, HTTPError
else:
    # python3
    from urllib.request import Request, urlopen
    from urllib.error import URLError, HTTPError
import time

from ginga.misc import Bunch
from ginga.util import wcs


## star_attrs = ('name', 'ra', 'dec', 'ra_deg', 'dec_deg', 'mag', 'preference',
##               'priority', 'flag', 'b_r', 'dst', 'description')


# Do we have astropy.vo installed?
have_astropy = False
try:
    from astropy.vo.client import conesearch
    from astropy import coordinates, units
    have_astropy = True

except ImportError:
    pass

# How about pyvo?
have_pyvo = False
try:
    import pyvo
    have_pyvo = True

except ImportError:
    pass


class Star(object):
    def __init__(self, **kwdargs):
        starInfo = {}
        starInfo.update(kwdargs)
        ## for attrname in star_attrs:
        ##     starInfo[attrname] = kwdargs.get(attrname)
        self.starInfo = starInfo

    def __getitem__(self, key):
        return self.starInfo[key]

    def __contains__(self, key):
        return key in self.starInfo.keys()

    def __setitem__(self, key, value):
        self.starInfo[key] = value

    def has_key(self, key):
        return key in self.starInfo


class AstroPyCatalogServer(object):

    def __init__(self, logger, full_name, key, url, description):
        self.logger = logger
        self.full_name = full_name
        self.short_name = key
        self.description = description
        self.kind = 'astropy.vo-catalog'
        self.url = url

        # For compatibility with URL catalog servers
        self.params = {}
        count = 0
        for label, key in (('RA', 'ra'), ('DEC', 'dec'), ('Radius', 'r')):
            self.params[key] = Bunch.Bunch(name=key, convert=str,
                                           label=label, order=count)
            count += 1

    def getParams(self):
        return self.params

    def toStar(self, data, ext, magfield):
        try:
            mag = float(data[magfield])
        except:
            mag = 0.0

        # Make sure we have at least these Ginga standard fields defined
        d = { 'name':         data[ext['id']],
              'ra_deg':       float(data[ext['ra']]),
              'dec_deg':      float(data[ext['dec']]),
              'mag':          mag,
              'preference':   0.0,
              'priority':     0,
              'description':  'fake magnitude' }
        data.update(d)
        data['ra'] = wcs.raDegToString(data['ra_deg'])
        data['dec'] = wcs.decDegToString(data['dec_deg'])
        return Star(**data)

    def search(self, **params):
        """For compatibility with generic star catalog search.
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
        #radius_deg = float(params['r'])

        # Note requires astropy 3.x+
        c = coordinates.SkyCoord(ra_deg * units.degree,
                                 dec_deg * units.degree,
                                 frame='icrs')
        self.logger.info("Querying catalog: %s" % (self.full_name))
        time_start = time.time()
        results = conesearch.conesearch(c, radius_deg * units.degree,
                                        catalog_db=self.full_name)
        time_elapsed = time.time() - time_start

        numsources = results.array.size
        self.logger.info("Found %d sources in %.2f sec" % (
            numsources, time_elapsed))

        # Scan the returned fields to find ones we need to extract
        # particulars from (ra, dec, id, magnitude)
        mags = []
        ext = {}
        fields = results.array.dtype.names
        for name in fields:
            ucd = results.get_field_by_id(name).ucd
            ucd = str(ucd).lower()
            if ucd == 'id_main':
                ext['id'] = name
            elif ucd == 'pos_eq_ra_main':
                ext['ra'] = name
            elif ucd == 'pos_eq_dec_main':
                ext['dec'] = name
            if ('phot_' in ucd) or ('phot.' in ucd):
                mags.append(name)
        self.logger.debug("possible magnitude fields: %s" % str(mags))
        if len(mags) > 0:
            magfield = mags[0]
        else:
            magfield = None

        # prepare the result list
        starlist = []
        arr = results.array
        for i in range(numsources):
            source = dict(zip(fields, arr[i]))
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
        # TODO: what if not all sources have same record structure?
        # is this possible with VO?
        cols = list(fields)
        cols.remove(ext['ra'])
        cols.remove(ext['dec'])
        cols.remove(ext['id'])
        columns.extend(zip(cols, cols))

        # which column is the likely one to color source circles
        colorCode = 'Mag'

        info = Bunch.Bunch(columns=columns, color=colorCode)
        return starlist, info


class AstroQueryImageServer(object):

    def __init__(self, logger, full_name, key, querymod, description):
        self.logger = logger
        self.full_name = full_name
        self.short_name = key
        self.description = description
        self.kind = 'astroquery-image'
        self.querymod = querymod

        # For compatibility with other Ginga catalog servers
        self.params = {}
        count = 0
        for label, key in (('RA', 'ra'), ('DEC', 'dec'),
                          ('Width', 'width'), ('Height', 'height')):
            self.params[key] = Bunch.Bunch(name=key, convert=str,
                                           label=label, order=count)
            count += 1

    def getParams(self):
        return self.params

    def search(self, dstpath, **params):
        """For compatibility with generic image catalog search.

        TODO: dstpath provides the pathname for storing the image
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
        self.logger.info("Querying catalog: %s" % (self.full_name))
        time_start = time.time()
        results = self.querymod.get_image_list(c,
                                               image_width=wd_deg * units.degree,
                                               image_height=ht_deg * units.degree)
        time_elapsed = time.time() - time_start

        if len(results) > 0:
            self.logger.info("Found %d images" % len(results))
        else:
            self.logger.warn("Found no images in this area" % len(results))
            return None

        # For now, we pick the first one found
        url = results[0]
        #fitspath = results[0].make_dataset_filename(dir="/tmp")

        # TODO: download file
        fitspath = url

        # explicit return
        return fitspath


class PyVOCatalogServer(object):

    def __init__(self, logger, full_name, key, url, description):
        self.logger = logger
        self.full_name = full_name
        self.short_name = key
        self.description = description
        self.kind = 'pyvo-catalog'
        self.url = url

        # For compatibility with URL catalog servers
        self.params = {}
        count = 0
        for label, key in (('RA', 'ra'), ('DEC', 'dec'), ('Radius', 'r')):
            self.params[key] = Bunch.Bunch(name=key, convert=str,
                                           label=label, order=count)
            count += 1

    def getParams(self):
        return self.params

    def toStar(self, data, ext, magfield):
        try:
            mag = float(data[magfield])
        except:
            mag = 0.0

        # Make sure we have at least these Ginga standard fields defined
        d = { 'name':         data[ext['id']],
              'ra_deg':       float(data[ext['ra']]),
              'dec_deg':      float(data[ext['dec']]),
              'mag':          mag,
              'preference':   0.0,
              'priority':     0,
              'description':  'fake magnitude' }
        data.update(d)
        data['ra'] = wcs.raDegToString(data['ra_deg'])
        data['dec'] = wcs.decDegToString(data['dec_deg'])
        return Star(**data)

    def search(self, **params):
        """For compatibility with generic star catalog search.
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
        #radius_deg = float(params['r'])

        # initialize our query object with the service's base URL
        query = pyvo.scs.SCSQuery(self.url)
        query.ra = ra_deg
        query.dec = dec_deg
        query.radius = radius_deg
        self.logger.info("Will query: %s" % query.getqueryurl(True))

        time_start = time.time()
        results = query.execute()
        time_elapsed = time.time() - time_start

        numsources = len(results)
        self.logger.info("Found %d sources in %.2f sec" % (
            numsources, time_elapsed))

        # Scan the returned fields to find ones we need to extract
        # particulars from (ra, dec, id, magnitude)
        mags = []
        ext = {}
        fields = results.fielddesc()
        for field in fields:
            ucd = str(field.ucd).lower()
            if ucd == 'id_main':
                ext['id'] = field.name
            elif ucd == 'pos_eq_ra_main':
                ext['ra'] = field.name
            elif ucd == 'pos_eq_dec_main':
                ext['dec'] = field.name
            if ('phot_' in ucd) or ('phot.' in ucd):
                mags.append(field.name)
        self.logger.debug("possible magnitude fields: %s" % str(mags))
        if len(mags) > 0:
            magfield = mags[0]
        else:
            magfield = None

        self.logger.info("Found %d sources" % len(results))

        starlist = []
        for source in results:
            data = dict(source.items())
            starlist.append(self.toStar(data, ext, magfield))

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
        cols = list(source.keys())
        cols.remove(ext['ra'])
        cols.remove(ext['dec'])
        cols.remove(ext['id'])
        columns.extend(zip(cols, cols))

        # which column is the likely one to color source circles
        colorCode = 'Mag'

        info = Bunch.Bunch(columns=columns, color=colorCode)
        return starlist, info

    def get_catalogs(self):
        return conesearch.list_catalogs()

class PyVOImageServer(object):

    def __init__(self, logger, full_name, key, url, description):
        self.logger = logger
        self.full_name = full_name
        self.short_name = key
        self.description = description
        self.kind = 'pyvo-image'
        self.url = url

        # For compatibility with other Ginga catalog servers
        self.params = {}
        count = 0
        for label, key in (('RA', 'ra'), ('DEC', 'dec'),
                          ('Width', 'width'), ('Height', 'height')):
            self.params[key] = Bunch.Bunch(name=key, convert=str,
                                           label=label, order=count)
            count += 1

    def getParams(self):
        return self.params

    def search(self, dstpath, **params):
        """For compatibility with generic image catalog search.

        TODO: dstpath provides the pathname for storing the image
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
        ## wd_deg = float(params['width'])
        ## ht_deg = float(params['height'])

        # initialize our query object with the service's base URL
        query = pyvo.sia.SIAQuery(self.url)
        query.ra = ra_deg
        query.dec = dec_deg
        query.size = (wd_deg, ht_deg)
        query.format = 'image/fits'
        self.logger.info("Will query: %s" % query.getqueryurl(True))

        results = query.execute()
        if len(results) > 0:
            self.logger.info("Found %d images" % len(results))
        else:
            self.logger.warn("Found no images in this area" % len(results))
            return None

        # For now, we pick the first one found

        # REQUIRES FIX IN PYVO:
        # imfile = results[0].cachedataset(dir="/tmp")
        #
        # Workaround:
        fitspath = results[0].make_dataset_filename(dir="/tmp")
        results[0].cachedataset(fitspath)

        # explicit return
        return fitspath


class URLServer(object):

    def __init__(self, logger, full_name, key, url, description):
        self.logger = logger
        self.kind = 'url'
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
                response = urlopen(req)

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
            info = response.info()

            self.logger.debug("getting data")
            data = response.read()
            self.logger.debug("fetched %d bytes" % (len(data)))
            #data = data.decode('ascii')

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
                localpath, info = urllib.urlretrieve(url, filepath,
                                                            cb_fn)
            else:
                localpath, info = urllib.urlretrieve(url, filepath)

        except urllib.ContentTooShortError as e:
            self.logger.error("Content doesn't match length")
            raise e
        except Exception as e:
            self.logger.error("URL fetch failure: %s" % (str(e)))
            raise e

        if ofilepath is not None:
            return localpath

        with open(filepath, 'r') as in_f:
            return in_f.read()


    def search(self, filepath, **params):

        ## values = urllib.urlencode(params)
        ## if self.reqtype == 'get':
        ##     url = self.base_url + '?' + values
        ##     req = Request(url)

        ## elif self.reqtype == 'post':
        ##     url = self.base_url
        ##     req = Request(self.base_url, values)

        ## else:
        ##     raise Exception("Don't know how to handle a request of type '%s'" % (
        ##         self.reqtype))

        url = self.base_url % params

        self.fetch(url, filepath=filepath)
        return filepath


class ImageServer(URLServer):

    def __init__(self, logger, full_name, key, url, description):
        super(ImageServer, self).__init__(logger, full_name, key, url,
                                          description)
        self.kind = 'image'


class CatalogServer(URLServer):

    def __init__(self, logger, full_name, key, url, description):
        super(CatalogServer, self).__init__(logger, full_name, key, url,
                                            description)
        self.kind = 'catalog'
        self.index = { 'name': 0, 'ra': 1, 'dec': 2, 'mag': 10 }
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
            print(line)
            offset += 1
            if line.startswith('-'):
                break
        self.logger.debug("offset=%d" % (offset))

        results = []
        table = [lines[offset-2]]

        for line in lines[offset:]:
            line = line.strip()
            #print ">>>", line
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
                #print name

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
                if cmp(self.equinox, 2000.0) != 0:
                    ra_deg, dec_deg = wcs.eqToEq2000(ra_deg, dec_deg,
                                                     self.equinox)

                ra_txt = wcs.raDegToString(ra_deg, format='%02d:%02d:%06.3f')
                dec_txt = wcs.decDegToString(dec_deg,
                                               format='%s%02d:%02d:%05.2f')
                self.logger.debug("STAR %s AT ra=%s dec=%s mag=%f" % (
                    name, ra_txt, dec_txt, mag))

                results.append(Star(name=name, ra_deg=ra_deg, dec_deg=dec_deg,
                                    ra=ra_txt, dec=dec_txt, mag=mag,
                                    preference=0.0, priority=0,
                                    description=''))

            except Exception as e:
                print(str(e))
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
        self.imbank = {}
        self.ctbank = {}

    def addImageServer(self, srvobj):
        self.imbank[srvobj.short_name] = srvobj

    def addCatalogServer(self, srvobj):
        self.ctbank[srvobj.short_name] = srvobj

    def getImageServer(self, key):
        return self.imbank[key]

    def getCatalogServer(self, key):
        return self.ctbank[key]

    def getServerNames(self, kind='image'):
        if kind == 'image':
            keys = self.imbank.keys()
        else:
            keys = self.ctbank.keys()
        keys = list(keys)
        keys.sort()
        return keys

    def getImage(self, key, filepath, **params):
        obj = self.imbank[key]

        return obj.search(filepath, **params)

    def getCatalog(self, key, filepath, **params):
        obj = self.ctbank[key]

        return obj.search(**params)


# END
