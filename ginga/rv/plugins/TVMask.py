# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
"""
Display masks from file (non-interative mode) on an image.

**Plugin Type: Local**

``TVMask`` is a local plugin, which means it is associated with a
channel.  An instance can be opened for each channel.

**Usage**

This plugin allows non-interactive display of mask by reading in a FITS
file, where non-zero is assumed to be masked data.

To display different masks (e.g., some masked as green and some as pink, as
shown above):

1. Select green from the drop-down menu. Alternately, enter desired
   alpha value.
2. Using "Load Mask" button, load the relevant FITS file.
3. Repeat (1) but now select pink from the drop-down menu.
4. Repeat (2) but choose another FITS file.
5. To display a third mask as pink too, repeat (4) without changing the
   drop-down menu.

Selecting an entry (or multiple entries) from the table listing will
highlight the mask(s) on the image. The highlight uses a pre-defined color and
alpha (customizable below).

You can also highlight all the masks within a region both on the image
and the table listing by drawing a rectangle on the image
while this plugin is active.

Pressing the "Hide" button will hide the masks but does not clear the
plugin's memory; That is, when you press "Show", the same masks will
reappear on the same image. However, pressing "Forget" will clear the masks
both from display and memory; That is, you will need to reload your file(s) to
recreate the masks.

To redraw the same masks with different color or alpha, press "Forget"
and repeat the steps above, as necessary.

If images of very different pointings/dimensions are displayed in the same
channel, masks that belong to one image but fall outside another will not
appear in the latter.

To create a mask that this plugin can read, one can use results from
the ``Drawing`` plugin (press "Create Mask" after drawing and save the
mask using ``SaveImage``), in addition to creating a FITS
file by hand using ``astropy.io.fits``, etc.

Used together with ``TVMark``, you can overlay both point sources and
masked regions in Ginga.

"""
# STDLIB
import re
import os

# THIRD-PARTY
import numpy as np
from astropy.io import fits

# GINGA
from ginga import colors
from ginga.GingaPlugin import LocalPlugin
from ginga.gw import Widgets
from ginga.misc import Bunch
from ginga.util.dp import masktorgb

# Need this for API doc to build without warning
try:
    from ginga.gw.GwHelp import FileSelection
except ImportError:
    pass

__all__ = ['TVMask']


