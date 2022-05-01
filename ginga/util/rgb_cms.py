#
# rgb_cms.py -- RGB color management handling.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#

import os
import glob
import hashlib
import tempfile
import numpy as np

from ginga import trcalc
from ginga.misc import Bunch
from ginga.util.toolbox import PIL_LT_9_1

from . import paths

from PIL import Image
# How about color management (ICC profile) support?
have_cms = False
have_pil_lcms = False

try:
    import PIL.ImageCms as ImageCms
    have_pil_lcms = True
    have_cms = True
except ImportError:
    pass

basedir = paths.ginga_home

# Holds profiles
profile_dict = {}
rendering_intent = 'perceptual'
intents = dict(perceptual=0)

# The working profile, if there is one
working_profile = None

# Holds transforms
icc_transform_dict = {}


class ColorManagerError(Exception):
    pass


class ColorManager:

    def __init__(self, logger):
        self.logger = logger

    def can_profile(self):
        return have_cms

    def profile_to_working_numpy(self, image_np, kwds, intent=None):

        # If we have a working color profile then handle any embedded
        # profile or color space information, if possible
        if not have_cms:
            self.logger.info(
                "No CMS is installed; leaving image unprofiled.")
            return image_np

        if not have_profile(working_profile):
            self.logger.info(
                "No working profile defined; leaving image unprofiled.")
            return image_np

        out_profile = profile_dict[working_profile].name

        if not os.path.exists(profile_dict[out_profile].path):
            self.logger.info(
                "Working profile '%s' (%s) not found; leaving image "
                "unprofiled." % (out_profile, profile_dict[out_profile].path))
            return image_np

        if image_np.dtype != np.uint8:
            ## image_np = trcalc.array_convert(image_np, np.dtype(np.uint8))
            self.logger.info(
                "Cannot profile >8 bpp images; leaving image unprofiled.")
            return image_np

        if intent is None:
            intent = rendering_intent

        # Assume sRGB image, unless we learn to the contrary
        in_profile = 'sRGB'
        try:
            if 'icc_profile' in kwds:
                self.logger.info("image has embedded color profile")
                buf_profile = kwds['icc_profile']
                # NOTE: is there a way to get a name for this embedded profile?
                # make up a unique name
                in_profile = hashlib.md5(buf_profile).hexdigest()  # nosec

                # Write out embedded profile (if needed)
                if in_profile not in profile_dict:
                    _fd, path = tempfile.mkstemp(suffix=".icc",
                                                 prefix="_image_{}_".format(in_profile))
                    with os.fdopen(_fd, 'wb') as icc_f:
                        icc_f.write(buf_profile)
                    profile_dict[in_profile] = Bunch.Bunch(name=in_profile,
                                                           path=os.path.abspath(path))

            # see if there is any EXIF tag about the colorspace
            elif 'ColorSpace' in kwds:
                csp = kwds['ColorSpace']
                #iop = kwds.get('InteroperabilityIndex', None)
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

            # check if image has an alpha channel; if so we need to remove
            # it before ICC transform and tack it back on afterwards
            image_rgb, alpha = image_np, None
            if 'A' in trcalc.guess_order(image_np.shape):
                image_rgb, alpha = trcalc.remove_alpha(image_np)

            if have_pil_lcms:
                # fallback to LCMS bundled with pillow, if available
                # if we have a valid profile, try the conversion
                tr_key = get_transform_key(in_profile, out_profile, intent,
                                           None, None, 0)

                # convert numpy image to PIL format
                image_pil = to_image(image_rgb)

                if tr_key in icc_transform_dict:
                    # We have an in-core transform already for this (faster)
                    image_pil = convert_profile_pil_transform(image_pil,
                                                              icc_transform_dict[tr_key],
                                                              inPlace=True)
                else:
                    # Convert using profiles on disk (slower)
                    if in_profile in profile_dict:
                        in_profile = profile_dict[in_profile].path
                        image_pil = convert_profile_pil(image_pil, in_profile,
                                                        profile_dict[out_profile].path,
                                                        intent)

                # convert PIL image to numpy format
                image_rgb = from_image(image_pil)

            # reattach alpha channel if there was one
            if alpha is not None:
                image_rgb = trcalc.add_alpha(image_rgb, alpha=alpha)
            image_np = image_rgb

            self.logger.info("converted from profile (%s) to profile (%s)" % (
                in_profile, profile_dict[out_profile].name))

        except Exception as e:
            self.logger.error("Error converting from embedded color profile: {!r}".format(e),
                              exc_info=True)
            self.logger.warning("Leaving image unprofiled.")

        return image_np

    def profile_to_working_pil(self, image_pil, kwds, intent=None):
        image_np = from_image(image_pil)
        image_np = self.profile_to_working_numpy(image_np, kwds, intent=intent)
        return to_image(image_np)

# --- Color Management conversion functions ---


def to_image(image_np, flip_y=True):
    if flip_y:
        image_np = np.flipud(image_np)
    return Image.fromarray(image_np)


