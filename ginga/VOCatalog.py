#
# VOCatalog.py -- VO image and catalog interfaces for the Ginga fits viewer
#
# Raymond Plante
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke, et. al.   All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga import Catalog, wcs
from ginga.misc import Bunch

import pyvo


class CatalogServer(object):

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

    def toStar(self, sourcerec, magfield):
        data = {}
        data.update(dict(sourcerec.items()))
        try:
            mag = float(sourcerec[magfield])
        except:
            mag = 0.0
            
        # Make sure we have at least these Ginga standard fields defined
        d = { 'name':         sourcerec.id,
              'ra_deg':       float(sourcerec.ra),
              'dec_deg':      float(sourcerec.dec),
              'mag':          mag,
              'preference':   0.0,
              'priority':     0,
              'description':  'fake magnitude' }
        data.update(d)
        data['ra'] = wcs.raDegToString(data['ra_deg'])
        data['dec'] = wcs.decDegToString(data['dec_deg'])
        return Catalog.Star(**data)

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

        results = query.execute()

        # Scan the returned fields for ones that have a UCD containing 'phot'
        mags = []
        fields = results.fielddesc()
        for field in fields:
            ucd = str(field.ucd).lower()
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
            starlist.append(self.toStar(source, magfield))

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
        cols = list(source.keys())
        cols.remove('RA')
        cols.remove('DEC')
        cols.remove('id')
        columns.extend(zip(cols, cols))

        # which column is the likely one to color source circles
        colorCode = 'Mag'
        
        info = Bunch.Bunch(columns=columns, color=colorCode)
        return starlist, info


class ImageServer(object):

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
    
#END
