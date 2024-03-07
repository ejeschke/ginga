# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
"""
The ``GingaMenubar`` plugin provides a default menubar for the Ginga
reference viewer.

**Plugin Type: Global**

``GingaMenubar`` is a global plugin.  Only one instance can be opened.

"""
from ginga import GingaPlugin
from ginga.gw import Widgets

__all__ = ['Menubar', 'GingaMenubar']


class Menubar(GingaPlugin.GlobalPlugin):
    """Base class for menu bar plugins.
    """

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super().__init__(fv)

        self.gui_up = False

    def build_gui(self, container):
        menubar = Widgets.Menubar()
        self.w.menubar = menubar

        self.add_menus()

        container.add_widget(self.w.menubar, stretch=0)
        self.gui_up = True

    def add_menus(self):
        # Subclass should override this abstract method to add any needed
        # menus to the menubar
        pass

    def add_menu(self, name):
        """Add a menu with name `name` to the global menu bar.
        Returns a menu widget.
        """
        if self.w.menubar is None:
            raise ValueError("No menu bar configured")
        return self.w.menubar.add_name(name)

    def get_menu(self, name):
        """Get the menu with name `name` from the global menu bar.
        Returns a menu widget.
        """
        if self.w.menubar is None:
            raise ValueError("No menu bar configured")
        return self.w.menubar.get_menu(name)

    def start(self):
        pass

    def stop(self):
        self.w.menubar = None
        self.gui_up = False

    def close(self):
        self.fv.stop_global_plugin(str(self))
        return True

    def __str__(self):
        return 'menubar'


class GingaMenubar(Menubar):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super().__init__(fv)

        self.gui_up = False

    def add_menus(self):

        menubar = self.w.menubar
        # create a File pulldown menu, and add it to the menu bar
        filemenu = menubar.add_name("File")

        item = filemenu.add_name("Load Image")
        item.add_callback('activated', lambda *args: self.fv.gui_load_file())

        item = filemenu.add_name("Remove Image")
        item.add_callback("activated",
                          lambda *args: self.fv.remove_current_image())

        filemenu.add_separator()

        item = filemenu.add_name("Quit")
        item.add_callback('activated', self.fv.window_close)

        # create a Channel pulldown menu, and add it to the menu bar
        chmenu = menubar.add_name("Channel")

        item = chmenu.add_name("Add Channel")
        item.add_callback('activated', lambda *args: self.fv.gui_add_channel())

        item = chmenu.add_name("Add Channels")
        item.add_callback('activated', lambda *args: self.fv.gui_add_channels())

        item = chmenu.add_name("Delete Channel")
        item.add_callback('activated', lambda *args: self.fv.gui_delete_channel())

        # create a Window pulldown menu, and add it to the menu bar
        wsmenu = menubar.add_name("Workspace")

        item = wsmenu.add_name("Add Workspace")
        item.add_callback('activated', lambda *args: self.fv.gui_add_ws())

        # # create a Option pulldown menu, and add it to the menu bar
        # optionmenu = menubar.add_name("Option")

        # create a Plugins pulldown menu, and add it to the menu bar
        plugmenu = menubar.add_name("Plugins")
        self.w.menu_plug = plugmenu

        # create a Help pulldown menu, and add it to the menu bar
        helpmenu = menubar.add_name("Help")

        item = helpmenu.add_name("About")
        item.add_callback('activated',
                          lambda *args: self.fv.banner())

        item = helpmenu.add_name("Documentation")
        item.add_callback('activated', lambda *args: self.fv.help())

    def add_plugin_menu(self, name, spec):
        if not self.gui_up:
            return
        # NOTE: self.w.menu_plug is a ginga.Widgets wrapper
        if 'menu_plug' not in self.w:
            return
        category = spec.get('category', None)
        categories = None
        if category is not None:
            categories = category.split('.')
        menuname = spec.get('menu', spec.get('tab', name))

        menu = self.w.menu_plug
        if categories is not None:
            for catname in categories:
                try:
                    menu = menu.get_menu(catname)
                except KeyError:
                    menu = menu.add_menu(catname)

        item = menu.add_name(menuname)
        item.add_callback('activated',
                          lambda *args: self.fv.start_plugin(name, spec))

    def start(self):
        plugins = self.fv.get_plugins()
        for spec in plugins:
            if spec.get('hidden', False) or not spec.get('enabled', True):
                continue
            name = spec.get('name', spec.get('klass', spec.get('module')))
            self.fv.error_wrap(self.add_plugin_menu, name, spec)

    def __str__(self):
        return 'gingamenubar'
