#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import gtk
# TODO: this code should be shared with integgui and maybe others

class FileSelection(object):
    
    # Get the selected filename
    def file_ok_sel(self, w, rsp):
        self.close(w)
        if rsp == 0:
            return
        
        filepath = self.filew.get_filename()
        self.callfn(filepath)

    def __init__(self, action=gtk.FILE_CHOOSER_ACTION_OPEN):
        # Create a new file selection widget
        self.filew = gtk.FileChooserDialog(title="Select a file",
                                           action=action)
        self.filew.connect("destroy", self.close)
        if action == gtk.FILE_CHOOSER_ACTION_SAVE:
            self.filew.add_buttons(gtk.STOCK_SAVE, 1, gtk.STOCK_CANCEL, 0)
        else:
            self.filew.add_buttons(gtk.STOCK_OPEN, 1, gtk.STOCK_CANCEL, 0)
        self.filew.set_default_response(1)
        
        # Connect the ok_button to file_ok_sel method
        #self.filew.ok_button.connect("clicked", self.file_ok_sel)
        self.filew.connect("response", self.file_ok_sel)
    
        # Connect the cancel_button to destroy the widget
        #self.filew.cancel_button.connect("clicked", self.close)
    
    def popup(self, title, callfn, initialdir=None,
              filename=None):
        self.callfn = callfn
        self.filew.set_title(title)
        if initialdir:
            self.filew.set_current_folder(initialdir)

        if filename:
            #self.filew.set_filename(filename)
            self.filew.set_current_name(filename)

        self.filew.show()

    def close(self, widget):
        self.filew.hide()


#END
