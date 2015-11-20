#
# Desktop.py -- Generic widgets Desktop GUI layout
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import time
import math

from ginga.misc import Bunch, Callback
from ginga.gw import Widgets, GwHelp

class Desktop(Callback.Callbacks):

    def __init__(self, app):
        super(Desktop, self).__init__()

        self.app = app
        # for tabs
        self.tab = Bunch.caselessDict()
        self.tabcount = 0
        self.workspace = Bunch.caselessDict()

        self.toplevels = []

        for name in ('page-switch', 'all-closed'):
            self.enable_callback(name)

    # --- Workspace Handling ---

    def make_ws(self, name, group=1, show_tabs=True, show_border=False,
                detachable=True, tabpos=None, scrollable=True, closeable=False,
                wstype='nb'):
        if tabpos is None:
            tabpos = 'top'

        if wstype == 'mdi':
            nb = MDIWorkspace()

        elif wstype == 'grid':
            nb = GridWorkspace()

        elif show_tabs:
            nb = TabWorkspace()
            nb.set_tab_position(tabpos)

        else:
            nb = StackWorkspace()

        if nb.has_callback('page-switch'):
            nb.add_callback('page-switch', self.switch_page_cb)

        ## vbox = Widgets.VBox()
        ## toolbar = Widgets.Toolbar(orientation='horizontal')
        ## vbox.add_widget(toolbar, stretch=0)
        ## vbox.add_widget(nb, stretch=1)

        ## # create a Workspace pulldown menu, and add it to the menu bar
        ## winbtn = toolbar.add_action(text="Workspace")

        ## winmenu = Widgets.Menu()
        ## item = winmenu.add_name("Take Tab")
        ## item.add_callback('activated',
        ##                   lambda *args: self.take_tab_cb(nb, args))

        bnch = Bunch.Bunch(nb=nb, name=name, nbtype=wstype,
                           widget=nb, group=group)
        self.workspace[name] = bnch
        return bnch

    def has_ws(self, name):
        return name in self.workspace

    def get_ws(self, name):
        return self.workspace[name]

    def get_nb(self, name):
        return self.workspace[name].nb

    def get_size(self, widget):
        return widget.get_size()

    def get_ws_size(self, name):
        w = self.get_nb(name)
        return self.get_size(w)

    def get_wsnames(self, group=1):
        res = []
        for name in self.workspace.keys():
            bnch = self.workspace[name]
            if group is None:
                res.append(name)
            elif group == bnch.group:
                res.append(name)
        return res

    def get_tabnames(self, group=1):
        res = []
        for name in self.tab.keys():
            bnch = self.tab[name]
            if group is None:
                res.append(name)
            elif group == bnch.group:
                res.append(name)
        return res

    def add_tab(self, wsname, widget, group, labelname, tabname=None,
                data=None):
        ws_w = self.get_nb(wsname)
        self.tabcount += 1
        if not tabname:
            tabname = labelname
            if tabname in self.tab:
                tabname = 'tab%d' % self.tabcount

        ws_w.add_tab(widget, title=labelname)
        self.tab[tabname] = Bunch.Bunch(widget=widget, name=labelname,
                                        tabname=tabname, data=data,
                                        group=group)
        return tabname

    def _find_nb(self, tabname):
        widget = self.tab[tabname].widget
        for bnch in self.workspace.values():
            nb = bnch.nb
            page_num = nb.index_of(widget)
            if page_num < 0:
                continue
            return (nb, page_num)
        return (None, None)

    def _find_tab(self, widget):
        for key, bnch in self.tab.items():
            if widget == bnch.widget:
                return bnch
        return None

    def raise_tab(self, tabname):
        nb, index = self._find_nb(tabname)
        widget = self.tab[tabname].widget
        if (nb is not None) and (index >= 0):
            nb.set_index(index)

    def remove_tab(self, tabname):
        nb, index = self._find_nb(tabname)
        widget = self.tab[tabname].widget
        if (nb is not None) and (index >= 0):
            nb.remove_tab(widget)

    def highlight_tab(self, tabname, onoff):
        nb, index = self._find_nb(tabname)
        if nb and hasattr(nb, 'highlight_tab'):
            nb.highlight_tab(index)

    def add_toplevel(self, bnch, wsname, width=700, height=700):
        topw = self.app.make_window(title=wsname)
        topw.resize(width, height)
        self.toplevels.append(topw)

        vbox = Widgets.VBox()
        vbox.set_border_width(0)
        topw.add_widget(vbox, stretch=1)

        toolbar = Widgets.Toolbar()
        vbox.add_widget(toolbar, stretch=0)

        # create a Workspace pulldown menu, and add it to the menu bar
        winmenu = toolbar.add_name("Workspace")

        item = winmenu.add_name("Take Tab")
        item.add_callback('activated',
                          lambda *args: self.take_tab_cb(bnch.nb, args))

        winmenu.add_separator()

        closeitem = winmenu.add_name("Close")
        #bnch.widget.closeEvent = lambda event: self.close_page_cb(bnch, event)
        closeitem.add_callback('activated',
                               lambda *args: self._close_page(bnch))

        vbox.add_widget(bnch.widget, stretch=1)
        topw.show()
        return topw

    def create_toplevel_ws(self, width, height, group=2, x=None, y=None):
        # create main frame
        root = self.app.make_window()
        ## root.set_title(title)
        # TODO: this needs to be more sophisticated

        vbox = Widgets.VBox()
        vbox.set_border_width(0)
        root.add_widget(vbox)

        menubar = Widgets.Menubar()
        vbox.addWidget(menubar, stretch=0)

        # create a Window pulldown menu, and add it to the menu bar
        winmenu = menubar.add_name("Window")

        winmenu.add_separator()

        quititem = menubar.add_name("Quit")

        wsname = str(time.time())
        bnch = self.make_ws(wsname, group=1)
        bnch.root = root
        vbox.add_widget(bnch.widget, stretch=1)
        #root.closeEvent = lambda event: self.close_page_cb(bnch, event)
        quititem.add_callback('activated', lambda *args: self._close_page(bnch))

        root.resize(width, height)
        root.show()
        if x is not None:
            root.move(x, y)
        return True

    ## def detach_page_cb(self, source, widget, x, y, group):
    ##     # Detach page to new top-level workspace
    ##     ## page = self.widgetToPage(widget)
    ##     ## if not page:
    ##     ##     return None
    ##     width, height = widget.size()

    ##     ## self.logger.info("detaching page %s" % (page.name))
    ##     bnch = self.create_toplevel_ws(width, height, x=x, y=y)

    ##     return bnch.nb

    def _mk_take_tab_cb(self, tabname, to_nb):
        def _foo():
            nb, index = self._find_nb(tabname)
            widget = self.tab[tabname].widget
            if (nb is not None) and (index >= 0):
                nb.remove_tab(widget)
                to_nb.add_tab(widget, title=tabname)

        return _foo

    def _close_page(self, bnch):
        num_children = bnch.nb.count()
        if num_children == 0:
            del self.workspace[bnch.name]
            root = bnch.root
            bnch.root = None
            root.delete()
        return True

    ## def close_page_cb(self, bnch, event):
    ##     num_children = bnch.nb.count()
    ##     if num_children == 0:
    ##         del self.workspace[bnch.name]
    ##         #bnch.root.destroy()
    ##         event.accept()
    ##     else:
    ##         event.ignore()
    ##     return True

    def switch_page_cb(self, nbw, child):
        self.logger.debug("page switch: %s" % str(child))
        bnch = self._find_tab(child)
        if bnch is not None:
            self.make_callback('page-switch', bnch.name, bnch.data)
        return False

    def make_desktop(self, layout, widgetDict=None):
        if widgetDict is None:
            widgetDict = {}

        def process_common_params(widget, inparams):
            params = Bunch.Bunch(name=None, height=-1, width=-1,
                                 xpos=-1, ypos=-1)
            params.update(inparams)

            if params.name:
                widgetDict[params.name] = widget

            # User is specifying the size of the widget
            if ((params.width >= 0) or (params.height >= 0)) and \
                   isinstance(widget, Widgets.WidgetBase):
                w_exp, h_exp = 0, 0
                if params.width < 0:
                    width = widget.get_size()[0]
                    w_exp = 8
                else:
                    width = params.width
                    w_exp = 1|4
                if params.height < 0:
                    height = widget.get_size()[1]
                    h_exp = 8
                else:
                    height = params.height
                    h_exp = 1|4
                widget.resize(width, height)
                widget.cfg_expand(w_exp, h_exp)

            # User wants to place window somewhere
            if (params.xpos >= 0) and isinstance(widget, Widgets.WidgetBase):
                widget.move(params.xpos, params.ypos)

        def make_widget(kind, paramdict, args, pack):
            kind = kind.lower()

            # Process workspace parameters
            params = Bunch.Bunch(name=None, title=None, height=-1,
                                 width=-1, group=1, show_tabs=True,
                                 show_border=False, scrollable=True,
                                 detachable=True, wstype='nb',
                                 tabpos='top')
            params.update(paramdict)

            if kind == 'widget':
                widget = args[0]

            elif kind == 'ws':
                group = int(params.group)
                bnch = self.make_ws(params.name, group=group,
                                      show_tabs=params.show_tabs,
                                      show_border=params.show_border,
                                      detachable=params.detachable,
                                      tabpos=params.tabpos,
                                      wstype=params.wstype,
                                      scrollable=params.scrollable)
                widget = bnch.widget
                #debug(widget)

            # If a title was passed as a parameter, then make a frame to
            # wrap the widget using the title.
            if params.title:
                fr = Widgets.Frame(title=params.title)
                fr.set_widget(widget)
                pack(fr)
            else:
                pack(widget)

            process_common_params(widget, params)

            if (kind in ('ws', 'mdi', 'grid')) and (len(args) > 0):
                # <-- Workspace specified a sub-layout.  We expect a list
                # of tabname, layout pairs--iterate over these and add them
                # to the workspace as tabs.
                for tabname, layout in args[0]:
                    def pack(w):
                        # ?why should group be the same as parent group?
                        self.add_tab(params.name, w, group,
                                     tabname, tabname.lower())

                    make(layout, pack)

            #return widget

        # Horizontal adjustable panel
        def horz(params, cols, pack):
            if len(cols) >= 2:
                hpaned = Widgets.Splitter(orientation='horizontal')

                for col in cols:
                    make(col, lambda w: hpaned.add_widget(w))
                widget = hpaned

            elif len(cols) == 1:
                widget = Widgets.HBox()
                widget.set_border_width(0)
                make(cols[0], lambda w: widget.add_widget(w, stretch=1))
                #widget.show()

            process_common_params(widget, params)
            pack(widget)

        # Vertical adjustable panel
        def vert(params, rows, pack):
            if len(rows) >= 2:
                vpaned = Widgets.Splitter(orientation='vertical')

                for row in rows:
                    make(row, lambda w: vpaned.add_widget(w))
                widget = vpaned

            elif len(rows) == 1:
                widget = Widgets.VBox()
                widget.set_border_width(0)
                make(rows[0], lambda w: widget.add_widget(w, stretch=1))
                #widget.show()

            process_common_params(widget, params)
            pack(widget)

        # Horizontal fixed array
        def hbox(params, cols, pack):
            widget = Widgets.HBox()
            widget.set_border_width(0)

            for dct in cols:
                if isinstance(dct, dict):
                    stretch = dct.get('stretch', 0)
                    col = dct.get('col', None)
                else:
                    # assume a list defining the col
                    stretch = align = 0
                    col = dct
                if col is not None:
                    make(col, lambda w: widget.add_widget(w,
                                                          stretch=stretch))
            process_common_params(widget, params)
            pack(widget)

        # Vertical fixed array
        def vbox(params, rows, pack):
            widget = Widgets.VBox()
            widget.set_border_width(0)

            for dct in rows:
                if isinstance(dct, dict):
                    stretch = dct.get('stretch', 0)
                    row = dct.get('row', None)
                else:
                    # assume a list defining the row
                    stretch = align = 0
                    row = dct
                if row is not None:
                    make(row, lambda w: widget.add_widget(w,
                                                          stretch=stretch))
            process_common_params(widget, params)
            pack(widget)

        # Sequence of separate items
        def seq(params, cols, pack):
            def mypack(w):
                w_top = self.app.make_window()
                w_top.cfg_expand(8, 8)
                w_top.set_widget(w)
                self.toplevels.append(w_top)
                ## def closeEvent(*args):
                ##     #self.logger.debug("window %s closed" % str(w))
                ##     self.toplevels.remove(w)
                ##     w.deleteLater()
                ##     if len(self.toplevels) == 0:
                ##         self.make_callback('all-closed')

                ## w.closeEvent = closeEvent
                w_top.show()

            for dct in cols:
                if isinstance(dct, dict):
                    stretch = dct.get('stretch', 0)
                    col = dct.get('col', None)
                else:
                    # assume a list defining the col
                    stretch = align = 0
                    col = dct
                if col is not None:
                    make(col, mypack)

            widget = Widgets.Label("Placeholder")
            pack(widget)

        def make(constituents, pack):
            kind = constituents[0]
            params = constituents[1]
            if len(constituents) > 2:
                rest = constituents[2:]
            else:
                rest = []

            if kind == 'vpanel':
                vert(params, rest, pack)
            elif kind == 'hpanel':
                horz(params, rest, pack)
            elif kind == 'vbox':
                vbox(params, rest, pack)
            elif kind == 'hbox':
                hbox(params, rest, pack)
            elif kind == 'seq':
                seq(params, rest, pack)
            elif kind in ('ws', 'mdi', 'widget'):
                make_widget(kind, params, rest, pack)

        make(layout, lambda w: None)


    ##### WORKSPACES #####

