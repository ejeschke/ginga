#
# Desktop.py -- Generic widgets Desktop GUI layout
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import time
import math

from ginga.misc import Bunch, Callback
from ginga.gw import Widgets, GwHelp, Viewers

class Desktop(Callback.Callbacks):

    def __init__(self, app):
        super(Desktop, self).__init__()

        self.app = app
        self.logger = app.logger
        # for tabs
        self.tab = Bunch.caselessDict()
        self.tabcount = 0
        self.workspace = Bunch.caselessDict()

        self.toplevels = []
        self.node = {}
        self.node_idx = 0
        self._cur_dialogs = []

        for name in ('page-switch', 'all-closed'):
            self.enable_callback(name)

    # --- Workspace Handling ---

    def make_ws(self, name, group=1, show_tabs=True, show_border=False,
                detachable=False, tabpos=None, scrollable=True, closeable=False,
                wstype='tabs', use_toolbar=False):

        if (wstype in ('nb', 'ws', 'tabs')) and (not show_tabs):
            wstype = 'stack'

        ws = Workspace(name=name, wstype=wstype,
                       group=group, detachable=detachable,
                       use_toolbar=use_toolbar)
        ws.add_callback('page-switch', self.switch_page_cb)
        ws.add_callback('page-detach', self.page_detach_cb)

        nb = ws.nb

        if tabpos is None:
            tabpos = 'top'

        if (wstype == 'tabs') and show_tabs:
            nb.set_tab_position(tabpos)

        # # create a Workspace pulldown menu, and add it to the tool bar
        # if ws.toolbar is not None:
        #     winmenu = ws.toolbar.add_menu("Workspace")
        #     item = winmenu.add_name("Take Tab")
        #     item.add_callback('activated',
        #                       lambda *args: self.take_tab_cb(nb, args))

        self.workspace[name] = ws
        return ws

    def delete_ws(self, name):
        if not self.has_ws(name):
            raise ValueError("No workspace named '%s'" % (name))

        # NOTE: currently the Desktop object does not close the window
        # or tab--you must manage that yourself
        del self.workspace[name]

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
            ws = self.workspace[name]
            if group is None:
                res.append(name)
            elif group == ws.group:
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
        ws = self.get_ws(wsname)
        self.tabcount += 1
        if not tabname:
            tabname = labelname
            if tabname in self.tab:
                tabname = 'tab%d' % self.tabcount

        ws.add_tab(widget, title=labelname)
        bnch = Bunch.Bunch(widget=widget, name=labelname,
                           tabname=tabname, data=data,
                           group=group, wsname=wsname)
        self.tab[tabname] = bnch
        return bnch

    def _find_nb(self, tabname):
        widget = self.tab[tabname].widget
        for ws in self.workspace.values():
            nb = ws.nb
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
        # construct a list of the tabs to raise in the order they
        # should be raised
        l = []
        name = tabname.lower()
        while self.tab.has_key(name):
            bnch = self.tab[name]
            l.insert(0, name)
            name = bnch.wsname.lower()
            if name in l:
                break

        # now raise those tabs
        for name in l:
            nb, index = self._find_nb(name)
            if (nb is not None) and (index >= 0):
                nb.set_index(index)

    def remove_tab(self, tabname):
        nb, index = self._find_nb(tabname)
        widget = self.tab[tabname].widget
        if (nb is not None) and (index >= 0):
            del self.tab[tabname]
            nb.remove(widget)

    def highlight_tab(self, tabname, onoff):
        nb, index = self._find_nb(tabname)
        if (nb is not None) and hasattr(nb, 'highlight_tab'):
            nb.highlight_tab(index, onoff)

    def show_dialog(self, dialog):
        dialog.show()
        # save a handle so widgets aren't garbage collected
        if not dialog in self._cur_dialogs:
            self._cur_dialogs.append(dialog)

    def hide_dialog(self, dialog):
        dialog.hide()

    def remove_dialog(self, dialog):
        dialog.hide()
        if dialog in self._cur_dialogs:
            self._cur_dialogs.remove(dialog)
        dialog.delete()

    def add_toplevel(self, bnch, wsname, width=700, height=700):
        topw = self.app.make_window(title=wsname)
        topw.resize(width, height)
        self.toplevels.append(topw)
        # TODO: don't ignore close, but handle workspace deletion
        topw.add_callback('close', lambda w: None)

        vbox = Widgets.VBox()
        vbox.set_border_width(0)
        topw.set_widget(vbox)

        vbox.add_widget(bnch.widget, stretch=1)
        topw.show()
        return topw

    def remove_toplevel(self, widget):
        widget.hide()
        if widget in self.toplevels:
            self.toplevels.remove(widget)
        widget.delete()

    def create_toplevel_ws(self, wsname, width, height,
                           group=2, x=None, y=None):
        # create main frame
        root = self.app.make_window()

        # TODO: this needs to be more sophisticated
        ## root.set_title(wsname)
        ws = self.make_ws(wsname, wstype='tabs', use_toolbar=True)

        vbox = Widgets.VBox()
        vbox.set_border_width(0)

        vbox.add_widget(bnch.widget)
        root.set_widget(vbox)

        root.resize(width, height)
        root.show()
        self.toplevels.append(root)

        if x is not None:
            root.move(x, y)
        return bnch

    def _mk_take_tab_cb(self, tabname, to_nb):
        def _foo():
            nb, index = self._find_nb(tabname)
            widget = self.tab[tabname].widget
            if (nb is not None) and (index >= 0):
                nb.remove_tab(widget)
                to_nb.add_tab(widget, title=tabname)

        return _foo

    def _close_page(self, ws):
        num_children = ws.widget.num_children()
        if num_children == 0:
            del self.workspace[ws.name]
            root = ws.root
            bnch.root = None
            root.delete()
        return True

    def page_detach_cb(self, ws, child):
        try:
            width, height = child.get_size()

            wsname = str(time.time())
            ws = self.create_toplevel_ws(wsname, width, height+100)

            # get title of child
            try:
                title = child.extdata['tab_title']
            except KeyError:
                title = 'No Title'

            ws.add_tab(child, title=title)
        except Exception as e:
            print(str(e))

    def switch_page_cb(self, ws, child):
        self.logger.debug("page switch: %s" % str(child))
        bnch = self._find_tab(child)
        if bnch is not None:
            self.make_callback('page-switch', bnch.name, bnch.data)
        return False

    def make_desktop(self, layout, widget_dict=None):
        if widget_dict is None:
            widget_dict = {}
        self.node = {}
        self.node_idx = 0

        def process_common_params(kind, widget, params):
            subst_params = Bunch.Bunch(name=None, height=-1, width=-1,
                                       xpos=-1, ypos=-1, spacing=None,
                                       wexp=None, hexp=None)
            subst_params.update(params)
            params.update(subst_params)

            if params.name is not None:
                name = params.name
                widget_dict[params.name] = widget
            else:
                name = '%s_%d' % (kind, self.node_idx)
                self.node_idx += 1

            bnch = Bunch.Bunch(kind=kind, widget=widget,
                               name=name, params=params)
            self.node[name] = bnch

            wexp, hexp = params.wexp, params.hexp

            # User is specifying the size of the widget
            if isinstance(widget, Widgets.WidgetBase):

                if params.spacing is not None:
                    widget.set_spacing(params.spacing)

                # directive to size widget
                if (params.width >= 0) or (params.height >= 0):
                    if params.width < 0:
                        width = widget.get_size()[0]
                        if wexp is None:
                            wexp = 8
                    else:
                        width = params.width
                        if wexp is None:
                            wexp = 1|4
                    if params.height < 0:
                        height = widget.get_size()[1]
                        if hexp is None:
                            hexp = 8
                    else:
                        height = params.height
                        if hexp is None:
                            hexp = 1|4
                    widget.resize(width, height)

                # specify expansion policy of widget
                if (wexp is not None) or (hexp is not None):
                    if wexp is None:
                        wexp = 0
                    if hexp is None:
                        hexp = 0
                    widget.cfg_expand(wexp, hexp)

                # User wants to place window somewhere
                if params.xpos >= 0:
                    widget.move(params.xpos, params.ypos)

            return bnch

        def make_widget(kind, params, args, pack):
            kind = kind.lower()

            # Process workspace parameters
            param_dict = Bunch.Bunch(name=None, title=None, height=-1,
                                      width=-1, group=1, show_tabs=True,
                                      show_border=False, scrollable=True,
                                      detachable=False, wstype='tabs',
                                      tabpos='top', use_toolbar=False)
            param_dict.update(params)
            params.update(param_dict)

            if kind == 'widget':
                widget = args[0]

            elif kind == 'ws':
                group = int(params.group)
                ws = self.make_ws(params.name, group=group,
                                  show_tabs=params.show_tabs,
                                  show_border=params.show_border,
                                  detachable=params.detachable,
                                  tabpos=params.tabpos,
                                  wstype=params.wstype,
                                  scrollable=params.scrollable,
                                  use_toolbar=params.use_toolbar)
                widget = ws.widget
                #debug(widget)

            # If a title was passed as a parameter, then make a frame to
            # wrap the widget using the title.
            if params.title:
                fr = Widgets.Frame(title=params.title)
                fr.set_widget(widget)
                pack(fr)
            else:
                pack(widget)

            #process_common_params(kind, widget, params)

            res = []
            if (kind in ('ws', 'mdi', 'grid', 'stack')) and (len(args) > 0):
                # <-- Workspace specified a sub-layout.  We expect a list
                # of tabname, layout pairs--iterate over these and add them
                # to the workspace as tabs.
                for tabname, layout in args[0]:
                    def pack(w):
                        # ?why should group be the same as parent group?
                        self.add_tab(params.name, w, group,
                                     tabname, tabname.lower())

                    res.append((tabname, make(layout, pack)))

            bnch = process_common_params(kind, widget, params)
            if kind == 'ws':
                bnch.ws = ws

            #return [kind, params] + res
            return [kind, params, res]

        # Horizontal adjustable panel
        def hpanel(params, cols, pack):
            res = []
            if len(cols) >= 2:
                widget = Widgets.Splitter(orientation='horizontal')
                process_common_params('hpanel', widget, params)

                sizes = []
                for col in cols:
                    c = make(col, lambda w: widget.add_widget(w))
                    res.append(c)

                    # collect widths to set width of panes
                    params = col[1]
                    if 'width' in params:
                        sizes.append(params['width'])

                sizes = params.get('sizes', sizes)
                if len(sizes) == len(cols):
                    widget.set_sizes(sizes)
                    params.update(dict(sizes=sizes))

            elif len(cols) == 1:
                widget = Widgets.HBox()
                widget.set_border_width(0)
                process_common_params('hbox', widget, params)

                c = make(cols[0], lambda w: widget.add_widget(w, stretch=1))
                res.append(c)
                #widget.show()

            pack(widget)
            return ['hpanel', params] + res

        # Vertical adjustable panel
        def vpanel(params, rows, pack):
            res = []
            if len(rows) >= 2:
                widget = Widgets.Splitter(orientation='vertical')
                process_common_params('vpanel', widget, params)

                sizes = []
                for row in rows:
                    r = make(row, lambda w: widget.add_widget(w))
                    res.append(r)

                    # collect heights to set height of panes
                    params = row[1]
                    if 'height' in params:
                        sizes.append(params['height'])

                sizes = params.get('sizes', sizes)
                if len(sizes) == len(rows):
                    widget.set_sizes(sizes)
                    params.update(dict(sizes=sizes))

            elif len(rows) == 1:
                widget = Widgets.VBox()
                widget.set_border_width(0)
                process_common_params('vbox', widget, params)

                r = make(rows[0], lambda w: widget.add_widget(w, stretch=1))
                res.append(r)
                #widget.show()

            pack(widget)
            return ['vpanel', params] + res

        # Horizontal fixed array
        def hbox(params, cols, pack):
            widget = Widgets.HBox()
            widget.set_border_width(0)
            widget.set_spacing(0)

            res = []
            for dct in cols:
                if isinstance(dct, dict):
                    stretch = dct.get('stretch', 0)
                    col = dct.get('col', None)
                else:
                    # assume a list defining the col
                    stretch = 0
                    col = dct
                if col is not None:
                    c = make(col, lambda w: widget.add_widget(w,
                                                              stretch=stretch))
                    c = dict(col=c, stretch=stretch)
                    res.append(c)

            process_common_params('hbox', widget, params)
            pack(widget)
            return ['hbox', params] + res

        # Vertical fixed array
        def vbox(params, rows, pack):
            widget = Widgets.VBox()
            widget.set_border_width(0)
            widget.set_spacing(0)

            res = []
            for dct in rows:
                if isinstance(dct, dict):
                    stretch = dct.get('stretch', 0)
                    row = dct.get('row', None)
                else:
                    # assume a list defining the row
                    stretch = 0
                    row = dct
                if row is not None:
                    r = make(row, lambda w: widget.add_widget(w,
                                                              stretch=stretch))
                    r = dict(row=r, stretch=stretch)
                    res.append(r)

            process_common_params('vbox', widget, params)
            pack(widget)
            return ['vbox', params] + res

        # Sequence of separate top-level items
        def seq(params, cols, pack):
            def mypack(w):
                w_top = self.app.make_window()
                #w_top.cfg_expand(8, 8)
                # Ask the size of the widget that wants to get packed
                # and resize the top-level to fit
                wd, ht = w.get_size()
                w_top.resize(wd, ht)
                w_top.set_widget(w)
                self.toplevels.append(w_top)
                w_top.show()
                process_common_params('top', w_top, params)

            res = []
            for dct in cols:
                if isinstance(dct, dict):
                    stretch = dct.get('stretch', 0)
                    col = dct.get('col', None)
                else:
                    # assume a list defining the col
                    stretch = 0
                    col = dct
                if col is not None:
                    res.append(make(col, mypack))

            widget = Widgets.Label("Placeholder")
            pack(widget)
            return ['seq', params] + res

        def make(constituents, pack):
            kind = constituents[0]
            params = Bunch.Bunch(constituents[1])
            if len(constituents) > 2:
                rest = constituents[2:]
            else:
                rest = []

            if kind == 'vpanel':
                res = vpanel(params, rest, pack)
            elif kind == 'hpanel':
                res = hpanel(params, rest, pack)
            elif kind == 'vbox':
                res = vbox(params, rest, pack)
            elif kind == 'hbox':
                res = hbox(params, rest, pack)
            elif kind == 'seq':
                res = seq(params, rest, pack)
            elif kind in ('ws', 'mdi', 'widget'):
                res = make_widget(kind, params, rest, pack)

            return res

        self.layout = make(layout, lambda w: None)
        return self.layout

    def record_sizes(self):
        """Record sizes of all container widgets in the layout.
        The sizes are recorded in the `params` mappings in the layout.
        """
        for rec in self.node.values():
            w = rec.widget
            wd, ht = w.get_size()

            rec.params.update(dict(name=rec.name, width=wd, height=ht))

            if rec.kind in ('hpanel', 'vpanel'):
                sizes = w.get_sizes()
                rec.params.update(dict(sizes=sizes))

            if rec.kind in ('ws',):
                # record ws type
                # TODO: record positions of subwindows
                rec.params.update(dict(wstype=rec.ws.wstype))

            if rec.kind == 'top':
                # record position for top-level widgets as well
                x, y = w.get_pos()
                if x is not None and y is not None:
                    # we don't always get reliable information about position
                    rec.params.update(dict(xpos=x, ypos=y))

    def write_layout_conf(self, lo_file, layout=None):
        if layout is None:
            layout = self.layout

        import pprint
        self.record_sizes()

        # write layout
        with open(lo_file, 'w') as out_f:
            pprint.pprint(layout, out_f)

    def read_layout_conf(self, lo_file):
        import ast

        # read layout
        with open(lo_file, 'r') as in_f:
            buf = in_f.read()

        layout = ast.literal_eval(buf)
        return layout

    def build_desktop(self, layout, lo_file=None, widget_dict=None):
        if lo_file is not None:
            alt_layout = layout
            try:
                layout = self.read_layout_conf(lo_file)

            except Exception as e:
                self.logger.error("Error reading saved layout: %s" % (str(e)))
                layout = alt_layout

        return self.make_desktop(layout, widget_dict=widget_dict)

    ##### WORKSPACES #####

