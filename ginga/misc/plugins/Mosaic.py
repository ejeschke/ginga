#
# Mosaic.py -- Mosaic plugin for Ginga FITS viewer
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import math
import numpy
import os.path

from ginga import AstroImage
from ginga.util import wcs
from ginga import GingaPlugin
from ginga.misc import Widgets, CanvasTypes

class Mosaic(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(Mosaic, self).__init__(fv, fitsimage)

        # TODO: calculate this!
        self.fov_deg  = 0.92
        self.count = 0
        
        self.img_mosaic = None
        self.mosaic_chname = 'Mosaic'
        
        self.dc = self.fv.getDrawClasses()

        canvas = self.dc.DrawingCanvas()
        canvas.enable_draw(True)
        self.canvas = canvas
        self.layertag = 'mosaic-canvas'

        # Set preferences for destination channel
        prefs = self.fv.get_preferences()
        settings = prefs.createCategory('channel_%s' % (self.mosaic_chname))
        settings.setDefaults(genthumb=False, raisenew=False,
                             autocenter=True)

        #self.fv.add_callback('new-image', self.ingest_cb)

    def build_gui(self, container):
        sw = Widgets.ScrollArea()

        vbox1 = Widgets.VBox()
        vbox1.set_border_width(4)
        vbox1.set_spacing(2)

        self.msgFont = self.fv.getFont("sansFont", 12)
        tw = Widgets.TextArea(wrap=True, editable=False)
        tw.set_font(self.msgFont)
        self.tw = tw

        fr = Widgets.Frame("Instructions")
        fr.set_widget(tw)
        vbox1.add_widget(fr, stretch=0)
        
        fr = Widgets.Frame("Mosaic")

        captions = [('FOV (deg):', 'label', 'Fov', 'label'),
                    ('Set FOV:', 'label', 'Set FOV', 'entry'),
                    ('New Mosaic', 'button'),
                    ]
        w, b = Widgets.build_info(captions)
        self.w = b

        b.fov.set_text(str(self.fov_deg))
        b.set_fov.set_text(str(self.fov_deg))
        b.set_fov.add_callback('activated', self.set_fov_cb)
        b.new_mosaic.add_callback('activated', lambda w: self.new_mosaic_cb())

        fr.set_widget(w)
        vbox1.add_widget(fr, stretch=0)

        spacer = Widgets.Label('')
        vbox1.add_widget(spacer, stretch=1)
        
        btns = Widgets.HBox()
        btns.set_spacing(3)

        btn = Widgets.Button("Close")
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn, stretch=0)
        btns.add_widget(Widgets.Label(''), stretch=1)
        vbox1.add_widget(btns, stretch=0)

        sw.set_widget(vbox1)
        container.add_widget(sw, stretch=1)

    def create_blank_image(self, ra_deg, dec_deg, fov_deg, px_scale, rot_deg,
                           cdbase=[-1, 1]):

        self.logger.debug("ra=%9.3f dec=%8.2f fov=%.2f pscl=%.6f rot=%.3f" % (
                ra_deg, dec_deg, fov_deg, px_scale, rot_deg))

        # ra and dec in traditional format
        ra_txt = wcs.raDegToString(ra_deg, format='%02d:%02d:%06.3f')
        dec_txt = wcs.decDegToString(dec_deg, format='%s%02d:%02d:%05.2f')

        # Create a dummy sh image
        imagesize = int(round(fov_deg / px_scale))
        # round to even size
        if imagesize % 2 != 0:
            imagesize += 1
        width = height = imagesize
        self.logger.debug("created image size is %dx%d" % (width, height))
        data = numpy.zeros((height, width), dtype=numpy.float32)

        crpix = float(imagesize // 2)
        # TODO: this needs a more accurate WCS implementation
        # Image is reversed, seemingly
        header = {
            'SIMPLE': True,
            'BITPIX': -32,
            'EXTEND': True,
            'NAXIS': 2,
            'NAXIS1': imagesize,
            'NAXIS2': imagesize,
            'RA': ra_txt,
            'DEC': dec_txt,
            'EQUINOX': 2000.0,
            'OBJECT': 'MOSAIC',
            # these seem to be necessary at the moment because simple_wcs
            # is not adding them---fix this eventually
            'RADECSYS': 'FK5',
            # These only get copied if the rot_deg is 0
            'PC1_1': 1.0,
            'PC1_2': 0.0,
            'PC2_1': 0.0,
            'PC2_2': 1.0,
            'CUNIT1': 'deg',
            'CUNIT2': 'deg',
            'CTYPE1': 'RA---TAN',
            'CTYPE2': 'DEC--TAN',
            }

        # Add basic WCS keywords
        ## if rot_deg < 0.0:
        ##     rot_deg = 360.0 + math.fmod(rot_deg, 360.0)
        wcsobj = wcs.simple_wcs(crpix, crpix, ra_deg, dec_deg, px_scale,
                                rot_deg, cdbase=cdbase)
        wcshdr = wcsobj.to_header()
        header.update(wcshdr)

        # Create image container
        image = AstroImage.AstroImage(data, wcsclass=wcs.WCS,
                                      logger=self.logger)
        image.update_keywords(header)

        image.set(name='mosaic%d' % (self.count))
        self.count += 1
        return image

    def ingest_one(self, image):
        imname = image.get('name', 'image')
        imname, ext = os.path.splitext(imname)
        
        self.logger.info("Processing '%s' ..." % (imname))
        loc = self.img_mosaic.mosaic_inline([ image ])

        (xlo, ylo, xhi, yhi) = loc

        chinfo = self.fv.get_channelInfo(self.mosaic_chname)
        canvas = chinfo.fitsimage
        
        x, y = (xlo+xhi)//2, (ylo+yhi)//2
        self.canvas.add(self.dc.Text(x, y, imname, color='red'))
        print "text added at %d,%d" % (x, y)
        

    def prepare_mosaic(self, image):

        # Create Mosaic channel if it does not exist
        if not self.fv.has_channel(self.mosaic_chname):
            chinfo = self.fv.add_channel(self.mosaic_chname, num_images=1)
            self.canvas.setSurface(chinfo.fitsimage)
            chinfo.fitsimage.add(self.canvas, tag=self.layertag)
        else:
            chinfo = self.fv.get_channelInfo(self.mosaic_chname)

        header = image.get_header()
        ra_deg, dec_deg = header['CRVAL1'], header['CRVAL2']

        ((xrot, yrot), (cdelt1, cdelt2)) = wcs.get_rotation_and_scale(header)
        self.logger.debug("image0 xrot=%f yrot=%f cdelt1=%f cdelt2=%f" % (
            xrot, yrot, cdelt1, cdelt2))

        # TODO: handle differing pixel scale for each axis?
        px_scale = math.fabs(cdelt1)
        cdbase = [numpy.sign(cdelt1), numpy.sign(cdelt2)]
        rot_deg = yrot
        fov_deg = self.fov_deg

        self.canvas.deleteAllObjects()
        chinfo.fitsimage.onscreen_message("Creating blank image...")
        
        def _prepare_mosaic2():
            name = self.img_mosaic.get('name', 'mosaic')
            self.fv.add_image(name, self.img_mosaic, self.mosaic_chname)
            chinfo.fitsimage.onscreen_message(None)
            self.ingest_one(image)

        def _prepare_mosaic1():
            self.img_mosaic = self.create_blank_image(ra_deg, dec_deg,
                                                      fov_deg, px_scale,
                                                      rot_deg, cdbase=cdbase)
        
            header = self.img_mosaic.get_header()
            ((xrot, yrot),
             (cdelt1, cdelt2)) = wcs.get_rotation_and_scale(header)
            self.logger.debug("mosaic xrot=%f yrot=%f cdelt1=%f cdelt2=%f" % (
                xrot, yrot, cdelt1, cdelt2))

            self.fv.gui_do(_prepare_mosaic2)

        self.fv.nongui_do(_prepare_mosaic1)
        
        
    def close(self):
        chname = self.fv.get_channelName(self.fitsimage)
        self.fv.stop_local_plugin(chname, str(self))
        return True
        
    def instructions(self):
        self.tw.set_text("""TBD.""")
            
    def start(self):
        self.instructions()
        # insert layer if it is not already
        try:
            obj = self.fitsimage.getObjectByTag(self.layertag)

        except KeyError:
            # Add canvas layer
            self.fitsimage.add(self.canvas, tag=self.layertag)

    def stop(self):
        try:
            self.fitsimage.deleteObjectByTag(self.layertag)
        except:
            pass
        self.fv.showStatus("")

    def redo(self):
        image = self.fitsimage.get_image()

        if self.img_mosaic == None:
            self.prepare_mosaic(image)
        else:
            self.ingest_one(image)

    def new_mosaic_cb(self):
        self.img_mosaic = None
        
    def set_fov_cb(self, w):
        self.fov_deg = float(w.get_text())
        self.w.fov.set_text(str(self.fov_deg))
        
    def __str__(self):
        return 'mosaic'
    
#END
