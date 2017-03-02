#
# rgb_cms.py -- RGB color management handling.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from __future__ import print_function
import os
import glob
import hashlib

# How about color management (ICC profile) support?
try:
    import PIL.ImageCms as ImageCms
    have_cms = True
except ImportError:
    have_cms = False

have_pilutil = False
try:
    from scipy.misc import toimage, fromimage
    have_pilutil = True
except ImportError:
    pass

from ginga.util import paths


basedir = paths.ginga_home

# Holds profiles
profile = {}
rendering_intent = 'perceptual'
intents = dict(perceptual=0)

# Holds transforms
icc_transform = {}


class ColorManager(object):

    def __init__(self, logger):
        self.logger = logger

    def can_profile(self):
        return have_cms

    def profile_to_working_pil(self, image_pil, kwds, intent=None):

        image = image_pil

        # If we have a working color profile then handle any embedded
        # profile or color space information, if possible
        if not have_cms:
            self.logger.debug("No CMS is installed; leaving image unprofiled.")
            return image

        if not have_profile('working'):
            self.logger.debug("No working profile defined; leaving image unprofiled.")
            return image

        if not os.path.exists(profile['working']):
            self.logger.debug("Working profile %s not found; leaving image unprofiled." % (profile['working']))
            return image

        if intent is None:
            intent = rendering_intent

        # Assume sRGB image, unless we learn to the contrary
        in_profile = 'sRGB'
        try:
            if 'icc_profile' in image.info:
                self.logger.debug("image has embedded color profile")
                buf_profile = image.info['icc_profile']

                # Write out embedded profile (if needed)
                prof_md5 = hashlib.md5(buf_profile).hexdigest()
                in_profile = "/tmp/_image_%d_%s.icc" % (
                    os.getpid(), prof_md5)
                if not os.path.exists(in_profile):
                    with open(in_profile, 'w') as icc_f:
                        icc_f.write(buf_profile)

            # see if there is any EXIF tag about the colorspace
            elif 'ColorSpace' in kwds:
                csp = kwds['ColorSpace']
                iop = kwds.get('InteroperabilityIndex', None)
                if (csp == 0x2) or (csp == 0xffff):
                    # NOTE: 0xffff is really "undefined" and should be
                    # combined with a test of EXIF tag 0x0001
                    # ('InteropIndex') == 'R03', but PIL _getexif()
                    # does not return the InteropIndex
                    in_profile = 'AdobeRGB'
                    self.logger.debug("hmm..this looks like an AdobeRGB image")

                elif csp == 0x1:
                    self.logger.debug("hmm..this looks like a sRGB image")
                    in_profile = 'sRGB'

                else:
                    self.logger.debug("no color space metadata, assuming this is an sRGB image")

            # if we have a valid profile, try the conversion
            tr_key = (in_profile, 'working', intent)
            if tr_key in icc_transform:
                # We have am in-core transform already for this (faster)
                image = convert_profile_pil_transform(image,
                                                      icc_transform[tr_key],
                                                      inPlace=True)
            else:
                # Convert using profiles on disk (slower)
                if in_profile in profile:
                    in_profile = profile[in_profile]
                image = convert_profile_pil(image, in_profile,
                                            profile['working'],
                                            intent)

            self.logger.info("converted from profile (%s) to profile (%s)" % (
                in_profile, profile['working']))

        except Exception as e:
            self.logger.error("Error converting from embedded color profile: %s" % (str(e)))
            self.logger.warning("Leaving image unprofiled.")

        return image


# --- Color Management conversion functions ---

def convert_profile_pil(image_pil, inprof_path, outprof_path, intent_name,
                        inPlace=False):
    if not have_cms:
        return image_pil

    image_out = ImageCms.profileToProfile(image_pil, inprof_path,
                                          outprof_path,
                                          renderingIntent=intents[intent_name],
                                          outputMode='RGB', inPlace=inPlace,
                                          flags=0)
    if inPlace:
        return image_pil
    return image_out

def convert_profile_pil_transform(image_pil, transform, inPlace=False):
    if not have_cms:
        return image_pil

    image_out = ImageCms.applyTransform(image_pil, transform, inPlace)
    if inPlace:
        return image_pil
    return image_out