class Workspace(Widgets.WidgetBase):

    def __init__(self, name, wstype='tab', group=0, detachable=False,
                 use_toolbar=False):
        super(Workspace, self).__init__()

        self.name = name
        self.wstype = wstype
        self.wstypes = ['tabs', 'mdi', 'stack', 'grid']
        self.vbox = Widgets.VBox()
        self.vbox.set_spacing(0)
        self.vbox.set_border_width(0)
        # for now
        self.widget = self.vbox
        self.nb = None
        self.group = group
        self.detachable = detachable
        self.toolbar = None
        self.mdi_menu = None
        self.wstypes_c = ['Tabs', 'Grid', 'MDI', 'Stack']
        self.wstypes_l = ['tabs', 'grid', 'mdi', 'stack']
        self.extdata = Bunch.Bunch()

        if use_toolbar:
            self.toolbar = Widgets.Toolbar(orientation='horizontal')
            self.toolbar.set_border_width(0)
            self.vbox.add_widget(self.toolbar, stretch=0)

            ws_menu = self.toolbar.add_menu("Workspace")
            item = ws_menu.add_name("Close")
            item.add_callback('activated', self._close_menuitem_cb)


        self._set_wstype(wstype)
        self.vbox.add_widget(self.nb, stretch=1)

        if use_toolbar:
            cbox = Widgets.ComboBox()
            for _wstype in self.wstypes_c:
                cbox.append_text(_wstype)
            idx = self.wstypes_l.index(wstype)
            cbox.set_index(idx)
            cbox.add_callback('activated', self.config_wstype_cb)
            cbox.set_tooltip("Set workspace type")
            self.toolbar.add_widget(cbox)

            mdi_menu = self.toolbar.add_menu("MDI")
            ## item = mdi_menu.add_name("Panes as Tabs", checkable=True)
            ## item.add_callback('activated',
            ##                   lambda w, tf: self.tabstoggle_cb(tf))
            ## is_tabs = (self.nb.get_mode() == 'tabs')
            ## item.set_state(is_tabs)

            item = mdi_menu.add_name("Tile Panes")
            item.add_callback('activated',
                              lambda *args: self.tile_panes_cb())

            item = mdi_menu.add_name("Cascade Panes")
            item.add_callback('activated',
                              lambda *args: self.cascade_panes_cb())
            self.mdi_menu = mdi_menu
            self._update_mdi_menu()

        for name in ('page-switch', 'page-detach', 'ws-close'):
            self.enable_callback(name)

    def _set_wstype(self, wstype):
        if wstype in ('tabs', 'nb', 'ws'):
            wstype = 'tabs'
            self.nb = Widgets.TabWidget(detachable=self.detachable,
                                            group=self.group)

        elif wstype == 'mdi':
            self.nb = Widgets.MDIWidget(mode='mdi')

        elif wstype == 'stack':
            self.nb = Widgets.StackWidget()

        elif wstype == 'grid':
            self.nb = SymmetricGridWidget()

        self._update_mdi_menu()
        if self.nb.has_callback('page-switch'):
            self.nb.add_callback('page-switch', self._switch_page_cb)
        if self.nb.has_callback('page-detach'):
            self.nb.add_callback('page-detach', self._detach_page_cb)

        self.wstype = wstype

    def _update_mdi_menu(self):
        if self.mdi_menu is None:
            return
        if isinstance(self.nb, Widgets.MDIWidget) and self.nb.true_mdi:
            self.mdi_menu.set_enabled(True)
        else:
            self.mdi_menu.set_enabled(False)

    def tile_panes_cb(self):
        if isinstance(self.nb, Widgets.MDIWidget) and self.nb.true_mdi:
            self.nb.tile_panes()

    def cascade_panes_cb(self):
        if isinstance(self.nb, Widgets.MDIWidget) and self.nb.true_mdi:
            self.nb.cascade_panes()

    def tabstoggle_cb(self, tf):
        if isinstance(self.nb, Widgets.MDIWidget) and self.nb.true_mdi:
            self.nb.use_tabs(tf)

    def _switch_page_cb(self, nb, child):
        self.focus_index()
        self.make_callback('page-switch', child)

    def _detach_page_cb(self, nb, child):
        self.make_callback('page-detach', child)

    def _close_menuitem_cb(self, *args):
        self.make_callback('ws-close')

    def configure_wstype(self, wstype):
        old_widget = self.nb
        self.vbox.remove(old_widget)

        # remember which tab was on top
        idx = old_widget.get_index()

        self._set_wstype(wstype)
        self.vbox.add_widget(self.nb, stretch=1)

        for child in list(old_widget.get_children()):
            # TODO: sort by previous index so they get added to the
            # new widget in the same order
            title = child.extdata.get('tab_title', '')
            old_widget.remove(child)
            self.nb.add_widget(child, title=title)
            child.show()

        # restore focus to widget that was on top
        if idx >= 0:
            self.nb.set_index(idx)
        self.focus_index()

    def config_wstype_cb(self, w, idx):
        wstype = self.wstypes_l[idx]
        self.configure_wstype(wstype)

    def cycle_wstype(self):
        idx = self.wstypes.index(self.wstype)
        idx = (idx + 1) % len(self.wstypes)
        wstype = self.wstypes[idx]
        self.configure_wstype(wstype)

    def focus_index(self):
        def _f(widget):
            # TODO: this probably just ought to check whether a widget
            # *can take* focus
            if isinstance(widget, Viewers.GingaViewerWidget):
                widget.focus()
                return True
            # widget can't take focus.  If it is a container widget,
            # check its children
            if isinstance(widget, Widgets.ContainerBase):
                for child in widget.get_children():
                    if _f(child):
                        return True
                return False
            return False

        cur_idx = self.nb.get_index()
        child = self.nb.index_to_widget(cur_idx)
        _f(child)

    def to_next(self):
        num_tabs = self.nb.num_children()
        cur_idx = self.nb.get_index()
        new_idx = (cur_idx + 1) % num_tabs
        self.nb.set_index(new_idx)
        self.focus_index()

    def to_previous(self):
        num_tabs = self.nb.num_children()
        new_idx = self.nb.get_index() - 1
        if new_idx < 0:
            new_idx = max(num_tabs - 1, 0)
        self.nb.set_index(new_idx)
        self.focus_index()

    def add_tab(self, child, title=''):
        self.nb.add_widget(child, title=title)

    def remove_tab(self, child):
        self.nb.remove(child)


