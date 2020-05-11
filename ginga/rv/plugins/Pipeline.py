# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
"""
Simple data processing pipeline plugin for Ginga.

**Plugin Type: Local**

``Pipeline`` is a local plugin, which means it is associated with a channel.
An instance can be opened for each channel.

**Usage**

"""

from ginga import GingaPlugin, RGBImage
from ginga.util import pipeline, loader
from ginga.gw import Widgets
from ginga.util.stages import (Input, Output, Scale, Rotate, Flip, Cuts,
                               RGBMap, CProf)

__all__ = ['Pipeline']


class Pipeline(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(Pipeline, self).__init__(fv, fitsimage)

        # Load preferences
        prefs = self.fv.get_preferences()
        self.settings = prefs.create_category('plugin_Pipeline')
        self.settings.set_defaults(num_threads=4)
        self.settings.load(onError='silent')

        self.dc = fv.get_draw_classes()
        self.layertag = 'pipeline-canvas'
        canvas = self.dc.DrawingCanvas()
        canvas.enable_draw(True)
        canvas.enable_edit(True)
        canvas.set_drawtype('line', color='cyan', linestyle='dash')
        ## canvas.set_callback('draw-event', self.draw_cb)
        ## canvas.set_callback('edit-event', self.edit_cb)
        ## canvas.add_draw_mode('move', down=self.buttondown_cb,
        ##                      move=self.motion_cb, up=self.buttonup_cb,
        ##                      key=self.keydown)
        ## canvas.set_draw_mode('draw')
        #canvas.add_callback('drag-drop', self.drop_cb)
        canvas.register_for_cursor_drawing(self.fitsimage)
        canvas.set_surface(self.fitsimage)
        self.canvas = canvas

        self.stage_classes = [Scale, Cuts, RGBMap, CProf, Flip,
                              Rotate]
        self.stage_dict = {klass._stagename: klass
                           for klass in self.stage_classes}
        self.stage_names = list(self.stage_dict.keys())
        self.stage_names.sort()

        stages = [Input(), Output(self.fv)]
        self.pipeline = pipeline.Pipeline(self.logger, stages)
        self.pipeline.add_callback('stage-executing', self.stage_status, 'X')
        self.pipeline.add_callback('stage-done', self.stage_status, 'D')
        self.pipeline.add_callback('stage-errored', self.stage_status, 'E')
        self.pipeline.add_callback('pipeline-start', self.clear_status)

        self.gui_up = False

    def build_gui(self, container):
        top = Widgets.VBox()
        top.set_border_width(4)
        top.set_spacing(2)

        #top.add_widget(Widgets.Label("Pipeline"), stretch=0)
        vbox = Widgets.VBox()
        self.pipelist = vbox

        for stage in self.pipeline:
            stage_gui = self.make_stage_gui(stage)
            vbox.add_widget(stage_gui, stretch=0)

        # add stretch
        vbox.add_widget(Widgets.Label(''), stretch=1)

        # wrap it in a scrollbox
        scr = Widgets.ScrollArea()
        scr.set_widget(vbox)
        top.add_widget(scr, stretch=1)

        tbar = Widgets.Toolbar(orientation='horizontal')
        btn = tbar.add_action('Delete')
        btn.add_callback('activated', self.delete_stage_cb)
        btn.set_tooltip("Delete selected stages")
        self.w.delete = btn
        btn = tbar.add_action('Insert')
        btn.set_tooltip("Insert above selected stage")
        btn.add_callback('activated', self.insert_stage_cb)
        self.w.insert = btn
        self.insert_menu = Widgets.Menu()
        for name in self.stage_names:
            item = self.insert_menu.add_name(name)
            item.add_callback('activated', self._insert_stage_cb, name)
        btn = tbar.add_action('Run')
        btn.set_tooltip("Run pipeline (or from selected stage)")
        btn.add_callback('activated', self.run_pipeline_cb)
        self.w.run = btn
        top.add_widget(tbar, stretch=0)

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

        tbar = Widgets.Toolbar(orientation='horizontal')
        chk = tbar.add_action('B', toggle=True)
        chk.add_callback('activated', self.bypass_stage_cb, stage)
        chk.set_tooltip("Bypass this stage")
        chk = tbar.add_action('S', toggle=True)
        chk.add_callback('activated', self.select_stage_cb)
        chk.set_tooltip("Select this stage")
        stage.w.select = chk
        status = Widgets.Label('_')
        stage.w.status = status
        chk = tbar.add_widget(status)
        hbox.add_widget(tbar, stretch=0)
        ent = Widgets.TextEntry(str(stage))
        ent.add_callback('activated', self.rename_stage_cb, stage)
        ent.set_tooltip("Rename this stage")
        hbox.add_widget(ent, stretch=1)
        _vbox.add_widget(hbox, stretch=0)
        xpd = Widgets.Expander(title=str(stage))
        stage.build_gui(xpd)
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
        # insert canvas, if not already
        p_canvas = self.fitsimage.get_canvas()
        try:
            p_canvas.get_object_by_tag(self.layertag)

        except KeyError:
            # Add our canvas
            p_canvas.add(self.canvas, tag=self.layertag)

        for stage in self.pipeline:
            stage.start()

        # load any image in the channel into the start of the pipeline
        image = self.fitsimage.get_image()
        if image is not None:
            self.pipeline[0].set_image(image)

    def pause(self):
        self.canvas.ui_set_active(False)

    def resume(self):
        # turn off any mode user may be in
        self.modes_off()

        self.canvas.ui_set_active(True, viewer=self.fitsimage)

    def stop(self):
        self.gui_up = False

        for stage in self.pipeline:
            stage.stop()

        # remove the canvas from the image
        p_canvas = self.fitsimage.get_canvas()
        p_canvas.delete_object_by_tag(self.layertag)
        self.fv.show_status("")

    def bypass_stage_cb(self, widget, tf, stage):
        idx = self.pipeline.index(stage)
        stage.bypass(tf)
        self.pipeline.run_from(stage)

    def _update_toolbar(self):
        stages = self.get_selected_stages()
        self.w.insert.set_enabled(len(stages) == 1)
        self.w.delete.set_enabled(len(stages) >= 1)
        self.w.run.set_enabled(len(stages) <= 1)

    def select_stage_cb(self, widget, tf):
        self._update_toolbar()

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

    def delete_stage_cb(self, widget):
        stages = self.get_selected_stages()
        for stage in stages:
            self.pipeline.remove(stage)
        # destroy stage gui
        stage.gui_up = False
        stage.stop()
        self.pipelist.remove(stage.w.gui, delete=True)
        stage.w = None

    def insert_stage_cb(self, widget):
        stages = self.get_selected_stages()
        if len(stages) != 1:
            self.fv.show_error("Please select only a single stage",
                               raisetab=True)
            return
        self.insert_menu.popup()

    def _insert_stage_cb(self, widget, name):
        stages = self.get_selected_stages()
        stage = stages[0]
        idx = self.pipeline.index(stage)
        # realize this stage
        stage = self.stage_dict[name]()
        stage.pipeline = self.pipeline
        self.pipeline.insert(idx, stage)
        stage_gui = self.make_stage_gui(stage)
        self.pipelist.insert_widget(idx, stage_gui, stretch=0)
        self.clear_selected()

    def run_pipeline_cb(self, widget):
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

    def load_file(self, filepath):
        image = loader.load_data(filepath, logger=self.logger)
        self.pipeline[0].set_image(image)
        self.pipeline.run_all()
        self.fitsimage.reload_image()

    def drop_cb(self, canvas, paths):
        self.logger.info("files dropped: %s" % str(paths))
        filename = paths[0]
        self.load_file(filename)
        return True

    def redo(self):
        image = self.fitsimage.get_image()
        if image is not None:
            stage0 = self.pipeline[0]
            stage0.set_image(image)

    def stage_status(self, pipeline, stage, txt):
        if stage.gui_up:
            stage.w.status.set_text(txt)
            self.fv.update_pending()

    def clear_status(self, pipeline, stage):
        for stage in pipeline:
            if stage.gui_up:
                stage.w.status.set_text('_')
        self.fv.update_pending()

    def __str__(self):
        return 'pipeline'

# Append module docstring with config doc for auto insert by Sphinx.
from ginga.util.toolbox import generate_cfg_example  # noqa
if __doc__ is not None:
    __doc__ += generate_cfg_example('plugin_Pipeline', package='ginga')

# END
