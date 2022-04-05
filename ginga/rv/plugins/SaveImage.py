# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
"""
Save images to output files.

**Plugin Type: Global**

``SaveImage`` is a global plugin.  Only one instance can be opened.

**Usage**

This global plugin is used to save any changes made in Ginga back to output
images. For example, a mosaic image that was created by the ``Mosaic``
plugin. Currently, only FITS images (single or multiple extensions) are
supported.

Given the output directory (e.g., ``/mypath/outputs/``), a suffix
(e.g., ``ginga``), an image channel (``Image``), and a selected image
(e.g., ``image1.fits``), the output file will be
``/mypath/outputs/image1_ginga_Image.fits``. Inclusion of the channel name is
optional and can be omitted using plugin configuration file,
``plugin_SaveImage.cfg``.
The modified extension(s) will have new header or data extracted from
Ginga, while those not modified will remain untouched. Relevant change
log entries from the ``ChangeHistory`` global plugin will be inserted into
the history of its ``PRIMARY`` header.

.. note:: This plugin uses the module ``astropy.io.fits`` to write the output
          images, regardless of what is chosen for ``FITSpkg`` in the
          ``general.cfg`` configuration file.

"""

# STDLIB
import os
import shutil

# THIRD-PARTY
from astropy.io import fits

# GINGA
from ginga.GingaPlugin import GlobalPlugin
from ginga.gw import Widgets
from ginga.misc import Bunch
from ginga.util.iohelper import shorten_name

try:
    from ginga.gw.GwHelp import DirectorySelection
except ImportError:  # This is needed for RTD to build
    pass

__all__ = ['SaveImage']