class SymmetricGridWidget(Widgets.GridBox):
    """Custom widget for grid-type workspace that has the API of a
    tab-like widget.
    """

    def __init__(self):
        super(SymmetricGridWidget, self).__init__()

        self.set_margins(0, 0, 0, 0)
        self.set_spacing(2)
        self.cur_index = 0

        self.enable_callback('page-switch')

    def _relayout(self, widgets):
        # remove all the old widgets
        # TEMP: this call causes a recursive loop to happen
        #self.remove_all()
        children = list(self.get_children())
        for child in children:
            super(SymmetricGridWidget, self).remove(child)

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
                    super(SymmetricGridWidget, self).add_widget(child,
                                                                i, j, stretch=1)

    def add_widget(self, child, title=''):
        widgets = list(self.get_children())
        widgets.append(child)
        # attach title to child
        child.extdata.tab_title = title

        self._relayout(widgets)

    def remove(self, child, delete=False):
        super(SymmetricGridWidget, self).remove(child)

        widgets = list(self.get_children())

        self._relayout(widgets)

    def get_index(self):
        return self.cur_index

    def set_index(self, idx):
        old_index = self.cur_index
        if 0 <= idx < self.num_children():
            self.cur_index = idx
            child = self.children[idx]
            #child.focus()

            if old_index != idx:
                self.make_callback('page-switch', child)

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
