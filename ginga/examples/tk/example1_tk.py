#! /usr/bin/env python
#
# example1_tk.py -- Simple, configurable FITS viewer.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import sys, os
import logging

import ginga.util.six as six
if six.PY2:
    import Tkinter
    from tkFileDialog import askopenfilename
else:
    import tkinter as Tkinter
    from tkinter.filedialog import askopenfilename
from ginga.tkw.ImageViewTk import ImageViewCanvas
from ginga import AstroImage


STD_FORMAT = '%(asctime)s | %(levelname)1.1s | %(filename)s:%(lineno)d (%(funcName)s) | %(message)s'

class FitsViewer(object):

    def __init__(self, logger):

        self.logger = logger
        root = Tkinter.Tk()
        root.title("ImageViewTk Example")
        self.root = root

        vbox = Tkinter.Frame(root, relief=Tkinter.RAISED, borderwidth=1)
        vbox.pack(side=Tkinter.TOP, fill=Tkinter.BOTH, expand=1)

        canvas = Tkinter.Canvas(vbox, bg="grey", height=512, width=512)
        canvas.pack(side=Tkinter.TOP, fill=Tkinter.BOTH, expand=1)

        fi = ImageViewCanvas(logger)
        fi.set_widget(canvas)
        fi.enable_autocuts('on')
        fi.set_autocut_params('zscale')
        fi.enable_autozoom('on')
        fi.set_bg(0.2, 0.2, 0.2)
        fi.ui_setActive(True)
        fi.show_pan_mark(True)
        self.fitsimage = fi

        bd = fi.get_bindings()
        bd.enable_pan(True)
        bd.enable_zoom(True)
        bd.enable_cuts(True)
        bd.enable_flip(True)
        bd.enable_cmap(True)
        bd.enable_rotate(True)

        fi.configure(512, 512)

        hbox = Tkinter.Frame(root)
        hbox.pack(side=Tkinter.BOTTOM, fill=Tkinter.X, expand=0)

        wopen = Tkinter.Button(hbox, text="Open File",
                               command=self.open_file)
        wquit = Tkinter.Button(hbox, text="Quit",
                               command=lambda: self.quit(root))
        for w in (wquit, wopen):
            w.pack(side=Tkinter.RIGHT)


    def get_widget(self):
        return self.root

    def load_file(self, filepath):
        image = AstroImage.AstroImage(logger=self.logger)
        image.load_file(filepath)
        self.fitsimage.set_image(image)
        self.root.title(filepath)

    def open_file(self):
        filename = askopenfilename(filetypes=[("allfiles","*"),
                                              ("fitsfiles","*.fits")])
        self.load_file(filename)

    def quit(self, root):
        root.destroy()
        return True


def main(options, args):

    logger = logging.getLogger("example1")
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter(STD_FORMAT)
    stderrHdlr = logging.StreamHandler()
    stderrHdlr.setFormatter(fmt)
    logger.addHandler(stderrHdlr)

    fv = FitsViewer(logger)
    top = fv.get_widget()

    if len(args) > 0:
        fv.load_file(args[0])

    top.mainloop()


if __name__ == '__main__':
    main(None, sys.argv[1:])

# END
