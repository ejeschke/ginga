# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
"""
Simple data processing pipeline plugin for Ginga.

**Plugin Type: Local**

``Pipeline`` is a local plugin, which means it is associated with a channel.
An instance can be opened for each channel.

**Usage**

"""
import os.path
import tempfile

from ginga import GingaPlugin
from ginga.util import pipeline
from ginga.gw import Widgets

from ginga.util.stages.stage_info import get_stage_catalog

__all__ = ['Pipeline']


class Pipeline(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(Pipeline, self).__init__(fv, fitsimage)

        # TEMP: make user selectable
        self.save_file = "pipeline.yml"

        # Load preferences
        prefs = self.fv.get_preferences()
        self.settings = prefs.create_category('plugin_Pipeline')
        self.settings.set_defaults(output_suffix='-pipe')
        self.settings.load(onError='silent')

        self.stage_dict = get_stage_catalog(self.logger)
        self.stage_classes = list(self.stage_dict.values())
        self.stage_names = list(self.stage_dict.keys())
        self.stage_names.sort()

        stages = [self.stage_dict['input'](), self.stage_dict['output']()]
        self.pipeline = pipeline.Pipeline(self.logger, stages)
        self.pipeline.add_callback('stage-executing', self.stage_status, 'X')
        self.pipeline.add_callback('stage-done', self.stage_status, 'D')
        self.pipeline.add_callback('stage-errored', self.stage_status, 'E')
        self.pipeline.add_callback('pipeline-start', self.clear_status)

        self.pipeline.set(fv=self.fv, viewer=self.fitsimage)
        self.gui_up = False

    def build_gui(self, container):
        top = Widgets.VBox()
        top.set_border_width(4)
        top.set_spacing(2)

        tbar = Widgets.Toolbar(orientation='horizontal')
        menu = tbar.add_menu('Pipe', mtype='menu')
        menu.set_tooltip("Operation on pipeline")
        item = menu.add_name('Load')
        item.set_tooltip("Load a new pipeline")
        item.add_callback('activated', self.load_pipeline_cb)
        item = menu.add_name('Save')
        item.set_tooltip("Save this pipeline")
        item.add_callback('activated', self.save_pipeline_cb)

        menu = tbar.add_menu('Edit', mtype='menu')
        menu.set_tooltip("Edit on pipeline")
        item = menu.add_name('Undo')
        item.set_tooltip("Undo last action")
        item.add_callback('activated', self.undo_pipeline_cb)
        item = menu.add_name('Redo')
        item.set_tooltip("Redo last action")
        item.add_callback('activated', self.redo_pipeline_cb)

        name = Widgets.TextEntry(editable=True)
        name.add_callback('activated', self.set_pipeline_name_cb)
        name.set_text(self.pipeline.name)
        self.w.pipeline_name = name
        tbar.add_widget(name)
        top.add_widget(tbar, stretch=0)

        vbox = Widgets.VBox()
        vbox.set_border_width(2)
        vbox.set_spacing(2)
        self.pipelist = vbox

        for stage in self.pipeline:
            stage_gui = self.make_stage_gui(stage)
            vbox.add_widget(stage_gui, stretch=0)

        # add stretch
        vbox.add_widget(Widgets.Label(''), stretch=1)

        # wrap it in a scrollbox
        scr = Widgets.ScrollArea()
        scr.set_widget(vbox)

        name = self.pipeline.name
        if len(name) > 20:
            name = name[:20] + '...'
        fr = Widgets.Frame("Pipeline: {}".format(name))
        self.w.gui_fr = fr
        fr.set_widget(scr)
        #top.add_widget(scr, stretch=1)
        top.add_widget(fr, stretch=1)

        tbar = Widgets.Toolbar(orientation='horizontal')
        btn = tbar.add_action('Del')
        btn.add_callback('activated', self.delete_stage_cb)
        btn.set_tooltip("Delete selected stages")
        self.w.delete = btn
        btn = tbar.add_action('Ins')
        btn.set_tooltip("Insert above selected stage")
        btn.add_callback('activated', self.insert_stage_cb)
        self.w.insert = btn
        btn = tbar.add_action('Up')
        btn.set_tooltip("Move selected stage up")
        btn.add_callback('activated', self.move_stage_cb, 'up')
        self.w.move_up = btn
        btn = tbar.add_action('Dn')
        btn.set_tooltip("Move selected stage down")
        btn.add_callback('activated', self.move_stage_cb, 'down')
        self.w.move_dn = btn
        btn = tbar.add_action('Clr')
        btn.set_tooltip("Clear selection")
        btn.add_callback('activated', lambda w: self.clear_selected())
        self.w.clear = btn
        self.insert_menu = Widgets.Menu()
        for name in self.stage_names:
            item = self.insert_menu.add_name(name)
            item.add_callback('activated', self._insert_stage_cb, name)
        btn = tbar.add_action('Run')
        btn.set_tooltip("Run entire pipeline")
        btn.add_callback('activated', self.run_pipeline_cb)
        self.w.run = btn
        btn = tbar.add_action('En', toggle=True)
        btn.set_tooltip("Enable pipeline")
        btn.set_state(self.pipeline.enabled)
        btn.add_callback('activated', self.enable_pipeline_cb)
        self.w.enable = btn
        top.add_widget(tbar, stretch=0)

        status = Widgets.Label('')
        self.w.pipestatus = status
        top.add_widget(status, stretch=0)

        btns = Widgets.HBox()
        btns.set_spacing(3)

        btn = Widgets.Button("Close")
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn, stretch=0)
        btn = Widgets.Button("Help")
        btn.add_callback('activated', lambda w: self.help())
        btns.add_widget(btn, stretch=0)
        btns.add_widget(Widgets.Label(''), stretch=1)
        top.add_widget(btns, stretch=0)

        self._update_toolbar()
        container.add_widget(top, stretch=1)
        self.gui_up = True

    def make_stage_gui(self, stage):
        _vbox = Widgets.VBox()
        hbox = Widgets.HBox()

        xpd = Widgets.Expander(title=str(stage), notoggle=True)
        tbar = Widgets.Toolbar(orientation='horizontal')
        chk = tbar.add_action('B', toggle=True)
        chk.add_callback('activated', self.bypass_stage_cb, stage)
        chk.set_tooltip("Bypass this stage")
        chk = tbar.add_action('S', toggle=True)
        chk.add_callback('activated', self.select_stage_cb)
        chk.set_tooltip("Select this stage")
        stage.w.select = chk
        chk = tbar.add_action('C', toggle=True)
        chk.add_callback('activated', self.configure_stage_cb, xpd)
        chk.set_tooltip("Configure this stage")
        hbox.add_widget(tbar, stretch=0)
        ent = Widgets.TextEntry(str(stage))
        ent.add_callback('activated', self.rename_stage_cb, stage)
        ent.set_tooltip("Rename this stage")
        hbox.add_widget(ent, stretch=1)
        _vbox.add_widget(hbox, stretch=0)
        stage.build_gui(xpd)
        xpd.add_callback('opened', lambda w: stage.resume())
        xpd.add_callback('closed', lambda w: stage.pause())
        stage.gui_up = True
        _vbox.add_widget(xpd, stretch=0)
        stage.w.gui = _vbox
        return _vbox

    def close(self):
        chname = self.fv.get_channel_name(self.fitsimage)
        self.fv.stop_local_plugin(chname, str(self))
        self.gui_up = False
        return True

    def start(self):
        for stage in self.pipeline:
            stage.start()

        # load any image in the channel into the start of the pipeline
        image = self.fitsimage.get_image()
        if image is not None:
            self.pipeline[0].set_image(image)

    def pause(self):
        pass

    def resume(self):
        pass

    def stop(self):
        self.gui_up = False

        for stage in self.pipeline:
            stage.stop()

    def set_pipeline_name_cb(self, widget):
        name = widget.get_text().strip()
        self.pipeline.name = name
        if len(name) > 20:
            name = name[:20] + '...'
        self.w.gui_fr.set_text(name)

    def bypass_stage_cb(self, widget, tf, stage):
        idx = self.pipeline.index(stage)
        stage.bypass(tf)
        self.pipeline.run_from(stage)

    def _update_toolbar(self):
        stages = self.get_selected_stages()
        self.w.insert.set_enabled(len(stages) <= 1)
        self.w.delete.set_enabled(len(stages) >= 1)
        self.w.move_up.set_enabled(len(stages) == 1)
        self.w.move_dn.set_enabled(len(stages) == 1)
        self.w.clear.set_enabled(len(stages) >= 1)
        self.w.run.set_enabled(len(stages) <= 1)
        self.w.enable.set_enabled(len(self.pipeline) > 0)

    def select_stage_cb(self, widget, tf):
        self._update_toolbar()

    def configure_stage_cb(self, widget, tf, xpd):
        xpd.expand(tf)

    def rename_stage_cb(self, widget, stage):
        name = widget.get_text().strip()
        stage.name = name

    def get_selected_stages(self):
        res = [stage for stage in self.pipeline
               if stage.w.select.get_state()]
        return res

    def clear_selected(self):
        for stage in self.pipeline:
            stage.w.select.set_state(False)
        self._update_toolbar()

    def _remove_stage(self, stage, destroy=False):
        self.pipeline.remove(stage)
        self.pipelist.remove(stage.w.gui, delete=destroy)
        if destroy:
            # destroy stage gui
            stage.gui_up = False
            stage.stop()
            stage.w = None

    def delete_stage_cb(self, widget):
        stages = self.get_selected_stages()
        self.clear_selected()
        for stage in stages:
            self._remove_stage(stage, destroy=True)

    def insert_stage_cb(self, widget):
        stages = self.get_selected_stages()
        if len(stages) > 1:
            self.fv.show_error("Please select at most only one stage",
                               raisetab=True)
            return
        self.insert_menu.popup()

    def _insert_stage_cb(self, widget, name):
        stages = self.get_selected_stages()
        if len(stages) == 1:
            stage = stages[0]
            idx = self.pipeline.index(stage)
        else:
            idx = len(stages)
        # realize this stage
        stage = self.stage_dict[name]()
        self.pipeline._init_stage(stage)
        self.pipeline.insert(idx, stage)
        stage_gui = self.make_stage_gui(stage)
        self.pipelist.insert_widget(idx, stage_gui, stretch=0)

    def _relocate_stage(self, idx, stage):
        self._remove_stage(stage, destroy=False)
        self.pipeline.insert(idx, stage)
        self.pipelist.insert_widget(idx, stage.w.gui, stretch=0)

    def move_up(self, stage):
        idx = self.pipeline.index(stage)
        if idx == 0:
            # stage is already at the top
            return
        self._relocate_stage(idx - 1, stage)

    def move_down(self, stage):
        idx = self.pipeline.index(stage)
        if idx == len(self.pipeline) - 1:
            # stage is already at the bottom
            return
        self._relocate_stage(idx + 1, stage)

    def move_stage_cb(self, widget, direction):
        stages = self.get_selected_stages()
        if len(stages) != 1:
            self.fv.show_error("Please select only a single stage",
                               raisetab=True)
        stage = stages[0]
        if direction == 'up':
            self.move_up(stage)
        else:
            self.move_down(stage)

    def run_pipeline_cb(self, widget):
        self.pipeline.run_all()

    def run_pipeline_partial_cb(self, widget):
        stages = self.get_selected_stages()
        if len(stages) == 0:
            self.pipeline.run_all()
            return
        if len(stages) != 1:
            self.fv.show_error("Please select only a single stage",
                               raisetab=True)
            return
        stage = stages[0]
        self.pipeline.run_from(stage)

    def enable_pipeline_cb(self, widget, tf):
        self.pipeline.enable(tf)

    def undo_pipeline_cb(self, widget):
        self.pipeline.undo()

    def redo_pipeline_cb(self, widget):
        self.pipeline.redo()

    def save_pipeline(self, path):
        import yaml
        d = self.pipeline.save()
        with open(path, 'w') as out_f:
            out_f.write(yaml.dump(d))

    def load_pipeline(self, path):
        import yaml
        self.pipelist.remove_all(delete=True)
        self.pipelist.add_widget(Widgets.Label(''), stretch=1)

        with open(path, 'r') as in_f:
            s = in_f.read()
        d = yaml.safe_load(s)
        self.pipeline.load(d, self.stage_dict)

        self.pipeline.set(fv=self.fv, viewer=self.fitsimage)

        for i, stage in enumerate(self.pipeline):
            stage_gui = self.make_stage_gui(stage)
            self.pipelist.insert_widget(i, stage_gui, stretch=0)

        name = self.pipeline.name
        self.w.pipeline_name.set_text(name)
        if len(name) > 20:
            name = name[:20] + '...'
        self.w.gui_fr.set_text(name)

    def save_pipeline_cb(self, widget):
        save_file = os.path.join(tempfile.gettempdir(), self.save_file)
        self.save_pipeline(save_file)

    def load_pipeline_cb(self, widget):
        save_file = os.path.join(tempfile.gettempdir(), self.save_file)
        self.load_pipeline(save_file)

    def redo(self):
        image = self.fitsimage.get_image()
        if image is not None:
            stage0 = self.pipeline[0]
            stage0.set_image(image)

    def stage_status(self, pipeline, stage, txt):
        if stage.gui_up:
            self.w.pipestatus.set_text(txt + ': ' + stage.name)
            self.fv.update_pending()

    def clear_status(self, pipeline, stage):
        for stage in pipeline:
            if stage.gui_up:
                self.w.pipestatus.set_text(stage.name)
        self.fv.update_pending()

    def __str__(self):
        return 'pipeline'


# Append module docstring with config doc for auto insert by Sphinx.
from ginga.util.toolbox import generate_cfg_example  # noqa
if __doc__ is not None:
    __doc__ += generate_cfg_example('plugin_Pipeline', package='ginga')

# END
