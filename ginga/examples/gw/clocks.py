#! /usr/bin/env python
#
# clocks.py -- Ginga clocks
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

NOTE: needs python >= 3.9
"""
import sys
import os
from datetime import datetime, timezone, timedelta
import zoneinfo

import ginga.toolkit as ginga_toolkit
from ginga import colors
from ginga.misc import log
from ginga.misc.Bunch import Bunch
from ginga.misc.Settings import SettingGroup
from ginga.util.paths import ginga_home

width, height = 300, 230


class Clock(object):

    def __init__(self, app, logger, timezone_info, color='lightgreen',
                 font='Liberation Sans', show_seconds=False):
        """Constructor for a clock object using a ginga canvas.
        """
        self.logger = logger

        if isinstance(timezone_info, Bunch):
            self.timezone_name = timezone_info.location
            self.tzinfo = timezone(timedelta(days=0,
                                             seconds=int(timezone_info.time_offset)),
                                   name=self.timezone_name)
        else:
            # assume timezone_info is a str
            self.timezone_name = timezone_info
            self.tzinfo = zoneinfo.ZoneInfo(timezone_info)

        self.color = color
        self.font = font
        self.largesize = 72
        self.smallsize = 24
        self.show_seconds = show_seconds

        # now import our items
        from ginga.gw import Viewers

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

        dt = datetime.now(tz=timezone.utc)
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
                             coord='window')
        self.canvas.add(self.time_txt, tag='_time', redraw=False)

        # for supplementary info (date, timezone, etc)
        self.suppl_txt = Text(x, height - 10, text='', color=self.color,
                              font=self.font, fontsize=self.smallsize,
                              coord='window')
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

        suppl_text = "{0} {1}".format(dt.strftime("%Y-%m-%d"),
                                      self.timezone_name)
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
        from ginga.gw import Widgets, GwHelp

        self.app = Widgets.Application(logger=logger)
        self.app.add_callback('shutdown', self.quit)
        self.top = self.app.make_window("Clocks")
        self.top.add_callback('close', self.closed)

        vbox = Widgets.VBox()

        menubar = Widgets.Menubar()
        clockmenu = menubar.add_name('Clock')
        item = clockmenu.add_name("Quit")
        item.add_callback('activated', lambda *args: self.quit())
        vbox.add_widget(menubar, stretch=0)

        self.grid = Widgets.GridBox()
        self.grid.set_border_width(1)
        self.grid.set_spacing(2)
        vbox.add_widget(self.grid, stretch=1)

        hbox = Widgets.HBox()

        self.timezone_label = Widgets.Label('TimeZone')
        self.country_timezone = Widgets.ComboBox(editable=True)

        # make a giant list of time zones
        zones = list(zoneinfo.available_timezones())
        zones.sort()
        for zonename in zones:
            self.country_timezone.append_text(zonename)

        # also let user set timezone by UTC offset
        self.location_label = Widgets.Label('Location')
        self.location = Widgets.TextEntry()
        self.location.set_tooltip("Type a label to denote this UTC offset")
        #self.location.set_length(10)
        self.timeoffset_label = Widgets.Label('UTC Offset(hour)')
        self.time_offset = Widgets.SpinBox(dtype=float)
        self.time_offset.set_decimals(2)
        self.time_offset.set_limits(-12, 12)
        self.time_offset.set_tooltip("Time offset from UTC")
        self.timezone_button = Widgets.Button('Add by Timezone')
        self.offset_button = Widgets.Button('Add by Offset')

        self.timezone_button.add_callback('activated',
                                          self.more_clock_by_timezone)
        self.offset_button.add_callback('activated',
                                        self.more_clock_by_offset)

        hbox.add_widget(self.timezone_label, stretch=0)
        hbox.add_widget(self.country_timezone, stretch=0)
        hbox.add_widget(self.timezone_button, stretch=0)
        hbox.add_widget(Widgets.Label(''), stretch=1)

        hbox.add_widget(self.location_label, stretch=0)
        hbox.add_widget(self.location, stretch=0)

        hbox.add_widget(self.timeoffset_label, stretch=0)
        hbox.add_widget(self.time_offset, stretch=0)
        hbox.add_widget(self.offset_button, stretch=0)
        hbox.add_widget(Widgets.Label(''), stretch=1)

        vbox.add_widget(hbox, stretch=0)
        self.top.set_widget(vbox)

        self.clocks = {}
        self.timer = GwHelp.Timer(1.0)
        self.timer.add_callback('expired', self.timer_cb)
        self.timer.start(1.0)

    def more_clock_by_offset(self, w):
        location = self.location.get_text().strip()
        time_offset = self.time_offset.get_value()
        sec_hour = 3600
        if location == "":
            location = f"UTC{time_offset:+.2f}"
        timezone_info = Bunch(location=location,
                              time_offset=time_offset * sec_hour)
        color = self.colors[self.color_index % len(self.colors)]
        self.color_index += 1
        self.add_clock(timezone_info, color=color)

    def more_clock_by_timezone(self, w):
        timezone_info = self.country_timezone.get_text()
        color = self.colors[self.color_index % len(self.colors)]
        self.color_index += 1

        self.add_clock(timezone_info, color=color)

    def add_clock(self, timezone_info, color='lightgreen', show_seconds=None):
        """Add a clock to the grid.  `timezone_info` is a string representing
        a valid timezone.
        """
        if show_seconds is None:
            show_seconds = self.options.show_seconds

        clock = Clock(self.app, self.logger, timezone_info, color=color,
                      font=self.options.font, show_seconds=show_seconds)
        clock.widget.cfg_expand(horizontal='expanding', vertical='expanding')

        num_clocks = len(self.clocks)
        cols = self.settings.get('columns')
        row = num_clocks // cols
        col = num_clocks % cols
        if not isinstance(timezone_info, str):
            timezone_info = timezone_info.location
        self.clocks[timezone_info] = clock

        self.grid.add_widget(clock.widget, row, col, stretch=1)

    def timer_cb(self, timer):
        """Timer callback.  Update all our clocks."""
        dt_now = datetime.now(tz=timezone.utc)
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
            dim = [int(i) for i in dim.split('x')]
            self.top.resize(*dim)

        if len(coords) > 0:
            # user specified position
            coords = [int(i) for i in coords]
            self.top.move(*coords)

    def closed(self, w):
        self.logger.info("Top window closed.")
        top = self.top
        self.top = None
        self.app.quit()

    def quit(self, *args):
        self.logger.info("Attempting to shut down the application...")
        if self.top is not None:
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
                        default='qt5',
                        help="Choose GUI toolkit (gtk|qt)")
    log.addlogopts(argprs)

    options = argprs.parse_args()
    args = options.args

    if options.show_timezones:
        zones = list(zoneinfo.available_timezones())
        zones.sort()
        for zonename in zones:
            print(zonename)
        sys.exit(0)

    if options.show_colors:
        names = colors.get_colors()
        for color in names:
            print(color)
        sys.exit(0)

    if options.display:
        os.environ['DISPLAY'] = options.display

    main(options, args)
