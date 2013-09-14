#
# gtksel.py -- select version of Gtk to use
# 
# Eric Jeschke (eric@naoj.org)
#
# try:
#     # Try to import Gtk 2->3 compatibility layer
#     from gi import pygtkcompat
#     from gi.repository import GdkPixbuf
#     have_gtk3 = True
    
# except ImportError:
#     have_gtk3 = False

# For now, Gtk 2 has preference
have_gtk3 = False
try:
    import pygtk
    pygtk.require('2.0')
    
except ImportError:
    # Try to import Gtk 2->3 compatibility layer
    from gi import pygtkcompat
    from gi.repository import GdkPixbuf
    have_gtk3 = True

if have_gtk3:
    pygtkcompat.enable() 
    pygtkcompat.enable_gtk(version='3.0')

import gtk
import gobject


def pixbuf_new_from_xpm_data(xpm_data):
    if have_gtk3:
        xpm_data = bytes('\n'.join(xpm_data))
        return GdkPixbuf.Pixbuf.new_from_xpm_data(xpm_data)
    else:
        return gtk.gdk.pixbuf_new_from_xpm_data(xpm_data)
        

def pixbuf_new_from_array(data, rgbtype, bpp):
    if have_gtk3:
        return GdkPixbuf.Pixbuf.new_from_array(data, rgbtype, bpp)
    else:
        return gtk.gdk.pixbuf_new_from_array(data, rgbtype, bpp)
    
def pixbuf_new_from_data(rgb_buf, rgbtype, hasAlpha, bpp, dawd, daht, stride):
    if have_gtk3:
        return GdkPixbuf.Pixbuf.new_from_data(rgb_buf, rgbtype, hasAlpha, bpp,
                                       dawd, daht, stride, None, None)
    else:
        return gtk.gdk.pixbuf_new_from_data(rgb_buf, rgbtype, hasAlpha, bpp,
                                            dawd, daht, stride)

def pixbuf_new_from_file_at_size(foldericon, width, height):
    if have_gtk3:
        return GdkPixbuf.Pixbuf.new_from_file_at_size(foldericon,
                                                      width, height)
    else:
        return gtk.gdk.pixbuf_new_from_file_at_size(foldericon,
                                                    width, height)
        
def make_cursor(widget, iconpath, x, y):
    if have_gtk3:
        image = gtk.Image()
        image.set_from_file(iconpath)
        pixbuf = image.get_pixbuf()
    else:
        pixbuf = gtk.gdk.pixbuf_new_from_file(iconpath)
        
    screen = widget.get_screen()
    display = screen.get_display()
    return gtk.gdk.Cursor(display, pixbuf, x, y)

