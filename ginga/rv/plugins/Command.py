# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
"""
This plugin provides a command line interface to the reference viewer.

.. note:: The command line is for use *within* the plugin UI.
          If you are looking for a *remote* command line interface,
          please see the ``RC`` plugin.

**Plugin Type: Global**

``Command`` is a global plugin.  Only one instance can be opened.

**Usage**

Get a list of commands and parameters::

        g> help

Execute a shell command::

        g> !cmd arg arg ...

**Notes**

An especially powerful tool is to use the ``reload_local`` and
``reload_global`` commands to reload a plugin when you are developing
that plugin.  This avoids having to restart the reference viewer and
laboriously reload data, etc.  Simply close the plugin, execute the
appropriate "reload" command (see the help!) and then start the plugin
again.

.. note:: If you have modifed modules *other* than the plugin itself,
          these will not be reloaded by these commands.

"""
import time
import os
import glob

from ginga.gw import Widgets
from ginga import GingaPlugin
from ginga.util import grc

__all__ = ['Command']


class Command(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(Command, self).__init__(fv)

        self.cmd_w = None
        self.hist_w = None
        self.histlimit = 5000

        self._cmdobj = CommandInterpreter(fv, self)

    def build_gui(self, container):

        vbox = Widgets.VBox()

        self.msg_font = self.fv.get_font('fixed', 12)

        vbox.add_widget(Widgets.Label("Output:"))
        tw = Widgets.TextArea(wrap=True, editable=False)
        tw.set_font(self.msg_font)
        tw.set_limit(self.histlimit)
        self.hist_w = tw

        vbox2 = Widgets.VBox()
        vbox2.add_widget(tw, stretch=1)
        vbox2.add_widget(Widgets.Label(''), stretch=0)

        vbox.add_widget(vbox2, stretch=1)

        vbox2 = Widgets.VBox()
        vbox2.add_widget(Widgets.Label("Type command here:"))
        self.cmd_w = Widgets.TextEntry()
        self.cmd_w.set_font(self.msg_font)
        vbox2.add_widget(self.cmd_w, stretch=0)
        self.cmd_w.add_callback('activated', self.exec_cmd_cb)
        vbox.add_widget(vbox2, stretch=0)

        btns = Widgets.HBox()
        btns.set_spacing(4)
        btns.set_border_width(4)

        btn = Widgets.Button("Close")
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn)
        btn = Widgets.Button("Help")
        btn.add_callback('activated', lambda w: self.help())
        btns.add_widget(btn, stretch=0)
        btns.add_widget(Widgets.Label(''), stretch=1)
        vbox.add_widget(btns, stretch=0)

        container.add_widget(vbox, stretch=1)

    def exec_cmd(self, text):
        text = text.strip()
        self.log("g> " + text, w_time=True)

        if text.startswith('!'):
            # escape to shell for this command
            self.exec_shell(text[1:])
            return

        args = text.split()
        cmd, tokens = args[0], args[1:]

        # process args
        args, kwargs = grc.prep_args(tokens)

        try:
            method = getattr(self._cmdobj, "cmd_" + cmd.lower())

        except AttributeError:
            self.log("|E| No such command: '%s'" % (cmd))
            return

        try:
            res = method(*args, **kwargs)
            if res is not None:
                self.log(str(res))

            # this brings the focus back to the command bar if the command
            # causes a new window to be opened
            self.cmd_w.focus()

        except Exception as e:
            self.log("|E| Error executing '%s': %s" % (text, str(e)))
            # TODO: add traceback

    def exec_cmd_cb(self, w):
        text = w.get_text()
        self.exec_cmd(text)
        w.set_text("")

    def exec_shell(self, cmd_str):
        res, out, err = grc.get_exitcode_stdout_stderr(cmd_str)
        if len(out) > 0:
            self.log(out.decode('utf-8'))
        if len(err) > 0:
            self.log(err.decode('utf-8'))
        if res != 0:
            self.log("command terminated with error code %d" % res)

    def log(self, text, w_time=False):
        if self.hist_w is not None:
            pfx = ''
            if w_time:
                pfx = time.strftime("%H:%M:%S", time.localtime()) + ": "
            self.fv.gui_do(self.hist_w.append_text, pfx + text + '\n',
                           autoscroll=True)
            #self.fv.update_pending()

    def close(self):
        self.fv.stop_global_plugin(str(self))
        return True

    def __str__(self):
        return 'command'


