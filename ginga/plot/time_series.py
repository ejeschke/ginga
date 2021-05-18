#
# time_series.py -- utilities to assist in making time-series plots
#
import time

from ginga.canvas.types.plots import XAxis, PlotTitle, PlotBG


class XTimeAxis(XAxis):
    """Override basic XAxis to print X values as times.
    """

    def _format_value(self, t):
        return time.strftime("%H:%M:%S", time.localtime(t))


class TimePlotTitle(PlotTitle):
    """Override basic PlotTitle to print current value of latest data
    points.
    """

    def _format_label(self, lbl, plot_src):
        pt = plot_src.get_latest()
        if pt is None:
            lbl.text = "{0:}".format(plot_src.name)
        else:
            x, y = pt[:2]
            lbl.text = "{0:}: {1: .2f}".format(plot_src.name, y)


class TimePlotBG(PlotBG):
    """Override basic PlotBg to make warnings and alerts happen if the
    most recent value exceeds the thresholds.
    """

    def _check_warning(self):
        max_y = None
        for i, plot_src in enumerate(self.aide.plots.values()):
            pt = plot_src.get_latest()
            if pt is not None:
                x, y = pt[:2]
                max_y = y if max_y is None else max(max_y, y)

        if max_y is not None:
            if self.alert_y is not None and max_y > self.alert_y:
                self.alert()
            elif self.warn_y is not None and max_y > self.warn_y:
                self.warning()
            else:
                self.normal()
