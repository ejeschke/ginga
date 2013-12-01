#
# gtksel.py -- select version of Gtk to use
# 
# Eric Jeschke (eric@naoj.org)
#

import ginga.toolkit

toolkit = ginga.toolkit.toolkit

have_gtk3 = False
have_gtk2 = False

# For now, Gtk 2 has preference
if toolkit in ('gtk2', 'choose'):
    try:
        import pygtk
        pygtk.require('2.0')
        have_gtk2 = True
    
    except ImportError:
        pass
    
if toolkit in ('gtk3', 'choose') and (not have_gtk2):
    try:
        # Try to import Gtk 2->3 compatibility layer
        from gi import pygtkcompat
        from gi.repository import GdkPixbuf

        pygtkcompat.enable() 
        pygtkcompat.enable_gtk(version='3.0')

        have_gtk3 = True

    except ImportError:
        pass

import gtk
import gobject

if have_gtk3:
    # TEMP: until this is fixed or some other acceptable workaround
    #   there is no good way to run on Gtk3
    raise Exception("Cairo.ImageSurface.create_for_data is not yet implemented in Gtk3")
    ginga.toolkit.use('gtk3')


    def pixbuf_new_from_xpm_data(xpm_data):
        xpm_data = bytes('\n'.join(xpm_data))
        return GdkPixbuf.Pixbuf.new_from_xpm_data(xpm_data)

    def pixbuf_new_from_array(data, rgbtype, bpp):
        # Seems Gtk3 Pixbufs do not have the new_from_array() method!
        #return GdkPixbuf.Pixbuf.new_from_array(data, rgbtype, bpp)
        daht, dawd, depth = data.shape
        stride = dawd * 4 * bpp
        rgb_buf = data.tostring(order='C')
        hasAlpha = False
        rgbtype = GdkPixbuf.Colorspace.RGB
        return GdkPixbuf.Pixbuf.new_from_data(rgb_buf, rgbtype, hasAlpha, 8,
                                              dawd, daht, stride, None, None)

    def pixbuf_new_from_data(rgb_buf, rgbtype, hasAlpha, bpp, dawd, daht, stride):
        return GdkPixbuf.Pixbuf.new_from_data(rgb_buf, rgbtype, hasAlpha, bpp,
                                              dawd, daht, stride, None, None)

    def pixbuf_new_from_file_at_size(foldericon, width, height):
        return GdkPixbuf.Pixbuf.new_from_file_at_size(foldericon,
                                                      width, height)

    def make_cursor(widget, iconpath, x, y):
        image = gtk.Image()
        image.set_from_file(iconpath)
        pixbuf = image.get_pixbuf()
        screen = widget.get_screen()
        display = screen.get_display()
        return gtk.gdk.Cursor(display, pixbuf, x, y)

elif have_gtk2:
    ginga.toolkit.use('gtk2')

    def pixbuf_new_from_xpm_data(xpm_data):
        return gtk.gdk.pixbuf_new_from_xpm_data(xpm_data)


    def pixbuf_new_from_array(data, rgbtype, bpp):
        return gtk.gdk.pixbuf_new_from_array(data, rgbtype, bpp)

    def pixbuf_new_from_data(rgb_buf, rgbtype, hasAlpha, bpp, dawd, daht, stride):
        return gtk.gdk.pixbuf_new_from_data(rgb_buf, rgbtype, hasAlpha, bpp,
                                            dawd, daht, stride)

    def pixbuf_new_from_file_at_size(foldericon, width, height):
        return gtk.gdk.pixbuf_new_from_file_at_size(foldericon,
                                                    width, height)

    def make_cursor(widget, iconpath, x, y):
        pixbuf = gtk.gdk.pixbuf_new_from_file(iconpath)
        screen = widget.get_screen()
        display = screen.get_display()
        return gtk.gdk.Cursor(display, pixbuf, x, y)

else:
    raise ImportError("Failed to import gtk. There may be an issue with the toolkit module or it is not installed")

#END