def convert_profile_numpy(image_np, inprof_path, outprof_path, intent_name):
    if (not have_pilutil) or (not have_cms):
        return image_np

    in_image_pil = toimage(image_np)
    out_image_pil = convert_profile_pil(in_image_pil,
                                        inprof_path, outprof_path, intent_name)
    image_out = fromimage(out_image_pil)
    return image_out

def convert_profile_numpy_transform(image_np, transform):
    if (not have_pilutil) or (not have_cms):
        return image_np

    in_image_pil = toimage(image_np)
    convert_profile_pil_transform(in_image_pil, transform, inPlace=True)
    image_out = fromimage(in_image_pil)
    return image_out

def get_transform_key(from_name, to_name, to_intent, proof_name,
                      proof_intent, flags):
    return (from_name, to_name, to_intent, proof_name, proof_intent,
            flags)

def get_transform(from_name, to_name, to_intent='perceptual',
                    proof_name=None, proof_intent=None,
                    use_black_pt=False):
    global icc_transform

    flags = 0
    if not (proof_name is None):
        flags |= ImageCms.SOFTPROOFING
    if use_black_pt:
        flags |= ImageCms.BLACKPOINTCOMPENSATION

    key = get_transform_key(from_name, to_name, to_intent, proof_name,
                            proof_intent, flags)

    try:
        output_transform = icc_transform[key]

    except KeyError:
        # try to build transform on the fly
        try:
            if not (proof_name is None):
                output_transform = ImageCms.buildProofTransform(
                    profile[from_name],
                    profile[to_name],
                    profile[proof_name],
                    'RGB', 'RGB',
                    renderingIntent=intents[to_intent],
                    proofRenderingIntent=intents[proof_intent],
                    flags=flags)
            else:
                output_transform = ImageCms.buildTransform(
                    profile[from_name],
                    profile[to_name],
                    'RGB', 'RGB',
                    renderingIntent=intents[to_intent],
                    flags=flags)

            icc_transform[key] = output_transform

        except Exception as e:
            raise Exception("Failed to build profile transform: %s" % (str(e)))

    return output_transform

def convert_profile_fromto(image_np, from_name, to_name,
                           to_intent='perceptual',
                           proof_name=None, proof_intent=None,
                           use_black_pt=False):

    try:
        output_transform = get_transform(from_name, to_name,
                                         to_intent=to_intent,
                                         proof_name=proof_name,
                                         proof_intent=proof_intent,
                                         use_black_pt=use_black_pt)

        out_np = convert_profile_numpy_transform(image_np, output_transform)
        return out_np

    except Exception as e:
        print("Error converting profile from '%s' to '%s': %s" % (
            from_name, to_name, str(e)))
        return image_np


def set_rendering_intent(intent):
    """
    Sets the color management attribute rendering intent.

    Parameters
    ----------
    intent: integer
      0: perceptual, 1: relative colorimetric, 2: saturation,
      3: absolute colorimetric
    """
    global rendering_intent
    rendering_intent = intent


# Look up all the profiles the user has available
glob_pat = os.path.join(basedir, "profiles", "*.icc")
for path in glob.glob(glob_pat):
    dirname, filename = os.path.split(path)
    profname, ext = os.path.splitext(filename)
    profile[profname] = os.path.abspath(path)

# These are ones we are particularly interested in
for filename in ('working.icc', 'monitor.icc', 'sRGB.icc', 'AdobeRGB.icc'):
    profname, ext = os.path.splitext(filename)
    profile[profname] = os.path.join(basedir, "profiles", filename)

# Build transforms for profile conversions for which we have profiles
if have_cms:
    d = dict(absolute_colorimetric=ImageCms.INTENT_ABSOLUTE_COLORIMETRIC,
             perceptual=ImageCms.INTENT_PERCEPTUAL,
             relative_colorimetric=ImageCms.INTENT_RELATIVE_COLORIMETRIC,
             saturation=ImageCms.INTENT_SATURATION)
    intents.update(d)


def have_profile(name):
    return name in profile.keys()

def get_profiles():
    names = list(profile.keys())
    names.sort()
    return names

def get_intents():
    names = list(intents.keys())
    names.sort()
    return names
