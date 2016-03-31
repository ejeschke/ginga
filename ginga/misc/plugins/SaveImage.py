"""Save output images local plugin for Ginga."""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
from ginga.util.six import itervalues
from ginga.util.six.moves import map

# STDLIB
import os
import shutil

# THIRD-PARTY
from astropy.io import fits

# GINGA
from ginga.GingaPlugin import LocalPlugin
from ginga.gw import Widgets
from ginga.gw.GwHelp import DirectorySelection
from ginga.misc import Bunch
from ginga.util import io_fits

__all__ = []


class SaveImage(LocalPlugin):
    """Save images to output files.

    This is a local plugin, not global, to avoid complications with
    the same image opened in multiple channels but having different
    modifications.

    """
    def __init__(self, *args):
        # superclass defines some variables for us, like logger
        if len(args) == 2:
            super(SaveImage, self).__init__(*args)
        else:
            super(SaveImage, self).__init__(args[0], None)

        # Image listing
        self.columns = [('Image', 'IMAGE'), ('Mod. Ext.', 'MODEXT')]

        try:
            self.list_plugin_obj = self.fv.gpmon.getPlugin('Contents')
        except:
            self.list_plugin_obj = None

        try:
            self.history_obj = self.fv.gpmon.getPlugin('ChangeHistory')
        except:
            self.history_obj = None

        # User preferences. Some are just default values and can also be
        # changed by GUI.
        prefs = self.fv.get_preferences()
        self.settings = prefs.createCategory('plugin_SaveImage')
        self.settings.load(onError='silent')
        self.outdir = os.path.abspath(
            self.settings.get('output_directory', '.'))
        self.suffix = self.settings.get('output_suffix', 'ginga')

        self.fv.add_callback('add-image', lambda *args: self.redo())
        self.fv.add_callback('remove-image', lambda *args: self.redo())
        self.fv.add_callback('delete-channel', self.delete_channel_cb)

        self.gui_up = False

    def build_gui(self, container):
        """Build GUI such that image list area is maximized."""

        vbox, sw, orientation = Widgets.get_oriented_box(container)

        msgFont = self.fv.getFont('sansFont', 12)
        tw = Widgets.TextArea(wrap=True, editable=False)
        tw.set_font(msgFont)
        self.tw = tw

        fr = Widgets.Expander('Instructions')
        fr.set_widget(tw)
        container.add_widget(fr, stretch=0)

        captions = (('Channel:', 'llabel', 'Channel Name', 'llabel'),
                    ('Path:', 'llabel', 'OutDir', 'entry',
                     'Browse', 'button'),
                    ('Suffix:', 'llabel', 'Suffix', 'entry'))
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)

        b.channel_name.set_text('Unknown')
        b.channel_name.set_tooltip('Channel this plugin is attached to')

        b.outdir.set_text(self.outdir)
        b.outdir.set_tooltip('Output directory')
        b.outdir.add_callback('activated', lambda w: self.set_outdir())

        b.browse.set_tooltip('Browse for output directory')
        b.browse.add_callback('activated', lambda w: self.browse_outdir())

        b.suffix.set_text(self.suffix)
        b.suffix.set_tooltip('Suffix to append to filename')
        b.suffix.add_callback('activated', lambda w: self.set_suffix())

        container.add_widget(w, stretch=0)

        self.treeview = Widgets.TreeView(auto_expand=True,
                                         sortable=True,
                                         selection='multiple',
                                         use_alt_row_color=True)
        self.treeview.setup_table(self.columns, 1, 'IMAGE')
        self.treeview.add_callback('selected', self.toggle_save_cb)
        container.add_widget(self.treeview, stretch=1)

        captions = (('Status', 'llabel'), )
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)
        b.status.set_text('')
        b.status.set_tooltip('Status message')
        container.add_widget(w, stretch=0)

        btns = Widgets.HBox()
        btns.set_border_width(4)
        btns.set_spacing(3)

        btn = Widgets.Button('Save')
        btn.set_tooltip('Save selected image(s)')
        btn.add_callback('activated', lambda w: self.save_images())
        btn.set_enabled(False)
        btns.add_widget(btn, stretch=0)
        self.w.save = btn

        btn = Widgets.Button('Close')
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn, stretch=0)
        btns.add_widget(Widgets.Label(''), stretch=1)
        container.add_widget(btns, stretch=0)

        self.gui_up = True

        # Initialize directory selection dialog
        self.dirsel = DirectorySelection(self.fv.w.root.get_widget())

        # In case this is called from global plugin space
        self.fv.error_wrap(self._check_chinfo)
        self.w.channel_name.set_text(self.chname)

        # Generate initial listing
        self.redo()

    def instructions(self):
        self.tw.set_text("""Enter output directory and suffix, if different than default. Left click to select image name to save. Multiple images can be selected using click with Shift or CTRL key. Click Save to save the selected image(s).

Output image will have the filename of <inputname>_<suffix>.fits.""")

    def redo(self, *args):
        """Generate listing of images that user can save."""
        if not self.gui_up:
            return

        mod_only = self.settings.get('modified_only', True)
        treedict = Bunch.caselessDict()
        self.treeview.clear()
        self.w.status.set_text('')

        # Only list modified images for saving. Scanning Datasrc is enough.
        if mod_only or (self.list_plugin_obj is None):
            func = self.keys_from_datasrc

        # List all images in the channel. Need to scan Contents global plugin.
        else:
            func = self.keys_from_contents

        # Extract info for listing and saving
        for key in func():
            iminfo = self.chinfo.get_image_info(key)
            path = iminfo.get('path')
            idx = iminfo.get('idx')
            t = iminfo.get('time_modified')

            if path is None:  # Special handling for generated buffer, eg mosaic
                infile = key
                is_fits = True
            else:
                infile = os.path.basename(path)
                infile_ext = os.path.splitext(path)[1]
                infile_ext = infile_ext.lower()
                is_fits = False

                if 'fit' in infile_ext:
                    is_fits = True

            # Only list FITS files unless it is Ginga generated buffer
            if not is_fits:
                continue

            # Only list modified buffers
            if mod_only and t is None:
                continue

            # More than one ext modified, append to existing entry
            if infile in treedict:
                if t is not None:
                    treedict[infile].extlist.add(idx)
                    elist = sorted(treedict[infile].extlist)
                    treedict[infile].MODEXT = ';'.join(
                        map(self._format_extname, elist))

            # Add new entry
            else:
                if t is None:
                    s = ''
                    extlist = set()
                else:
                    s = self._format_extname(idx)
                    extlist = set([idx])
                treedict[infile] = Bunch.Bunch(
                    IMAGE=infile, MODEXT=s, extlist=extlist, path=path)

        self.treeview.set_tree(treedict)

        # Resize column widths
        n_rows = len(treedict)
        if n_rows == 0:
            self.w.status.set_text('Nothing available for saving')
        elif n_rows < self.settings.get('max_rows_for_col_resize', 5000):
            self.treeview.set_optimal_column_widths()
            self.logger.debug('Resized columns for {0} row(s)'.format(n_rows))

        return

    def _check_chinfo(self):
        """Special handling for when plugin is started from global plugin
        menu.

        This locks the plugin to the active channel when it starts.
        To change the associated channel in global plugin space, user
        needs to manual close and reload the plugin. Doing this
        dynamically inside redo() messes up the behavior in
        local plugin space.

        """
        self.chinfo = self.fv.get_channelInfo()

        if self.chinfo is None:
            raise ValueError('No channel available')

        self.chname = self.chinfo.name

    def keys_from_datasrc(self):
        """Yield back keys for image listing from Ginga's data cache."""
        for key in self.chinfo.datasrc.sortedkeys:
            yield key

    def keys_from_contents(self):
        """Yield back keys for image listing  from ``Contents`` global plugin.
        """
        for key in self.list_plugin_obj.name_dict[self.chname]:
            yield key

    def _format_extname(self, ext):
        """Pretty print given extension name and number tuple."""
        if ext is None:
            outs = ext
        else:
            outs = '{0},{1}'.format(ext[0], ext[1])
        return outs

    def browse_outdir(self):
        """Browse for output directory."""
        self.dirsel.popup(
            'Select directory', self.w.outdir.set_text, initialdir=self.outdir)
        self.set_outdir()

    def set_outdir(self):
        """Set output directory."""
        dirname = self.w.outdir.get_text()
        if os.path.isdir(dirname):
            self.outdir = dirname
            self.logger.debug('Output directory set to {0}'.format(self.outdir))
        else:
            self.w.outdir.set_text(self.outdir)
            self.logger.error('{0} is not a directory'.format(dirname))

    def set_suffix(self):
        """Set output suffix."""
        self.suffix = self.w.suffix.get_text()
        self.logger.debug('Output suffix set to {0}'.format(self.suffix))

    def _write_history(self, pfx, hdu, linechar=60, indentchar=2):
        """Write change history to given HDU header.
        Limit each HISTORY line to given number of characters.
        Subsequent lines of the same history will be indented.
        """
        if self.history_obj is None:
            return

        file_dict = self.history_obj.name_dict[self.chname]
        chistory = []
        ind = ' ' * indentchar

        # NOTE: List comprehension too slow!
        for key in file_dict:
            if not key.startswith(pfx):
                continue
            for bnch in itervalues(file_dict[key]):
                chistory.append('{0} {1}'.format(bnch.MODIFIED, bnch.DESCRIP))

        # Add each HISTORY prettily into header, sorted by timestamp
        for s in sorted(chistory):
            for i in range(0, len(s), linechar):
                subs = s[i:i+linechar]
                if i > 0:
                    subs = ind + subs.lstrip()
                hdu.header.add_history(subs)

    def _write_header(self, image, hdu):
        """Write header from image object to given HDU."""
        hduhdr = hdu.header

        # Ginga image header object for the given extension only.
        # Cannot use get_header() because that might also return PRI hdr.
        ghdr = image.metadata['header']

        for key in ghdr:
            # Need this to avoid duplication because COMMENT is a weird field
            if key.upper() == 'COMMENT':
                continue

            bnch = ghdr.get_card(key)

            # Insert new keyword
            if key not in hduhdr:
                hduhdr[key] = (bnch.value, bnch.comment)

            # Update existing keyword
            elif hduhdr[key] != bnch.value:
                hduhdr[key] = bnch.value

    def _write_mosaic(self, key, outfile):
        """Write out mosaic data (or any new data generated within Ginga)
        to single-extension FITS.

        """
        maxsize = self.settings.get('max_mosaic_size', 1e8)  # Default 10k x 10k
        image = self.chinfo.datasrc[key]

        # Prevent writing very large mosaic
        if (image.width * image.height) > maxsize:
            s = 'Mosaic too large to be written {0}'.format(image.shape)
            self.w.status.set_text(s)
            self.logger.error(s)
            return

        # Insert mosaic data and header into output HDU
        hdu = fits.PrimaryHDU(image.get_data())
        self._write_header(image, hdu)

        # Write history to PRIMARY
        self._write_history(key, hdu)

        # Write to file
        hdu.writeto(outfile, clobber=True)

    def _write_mef(self, key, extlist, outfile):
        """Write out regular multi-extension FITS data."""
        with fits.open(outfile, mode='update') as pf:
            # Process each modified data extension
            for idx in extlist:
                k = '{0}[{1}]'.format(key, self._format_extname(idx))
                image = self.chinfo.datasrc[k]

                # Insert data and header into output HDU
                pf[idx].data = image.get_data()
                self._write_header(image, pf[idx])

            # Write history to PRIMARY
            self._write_history(key, pf['PRIMARY'])

    def toggle_save_cb(self, w, res_dict):
        """Only enable saving if something is selected."""
        if len(res_dict) > 0:
            self.w.save.set_enabled(True)
        else:
            self.w.save.set_enabled(False)
        return

    def save_images(self):
        """Save selected images."""
        res_dict = self.treeview.get_selected()
        clobber = self.settings.get('clobber', False)
        self.treeview.clear_selection()  # Automatically disables Save button

        # If user chooses fitsio over astropy, cannot continue.
        if (io_fits.fitsLoaderClass.__name__ !=
                io_fits.PyFitsFileHandler.__name__):
            s = 'Set FITSpkg="astropy" in general.cfg'
            self.w.status.set_text(s)
            self.logger.error(s)
            return

        # If user gives empty string, no suffix.
        if self.suffix:
            sfx = '_' + self.suffix
        else:
            sfx = ''

        # Process each selected file. Each can have multiple edited extensions.
        for infile in res_dict:
            f_pfx = os.path.splitext(infile)[0]  # prefix
            f_ext = '.fits'  # Only FITS supported
            oname = f_pfx + sfx + f_ext
            outfile = os.path.join(self.outdir, oname)

            s = 'Writing out {0} to {1} ...'.format(infile, oname)
            self.w.status.set_text(s)
            self.logger.debug(s)

            if os.path.exists(outfile) and not clobber:
                self.logger.error('{0} already exists'.format(outfile))
                continue

            bnch = res_dict[infile]

            if bnch.path is None or not os.path.isfile(bnch.path):
                self._write_mosaic(f_pfx, outfile)
            else:
                shutil.copyfile(bnch.path, outfile)
                self._write_mef(f_pfx, bnch.extlist, outfile)

            self.logger.info('{0} written'.format(outfile))

        self.w.status.set_text('Saving done, see log')

    def delete_channel_cb(self, viewer, channel):
        """If channel is deleted, close the plugin immediately in
        global plugin space."""
        if self.chname == channel.name and self.fitsimage is None:
            self.close()

    def close(self):
        if self.fitsimage is None:
            self.fv.stop_global_plugin(str(self))
        else:
            self.fv.stop_local_plugin(self.chname, str(self))
        return

    def start(self):
        self.instructions()
        self.resume()

    def pause(self):
        self.canvas.ui_setActive(False)

    def resume(self):
        # turn off any mode user may be in
        try:
            self.modes_off()
        except AttributeError:
            pass

        self.fv.showStatus('See instructions')

    def stop(self):
        self.gui_up = False
        self.fv.showStatus('')

    def __str__(self):
        """
        This method should be provided and should return the lower case
        name of the plugin.
        """
        return 'saveimage'


# Replace module docstring with config doc for auto insert by Sphinx.
# In the future, if we need the real docstring, we can append instead of
# overwrite.
from ginga.util.toolbox import generate_cfg_example
__doc__ = generate_cfg_example('plugin_SaveImage', package='ginga')
