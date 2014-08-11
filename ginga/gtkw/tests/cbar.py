import sys
import gtk

from ginga.gtkw import ColorBar
from ginga import cmap, imap
import logging

if __name__ == "__main__":
    logger = logging.getLogger('cbar')

    root = gtk.Window(gtk.WINDOW_TOPLEVEL)
    root.set_size_request(400, 150)
    w = ColorBar.ColorBar(logger)
    w.set_cmap(cmap.get_cmap('rainbow'))
    w.set_imap(imap.get_imap('ramp'))
    root.add(w)
    root.show_all()

    gtk.main()
