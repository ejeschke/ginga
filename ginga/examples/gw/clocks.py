#! /usr/bin/env python
#
# clocks.py -- Ginga clocks
#
# eric@naoj.org
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""
"clocks" displays a grid of clocks in different time zones.

Usage:
  $ clock.py HST Asia/Tokyo UTC US/Eastern US/Pacific Hongkong Portugal
  $ clock.py --help
  $ clock.py --show-timezones
  $ clock.py --show-colors
"""
import sys, os
import logging
import pytz
from datetime import datetime
from dateutil import tz

from ginga import colors
import ginga.toolkit as ginga_toolkit
from ginga.canvas.CanvasObject import get_canvas_types
from ginga.misc import log
from ginga.misc.Settings import SettingGroup
from ginga.util.six.moves import map
from ginga.misc.Bunch import Bunch
from ginga.util.paths import ginga_home


width, height = 300, 230


class Clock(object):

    def __init__(self, app, logger, timezone, color='lightgreen',
                 font='Liberation Sans', show_seconds=False):
        """Constructor for a clock object using a ginga canvas.
        """
        self.logger = logger

        if isinstance(timezone, Bunch):
            self.timezone = timezone.location
            self.tzinfo = tz.tzoffset(timezone.location, timezone.time_offset)
        else:
            self.timezone = timezone
            self.tzinfo = pytz.timezone(timezone)

        self.color = color
        self.font = font
        self.largesize = 72
        self.smallsize = 24
        self.show_seconds = show_seconds

        # now import our items
        from ginga.gw import Widgets, Viewers, GwHelp

        fi = Viewers.CanvasView(logger=logger)
        fi.set_bg(0.2, 0.2, 0.2)
        self.viewer = fi
        fi.add_callback('configure', self.clock_resized_cb)

        # canvas that we will draw on
        self.canvas = fi.get_canvas()

        wd, ht = width, height
        if self.show_seconds:
            wd += 300

        fi.set_desired_size(wd, ht)
        iw = Viewers.GingaViewerWidget(viewer=fi)

        self.widget = iw

        self.clock_resized_cb(self.viewer, wd, ht)

        dt = datetime.utcnow().replace(tzinfo=pytz.utc)
        self.update_clock(dt)

    def clock_resized_cb(self, viewer, width, height):
        """This method is called when an individual clock is resized.
        It deletes and reconstructs the placement of the text objects
        in the canvas.
        """
        self.logger.info("resized canvas to %dx%d" % (width, height))
        # add text objects to canvas

        self.canvas.delete_all_objects()

        Text = self.canvas.get_draw_class('text')
        x, y = 20, int(height * 0.55)
        # text object for the time
        self.time_txt = Text(x, y, text='', color=self.color,
                             font=self.font, fontsize=self.largesize,
                             coord='canvas')
        self.canvas.add(self.time_txt, tag='_time', redraw=False)

        # for supplementary info (date, timezone, etc)
        self.suppl_txt = Text(x, height-10, text='', color=self.color,
                              font=self.font, fontsize=self.smallsize,
                              coord='canvas')
        self.canvas.add(self.suppl_txt, tag='_suppl', redraw=False)

        self.canvas.update_canvas(whence=3)

    def update_clock(self, dt):
        """This method is called by the ClockApp whenever the timer fires
        to update the clock.  `dt` is a timezone-aware datetime object.
        """
        dt = dt.astimezone(self.tzinfo)
        fmt = "%H:%M"
        if self.show_seconds:
            fmt = "%H:%M:%S"

        self.time_txt.text = dt.strftime(fmt)

        suppl_text = "{0} {1}".format(dt.strftime("%Y-%m-%d"), self.timezone)
        self.suppl_txt.text = suppl_text

        self.viewer.redraw(whence=3)


class ClockApp(object):

    def __init__(self, logger, settings, options):
        self.logger = logger
        self.options = options
        self.settings = settings

        colors = ['lightgreen', 'orange', 'cyan', 'pink', 'slateblue',
                  'yellow', 'maroon', 'brown']
        self.color_index = 0

        cols = 3
        if options.num_cols is not None:
            cols = options.num_cols

        self.settings.add_defaults(columns=cols, zones=['UTC'],
                                   colors=colors)
        self.colors = self.settings.get('colors', colors)

        # now import our items
        from ginga.gw import Widgets, Viewers, GwHelp

        self.app = Widgets.Application(logger=logger)
        self.app.add_callback('shutdown', self.quit)
        self.top = self.app.make_window("Clocks")
        self.top.add_callback('close', self.closed)


        menubar = Widgets.Menubar()
        clockmenu = menubar.add_name('Clock')
        item = clockmenu.add_name("Quit")
        item.add_callback('activated', lambda *args: self.quit())

        self.top.set_widget(menubar)

        vbox = Widgets.VBox()
        self.grid = Widgets.GridBox()
        self.grid.set_border_width(1)
        self.grid.set_spacing(2)
        vbox.add_widget(self.grid, stretch=1)
        self.top.set_widget(vbox)


        hbox = Widgets.HBox()

        self.timezone_label = Widgets.Label('TimeZone')
        self.county_timezone = Widgets.ComboBox()
        self.county_timezone.widget.setEditable(True)

        # make a giant list of time zones
        zones = [timezone for timezones in pytz.country_timezones.values()
                 for timezone in timezones]
        zones.sort()
        for timezone in zones:
            self.county_timezone.append_text(timezone)

        # also let user set timezone by UTC offset
        self.location_label = Widgets.Label('Location')
        self.location = Widgets.TextEntry()
        #self.location.set_length(10)
        self.timeoffset_label = Widgets.Label('UTC Offset(hour)')
        self.time_offset = Widgets.SpinBox(dtype=float)
        self.time_offset.set_decimals(2)
        self.time_offset.set_limits(-12, 12)
        self.timezone_button =  Widgets.Button('Add by Timezone')
        self.offset_button =  Widgets.Button('Add by Offset')

        self.timezone_button.widget.clicked.connect(self.more_clock_by_timezone)
        self.offset_button.widget.clicked.connect(self.more_clock_by_offset)

        hbox.add_widget(self.timezone_label, stretch=0)
        hbox.add_widget(self.county_timezone, stretch=0)
        hbox.add_widget(self.timezone_button, stretch=0)
        hbox.add_widget(Widgets.Label(''), stretch=1)

        hbox.add_widget(self.location_label, stretch=0)
        hbox.add_widget(self.location, stretch=0)

        hbox.add_widget(self.timeoffset_label, stretch=0)
        hbox.add_widget(self.time_offset, stretch=0)
        hbox.add_widget(self.offset_button, stretch=0)
        hbox.add_widget(Widgets.Label(''), stretch=1)

        self.top.set_widget(hbox)

        self.clocks = {}
        self.timer = GwHelp.Timer(1.0)
        self.timer.add_callback('expired', self.timer_cb)
        self.timer.start(1.0)

    def more_clock_by_offset(self):
        location = self.location.get_text()
        time_offset = self.time_offset.get_value()
        sec_hour = 3600
        timezone = Bunch(location=location, time_offset=time_offset*sec_hour)
        color = self.colors[self.color_index % len(self.colors)]
        self.color_index += 1
        self.add_clock(timezone=timezone, color=color)

    def more_clock_by_timezone(self):
        index = self.county_timezone.get_index()
        timezone = self.county_timezone.get_alpha(index)
        color = self.colors[self.color_index % len(self.colors)]
        self.color_index += 1

        self.add_clock(timezone=timezone, color=color)

    def add_clock(self, timezone, color='lightgreen', show_seconds=None):
        """Add a clock to the grid.  `timezone` is a string representing
        a valid timezone.
        """
        if show_seconds is None:
            show_seconds = self.options.show_seconds

        clock = Clock(self.app, self.logger, timezone, color=color,
                      font=self.options.font, show_seconds=show_seconds)
        clock.widget.cfg_expand(0x7, 0x7)

        num_clocks = len(self.clocks)
        cols = self.settings.get('columns')
        row = num_clocks // cols
        col = num_clocks % cols
        self.clocks[timezone] = clock

        self.grid.add_widget(clock.widget, row, col, stretch=1)

    def timer_cb(self, timer):
        """Timer callback.  Update all our clocks."""
        dt_now = datetime.utcnow().replace(tzinfo=pytz.utc)
        self.logger.debug("timer fired. utc time is '%s'" % (str(dt_now)))

        for clock in self.clocks.values():
            clock.update_clock(dt_now)

        # update clocks approx every second
        timer.start(1.0)

    def set_geometry(self, geometry):
        # translation of X window geometry specification WxH+X+Y
        coords = geometry.replace('+', ' +')
        coords = coords.replace('-', ' -')
        coords = coords.split()
        if 'x' in coords[0]:
            # spec includes dimensions
            dim = coords[0]
            coords = coords[1:]
        else:
            # spec is position only
            dim = None

        if dim is not None:
            # user specified dimensions
            dim = list(map(int, dim.split('x')))
            self.top.resize(*dim)

        if len(coords) > 0:
            # user specified position
            coords = list(map(int, coords))
            self.top.move(*coords)

    def closed(self, w):
        self.logger.info("Top window closed.")
        self.top = None
        sys.exit()

    def quit(self, *args):
        self.logger.info("Attempting to shut down the application...")
        if not self.top is None:
            self.top.close()
        sys.exit()


def main(options, args):

    # TODO: when ginga gets updated on the summit
    logger = log.get_logger("clocks", options=options)

    if options.toolkit is None:
        logger.error("Please choose a GUI toolkit with -t option")

    # decide our toolkit, then import
    ginga_toolkit.use(options.toolkit)

    cfgfile = os.path.join(ginga_home, "clocks.cfg")
    settings = SettingGroup(name='clocks', logger=logger,
                            preffile=cfgfile)
    settings.load(onError='silent')

    clock = ClockApp(logger, settings, options)

    if len(options.args) == 0:
        zones = ['UTC']
        #zones = ['HST', 'Asia/Tokyo', 'UTC']
    else:
        zones = options.args
    cols = settings.get('columns', 3)

    wd, ht = width * cols, height
    if options.show_seconds:
        wd += cols * 300
    clock.top.resize(wd, ht)

    # get the list of colors
    if options.colors is None:
        colors = clock.colors
    else:
        colors = options.colors.split(',')

    # get the list of time zones
    for i, zone in enumerate(zones):
        color = colors[i % len(colors)]
        clock.add_clock(zone, color=color)
        clock.color_index = i + 1

    clock.top.show()

    if options.geometry is not None:
        clock.set_geometry(options.geometry)

    clock.top.raise_()

    try:
        app = clock.top.get_app()
        app.mainloop()

    except KeyboardInterrupt:
        if clock.top is not None:
            clock.top.close()

    logger.info("Terminating clocks...")


if __name__ == "__main__":

    # Parse command line options
    import argparse

    usage = "usage: %prog [options]"
    argprs = argparse.ArgumentParser(description="Parse command line options to clock")

    argprs.add_argument("args", type=str, nargs='*',
                        help="All remaining arguments")
    argprs.add_argument("--colors", dest="colors", metavar="COLORS",
                        default=None,
                        help="Comma-separated list of COLORS to use for clocks")
    argprs.add_argument("--debug", dest="debug", default=False,
                        action="store_true",
                        help="Enter the pdb debugger on main()")
    argprs.add_argument("--display", dest="display", metavar="HOST:N",
                        help="Use X display on HOST:N")
    argprs.add_argument("--font", dest="font", metavar="NAME",
                        default='Liberation Sans',
                        help="Choose font NAME")
    argprs.add_argument("-g", "--geometry", dest="geometry",
                        metavar="GEOM",
                        help="X geometry for initial size and placement")
    argprs.add_argument("-c", "--num-cols", dest="num_cols",
                        metavar="NUM", type=int, default=None,
                        help="Number of columns to use")
    argprs.add_argument("--profile", dest="profile", action="store_true",
                        default=False,
                        help="Run the profiler on main()")
    argprs.add_argument("-s", "--show-seconds", dest="show_seconds",
                        default=False, action="store_true",
                        help="Show seconds on the clock")
    argprs.add_argument("--show-colors", dest="show_colors",
                        default=False, action="store_true",
                        help="Show a list of valid colors")
    argprs.add_argument("--show-timezones", dest="show_timezones",
                        default=False, action="store_true",
                        help="Show a list of valid time zones and exit")
    argprs.add_argument("-t", "--toolkit", dest="toolkit", metavar="NAME",
                        default='qt',
                        help="Choose GUI toolkit (gtk|qt)")
    log.addlogopts(argprs)

    options = argprs.parse_args()
    args = options.args

    if options.show_timezones:
        for timezone in pytz.all_timezones:
            print(timezone)
        sys.exit(0)

    if options.show_colors:
        names = colors.get_colors()
        for color in names:
            print(color)
        sys.exit(0)

    if options.display:
        os.environ['DISPLAY'] = options.display

    # Are we debugging this?
    if options.debug:
        import pdb

        pdb.run('main(options, args)')

    # Are we profiling this?
    elif options.profile:
        import profile

        print(("%s profile:" % sys.argv[0]))
        profile.run('main(options, args)')


    else:
        main(options, args)

# END
