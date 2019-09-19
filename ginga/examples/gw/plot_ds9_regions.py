#
# Plot DS9 regions in a Ginga viewer
#
# NOTE: You need the Astropy "regions" package for this to work.
#
from ginga import toolkit
toolkit.use('qt5')

from astropy.utils.data import get_pkg_data_filename
import regions

from ginga.gw import sv
from ginga.util import ap_region

vf = sv.ViewerFactory()
v = vf.make_viewer(name="Ginga regions example", width=1000, height=1000)

image_file = get_pkg_data_filename('tutorials/FITS-images/HorseHead.fits')
v.load(image_file)

ds9_file = get_pkg_data_filename('data/plot_image.reg',
                                 package='regions.io.ds9.tests')
regs = regions.read_ds9(ds9_file)

canvas = v.add_canvas()
for i, reg in enumerate(regs):
    ap_region.add_region(canvas, reg)

vf.mainloop()