class TVMask(LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(TVMask, self).__init__(fv, fitsimage)

        self.layertag = 'tvmask-canvas'
        self.masktag = None
        self.maskhltag = None

        self._color_options = self._short_color_list()

        # User preferences. Some are just default values and can also be
        # changed by GUI.
        prefs = self.fv.get_preferences()
        self.settings = prefs.create_category('plugin_TVMask')
        self.settings.add_defaults(maskcolor='green', maskalpha=0.5,
                                   hlcolor='white', hlalpha=1.0)
        self.settings.load(onError='silent')
        self.maskcolor = self.settings.get('maskcolor', 'green')
        self.maskalpha = self.settings.get('maskalpha', 0.5)
        self.hlcolor = self.settings.get('hlcolor', 'white')
        self.hlalpha = self.settings.get('hlalpha', 1.0)

        # Display coords info table
        self.treeview = None
        self.tree_dict = Bunch.caselessDict()
        self.columns = [('No.', 'ID'), ('Filename', 'MASKFILE')]

        # Store results
        self._seqno = 1
        self._maskobjs = []
        self._treepaths = []

        self.dc = self.fv.get_draw_classes()

        canvas = self.dc.DrawingCanvas()
        canvas.enable_draw(True)
        canvas.enable_edit(False)
        canvas.set_callback('draw-event', self.hl_canvas2table_box)
        #canvas.set_callback('cursor-down', self.hl_canvas2table)
        canvas.register_for_cursor_drawing(self.fitsimage)
        canvas.set_surface(self.fitsimage)
        canvas.set_drawtype('rectangle', color='green', linestyle='dash')
        self.canvas = canvas

        fv.add_callback('remove-image', lambda *args: self.redo())

        self.gui_up = False

    # If user complains about lack of choices (!!!), we can remove this.
    def _short_color_list(self):
        """Color list is too long. Discard variations with numbers."""
        return [c for c in colors.get_colors() if not re.search(r'\d', c)]

    def build_gui(self, container):
        vbox, sw, self.orientation = Widgets.get_oriented_box(container,
                                                              orientation=self.settings.get('orientation', None))

        captions = (('Color:', 'label', 'mask color', 'combobox'),
                    ('Alpha:', 'label', 'mask alpha', 'entry'))
        w, b = Widgets.build_info(captions)
        self.w.update(b)

        combobox = b.mask_color
        for name in self._color_options:
            combobox.append_text(name)
        b.mask_color.set_index(self._color_options.index(self.maskcolor))
        b.mask_color.add_callback('activated', self.set_maskcolor_cb)

        b.mask_alpha.set_tooltip('Mask alpha (transparency)')
        b.mask_alpha.set_text(str(self.maskalpha))
        b.mask_alpha.add_callback('activated', lambda w: self.set_maskalpha())

        container.add_widget(w, stretch=0)

        treeview = Widgets.TreeView(auto_expand=True,
                                    sortable=True,
                                    selection='multiple',
                                    use_alt_row_color=True)
        self.treeview = treeview
        treeview.setup_table(self.columns, 2, 'ID')
        treeview.add_callback('selected', self.hl_table2canvas)
        container.add_widget(treeview, stretch=1)

        captions = (('Load Mask', 'button'),
                    ('Show', 'button', 'Hide', 'button', 'Forget', 'button'))
        w, b = Widgets.build_info(captions)
        self.w.update(b)

        b.load_mask.set_tooltip('Load mask image')
        b.load_mask.add_callback('activated', lambda w: self.load_mask_cb())

        b.show.set_tooltip('Show masks')
        b.show.add_callback('activated', lambda w: self.redo())

        b.hide.set_tooltip('Hide masks')
        b.hide.add_callback('activated', lambda w: self.clear_mask())

        b.forget.set_tooltip('Forget masks')
        b.forget.add_callback('activated', lambda w: self.forget_masks())

        container.add_widget(w, stretch=0)

        btns = Widgets.HBox()
        btns.set_border_width(4)
        btns.set_spacing(3)

        btn = Widgets.Button('Close')
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn, stretch=0)
        btn = Widgets.Button("Help")
        btn.add_callback('activated', lambda w: self.help())
        btns.add_widget(btn, stretch=0)
        btns.add_widget(Widgets.Label(''), stretch=1)

        container.add_widget(btns, stretch=0)

        self.gui_up = True

        # Initialize mask file selection dialog
        self.mfilesel = FileSelection(self.fv.w.root.get_widget(),
                                      all_at_once=True)

        # Populate table
        self.redo()

    def redo(self):
        """Image or masks have changed. Clear and redraw."""
        if not self.gui_up:
            return

        self.clear_mask()

        image = self.fitsimage.get_image()
        if image is None:
            return

        n_obj = len(self._maskobjs)
        self.logger.debug('Displaying {0} masks'.format(n_obj))
        if n_obj == 0:
            return

        # Display info table
        self.recreate_toc()

        # Draw on canvas
        self.masktag = self.canvas.add(self.dc.CompoundObject(*self._maskobjs))
        self.fitsimage.redraw()  # Force immediate redraw

    def clear_mask(self):
        """Clear mask from image.
        This does not clear loaded masks from memory."""
        if self.masktag:
            try:
                self.canvas.delete_object_by_tag(self.masktag, redraw=False)
            except Exception:
                pass

        if self.maskhltag:
            try:
                self.canvas.delete_object_by_tag(self.maskhltag, redraw=False)
            except Exception:
                pass

        self.treeview.clear()  # Clear table too
        self.fitsimage.redraw()  # Force immediate redraw

    def forget_masks(self):
        """Forget all loaded coordinates."""
        self._seqno = 1
        self._maskobjs = []
        self._treepaths = []
        self.tree_dict = Bunch.caselessDict()
        self.redo()

    # TODO: Support more formats?
    def load_file(self, filename):
        """Load mask image.

        Results are appended to previously loaded masks.
        This can be used to load mask per color.

        """
        if not os.path.isfile(filename):
            return

        self.logger.info('Loading mask image from {0}'.format(filename))

        try:
            # 0=False, everything else True
            dat = fits.getdata(filename).astype(np.bool)
        except Exception as e:
            self.logger.error('{0}: {1}'.format(e.__class__.__name__, str(e)))
            return

        key = '{0},{1}'.format(self.maskcolor, self.maskalpha)

        if key in self.tree_dict:
            sub_dict = self.tree_dict[key]
        else:
            sub_dict = {}
            self.tree_dict[key] = sub_dict

        # Add to listing
        seqstr = '{0:04d}'.format(self._seqno)  # Prepend 0s for proper sort
        sub_dict[seqstr] = Bunch.Bunch(ID=seqstr,
                                       MASKFILE=os.path.basename(filename))
        self._treepaths.append((key, seqstr))
        self._seqno += 1

        # Create mask layer
        obj = self.dc.Image(0, 0, masktorgb(
            dat, color=self.maskcolor, alpha=self.maskalpha))
        self._maskobjs.append(obj)

        self.redo()

    def load_files(self, filenames):
        """Load mask images.

        Results are appended to previously loaded masks.
        This can be used to load mask per color.

        """
        for filename in filenames:
            self.load_file(filename)

    def load_mask_cb(self):
        """Activate file dialog to select mask image."""
        self.mfilesel.popup('Load mask image', self.load_files,
                            initialdir='.', filename='FITS files (*.fits)')

    def recreate_toc(self):
        self.logger.debug('Recreating table of contents...')
        self.treeview.set_tree(self.tree_dict)

    def _rgbtomask(self, obj):
        """Convert RGB arrays from mask canvas object back to boolean mask."""
        dat = obj.get_image().get_data()  # RGB arrays
        return dat.sum(axis=2).astype(np.bool)  # Convert to 2D mask

    def hl_table2canvas(self, w, res_dict):
        """Highlight mask on canvas when user click on table."""
        objlist = []

        # Remove existing highlight
        if self.maskhltag:
            try:
                self.canvas.delete_object_by_tag(self.maskhltag, redraw=False)
            except Exception:
                pass

        for sub_dict in res_dict.values():
            for seqno in sub_dict:
                mobj = self._maskobjs[int(seqno) - 1]
                dat = self._rgbtomask(mobj)
                obj = self.dc.Image(0, 0, masktorgb(
                    dat, color=self.hlcolor, alpha=self.hlalpha))
                objlist.append(obj)

        # Draw on canvas
        if len(objlist) > 0:
            self.maskhltag = self.canvas.add(self.dc.CompoundObject(*objlist))

        self.fitsimage.redraw()  # Force immediate redraw

    def hl_canvas2table_box(self, canvas, tag):
        """Highlight all masks inside user drawn box on table."""
        self.treeview.clear_selection()

        # Remove existing box
        cobj = canvas.get_object_by_tag(tag)
        if cobj.kind != 'rectangle':
            return
        canvas.delete_object_by_tag(tag, redraw=False)

        # Remove existing highlight
        if self.maskhltag:
            try:
                canvas.delete_object_by_tag(self.maskhltag, redraw=True)
            except Exception:
                pass

        # Nothing to do if no masks are displayed
        try:
            obj = canvas.get_object_by_tag(self.masktag)
        except Exception:
            return

        if obj.kind != 'compound':
            return

        # Nothing to do if table has no data
        if len(self._maskobjs) == 0:
            return

        # Find masks that intersect the rectangle
        for i, mobj in enumerate(self._maskobjs):
            # The actual mask
            mask1 = self._rgbtomask(mobj)

            # The selected area
            rgbimage = mobj.get_image()
            mask2 = rgbimage.get_shape_mask(cobj)

            # Highlight mask with intersect
            if np.any(mask1 & mask2):
                self._highlight_path(self._treepaths[i])

    # NOTE: This does not work anymore when left click is used to draw box.
    def hl_canvas2table(self, canvas, button, data_x, data_y):
        """Highlight mask on table when user click on canvas."""
        self.treeview.clear_selection()

        # Remove existing highlight
        if self.maskhltag:
            try:
                canvas.delete_object_by_tag(self.maskhltag, redraw=True)
            except Exception:
                pass

        # Nothing to do if no masks are displayed
        try:
            obj = canvas.get_object_by_tag(self.masktag)
        except Exception:
            return

        if obj.kind != 'compound':
            return

        # Nothing to do if table has no data
        if len(self._maskobjs) == 0:
            return

        for i, mobj in enumerate(self._maskobjs):
            mask1 = self._rgbtomask(mobj)

            # Highlight mask covering selected cursor position
            if mask1[int(data_y), int(data_x)]:
                self._highlight_path(self._treepaths[i])

    def _highlight_path(self, hlpath):
        """Highlight an entry in the table and associated mask."""
        self.logger.debug('Highlighting {0}'.format(hlpath))
        self.treeview.select_path(hlpath)

        # TODO: Does not work in Qt. This is known issue in Ginga.
        self.treeview.scroll_to_path(hlpath)

    def set_maskcolor_cb(self, w, index):
        """Set color of mask."""
        self.maskcolor = self._color_options[index]

    def set_maskalpha(self):
        """Set alpha (transparency) of mask."""
        try:
            a = float(self.w.mask_alpha.get_text())
        except ValueError:
            self.logger.error('Cannot set mask alpha')
            self.w.mask_alpha.set_text(str(self.maskalpha))
            return

        if a < 0 or a > 1:
            self.logger.error('Alpha must be between 0 and 1, inclusive')
            self.w.mask_alpha.set_text(str(self.maskalpha))
            return

        self.maskalpha = a

    def close(self):
        self.fv.stop_local_plugin(self.chname, str(self))
        return True

    def start(self):
        # insert canvas, if not already
        p_canvas = self.fitsimage.get_canvas()
        try:
            p_canvas.get_object_by_tag(self.layertag)
        except KeyError:
            # Add drawing layer
            p_canvas.add(self.canvas, tag=self.layertag)

        self.resume()

    def pause(self):
        self.canvas.ui_set_active(False)

    def resume(self):
        # turn off any mode user may be in
        self.modes_off()

        self.canvas.ui_set_active(True, viewer=self.fitsimage)
        self.fv.show_status('Press "Help" for instructions')

    def stop(self):
        # remove canvas from image
        p_canvas = self.fitsimage.get_canvas()
        try:
            p_canvas.delete_object_by_tag(self.layertag)
        except Exception:
            pass

        self.canvas.update_canvas(whence=0)  # Force redraw
        self.gui_up = False
        self.fv.show_status('')

    def __str__(self):
        """
        This method should be provided and should return the lower case
        name of the plugin.
        """
        return 'tvmask'


# Append module docstring with config doc for auto insert by Sphinx.
from ginga.util.toolbox import generate_cfg_example  # noqa
if __doc__ is not None:
    __doc__ += generate_cfg_example('plugin_TVMask', package='ginga')

# END