class WorkspaceMixin(object):

    def to_next(self):
        num_tabs = self.num_children()
        cur_idx = self.get_index()
        new_idx = (cur_idx + 1) % num_tabs
        self.set_index(new_idx)

    def to_previous(self):
        num_tabs = self.num_children()
        new_idx = self.get_index() - 1
        if new_idx < 0:
            new_idx = max(num_tabs - 1, 0)
        self.set_index(new_idx)


class TabWorkspace(Widgets.TabWidget, WorkspaceMixin):

    def __init__(self):
        super(TabWorkspace, self).__init__()

    def add_tab(self, widget, title=''):
        self.add_widget(widget, title=title)

    def remove_tab(self, widget):
        self.remove(widget)


class StackWorkspace(Widgets.StackWidget, WorkspaceMixin):

    def __init__(self):
        super(StackWorkspace, self).__init__()

    def add_tab(self, widget, title=''):
        self.add_widget(widget)

    def remove_tab(self, widget):
        self.remove(widget)


class MDIWorkspace(Widgets.MDIWidget, WorkspaceMixin):

    def __init__(self):
        super(MDIWorkspace, self).__init__(mode='mdi')

    def add_tab(self, widget, title=''):
        self.add_widget(widget, title=title)

    def remove_tab(self, widget):
        self.remove(widget)


