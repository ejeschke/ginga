"""Non-interactive points marking local plugin for Ginga."""
from __future__ import absolute_import, division, print_function
from ginga.util.six import iteritems, itervalues
from ginga.util.six.moves import map, zip

# STDLIB
import re
import os
from collections import defaultdict

# THIRD-PARTY
import numpy as np
from astropy.table import Table

# GINGA
from ginga import colors
from ginga.GingaPlugin import LocalPlugin
from ginga.gw import Widgets
from ginga.misc import Bunch

# Need this for API doc to build without warning
try:
    from ginga.gw.GwHelp import FileSelection
except ImportError:
    pass

__all__ = []


class TVMark(LocalPlugin):
    """Mark points from file (non-interative mode) on an image."""
    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(TVMark, self).__init__(fv, fitsimage)

        self.layertag = 'tvmark-canvas'
        self.marktag = None
        self.markhltag = None

        self._mark_options = ['box', 'circle', 'cross', 'plus', 'point']
        self._color_options = self._short_color_list()
        self._dwidth = 2  # Additional width to highlight selection

        # User preferences. Some are just default values and can also be
        # changed by GUI.
        prefs = self.fv.get_preferences()
        self.settings = prefs.createCategory('plugin_TVMark')
        self.settings.load(onError='silent')
        self.marktype = self.settings.get('marktype', 'circle')
        self.markcolor = self.settings.get('markcolor', 'green')
        self.marksize = self.settings.get('marksize', 5)
        self.markwidth = self.settings.get('markwidth', 1)
        self.pixelstart = self.settings.get('pixelstart', 1)
        self.use_radec = self.settings.get('use_radec', True)
        self.extra_columns = self.settings.get('extra_columns', [])

        # Display coords info table
        self.treeview = None
        self.treeviewsel = None
        self.treeviewbad = None
        self.tree_dict = Bunch.caselessDict()
        self.columns = [('No.', 'MARKID'), ('RA', 'RA'), ('DEC', 'DEC'),
                        ('X', 'X'), ('Y', 'Y')]

        # Append extra columns to table header
        self.columns += [(colname, colname) for colname in self.extra_columns]

        # Store results
        self.coords_dict = defaultdict(list)
        self._xarr = []
        self._yarr = []
        self._treepaths = []

        self.dc = self.fv.get_draw_classes()

        canvas = self.dc.DrawingCanvas()
        canvas.enable_draw(True)
        canvas.enable_edit(False)
        canvas.set_callback('draw-event', self.hl_canvas2table_box)
        canvas.set_callback('cursor-down', self.hl_canvas2table)
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
        vbox, sw, self.orientation = Widgets.get_oriented_box(container)

        msg_font = self.fv.get_font('sansFont', 12)
        tw = Widgets.TextArea(wrap=True, editable=False)
        tw.set_font(msg_font)
        self.tw = tw

        fr = Widgets.Expander('Instructions')
        fr.set_widget(tw)
        container.add_widget(fr, stretch=0)

        captions = (('Mark:', 'label', 'mark type', 'combobox'),
                    ('Color:', 'label', 'mark color', 'combobox'),
                    ('Size:', 'label', 'mark size', 'entry'),
                    ('Width:', 'label', 'mark width', 'entry'))
        w, b = Widgets.build_info(captions)
        self.w.update(b)

        combobox = b.mark_type
        for name in self._mark_options:
            combobox.append_text(name)
        b.mark_type.set_index(self._mark_options.index(self.marktype))
        b.mark_type.add_callback('activated', self.set_marktype_cb)

        combobox = b.mark_color
        for name in self._color_options:
            combobox.append_text(name)
        b.mark_color.set_index(self._color_options.index(self.markcolor))
        b.mark_color.add_callback('activated', self.set_markcolor_cb)

        b.mark_size.set_tooltip('Size/radius of the marking')
        b.mark_size.set_text(str(self.marksize))
        b.mark_size.add_callback('activated', lambda w: self.set_marksize())

        b.mark_width.set_tooltip('Line width of the marking')
        b.mark_width.set_text(str(self.markwidth))
        b.mark_width.add_callback('activated', lambda w: self.set_markwidth())

        container.add_widget(w, stretch=0)

        nb = Widgets.TabWidget()
        self.w.nb1 = nb
        container.add_widget(nb, stretch=1)

        treeview = Widgets.TreeView(auto_expand=True,
                                    sortable=True,
                                    selection='multiple',
                                    use_alt_row_color=True)
        self.treeview = treeview
        treeview.setup_table(self.columns, 2, 'MARKID')
        treeview.add_callback('selected', self.hl_table2canvas)
        nb.add_widget(treeview, title='Shown')

        treeview2 = Widgets.TreeView(auto_expand=True,
                                     sortable=True,
                                     use_alt_row_color=True)
        self.treeviewsel = treeview2
        treeview2.setup_table(self.columns, 2, 'MARKID')
        nb.add_widget(treeview2, title='Selected')

        treeview3 = Widgets.TreeView(auto_expand=True,
                                     sortable=True,
                                     use_alt_row_color=True)
        self.treeviewbad = treeview3
        treeview3.setup_table(self.columns, 2, 'MARKID')
        nb.add_widget(treeview3, title='Outliers')

        captions = (('Loaded:', 'llabel', 'ntotal', 'llabel',
                     'Shown:', 'llabel', 'nshown', 'llabel',
                     'Selected:', 'llabel', 'nselected', 'llabel'), )
        w, b = Widgets.build_info(captions)
        self.w.update(b)

        b.ntotal.set_tooltip('Number of objects read from tables')
        b.ntotal.set_text('0')

        b.nshown.set_tooltip('Number of objects shown on image')
        b.nshown.set_text('0')

        b.nselected.set_tooltip('Number of objects selected')
        b.nselected.set_text('0')

        container.add_widget(w, stretch=0)

        captions = (('Load Coords', 'button', 'Use RADEC', 'checkbutton'),
                    ('Show', 'button', 'Hide', 'button', 'Forget', 'button'))
        w, b = Widgets.build_info(captions)
        self.w.update(b)

        b.load_coords.set_tooltip('Load coordinates file')
        b.load_coords.add_callback('activated', lambda w: self.load_coords_cb())

        b.use_radec.set_tooltip('Use RA/DEC as coordinates instead of X/Y')
        b.use_radec.set_state(self.use_radec)
        b.use_radec.add_callback('activated', self.set_coordtype_cb)

        b.show.set_tooltip('Show markings')
        b.show.add_callback('activated', lambda w: self.redo())

        b.hide.set_tooltip('Hide markings')
        b.hide.add_callback('activated', lambda w: self.clear_marking())

        b.forget.set_tooltip('Forget markings')
        b.forget.add_callback('activated', lambda w: self.forget_coords())

        container.add_widget(w, stretch=0)

        btns = Widgets.HBox()
        btns.set_border_width(4)
        btns.set_spacing(3)

        btn = Widgets.Button('Close')
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn, stretch=0)
        btns.add_widget(Widgets.Label(''), stretch=1)

        container.add_widget(btns, stretch=0)

        self.gui_up = True

        # Initialize coordinates file selection dialog
        self.cfilesel = FileSelection(self.fv.w.root.get_widget())

        # Populate table
        self.redo()

    def instructions(self):
        self.tw.set_text("""Set mark parameters. Then, load coordinates file to mark them on image with the specified marking. To add different kind of marking, change the mark parameters and load another file.

Press "Hide" to clear all markings (does not clear memory). Press "Show" to replot them. Press "Forget" to forget all markings in memory.

""")

    def redo(self):
        """Image or coordinates have changed. Clear and redraw."""
        if not self.gui_up:
            return

        self.clear_marking()
        self.tree_dict = Bunch.caselessDict()
        self.treeviewbad.clear()
        bad_tree_dict = Bunch.caselessDict()
        nbad = 0
        self._xarr = []
        self._yarr = []
        self._treepaths = []

        image = self.fitsimage.get_image()
        if image is None:
            return

        if not hasattr(image, 'radectopix'):
            self.logger.error(
                'Image as no radectopix() method for coordinates conversion')
            return

        objlist = []
        seqno = 1
        max_x = image.width - 1
        max_y = image.height - 1

        for key, coords in iteritems(self.coords_dict):
            if len(coords) == 0:
                continue

            marktype, marksize, markcolor = key
            kstr = ','.join(map(str, key))
            sub_dict = {}
            bad_sub_dict = {}
            self.tree_dict[kstr] = sub_dict
            bad_tree_dict[kstr] = bad_sub_dict

            for args in coords:
                ra, dec, x, y = args[:4]

                # Use X and Y positions directly. Convert to RA and DEC (deg).
                if ra is None or dec is None:
                    ra, dec = image.pixtoradec(x, y)

                # RA and DEC already in degrees. Convert to pixel X and Y.
                else:
                    x, y = image.radectopix(ra, dec)

                # Display original X/Y (can be 0- or 1-indexed) using
                # our internal 0-indexed values.
                xdisp = x + self.pixelstart
                ydisp = y + self.pixelstart

                seqstr = '{0:04d}'.format(seqno)  # Prepend 0s for proper sort
                bnch = Bunch.Bunch(zip(self.extra_columns, args[4:]))  # Extra
                bnch.update(Bunch.Bunch(MARKID=seqstr, RA=ra, DEC=dec,
                                        X=xdisp, Y=ydisp))

                # Do not draw out of bounds
                if (not np.isfinite(x) or x < 0 or x > max_x or
                        not np.isfinite(y) or y < 0 or y > max_y):
                    self.logger.debug('Ignoring RA={0}, DEC={1} '
                                      '(x={2}, y={3})'.format(ra, dec, x, y))
                    bad_sub_dict[seqstr] = bnch
                    nbad += 1

                # Display point
                else:
                    obj = self._get_markobj(
                        x, y, marktype, marksize, markcolor, self.markwidth)
                    objlist.append(obj)

                    sub_dict[seqstr] = bnch
                    self._xarr.append(x)
                    self._yarr.append(y)
                    self._treepaths.append((kstr, seqstr))

                seqno += 1

        n_obj = len(objlist)
        self.logger.debug('Displaying {0} markings'.format(n_obj))

        if nbad > 0:
            self.treeviewbad.set_tree(bad_tree_dict)

        if n_obj == 0:
            return

        # Convert to Numpy arrays to avoid looping later
        self._xarr = np.array(self._xarr)
        self._yarr = np.array(self._yarr)
        self._treepaths = np.array(self._treepaths)

        # Display info table
        self.recreate_toc()

        # Draw on canvas
        self.marktag = self.canvas.add(self.dc.CompoundObject(*objlist))
        self.fitsimage.redraw()  # Force immediate redraw

    def _get_markobj(self, x, y, marktype, marksize, markcolor, markwidth):
        """Generate canvas object for given mark parameters."""
        if marktype == 'circle':
            obj = self.dc.Circle(
                x=x, y=y, radius=marksize, color=markcolor, linewidth=markwidth)
        elif marktype in ('cross', 'plus'):
            obj = self.dc.Point(
                x=x, y=y, radius=marksize, color=markcolor, linewidth=markwidth,
                style=marktype)
        elif marktype == 'box':
            obj = self.dc.Box(
                x=x, y=y, xradius=marksize, yradius=marksize, color=markcolor,
                linewidth=markwidth)
        else:  # point, marksize
            obj = self.dc.Box(
                x=x, y=y, xradius=1, yradius=1, color=markcolor,
                linewidth=markwidth, fill=True, fillcolor=markcolor)

        return obj

    def clear_marking(self):
        """Clear marking from image.
        This does not clear loaded coordinates from memory."""
        if self.marktag:
            try:
                self.canvas.delete_object_by_tag(self.marktag, redraw=False)
            except:
                pass

        if self.markhltag:
            try:
                self.canvas.delete_object_by_tag(self.markhltag, redraw=False)
            except:
                pass

        self.treeview.clear()  # Clear table too
        self.w.nshown.set_text('0')
        self.fitsimage.redraw()  # Force immediate redraw

    def forget_coords(self):
        """Forget all loaded coordinates."""
        self.w.ntotal.set_text('0')
        self.coords_dict.clear()
        self.redo()

    # TODO: Support more formats?
    def load_file(self, filename):
        """Load coordinates file.

        Results are appended to previously loaded coordinates.
        This can be used to load one file per color.

        """
        if not os.path.isfile(filename):
            return

        self.logger.info('Loading coordinates from {0}'.format(filename))

        if filename.endswith('.fits'):
            fmt = 'fits'
        else:  # Assume ASCII
            fmt = 'ascii'

        try:
            tab = Table.read(filename, format=fmt)
        except Exception as e:
            self.logger.error('{0}: {1}'.format(e.__class__.__name__, str(e)))
            return

        if self.use_radec:
            colname0 = self.settings.get('ra_colname', 'ra')
            colname1 = self.settings.get('dec_colname', 'dec')
        else:
            colname0 = self.settings.get('x_colname', 'x')
            colname1 = self.settings.get('y_colname', 'y')

        try:
            col_0 = tab[colname0]
            col_1 = tab[colname1]
        except Exception as e:
            self.logger.error('{0}: {1}'.format(e.__class__.__name__, str(e)))
            return

        nrows = len(col_0)
        dummy_col = [None] * nrows

        try:
            oldrows = int(self.w.ntotal.get_text())
        except ValueError:
            oldrows = 0

        self.w.ntotal.set_text(str(oldrows + nrows))

        if self.use_radec:
            ra = self._convert_radec(col_0)
            dec = self._convert_radec(col_1)
            x = y = dummy_col
        else:
            ra = dec = dummy_col

            # X and Y always 0-indexed internally
            x = col_0.data - self.pixelstart
            y = col_1.data - self.pixelstart

        args = [ra, dec, x, y]

        # Load extra columns
        for colname in self.extra_columns:
            try:
                col = tab[colname].data
            except Exception as e:
                self.logger.error(
                    '{0}: {1}'.format(e.__class__.__name__, str(e)))
                col = dummy_col

            args.append(col)

        # Use list to preserve order. Does not handle duplicates.
        key = (self.marktype, self.marksize, self.markcolor)
        self.coords_dict[key] += list(zip(*args))

        self.redo()

    def _convert_radec(self, val):
        """Convert RA or DEC table column to degrees and extract data.
        Assume already in degrees if cannot convert.

        """
        try:
            ans = val.to('deg')
        except Exception as e:
            self.logger.error('Cannot convert, assume already in degrees')
            ans = val.data
        else:
            ans = ans.value

        return ans

    # TODO: Support more extensions?
    def load_coords_cb(self):
        """Activate file dialog to select coordinates file."""
        self.cfilesel.popup('Load coordinates file', self.load_file,
                            initialdir='.',
                            filename='Table files (*.txt *.dat *.fits)')

    def set_coordtype_cb(self, w, val):
        """Toggle between RA/DEC or X/Y coordinates."""
        self.use_radec = val

    def recreate_toc(self):
        self.logger.debug('Recreating table of contents...')
        self.treeview.set_tree(self.tree_dict)
        n = 0

        for sub_dict in itervalues(self.tree_dict):
            n += len(sub_dict)

        self.w.nshown.set_text(str(n))

    def hl_table2canvas(self, w, res_dict):
        """Highlight marking on canvas when user click on table."""
        objlist = []
        width = self.markwidth + self._dwidth

        # Remove existing highlight
        if self.markhltag:
            try:
                self.canvas.delete_object_by_tag(self.markhltag, redraw=False)
            except:
                pass

        # Display highlighted entries only in second table
        self.treeviewsel.set_tree(res_dict)

        for kstr, sub_dict in iteritems(res_dict):
            s = kstr.split(',')
            marktype = s[0]
            marksize = float(s[1])
            markcolor = s[2]

            for bnch in itervalues(sub_dict):
                obj = self._get_markobj(bnch.X - self.pixelstart,
                                        bnch.Y - self.pixelstart,
                                        marktype, marksize, markcolor, width)
                objlist.append(obj)

        nsel = len(objlist)
        self.w.nselected.set_text(str(nsel))

        # Draw on canvas
        if nsel > 0:
            self.markhltag = self.canvas.add(self.dc.CompoundObject(*objlist))

        self.fitsimage.redraw()  # Force immediate redraw

    def hl_canvas2table_box(self, canvas, tag):
        """Highlight all markings inside user drawn box on table."""
        self.treeview.clear_selection()

        # Remove existing box
        cobj = canvas.get_object_by_tag(tag)
        if cobj.kind != 'rectangle':
            return
        canvas.delete_object_by_tag(tag, redraw=False)

        # Remove existing highlight
        if self.markhltag:
            try:
                canvas.delete_object_by_tag(self.markhltag, redraw=True)
            except:
                pass

        # Nothing to do if no markings are displayed
        try:
            obj = canvas.get_object_by_tag(self.marktag)
        except:
            return

        if obj.kind != 'compound':
            return

        # Nothing to do if table has no data
        if (len(self._xarr) == 0 or len(self._yarr) == 0 or
                len(self._treepaths) == 0):
            return

        # Find markings inside box
        mask = cobj.contains_arr(self._xarr, self._yarr)

        for hlpath in self._treepaths[mask]:
            self._highlight_path(hlpath)

    def hl_canvas2table(self, canvas, button, data_x, data_y):
        """Highlight marking on table when user click on canvas."""
        self.treeview.clear_selection()

        # Remove existing highlight
        if self.markhltag:
            try:
                canvas.delete_object_by_tag(self.markhltag, redraw=True)
            except:
                pass

        # Nothing to do if no markings are displayed
        try:
            obj = canvas.get_object_by_tag(self.marktag)
        except:
            return

        if obj.kind != 'compound':
            return

        # Nothing to do if table has no data
        if (len(self._xarr) == 0 or len(self._yarr) == 0 or
                len(self._treepaths) == 0):
            return

        sr = self.settings.get('searchradius', 10)
        dx = data_x - self._xarr
        dy = data_y - self._yarr
        dr = np.sqrt(dx * dx + dy * dy)
        mask = dr <= sr

        for hlpath in self._treepaths[mask]:
            self._highlight_path(hlpath)

    def _highlight_path(self, hlpath):
        """Highlight an entry in the table and associated marking."""
        self.logger.debug('Highlighting {0}'.format(hlpath))
        self.treeview.select_path(hlpath)

        # TODO: Does not work in Qt. This is known issue in Ginga.
        self.treeview.scroll_to_path(hlpath)

    def set_marktype_cb(self, w, index):
        """Set type of marking."""
        self.marktype = self._mark_options[index]

        # Mark size is not used for point
        if self.marktype != 'point':
            self.w.mark_size.set_enabled(True)
        else:
            self.w.mark_size.set_enabled(False)

    def set_markcolor_cb(self, w, index):
        """Set color of marking."""
        self.markcolor = self._color_options[index]

    def set_marksize(self):
        """Set size/radius of marking."""
        try:
            sz = float(self.w.mark_size.get_text())
        except ValueError:
            self.logger.error('Cannot set mark size')
            self.w.mark_size.set_text(str(self.marksize))
        else:
            self.marksize = sz

    def set_markwidth(self):
        """Set width of marking."""
        try:
            sz = int(self.w.mark_width.get_text())
        except ValueError:
            self.logger.error('Cannot set mark width')
            self.w.mark_width.set_text(str(self.markwidth))
        else:
            self.markwidth = sz

    def close(self):
        self.fv.stop_local_plugin(self.chname, str(self))
        return True

    def start(self):
        self.instructions()

        # insert canvas, if not already
        p_canvas = self.fitsimage.get_canvas()
        try:
            obj = p_canvas.get_object_by_tag(self.layertag)
        except KeyError:
            # Add drawing layer
            p_canvas.add(self.canvas, tag=self.layertag)

        self.resume()

    def pause(self):
        self.canvas.ui_setActive(False)

    def resume(self):
        # turn off any mode user may be in
        self.modes_off()

        self.canvas.ui_setActive(True)
        self.fv.show_status('See instructions')

    def stop(self):
        # remove canvas from image
        p_canvas = self.fitsimage.get_canvas()
        try:
            p_canvas.delete_object_by_tag(self.layertag)
        except:
            pass

        # Free some memory, maybe
        self.tree_dict = Bunch.caselessDict()
        self._xarr = []
        self._yarr = []
        self._treepaths = []

        self.gui_up = False
        self.fv.show_status('')

    def __str__(self):
        """
        This method should be provided and should return the lower case
        name of the plugin.
        """
        return 'tvmark'


# Replace module docstring with config doc for auto insert by Sphinx.
# In the future, if we need the real docstring, we can append instead of
# overwrite.
from ginga.util.toolbox import generate_cfg_example
__doc__ = generate_cfg_example('plugin_TVMark', package='ginga')
