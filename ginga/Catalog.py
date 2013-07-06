#
# Catalog.py -- DSS and star catalog interfaces for the Ginga fits viewer
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import re
import urllib
import urllib2

from ginga.misc import Bunch
from ginga import wcs


star_attrs = ('name', 'ra', 'dec', 'ra_deg', 'dec_deg', 'mag', 'preference',
              'priority', 'flag', 'b_r', 'dst', 'description')

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

        req = urllib2.Request(url)

        try:
            self.logger.info("Opening url=%s" % (url))
            try:
                response = urllib2.urlopen(req)

            except urllib2.HTTPError as e:
                self.logger.error("Server returned error code %s" % (e.code))
                raise e
            except urllib2.URLError as e:
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

        except Exception, e:
            self.logger.error("Error reading data from '%s': %s" % (
                url, str(e)))
            raise e

        if filepath:
            with open(filepath, 'wb') as out_f:
                out_f.write(data)
            return None

        else:
            return data


    def search(self, filepath, **params):

        ## values = urllib.urlencode(params)
        ## if self.reqtype == 'get':
        ##     url = self.base_url + '?' + values
        ##     req = urllib2.Request(url)
            
        ## elif self.reqtype == 'post':
        ##     url = self.base_url
        ##     req = urllib2.Request(self.base_url, values)

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

class Star(object):
    def __init__(self, **kwdargs):
        starInfo = {}
        starInfo.update(kwdargs)
        for attrname in star_attrs:
            starInfo[attrname] = kwdargs.get(attrname)
        self.starInfo = starInfo

    def __getitem__(self, key):
        return self.starInfo[key]
        
    def __contains__(self, key):
        return key in self.starInfo.keys()
        
    def __setitem__(self, key, value):
        self.starInfo[key] = value
        
    def has_key(self, key):
        return self.starInfo.has_key(key)
        
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
            print line
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

            except Exception, e:
                print str(e)
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
