# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.misc import ParamSet, Bunch
from ginga import AutoCuts
from ginga.gw import Widgets

from .base import Stage, StageAction


class Cuts(Stage):

    _stagename = 'cut-levels'

    def __init__(self):
        super().__init__()

        self.autocuts = None
        self.autocuts_cache = {}
        self.autocuts_methods = []
        self._auto = True
        self._locut = 0.0
        self._hicut = 0.0
        self._vmin = 0
        self._vmax = 255
        self.__varlist = ['auto', 'locut', 'hicut', 'vmin', 'vmax']

    def build_gui(self, container):
        self.viewer = self.pipeline.get('viewer')

        top = Widgets.VBox()
        fr = Widgets.Frame("Cuts")

        captions = (('Auto:', 'label', 'Auto', 'checkbutton'),
                    ('Cut Low:', 'label', 'locut', 'entryset'),
                    ('Cut High:', 'label', 'hicut', 'entryset'),
                    ('__sp1', 'spacer', 'hbox1', 'hbox'),
                    ('VMin:', 'label', 'vmin', 'entryset'),
                    ('VMax:', 'label', 'vmax', 'entryset'),
                    )
        w, b = Widgets.build_info(captions, orientation='vertical')

        b.auto.set_tooltip("Auto calculate cut levels")
        b.auto.set_state(self._auto)
        b.auto.add_callback('activated', self.auto_cb)
        b.locut.set_text(str(self._locut))
        b.locut.set_tooltip("Set low cut level")
        b.locut.add_callback('activated', self.manual_cuts_cb)
        b.hicut.set_text(str(self._hicut))
        b.hicut.set_tooltip("Set high cut level")
        b.hicut.add_callback('activated', self.manual_cuts_cb)

        b.vmin.set_text(str(self.vmin))
        b.vmin.set_tooltip("Set output minimum level")
        b.vmin.add_callback('activated', self.manual_output_cb)
        b.vmax.set_text(str(self.vmax))
        b.vmax.set_tooltip("Set output maximum level")
        b.vmax.add_callback('activated', self.manual_output_cb)

        b.copy_from_viewer = Widgets.Button("Copy from viewer")
        b.copy_from_viewer.set_tooltip("Copy cut levels from viewer")
        b.copy_from_viewer.add_callback('activated', self.copy_from_viewer_cb)
        b.hbox1.add_widget(b.copy_from_viewer, stretch=0)
        b.hbox1.add_widget(Widgets.Label(''), stretch=1)

        self.w.update(b)
        fr.set_widget(w)
        top.add_widget(fr, stretch=0)

        fr = Widgets.Frame("Auto Cuts")
        vbox2 = Widgets.VBox()
        fr.set_widget(vbox2)

        captions = (("Auto Method:", 'label', "Auto Method", 'combobox'),
                    )
        w, b = Widgets.build_info(captions, orientation='vertical')
        self.w.update(b)

        self.autocuts = AutoCuts.Histogram(self.logger)
        self.autocut_methods = self.autocuts.get_algorithms()
        # Setup auto cuts method choice
        combobox = b.auto_method
        index = 0
        #method = self.t_.get('autocut_method', "histogram")
        method = "histogram"
        for name in self.autocut_methods:
            combobox.append_text(name)
            index += 1
        try:
            index = self.autocut_methods.index(method)
            combobox.set_index(index)
        except Exception:
            pass
        combobox.add_callback('activated', self.set_autocut_method_cb)
        b.auto_method.set_tooltip("Choose algorithm for auto levels")
        vbox2.add_widget(w, stretch=0)

        self.w.acvbox = Widgets.VBox()
        vbox2.add_widget(self.w.acvbox, stretch=1)

        top.add_widget(fr, stretch=0)

        container.set_widget(top)

    def config_autocut_params(self, method):
        try:
            index = self.autocut_methods.index(method)
            self.w.auto_method.set_index(index)
        except Exception:
            pass

        # remove old params
        self.w.acvbox.remove_all()

        # Create new autocuts object of the right kind
        ac_class = AutoCuts.get_autocuts(method)

        # Build up a set of control widgets for the autocuts
        # algorithm tweakable parameters
        paramlst = ac_class.get_params_metadata()

        # Get the canonical version of this object stored in our cache
        # and make a ParamSet from it
        params = self.autocuts_cache.setdefault(method, Bunch.Bunch())
        self.ac_params = ParamSet.ParamSet(self.logger, params)

        # Build widgets for the parameter/attribute list
        w = self.ac_params.build_params(paramlst,
                                        orientation='vertical')
        self.ac_params.add_callback('changed', self.autocut_params_changed_cb)

        # Add this set of widgets to the pane
        self.w.acvbox.add_widget(w, stretch=1)

    def _config_autocuts(self, method, params):
        params = dict(params)

        if method != str(self.autocuts):
            ac_class = AutoCuts.get_autocuts(method)
            self.autocuts = ac_class(self.logger, **params)
        else:
            self.autocuts.update_params(**params)

        self.pipeline.run_from(self)

    def set_autocut_method_cb(self, w, idx):
        method = self.autocut_methods[idx]

        self.config_autocut_params(method)

        args, kwdargs = self.ac_params.get_params()
        params = list(kwdargs.items())
        self._config_autocuts(method, params)

    def autocut_params_changed_cb(self, paramObj, ac_obj):
        """This callback is called when the user changes the attributes of
        an object via the paramSet.
        """
        args, kwdargs = paramObj.get_params()
        params = list(kwdargs.items())

        self._config_autocuts(str(self.autocuts), params)

    def manual_cuts_cb(self, widget):
        old = dict(locut=self._locut, hicut=self._hicut, auto=self._auto)
        self._locut = float(self.w.locut.get_text().strip())
        self._hicut = float(self.w.hicut.get_text().strip())
        self.auto = False
        new = dict(locut=self._locut, hicut=self._hicut, auto=self._auto)
        self.pipeline.push(StageAction(self, old, new,
                                       descr="cuts"))
        self.pipeline.run_from(self)

    def manual_output_cb(self, widget):
        old = dict(vmin=self._vmin, vmax=self._vmax)
        self._vmin = float(self.w.vmin.get_text().strip())
        self._vmax = float(self.w.vmax.get_text().strip())
        new = dict(vmin=self._vmin, vmax=self._vmax)
        self.pipeline.push(StageAction(self, old, new,
                                       descr="cuts / vmin,vmax"))
        self.pipeline.run_from(self)

    def auto_cb(self, widget, tf):
        old = dict(locut=self._locut, hicut=self._hicut, auto=self._auto)
        self._auto = tf
        new = dict(locut=self._locut, hicut=self._hicut, auto=self._auto)
        self.pipeline.push(StageAction(self, old, new,
                                       descr="cuts"))
        self.pipeline.run_from(self)

    def copy_from_viewer_cb(self, widget):
        old = dict(locut=self._locut, hicut=self._hicut)
        self.locut, self.hicut = self.viewer.get_cut_levels()
        new = dict(locut=self._locut, hicut=self._hicut)
        self.pipeline.push(StageAction(self, old, new,
                                       descr="cuts"))
        self.pipeline.run_from(self)

    @property
    def locut(self):
        return self._locut

    @locut.setter
    def locut(self, val):
        self._locut = val
        if self.gui_up:
            self.w.locut.set_text(str(val))

    @property
    def hicut(self):
        return self._hicut

    @hicut.setter
    def hicut(self, val):
        self._hicut = val
        if self.gui_up:
            self.w.hicut.set_text(str(val))

    @property
    def auto(self):
        return self._auto

    @auto.setter
    def auto(self, tf):
        self._auto = tf
        if self.gui_up:
            self.w.auto.set_state(tf)

    @property
    def vmin(self):
        return self._vmin

    @vmin.setter
    def vmin(self, val):
        self._vmin = val
        if self.gui_up:
            self.w.vmin.set_text(str(val))

    @property
    def vmax(self):
        return self._vmax

    @vmax.setter
    def vmax(self, val):
        self._vmax = val
        if self.gui_up:
            self.w.vmax.set_text(str(val))

    def _get_state(self):
        return dict(locut=self._locut, hicut=self._hicut, auto=self._auto,
                    vmin=self._vmin, vmax=self._vmax)

    def run(self, prev_stage):
        data = self.pipeline.get_data(prev_stage)
        self.verify_2d(data)

        if self._bypass or data is None:
            self.pipeline.send(res_np=data)
            return

        if self.auto:
            self.locut, self.hicut = self.autocuts.calc_cut_levels_data(data)

        res_np = self.autocuts.cut_levels(data, self.locut, self.hicut,
                                          vmin=self.vmin, vmax=self.vmax)
        self.pipeline.send(res_np=res_np)

    def export_as_dict(self):
        d = super().export_as_dict()
        d.update(self._get_state())
        return d

    def import_from_dict(self, d):
        super().import_from_dict(d)
        self.vmin = d['vmin']
        self.vmax = d['vmax']
        self.auto = d['auto']
        self.locut = d['locut']
        self.hicut = d['hicut']
