#! /usr/bin/env python
#
# example2_tk.py -- Simple, configurable FITS viewer.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import sys

from ginga.tkw.ImageViewTk import CanvasView
from ginga.misc import log
from ginga.canvas.CanvasObject import get_canvas_types
from ginga.util.loader import load_data

import tkinter as Tkinter
from tkinter.filedialog import askopenfilename

STD_FORMAT = '%(asctime)s | %(levelname)1.1s | %(filename)s:%(lineno)d (%(funcName)s) | %(message)s'


class FitsViewer(object):

    def __init__(self, logger):

        self.logger = logger
        self.drawcolors = ['white', 'black', 'red', 'yellow', 'blue', 'green']
        self.dc = get_canvas_types()

        root = Tkinter.Tk()
        root.title("ImageViewTk Example")
        #root.set_border_width(2)
        #root.connect("delete_event", lambda w, e: self.quit(w))
        self.root = root

        #self.select = FileSelection.FileSelection()

        vbox = Tkinter.Frame(root, relief=Tkinter.RAISED, borderwidth=1)
        vbox.pack(side=Tkinter.TOP, fill=Tkinter.BOTH, expand=1)

        canvas = Tkinter.Canvas(vbox, bg="grey", height=512, width=512)
        canvas.pack(side=Tkinter.TOP, fill=Tkinter.BOTH, expand=1)

        fi = CanvasView(logger)
        fi.set_widget(canvas)
        #fi.set_redraw_lag(0.0)
        fi.enable_autocuts('on')
        fi.set_autocut_params('zscale')
        fi.enable_autozoom('on')
        # tk seems to not take focus with a click
        fi.set_enter_focus(True)
        fi.set_callback('cursor-changed', self.cursor_cb)
        fi.set_bg(0.2, 0.2, 0.2)
        fi.ui_set_active(True)
        fi.show_pan_mark(True)
        fi.show_mode_indicator(True, corner='ur')
        self.fitsimage = fi

        bd = fi.get_bindings()
        bd.enable_all(True)

        # canvas that we will draw on
        canvas = self.dc.DrawingCanvas()
        canvas.enable_draw(True)
        #canvas.enable_edit(True)
        canvas.set_drawtype('rectangle', color='blue')
        self.canvas = canvas
        # add canvas to view
        fi.get_canvas().add(canvas)
        canvas.register_for_cursor_drawing(fi)
        canvas.set_draw_mode('draw')
        canvas.ui_set_active(True)

        fi.configure(512, 512)
        # add little mode indicator that shows keyboard modal states
        fi.show_mode_indicator(True, corner='ur')

        hbox = Tkinter.Frame(root)
        hbox.pack(side=Tkinter.BOTTOM, fill=Tkinter.X, expand=0)

        self.readout = Tkinter.Label(root, text='')
        self.readout.pack(side=Tkinter.BOTTOM, fill=Tkinter.X, expand=0)

        self.drawtypes = self.canvas.get_drawtypes()
        ## wdrawtype = ttk.Combobox(root, values=self.drawtypes,
        ##                          command=self.set_drawparams)
        ## index = self.drawtypes.index('ruler')
        ## wdrawtype.current(index)
        wdrawtype = Tkinter.Entry(hbox, width=12)
        wdrawtype.insert(0, 'rectangle')
        wdrawtype.bind("<Return>", self.set_drawparams)
        self.wdrawtype = wdrawtype

        # wdrawcolor = ttk.Combobox(root, values=self.drawcolors,
        #                           command=self.set_drawparams)
        # index = self.drawcolors.index('blue')
        # wdrawcolor.current(index)
        wdrawcolor = Tkinter.Entry(hbox, width=12)
        wdrawcolor.insert(0, 'blue')
        wdrawcolor.bind("<Return>", self.set_drawparams)
        self.wdrawcolor = wdrawcolor

        self.vfill = Tkinter.IntVar()
        wfill = Tkinter.Checkbutton(hbox, text="Fill", variable=self.vfill)
        self.wfill = wfill

        walpha = Tkinter.Entry(hbox, width=12)
        walpha.insert(0, '1.0')
        walpha.bind("<Return>", self.set_drawparams)
        self.walpha = walpha

        wclear = Tkinter.Button(hbox, text="Clear Canvas",
                                command=self.clear_canvas)
        wopen = Tkinter.Button(hbox, text="Open File",
                               command=self.open_file)
        wquit = Tkinter.Button(hbox, text="Quit",
                               command=lambda: self.quit(root))
        for w in (wquit, wclear, walpha, Tkinter.Label(hbox, text='Alpha:'),
                  wfill, wdrawcolor, wdrawtype, wopen):
            w.pack(side=Tkinter.RIGHT)

    def get_widget(self):
        return self.root

    def set_drawparams(self, evt):
        kind = self.wdrawtype.get()
        color = self.wdrawcolor.get()
        alpha = float(self.walpha.get())
        fill = self.vfill.get() != 0

        params = {'color': color,
                  'alpha': alpha,
                  #'cap': 'ball',
                  }
        if kind in ('circle', 'rectangle', 'polygon', 'triangle',
                    'righttriangle', 'ellipse', 'square', 'box'):
            params['fill'] = fill
            params['fillalpha'] = alpha

        self.canvas.set_drawtype(kind, **params)

    def clear_canvas(self):
        self.canvas.delete_all_objects()

    def load_file(self, filepath):
        image = load_data(filepath, logger=self.logger)
        self.fitsimage.set_image(image)
        self.root.title(filepath)

    def open_file(self):
        filename = askopenfilename(filetypes=[("allfiles", "*"),
                                              ("fitsfiles", "*.fits")])
        self.load_file(filename)

    def cursor_cb(self, viewer, button, data_x, data_y):
        """This gets called when the data position relative to the cursor
        changes.
        """
        # Get the value under the data coordinates
        try:
            # We report the value across the pixel, even though the coords
            # change halfway across the pixel
            value = viewer.get_data(int(data_x + viewer.data_off),
                                    int(data_y + viewer.data_off))

        except Exception:
            value = None

        fits_x, fits_y = data_x + 1, data_y + 1

        # Calculate WCS RA
        try:
            # NOTE: image function operates on DATA space coords
            image = viewer.get_image()
            if image is None:
                # No image loaded
                return
            ra_txt, dec_txt = image.pixtoradec(fits_x, fits_y,
                                               format='str', coords='fits')
        except Exception as e:
            self.logger.warning("Bad coordinate conversion: %s" % (
                str(e)))
            ra_txt = 'BAD WCS'
            dec_txt = 'BAD WCS'

        text = "RA: %s  DEC: %s  X: %.2f  Y: %.2f  Value: %s" % (
            ra_txt, dec_txt, fits_x, fits_y, value)
        self.readout.config(text=text)

    def quit(self, root):
        root.destroy()
        return True


def main(options, args):

    logger = log.get_logger("example2", options=options)

    fv = FitsViewer(logger)
    top = fv.get_widget()

    if len(args) > 0:
        fv.load_file(args[0])

    top.mainloop()


if __name__ == "__main__":

    # Parse command line options
    from argparse import ArgumentParser

    argprs = ArgumentParser()

    argprs.add_argument("--debug", dest="debug", default=False,
                        action="store_true",
                        help="Enter the pdb debugger on main()")
    argprs.add_argument("--profile", dest="profile", action="store_true",
                        default=False,
                        help="Run the profiler on main()")
    log.addlogopts(argprs)

    (options, args) = argprs.parse_known_args(sys.argv[1:])

    # Are we debugging this?
    if options.debug:
        import pdb

        pdb.run('main(options, args)')

    # Are we profiling this?
    elif options.profile:
        import profile

        print("%s profile:" % sys.argv[0])
        profile.run('main(options, args)')

    else:
        main(options, args)

# END
