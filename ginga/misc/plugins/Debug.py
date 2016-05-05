#
# Debug.py -- Debugging plugin for Ginga
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import time
import os

from ginga.gw import Widgets
from ginga import GingaPlugin, AstroImage
from ginga.misc import Bunch
from ginga.util import grc

class Debug(GingaPlugin.GlobalPlugin):
    """
    Usage:
    This plugin provides a command line interface to the reference viewer.

    Useful commands:

    d> help

    d> reload_local_plugin <NAME>

    d> reload_global_plugin <NAME>
    """

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(Debug, self).__init__(fv)

        self.cmd_w = None
        self.hist_w = None
        self.histlimit = 5000

        self._cmdobj = CommandInterpreter(fv, self)

    def build_gui(self, container):

        vbox = Widgets.VBox()

        self.msg_font = self.fv.getFont("fixedFont", 12)

        vbox.add_widget(Widgets.Label("Type command here:"))
        self.cmd_w = Widgets.TextEntry()
        self.cmd_w.set_font(self.msg_font)
        vbox.add_widget(self.cmd_w, stretch=0)
        self.cmd_w.add_callback('activated', self.exec_cmd_cb)

        vbox.add_widget(Widgets.Label("Output:"))
        tw = Widgets.TextArea(wrap=True, editable=False)
        tw.set_font(self.msg_font)
        tw.set_limit(self.histlimit)
        self.hist_w = tw

        ## sw = Widgets.ScrollArea()
        ## sw.set_widget(self.hist_w)
        ## vbox.add_widget(sw, stretch=1)
        vbox.add_widget(tw, stretch=1)

        btns = Widgets.HBox()
        btns.set_spacing(4)
        btns.set_border_width(4)

        btn = Widgets.Button("Close")
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn)
        btns.add_widget(Widgets.Label(''), stretch=1)
        vbox.add_widget(btns)

        container.add_widget(vbox, stretch=1)

    def exec_cmd(self, text):
        text = text.strip()
        self.log("d> " + text, w_time=True)

        if text.startswith('/'):
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
            self.log("!! No such command: '%s'" % (cmd))
            return

        try:
            res = method(*args, **kwargs)
            if res is not None:
                self.log(str(res))

            # this brings the focus back to the command bar if the command
            # causes a new window to be opened
            self.cmd_w.focus()

        except Exception as e:
            self.log("!! Error executing '%s': %s" % (text, str(e)))
            # TODO: add traceback


    def exec_cmd_cb(self, w):
        text = w.get_text()
        self.exec_cmd(text)
        w.set_text("")

    def exec_shell(self, cmd_str):
        res, out, err = grc.get_exitcode_stdout_stderr(cmd_str)
        if len(out) > 0:
            self.log(out)
        if len(err) > 0:
            self.log(err)
        if res != 0:
            self.log("command terminated with error code %d" % res)

    def log(self, text, w_time=False):
        if self.hist_w is not None:
            pfx = ''
            if w_time:
                pfx = time.strftime("%H:%M:%S", time.localtime()) + ": "
            self.hist_w.append_text(pfx + text + '\n',
                                    autoscroll=True)

    def close(self):
        self.fv.stop_global_plugin(str(self))
        return True

    def __str__(self):
        return 'debug'


class CommandInterpreter(object):

    def __init__(self, fv, plugin):
        super(CommandInterpreter, self).__init__()

        self.fv = fv
        self.plugin = plugin
        self.logger = plugin.logger
        self.log = plugin.log

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

    def cmd_reload_local_plugin(self, plname):
        """reload_local_plugin `plname`

        Reload the *local* plugin named `plname`.  You should close
        all instances of the plugin before attempting to reload.
        """
        self.fv.mm.loadModule(plname)
        for chname in self.fv.get_channelNames():
            chinfo = self.fv.get_channelInfo(chname)
            chinfo.opmon.reloadPlugin(plname, chinfo=chinfo)
        return True

    def cmd_reload_global_plugin(self, plname):
        """reload_global_plugin `plname`

        Reload the *global* plugin named `plname`.  You should close
        all instances of the plugin before attempting to reload.
        """
        gpmon = self.fv.gpmon
        pInfo = gpmon.getPluginInfo(plname)
        gpmon.stop_plugin(pInfo)
        self.fv.update_pending(0.5)
        self.fv.mm.loadModule(plname)
        gpmon.reloadPlugin(plname)
        self.fv.start_global_plugin(plname)
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

#END