class CommandInterpreter(object):

    def __init__(self, fv, plugin):
        super(CommandInterpreter, self).__init__()

        self.fv = fv
        self.plugin = plugin
        self.logger = plugin.logger
        self.log = plugin.log

    def get_viewer(self, chname):
        if chname is None:
            channel = self.fv.get_channel_info()
        else:
            channel = self.fv.get_channel_on_demand(chname)

        viewer = channel.viewer
        return viewer

    ##### COMMANDS #####

    def cmd_help(self, *args):
        """help [cmd]

        Get general help, or help for command `cmd`.
        """
        if len(args) > 0:
            cmdname = args[0].lower()
            try:
                method = getattr(self, "cmd_" + cmdname)
                doc = method.__doc__
                if doc is None:
                    self.log("Sorry, no documentation found for '%s'" % (
                        cmdname))
                else:
                    self.log("%s: %s" % (cmdname, doc))
            except AttributeError:
                self.log("No such command '%s'; type help for general help." % (
                    cmdname))
        else:
            res = []
            for attrname in dir(self):
                if attrname.startswith('cmd_'):
                    method = getattr(self, attrname)
                    doc = method.__doc__
                    cmdname = attrname[4:]
                    if doc is None:
                        doc = "no documentation"
                    res.append("%s: %s" % (cmdname, doc))
            self.log('\n'.join(res))

    def cmd_reload_local(self, plname):
        """reload_local `plname`

        Reload the *local* plugin named `plname`.  You should close
        all instances of the plugin before attempting to reload.
        """
        self.fv.mm.load_module(plname)
        for chname in self.fv.get_channel_names():
            chinfo = self.fv.get_channel(chname)
            chinfo.opmon.reload_plugin(plname, chinfo=chinfo)
        return True

    def cmd_reload_global(self, plname):
        """reload_global `plname`

        Reload the *global* plugin named `plname`.  You should close
        all instances of the plugin before attempting to reload.
        """
        gpmon = self.fv.gpmon
        p_info = gpmon.get_plugin_info(plname)
        gpmon.stop_plugin(p_info)
        self.fv.update_pending(0.5)
        self.fv.mm.load_module(plname)
        gpmon.reload_plugin(plname)
        self.fv.start_global_plugin(plname)
        return True

    def cmd_reload_module(self, modname):
        """reload_module `modname`

        Reload the Python module named `modname`.
        """
        self.fv.mm.load_module(modname)
        return True

    def cmd_cd(self, *args):
        """cd [path]

        Change the current working directory to `path`.
        """
        if len(args) == 0:
            path = os.environ['HOME']
        else:
            path = args[0]
        os.chdir(path)
        self.cmd_pwd()

    def cmd_ls(self, *args):
        """ls [options]

        Execute list files command
        """
        cmd_str = ' '.join(['ls'] + list(args))
        self.plugin.exec_shell(cmd_str)

    def cmd_pwd(self):
        """pwd

        List the current working directory.
        """
        self.log("%s" % (os.getcwd()))

    def cmd_load(self, *args, **kwargs):
        """load file ... ch=chname

        Read files or URLs into the given channel.

        If the item is a path and it does not begin with a slash it is assumed
        to be relative to the current working directory.  File patterns can
        also be provided.
        """
        ch = kwargs.get('ch', None)

        for item in args:
            # TODO: check for URI syntax
            files = glob.glob(item)
            self.fv.gui_do(self.fv.open_uris, files, chname=ch)

    def cmd_cuts(self, lo=None, hi=None, ch=None):
        """cuts lo=val hi=val ch=chname

        If neither `lo` nor `hi` is provided, returns the current cut levels.
        Otherwise sets the corresponding cut level for the given channel.
        If `ch` is omitted, assumes the current channel.
        """
        viewer = self.get_viewer(ch)
        if viewer is None:
            self.log("No current viewer/channel.")
            return

        loval, hival = viewer.get_cut_levels()

        if (lo is None) and (hi is None):
            self.log("lo=%f hi=%f" % (loval, hival))

        else:
            if lo is not None:
                loval = lo
            if hi is not None:
                hival = hi
            viewer.cut_levels(loval, hival)

            self.log("lo=%f hi=%f" % (loval, hival))

    def cmd_ac(self, ch=None):
        """ac ch=chname

        Calculate and set auto cut levels for the given channel.
        If `ch` is omitted, assumes the current channel.
        """
        viewer = self.get_viewer(ch)
        if viewer is None:
            self.log("No current viewer/channel.")
            return

        viewer.auto_levels()
        self.cmd_cuts(ch=ch)

    def cmd_lscm(self):
        """lscm

        List the possible color maps that can be loaded.
        """
        self.log("\n".join(self.fv.get_color_maps()))

    def cmd_cm(self, nm=None, ch=None):
        """cm nm=color_map_name ch=chname

        Set a color map (name `nm`) for the given channel.
        If no value is given, reports the current color map.
        """
        viewer = self.get_viewer(ch)
        if viewer is None:
            self.log("No current viewer/channel.")
            return

        if nm is None:
            rgbmap = viewer.get_rgbmap()
            cmap = rgbmap.get_cmap()
            self.log(cmap.name)

        else:
            viewer.set_color_map(nm)

    def cmd_cminv(self, ch=None):
        """cminv ch=chname

        Invert the color map in the channel/viewer
        """
        viewer = self.get_viewer(ch)
        if viewer is None:
            self.log("No current viewer/channel.")
            return

        viewer.invert_cmap()

    def cmd_dist(self, nm=None, ch=None):
        """dist nm=dist_name ch=chname

        Set a color distribution for the given channel.
        Possible values are linear, log, power, sqrt, squared, asinh, sinh,
        and histeq.

        If no value is given, reports the current color distribution
        algorithm.
        """
        viewer = self.get_viewer(ch)
        if viewer is None:
            self.log("No current viewer/channel.")
            return

        if nm is None:
            rgbmap = viewer.get_rgbmap()
            dist = rgbmap.get_dist()
            self.log(str(dist))
        else:
            viewer.set_color_algorithm(nm)

    def cmd_lsimap(self):
        """lsimap

        List the possible intensity maps that can be loaded.
        """
        self.log("\n".join(self.fv.get_intensity_maps()))

    def cmd_imap(self, nm=None, ch=None):
        """imap nm=intensity_map_name ch=chname

        Set an intensity map (name `nm`) for the given channel.
        If no value is given, reports the current intensity map.
        """
        viewer = self.get_viewer(ch)
        if viewer is None:
            self.log("No current viewer/channel.")
            return

        if nm is None:
            rgbmap = viewer.get_rgbmap()
            imap = rgbmap.get_imap()
            self.log(imap.name)

        else:
            viewer.set_intensity_map(nm)

    def cmd_lsch(self):
        """lsch

        List the channels, showing the current one.
        """
        names = list(self.fv.get_channel_names())
        names.sort()

        if len(names) == 0:
            self.log("No channels")
            return

        res = []
        cur_ch = self.fv.get_channel_info()
        for name in names:
            if (cur_ch is not None) and (cur_ch.name == name):
                res.append("=>%s" % (name))
            else:
                res.append("  %s" % (name))

        self.log("\n".join(res))

    def cmd_rot(self, deg=None, ch=None):
        """rot deg=num_deg ch=chname

        Rotate the image for the given viewer/channel by the given
        number of degrees.
        If no value is given, reports the current rotation.
        """
        viewer = self.get_viewer(ch)
        if viewer is None:
            self.log("No current viewer/channel.")
            return

        if deg is None:
            self.log("%f deg" % (viewer.get_rotation()))

        else:
            viewer.rotate(deg)

    def cmd_tr(self, x=None, y=None, xy=None, ch=None):
        """tr x=0|1 y=0|1 xy=0|1 ch=chname

        Transform the image for the given viewer/channel by flipping
        (x=1 and/or y=1) or swapping axes (xy=1).
        If no value is given, reports the current rotation.
        """
        viewer = self.get_viewer(ch)
        if viewer is None:
            self.log("No current viewer/channel.")
            return

        fx, fy, sxy = viewer.get_transforms()

        if x is None and y is None and xy is None:
            self.log("x=%s y=%s xy=%s" % (fx, fy, sxy))

        else:
            # turn these into True or False
            if x is None:
                x = fx
            else:
                x = (x != 0)
            if y is None:
                y = fy
            else:
                y = (y != 0)
            if xy is None:
                xy = sxy
            else:
                xy = (xy != 0)

            viewer.transform(x, y, xy)

    def cmd_scale(self, x=None, y=None, ch=None):
        """scale x=scale_x y=scale_y ch=chname

        Scale the image for the given viewer/channel by the given amounts.
        If only one scale value is given, the other is assumed to be the
        same.  If no value is given, reports the current scale.
        """
        viewer = self.get_viewer(ch)
        if viewer is None:
            self.log("No current viewer/channel.")
            return

        scale_x, scale_y = viewer.get_scale_xy()

        if x is None and y is None:
            self.log("x=%f y=%f" % (scale_x, scale_y))

        else:
            if x is not None:
                if y is None:
                    y = x
            if y is not None:
                if x is None:
                    x = y
            viewer.scale_to(x, y)

    def cmd_z(self, lvl=None, ch=None):
        """z lvl=level ch=chname

        Zoom the image for the given viewer/channel to the given zoom
        level.  Levels can be positive or negative numbers and are
        relative to a scale of 1:1 at zoom level 0.
        """
        viewer = self.get_viewer(ch)
        if viewer is None:
            self.log("No current viewer/channel.")
            return

        cur_lvl = viewer.get_zoom()

        if lvl is None:
            self.log("zoom=%f" % (cur_lvl))

        else:
            viewer.zoom_to(lvl)

    def cmd_zf(self, ch=None):
        """zf ch=chname

        Zoom the image for the given viewer/channel to fit the window.
        """
        viewer = self.get_viewer(ch)
        if viewer is None:
            self.log("No current viewer/channel.")
            return

        viewer.zoom_fit()
        cur_lvl = viewer.get_zoom()
        self.log("zoom=%f" % (cur_lvl))

    def cmd_c(self, ch=None):
        """c ch=chname

        Center the image for the given viewer/channel.
        """
        viewer = self.get_viewer(ch)
        if viewer is None:
            self.log("No current viewer/channel.")
            return

        viewer.center_image()

    def cmd_pan(self, x=None, y=None, ch=None):
        """scale ch=chname x=pan_x y=pan_y

        Set the pan position for the given viewer/channel to the given
        pixel coordinates.
        If no coordinates are given, reports the current position.
        """
        viewer = self.get_viewer(ch)
        if viewer is None:
            self.log("No current viewer/channel.")
            return

        pan_x, pan_y = viewer.get_pan()

        if x is None and y is None:
            self.log("x=%f y=%f" % (pan_x, pan_y))

        else:
            if x is not None:
                if y is None:
                    y = pan_y
            if y is not None:
                if x is None:
                    x = pan_x
            viewer.set_pan(x, y)

# END