class GridWorkspace(Widgets.GridBox, WorkspaceMixin):

    def __init__(self):
        super(GridWorkspace, self).__init__()

        self.set_margins(0, 0, 0, 0)
        self.set_spacing(2)

    def _relayout(self, widgets):
        # remove all the old widgets
        self.remove_all()

        # calculate number of rows and cols, try to maintain a square
        # TODO: take into account the window geometry
        num_widgets = len(widgets)
        rows = int(round(math.sqrt(num_widgets)))
        cols = rows
        if rows**2 < num_widgets:
            cols += 1

        self.resize_grid(rows, cols)

        # add them back in, in a grid
        for i in range(0, rows):
            for j in range(0, cols):
                index = i*cols + j
                if index < num_widgets:
                    child = widgets[index]
                    self.add_widget(child, i, j, stretch=1)

    def add_tab(self, widget, title=''):
        widgets = list(self.get_children())
        widgets.append(widget)

        self._relayout(widgets)


    def remove_tab(self, widget):
        self.remove(widget)

        widgets = list(self.get_children())
        self._relayout(widgets)

    def get_index(self):
        return self.cur_index

    def set_index(self, idx):
        if 0 <= idx < self.num_children():
            self.cur_index = idx
            # TODO: focus widget

    def index_of(self, child):
        children = self.get_children()
        try:
            return children.index(child)
        except (IndexError, ValueError) as e:
            return -1

    def index_to_widget(self, idx):
        children = self.get_children()
        return children[idx]

#END