def from_image(image_pil, flip_y=True):
    image_np = np.array(image_pil)
    if flip_y:
        image_np = np.flipud(image_np)
    return image_np


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
    if not have_cms:
        return image_np

    in_image_pil = to_image(image_np)
    out_image_pil = convert_profile_pil(in_image_pil,
                                        inprof_path, outprof_path, intent_name)
    image_out = from_image(out_image_pil)
    return image_out


def convert_profile_numpy_transform(image_np, transform):
    if not have_cms:
        return image_np

    in_image_pil = to_image(image_np)
    convert_profile_pil_transform(in_image_pil, transform, inPlace=True)
    image_out = from_image(in_image_pil)
    return image_out


def get_transform_key(from_name, to_name, to_intent, proof_name,
                      proof_intent, flags):
    return (from_name, to_name, to_intent, proof_name, proof_intent, flags)


def get_transform(from_name, to_name, to_intent='perceptual',
                  proof_name=None, proof_intent=None,
                  use_black_pt=False):
    global icc_transform_dict

    if not have_cms:
        return ColorManagerError("Either pillow is not installed, or there is "
                                 "no ICC support in this version of pillow")

    flags = 0
    if proof_name is not None:
        if hasattr(ImageCms, 'FLAGS'):
            # supporting multiple versions of lcms...sigh..
            flags |= ImageCms.FLAGS['SOFTPROOFING']
        else:
            flags |= ImageCms.SOFTPROOFING
    if use_black_pt:
        if hasattr(ImageCms, 'FLAGS'):
            flags |= ImageCms.FLAGS['BLACKPOINTCOMPENSATION']
        else:
            flags |= ImageCms.BLACKPOINTCOMPENSATION

    key = get_transform_key(from_name, to_name, to_intent, proof_name,
                            proof_intent, flags)

    try:
        output_transform = icc_transform_dict[key]

    except KeyError:
        # try to build transform on the fly
        try:
            if proof_name is not None:
                output_transform = ImageCms.buildProofTransform(
                    profile_dict[from_name].path,
                    profile_dict[to_name].path,
                    profile_dict[proof_name].path,
                    'RGB', 'RGB',
                    renderingIntent=intents[to_intent],
                    proofRenderingIntent=intents[proof_intent],
                    flags=flags)
            else:
                output_transform = ImageCms.buildTransform(
                    profile_dict[from_name].path,
                    profile_dict[to_name].path,
                    'RGB', 'RGB',
                    renderingIntent=intents[to_intent],
                    flags=flags)

            # cache it so we don't have to build it later
            icc_transform_dict[key] = output_transform

        except Exception as e:
            raise ColorManagerError("Failed to build profile transform: {!r}".format(e))

    return output_transform


def convert_profile_fromto(image_np, from_name, to_name,
                           to_intent='perceptual',
                           proof_name=None, proof_intent=None,
                           use_black_pt=False, logger=None):

    if image_np.dtype != np.uint8:
        ## image_np = trcalc.array_convert(image_np, np.dtype(np.uint8))
        if logger is not None:
            logger.info(
                "Cannot profile >8 bpp images; leaving image unprofiled.")
        return image_np

    alpha = None
    ht, wd, dp = image_np.shape
    if dp > 3:
        # color profile conversion does not handle an alpha layer
        image_np, alpha = trcalc.remove_alpha(image_np)

    try:
        output_transform = get_transform(from_name, to_name,
                                         to_intent=to_intent,
                                         proof_name=proof_name,
                                         proof_intent=proof_intent,
                                         use_black_pt=use_black_pt)

        out_np = convert_profile_numpy_transform(image_np, output_transform)

        if alpha is not None:
            # reattach alpha layer if there was one
            out_np = trcalc.add_alpha(out_np, alpha)

        return out_np

    except Exception as e:
        if logger is not None:
            logger.warning("Error converting profile from '{}' to '{}': {!r}".format(
                from_name, to_name, e))
            logger.warning("Leaving image unprofiled")
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
    profile_dict[profname] = Bunch.Bunch(name=profname,
                                         path=os.path.abspath(path))

if have_pil_lcms:
    if PIL_LT_9_1:
        d = dict(absolute_colorimetric=ImageCms.INTENT_ABSOLUTE_COLORIMETRIC,
                 perceptual=ImageCms.INTENT_PERCEPTUAL,
                 relative_colorimetric=ImageCms.INTENT_RELATIVE_COLORIMETRIC,
                 saturation=ImageCms.INTENT_SATURATION)
    else:
        d = dict(absolute_colorimetric=ImageCms.Intent.ABSOLUTE_COLORIMETRIC,
                 perceptual=ImageCms.Intent.PERCEPTUAL,
                 relative_colorimetric=ImageCms.Intent.RELATIVE_COLORIMETRIC,
                 saturation=ImageCms.Intent.SATURATION)
    intents.update(d)

    # Build transforms for profile conversions for which we have profiles


def have_profile(name):
    return name in profile_dict.keys()


def get_profiles():
    names = list(profile_dict.keys())
    names.sort()
    return names


def get_intents():
    names = list(intents.keys())
    names.sort()
    return names


def set_profile_alias(alias, profname):
    global profile_dict
    profile_dict[alias] = profile_dict[profname]
