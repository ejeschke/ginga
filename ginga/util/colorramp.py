#
# Make an RGB colorramp from HS
#
# Eric Jeschke (eric@naoj.org)
#
import sys
import colorsys

hue = float(sys.argv[1]) / 360.0
sat = float(sys.argv[2]) / 100.0

for val in xrange(256):
    hsv_val = float(val) / 255.0
    r, g, b = colorsys.hsv_to_rgb(hue, sat, hsv_val)
    print "    (%f, %f, %f)," % (r, g, b)

#END