class SaveImage(GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(SaveImage, self).__init__(fv)

        # Image listing
        self.columns = [('Image', 'IMAGE'), ('Mod. Ext.', 'MODEXT')]

        # User preferences. Some are just default values and can also be
        # changed by GUI.
        prefs = self.fv.get_preferences()
        self.settings = prefs.create_category('plugin_SaveImage')
        self.settings.add_defaults(output_directory='.',
                                   output_suffix='ginga',
                                   include_chname=True,
                                   clobber=False,
                                   modified_only=True,
                                   max_mosaic_size=1e8,
                                   max_rows_for_col_resize=5000)
        self.settings.load(onError='silent')

        self.outdir = os.path.abspath(
            self.settings.get('output_directory', '.'))
        self.suffix = self.settings.get('output_suffix', 'ginga')

        self.fv.add_callback('add-image', lambda *args: self.redo())
        self.fv.add_callback('remove-image', lambda *args: self.redo())
        self.fv.add_callback('add-channel',
                             lambda *args: self.update_channels())
        self.fv.add_callback('delete-channel',
                             lambda *args: self.update_channels())

        self.chnames = []
        self.chname = None

        self.gui_up = False

    def build_gui(self, container):
        """Build GUI such that image list area is maximized."""

        vbox, sw, orientation = Widgets.get_oriented_box(container,
                                                         orientation=self.settings.get('orientation', None))

        captions = (('Channel:', 'label', 'Channel Name', 'combobox',
                     'Modified only', 'checkbutton'), )
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)

        b.channel_name.set_tooltip('Channel for locating images to save')
        b.channel_name.add_callback('activated', self.select_channel_cb)

        mod_only = self.settings.get('modified_only', True)
        b.modified_only.set_state(mod_only)
        b.modified_only.add_callback('activated', lambda *args: self.redo())
        b.modified_only.set_tooltip("Show only locally modified images")

        container.add_widget(w, stretch=0)

        captions = (('Path:', 'llabel', 'OutDir', 'entry', 'Browse', 'button'),
                    ('Suffix:', 'llabel', 'Suffix', 'entry'))
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)

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
        btn = Widgets.Button("Help")
        btn.add_callback('activated', lambda w: self.help())
        btns.add_widget(btn, stretch=0)
        btns.add_widget(Widgets.Label(''), stretch=1)
        container.add_widget(btns, stretch=0)

        self.gui_up = True

        # Initialize directory selection dialog
        self.dirsel = DirectorySelection(self.fv.w.root.get_widget())

        # Generate initial listing
        self.update_channels()

    def redo(self, *args):
        """Generate listing of images that user can save."""
        if not self.gui_up:
            return

        mod_only = self.w.modified_only.get_state()
        treedict = Bunch.caselessDict()
        self.treeview.clear()
        self.w.status.set_text('')

        channel = self.fv.get_channel(self.chname)
        if channel is None:
            return

        # Only list modified images for saving. Scanning Datasrc is enough.
        if mod_only:
            all_keys = channel.datasrc.keys(sort='alpha')

        # List all images in the channel.
        else:
            all_keys = channel.get_image_names()

        # Extract info for listing and saving
        for key in all_keys:
            iminfo = channel.get_image_info(key)
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

    def update_channels(self):
        """Update the GUI to reflect channels and image listing.
        """
        if not self.gui_up:
            return

        self.logger.debug("channel configuration has changed--updating gui")
        try:
            channel = self.fv.get_channel(self.chname)

        except KeyError:
            channel = self.fv.get_channel_info()

        if channel is None:
            raise ValueError('No channel available')

        self.chname = channel.name

        w = self.w.channel_name
        w.clear()

        self.chnames = list(self.fv.get_channel_names())
        #self.chnames.sort()
        for chname in self.chnames:
            w.append_text(chname)

        # select the channel that is the current one
        try:
            i = self.chnames.index(channel.name)
        except IndexError:
            i = 0
        self.w.channel_name.set_index(i)

        # update the image listing
        self.redo()

    def select_channel_cb(self, w, idx):
        self.chname = self.chnames[idx]
        self.logger.debug("channel name changed to '%s'" % (self.chname))
        self.redo()

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
        channel = self.fv.get_channel(self.chname)
        if channel is None:
            return

        history_plgname = 'ChangeHistory'
        try:
            history_obj = self.fv.gpmon.getPlugin(history_plgname)
        except Exception:
            self.logger.error(
                '{0} plugin is not loaded. No HISTORY will be written to '
                '{1}.'.format(history_plgname, pfx))
            return

        if channel.name not in history_obj.name_dict:
            self.logger.error(
                '{0} channel not found in {1}. No HISTORY will be written to '
                '{2}.'.format(channel.name, history_plgname, pfx))
            return

        file_dict = history_obj.name_dict[channel.name]
        chistory = []
        ind = ' ' * indentchar

        # NOTE: List comprehension too slow!
        for key in file_dict:
            if not key.startswith(pfx):
                continue
            for bnch in file_dict[key].values():
                chistory.append('{0} {1}'.format(bnch.MODIFIED, bnch.DESCRIP))

        # Add each HISTORY prettily into header, sorted by timestamp
        for s in sorted(chistory):
            for i in range(0, len(s), linechar):
                subs = s[i:i + linechar]
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
        channel = self.fv.get_channel(self.chname)
        image = channel.datasrc[key]

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
        hdu.writeto(outfile, overwrite=True)

    def _write_mef(self, key, extlist, outfile):
        """Write out regular multi-extension FITS data."""
        channel = self.fv.get_channel(self.chname)
        with fits.open(outfile, mode='update') as pf:
            # Process each modified data extension
            for idx in extlist:
                k = '{0}[{1}]'.format(key, self._format_extname(idx))
                image = channel.datasrc[k]

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

    def save_images(self):
        """Save selected images.

        This uses Astropy FITS package to save the outputs no matter
        what user chose to load the images.

        """
        res_dict = self.treeview.get_selected()
        clobber = self.settings.get('clobber', False)
        self.treeview.clear_selection()  # Automatically disables Save button

        # If user gives empty string, no suffix.
        if self.suffix:
            sfx = '_' + self.suffix
        else:
            sfx = ''

        # Also include channel name in suffix. This is useful if user likes to
        # open the same image in multiple channels.
        if self.settings.get('include_chname', True):
            sfx += '_' + self.chname

        # Process each selected file. Each can have multiple edited extensions.
        for infile in res_dict:
            f_pfx = os.path.splitext(infile)[0]  # prefix
            f_ext = '.fits'  # Only FITS supported
            oname = f_pfx + sfx + f_ext
            outfile = os.path.join(self.outdir, oname)

            self.w.status.set_text(
                'Writing out {0} to {1} ...'.format(shorten_name(infile, 10),
                                                    shorten_name(oname, 10)))
            self.logger.debug(
                'Writing out {0} to {1} ...'.format(infile, oname))

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

    def close(self):
        self.fv.stop_global_plugin(str(self))

    def start(self):
        self.resume()

    def resume(self):
        # turn off any mode user may be in
        try:
            self.modes_off()
        except AttributeError:
            pass

        self.fv.show_status('Press "Help" for instructions')

    def stop(self):
        self.gui_up = False
        self.fv.show_status('')

    def __str__(self):
        """
        This method should be provided and should return the lower case
        name of the plugin.
        """
        return 'saveimage'


# Append module docstring with config doc for auto insert by Sphinx.
from ginga.util.toolbox import generate_cfg_example  # noqa
if __doc__ is not None:
    __doc__ += generate_cfg_example('plugin_SaveImage', package='ginga')

# END
