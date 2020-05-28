# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy as np

from ginga.gw import Widgets
from ginga.util import rgb_cms
from ginga import trcalc

from .base import Stage

icc_profiles = list(rgb_cms.get_profiles())
icc_profiles.insert(0, None)
icc_intents = list(rgb_cms.get_intents())


class ICCProf(Stage):
    """Convert the given RGB data from the input ICC profile
    to the output ICC profile.
    """
    _stagename = 'icc-profile'

    def __init__(self):
        super(ICCProf, self).__init__()

        self.icc_input_profile = None
        self.icc_output_profile = None
        self.icc_output_intent = 'perceptual'
        self.icc_proof_profile = None
        self.icc_proof_intent = 'perceptual'
        self.icc_black_point_compensation = False

    def build_gui(self, container):

        captions = (('Input ICC profile:', 'label', 'Input ICC profile',
                     'combobox'),
                    ('Output ICC profile:', 'label', 'Output ICC profile',
                     'combobox'),
                    ('Rendering intent:', 'label', 'Rendering intent',
                     'combobox'),
                    ('Proof ICC profile:', 'label', 'Proof ICC profile',
                     'combobox'),
                    ('Proof intent:', 'label', 'Proof intent', 'combobox'),
                    ('__x', 'spacer', 'Black point compensation', 'checkbutton'),
                    )
        w, b = Widgets.build_info(captions, orientation='vertical')
        self.w.update(b)

        value = self.icc_input_profile
        combobox = b.input_icc_profile
        index = 0
        for name in icc_profiles:
            combobox.append_text(str(name))
            index += 1
        try:
            index = icc_profiles.index(value)
            combobox.set_index(index)
        except Exception:
            pass
        combobox.add_callback('activated', self.set_icc_profile_cb)
        combobox.set_tooltip("ICC profile for the input data")

        value = self.icc_output_profile
        combobox = b.output_icc_profile
        index = 0
        for name in icc_profiles:
            combobox.append_text(str(name))
            index += 1
        try:
            index = icc_profiles.index(value)
            combobox.set_index(index)
        except Exception:
            pass
        combobox.add_callback('activated', self.set_icc_profile_cb)
        combobox.set_tooltip("ICC profile for the viewer display")

        value = self.icc_output_intent
        combobox = b.rendering_intent
        index = 0
        for name in icc_intents:
            combobox.append_text(name)
            index += 1
        try:
            index = icc_intents.index(value)
            combobox.set_index(index)
        except Exception:
            pass
        combobox.add_callback('activated', self.set_icc_profile_cb)
        combobox.set_tooltip("Rendering intent for the viewer display")

        value = self.icc_proof_profile
        combobox = b.proof_icc_profile
        index = 0
        for name in icc_profiles:
            combobox.append_text(str(name))
            index += 1
        try:
            index = icc_profiles.index(value)
            combobox.set_index(index)
        except Exception:
            pass
        combobox.add_callback('activated', self.set_icc_profile_cb)
        combobox.set_tooltip("ICC profile for soft proofing")

        value = self.icc_proof_intent
        combobox = b.proof_intent
        index = 0
        for name in icc_intents:
            combobox.append_text(name)
            index += 1
        try:
            index = icc_intents.index(value)
            combobox.set_index(index)
        except Exception:
            pass
        combobox.add_callback('activated', self.set_icc_profile_cb)
        combobox.set_tooltip("Rendering intent for soft proofing")

        value = self.icc_black_point_compensation
        b.black_point_compensation.set_state(value)
        b.black_point_compensation.add_callback(
            'activated', self.set_icc_profile_cb)
        b.black_point_compensation.set_tooltip("Use black point compensation")

        fr = Widgets.Frame()
        fr.set_widget(w)

        container.set_widget(fr)

    def set_icc_profile_cb(self, setting, idx):
        idx = self.w.input_icc_profile.get_index()
        input_profile_name = icc_profiles[idx]
        idx = self.w.output_icc_profile.get_index()
        output_profile_name = icc_profiles[idx]
        idx = self.w.rendering_intent.get_index()
        intent_name = icc_intents[idx]

        idx = self.w.proof_icc_profile.get_index()
        proof_profile_name = icc_profiles[idx]
        idx = self.w.proof_intent.get_index()
        proof_intent = icc_intents[idx]

        bpc = self.w.black_point_compensation.get_state()

        self.icc_input_profile = input_profile_name
        self.icc_output_profile = output_profile_name
        self.icc_output_intent = intent_name
        self.icc_proof_profile = proof_profile_name
        self.icc_proof_intent = proof_intent
        self.icc_black_point_compensation = bpc

        self.pipeline.run_from(self)

    def run(self, prev_stage):
        data = self.pipeline.get_data(prev_stage)
        self.verify_2d(data)

        if (self._bypass or data is None or None in [self.icc_input_profile,
                                                     self.icc_output_profile]):
            self.pipeline.set(icc_output_profile=self.icc_input_profile)
            self.pipeline.send(res_np=data)
            return

        # color profiling will not work with other types
        data = data.astype(np.uint8)

        alpha = None
        ht, wd, dp = data.shape
        if dp > 3:
            # color profile conversion does not handle an alpha layer
            alpha = data[:, :, 3]
            data = data[:, :, 0:3]

        try:
            arr = rgb_cms.convert_profile_fromto(data,
                                                 self.icc_input_profile,
                                                 self.icc_output_profile,
                                                 to_intent=self.icc_output_intent,
                                                 proof_name=self.icc_proof_profile,
                                                 proof_intent=self.icc_proof_intent,
                                                 use_black_pt=self.icc_black_point_compensation,
                                                 logger=self.logger)

            self.logger.debug("Converted from '%s' to '%s' profile" % (
                self.icc_input_profile, self.icc_output_profile))

        except Exception as e:
            self.logger.warning("Error converting output from working profile: %s" % (str(e)))
            # TODO: maybe should have a traceback here
            self.logger.info("Output left unprofiled")
            arr = data

        if alpha is not None:
            arr = trcalc.add_alpha(arr, alpha)

        self.pipeline.set(icc_output_profile=self.icc_output_profile)
        self.pipeline.send(res_np=arr)
