#
# Thumbs.py -- Thumbnail plugin for Ginga fits viewer
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import os
import gtk
import gobject

from ginga.gtkw import ImageViewCanvasGtk
from ginga.gtkw import GtkHelp
from ginga.misc.plugins import ThumbsBase
from ginga.misc import Bunch


class Thumbs(ThumbsBase.ThumbsBase):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(Thumbs, self).__init__(fv)

        self.TARGET_TYPE_TEXT = 0
        self.TARGET_TYPE_THUMB = 1
        self.action = None

    def build_gui(self, container):
        width, height = 300, 300
        cm, im = self.fv.cm, self.fv.im

        tg = ImageViewCanvasGtk.ImageViewCanvas(logger=self.logger)
        tg.configure_window(200, 200)
        tg.enable_autozoom('on')
        tg.enable_autocuts('override')
        tg.enable_auto_orient(True)
        tg.set_bg(0.7, 0.7, 0.7)
        tg.defer_redraw = False
        self.thumb_generator = tg

        sw = gtk.ScrolledWindow()
        sw.set_border_width(2)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

        # Create thumbnails pane
        vbox = gtk.VBox(spacing=14)
        vbox.set_border_width(4)
        self.w.thumbs = vbox
        sw.add_with_viewport(vbox)
        sw.show_all()
        self.w.thumbs_scroll = sw
        self.w.thumbs_scroll.connect("size_allocate", self.thumbpane_resized_cb)
        #nb.connect("size_allocate", self.thumbpane_resized_cb)

        # TODO: should this even have it's own scrolled window?
        cw = container.get_widget()
        cw.pack_start(sw, fill=True, expand=True)

        captions = (('Auto scroll', 'checkbutton', 'Clear', 'button'),)
        w, b = GtkHelp.build_info(captions)
        self.w.update(b)

        b.auto_scroll.set_tooltip_text(
            "Scroll the thumbs window when new images arrive")
        b.clear.set_tooltip_text("Remove all current thumbnails")
        b.clear.connect("clicked", lambda w: self.clear())
        auto_scroll = self.settings.get('auto_scroll', True)
        b.auto_scroll.set_active(auto_scroll)

        cw.pack_start(w, fill=True, expand=False)
        self.gui_up = True


    def _mk_tooltip(self, thumbkey, name, metadata):
        return lambda tw, x, y, kbmode, ttw: self.query_thumb(thumbkey, name, metadata, x, y, ttw)

    def _mk_context_menu(self, thumbkey, chname, name, path, image_future):
        menu = gtk.Menu()
        item = gtk.MenuItem("Display")
        item.connect("activate", lambda w: self.load_file(thumbkey, chname,
                                                          name, path,
                                                          image_future))
        menu.append(item)
        sep = gtk.SeparatorMenuItem()
        menu.append(sep)
        item = gtk.MenuItem("Remove")
        item.connect("activate", lambda w: self.fv.remove_image_by_name(chname, name, impath=path))
        menu.append(item)
        menu.show_all()
        return menu

    def insert_thumbnail(self, imgwin, thumbkey, thumbname, chname, name, path,
                         thumbpath, metadata, image_future):

        imgwin.set_property("has-tooltip", True)
        imgwin.connect("query-tooltip", self._mk_tooltip(thumbkey, name, metadata))

        vbox = gtk.VBox(spacing=0)
        vbox.pack_start(gtk.Label(thumbname), expand=False,
                        fill=False, padding=0)
        evbox = gtk.EventBox()
        evbox.add(imgwin)
        evbox.connect("button-press-event",
                      lambda w, e: self.button_down(w, e, thumbkey, chname,
                                                    name, path,
                                                    image_future))
        evbox.connect("button-release-event",
                      lambda w, e: self.button_up(w, e, thumbkey, chname,
                                                  name, path,
                                                  image_future))
        # set up for drag & drop
        targets = [ ( "text/plain", 0, self.TARGET_TYPE_TEXT ),
                    #( "text/uri-list", 0, self.TARGET_TYPE_TEXT ),
                    ( "text/thumb", gtk.TARGET_SAME_APP,
                      self.TARGET_TYPE_THUMB ),
                    ]
        evbox.drag_source_set(gtk.gdk.BUTTON1_MASK, targets,
                              gtk.gdk.ACTION_COPY | gtk.gdk.ACTION_MOVE)

        evbox.connect("drag-begin",
                      lambda *args: self.drag_begin(args, imgwin, thumbkey))
        evbox.connect("drag-data-get",
                      lambda *args: self.drag_data_get(args, chname, name,
                                                       path))
        evbox.connect("drag-data-delete",
                      lambda *args: self.drag_data_move(args))
        evbox.connect("drag-end",
                      lambda *args: self.drag_end(args))

        vbox.pack_start(evbox, expand=False, fill=False)
        vbox.show_all()

        bnch = Bunch.Bunch(widget=vbox, evbox=evbox, imname=name,
                           thumbname=thumbname, chname=chname, path=path,
                           thumbpath=thumbpath, image_future=image_future)

        with self.thmblock:
            self.thumbDict[thumbkey] = bnch
            self.thumbList.append(thumbkey)

            sort_order = self.settings.get('sort_order', None)
            if sort_order:
                self.thumbList.sort()
                self.reorder_thumbs()
                return

            if self.thumbColCount == 0:
                hbox = gtk.HBox(homogeneous=True, spacing=self.thumbSep)
                self.w.thumbs.pack_start(hbox)
                self.thumbRowList.append(hbox)

            else:
                hbox = self.thumbRowList[-1]

            hbox.pack_start(bnch.widget)
            self.thumbColCount = (self.thumbColCount + 1) % self.thumbNumCols

            self.w.thumbs.show_all()

        # force scroll to bottom of thumbs, if checkbox is set
        scrollp = self.w.auto_scroll.get_active()
        if scrollp:
            adj_w = self.w.thumbs_scroll.get_vadjustment()
            max = adj_w.get_upper()
            adj_w.set_value(max)
        self.logger.debug("added thumb for %s" % (thumbname))

    def clearWidget(self):
        """Clears the thumbnail display widget of all thumbnails, but does
        not remove them from the thumbDict or thumbList.
        """
        with self.thmblock:
            # Remove old rows
            for hbox in self.thumbRowList:
                children = hbox.get_children()
                for child in children:
                    hbox.remove(child)
                self.w.thumbs.remove(hbox)
            self.thumbRowList = []
            self.thumbColCount = 0

    def reorder_thumbs(self):
        self.logger.debug("Reordering thumb grid")
        with self.thmblock:
            self.clearWidget()

            # Add thumbs back in by rows
            colCount = 0
            hbox = None
            for thumbkey in self.thumbList:
                self.logger.debug("adding thumb for %s" % (str(thumbkey)))
                chname, name = thumbkey[:2]
                bnch = self.thumbDict[thumbkey]
                if colCount == 0:
                    hbox = gtk.HBox(homogeneous=True, spacing=self.thumbSep)
                    hbox.show()
                    self.w.thumbs.pack_start(hbox)
                    self.thumbRowList.append(hbox)

                hbox.pack_start(bnch.widget)
                hbox.show_all()
                colCount = (colCount + 1) % self.thumbNumCols

            self.thumbColCount = colCount
            self.w.thumbs.show_all()

    def thumbpane_resized_cb(self, widget, allocation):
        rect = widget.get_allocation()
        x, y, width, height = rect.x, rect.y, rect.width, rect.height
        return self.thumbpane_resized(width, height)

    def query_thumb(self, thumbkey, name, metadata, x, y, ttw):
        result = []
        for kwd in self.keywords:
            try:
                text = kwd + ': ' + str(metadata[kwd])
            except Exception as e:
                self.logger.warn("Couldn't determine %s name: %s" % (
                    kwd, str(e)))
                text = "%s: N/A" % (kwd)
            result.append(text)

        ttw.set_text('\n'.join(result))
        return True

    def button_down(self, widget, event, thumbkey, chname,
                    name, path, image_future):
        if event.type == gtk.gdk.BUTTON_PRESS:
            if event.button == 1:
                self.action = 'click'
            elif event.button == 3:
                # make widget popup
                menu = self._mk_context_menu(thumbkey, chname, name, path,
                                             image_future)
                menu.popup(None, None, None, event.button, event.time)

    def button_up(self, widget, event, thumbkey, chname,
                  name, path, image_future):
        if event.type == gtk.gdk.BUTTON_RELEASE:
            if (event.button == 1) and (self.action == 'click'):
                self.action = None
                self.load_file(thumbkey, chname, name, path,
                               image_future)

    def drag_begin(self, args, imgwin, thumbkey):
        widget, context = args
        self.action = 'drag'
        # set drag icon
        pixbuf = imgwin.get_pixbuf()
        context.set_icon_pixbuf(pixbuf, 10, 10)

    def drag_data_get(self, args, chname, name, path):
        widget, context, selection, target_type, dragtime = args
        if "text/thumb" in context.targets:
            path = "%s||%s||%s" % (chname, name, path)
            selection.set(selection.target, 8, path)
        elif "text/uri-list" in context.targets:
            path = "file://%s" % (path)
            selection.set(selection.target, 8, path)
        elif "text/plain" in context.targets:
            selection.set(selection.target, 8, path)

    def drag_data_delete(self, args):
        widget, context = args
        #print(('drag data delete', widget, context))

    def drag_end(self, args):
        widget, context = args
        self.action = None

    def update_thumbnail(self, thumbkey, imgwin, name, metadata):
        with self.thmblock:
            try:
                bnch = self.thumbDict[thumbkey]
            except KeyError:
                self.logger.debug("No thumb found for %s; not updating thumbs" % (
                    str(thumbkey)))
                return

            imgwin.set_property("has-tooltip", True)
            imgwin.connect("query-tooltip", self._mk_tooltip(thumbkey, name, metadata))

            # Replace thumbnail image widget
            self.logger.debug("replacing thumb widget.")
            child = bnch.evbox.get_child()
            bnch.evbox.remove(child)
            bnch.evbox.add(imgwin)
            bnch.evbox.show_all()
        self.logger.debug("update finished.")

    def __str__(self):
        return 'thumbs'

#END
