#
# Crosshair.py -- Crosshair plugin for Ginga reference viewer
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga import GingaPlugin
from ginga.gw import Widgets

class Crosshair(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(Crosshair, self).__init__(fv, fitsimage)

        self.xhcolor = 'green'
        self.layertag = 'crosshair-canvas'
        self.xhtag = None

        self.dc = fv.get_draw_classes()
        canvas = self.dc.DrawingCanvas()
        canvas.name = 'crosshair-canvas'
        ## canvas.add_draw_mode('move', down=self.btndown,
        ##                      move=self.btndrag, up=self.drag)
        ## canvas.set_draw_mode('move')
        ## canvas.enable_draw(True)
        canvas.add_callback('cursor-down', self.btndown)
        canvas.add_callback('cursor-move', self.btndrag)
        canvas.set_surface(self.fitsimage)
        self.canvas = canvas

        # create crosshair
        self.xh = self.dc.Crosshair(0, 0, color=self.xhcolor,
                                    coord='data', format='xy')
        self.canvas.add(self.xh, redraw=False)

        self.w = None
        self.formats = ('xy', 'value', 'coords')
        self.format = 'xy'

    def build_gui(self, container):
        top = Widgets.VBox()
        top.set_border_width(4)

        vbox, sw, orientation = Widgets.get_oriented_box(container)
        vbox.set_border_width(4)
        vbox.set_spacing(2)

        self.msg_font = self.fv.get_font("sansFont", 12)
        tw = Widgets.TextArea(wrap=True, editable=False)
        tw.set_font(self.msg_font)
        self.tw = tw

        fr = Widgets.Expander("Instructions")
        fr.set_widget(tw)
        vbox.add_widget(fr, stretch=0)

        fr = Widgets.Frame("Crosshair")

        captions = (('Format:', 'label', 'Format', 'combobox'),
                    )
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w = b

        combobox = b.format
        for name in self.formats:
            combobox.append_text(name)
        index = self.formats.index(self.format)
        combobox.set_index(index)
        combobox.add_callback('activated', lambda w, idx: self.set_format())

        fr.set_widget(w)
        vbox.add_widget(fr, stretch=0)

        spacer = Widgets.Label('')
        vbox.add_widget(spacer, stretch=1)

        top.add_widget(sw, stretch=1)

        btns = Widgets.HBox()
        btns.set_spacing(3)

        btn = Widgets.Button("Close")
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn, stretch=0)
        btns.add_widget(Widgets.Label(''), stretch=1)
        top.add_widget(btns, stretch=0)

        container.add_widget(top, stretch=1)

    def set_format(self):
        index = self.w.format.get_index()
        self.format = self.formats[index]
        self.xh.format = self.format

        self.canvas.redraw(whence=3)
        return True

    def close(self):
        self.fv.stop_local_plugin(self.chname, str(self))
        return True

    def instructions(self):
        self.tw.set_text("""Click or drag to set crosshair.""")

    def start(self):
        self.instructions()
        # start crosshair operation
        p_canvas = self.fitsimage.get_canvas()
        if not p_canvas.has_object(self.canvas):
            p_canvas.add(self.canvas, tag=self.layertag)

        self.resume()

    def pause(self):
        self.canvas.ui_setActive(False)

    def resume(self):
        self.canvas.ui_setActive(True)
        self.fv.show_status("Draw a ruler with the right mouse button")

    def stop(self):
        # remove the canvas from the image
        p_canvas = self.fitsimage.get_canvas()
        try:
            p_canvas.delete_object_by_tag(self.layertag)
        except:
            pass
        self.canvas.ui_setActive(False)
        self.fv.show_status("")

    def redo(self):
        pass

    def move_crosshair(self, viewer, data_x, data_y):
        self.logger.debug("move crosshair data x,y=%f,%f" % (data_x, data_y))
        self.xh.move_to(data_x, data_y)
        self.canvas.update_canvas(whence=3)

    def btndown(self, canvas, event, data_x, data_y):
        self.move_crosshair(self.fitsimage, data_x, data_y)

    def btndrag(self, canvas, event, data_x, data_y):
        self.move_crosshair(self.fitsimage, data_x, data_y)

    def __str__(self):
        return 'crosshair'

#END
