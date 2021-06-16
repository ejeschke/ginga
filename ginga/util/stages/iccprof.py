# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy as np

from ginga.gw import Widgets
from ginga.util import rgb_cms
from ginga import trcalc

from .base import Stage, StageAction

icc_profiles = list(rgb_cms.get_profiles())
icc_profiles.insert(0, None)
icc_profiles.insert(0, 'working')
icc_intents = list(rgb_cms.get_intents())


class ICCProf(Stage):
    """Convert the given RGB data from the input ICC profile
    to the output ICC profile.
    """
    _stagename = 'icc-profile'

    def __init__(self):
        super().__init__()

        self._icc_input_profile = 'working'
        self._icc_output_profile = 'working'
        self._icc_output_intent = 'perceptual'
        self._icc_proof_profile = None
        self._icc_proof_intent = 'perceptual'
        self._icc_black_point_compensation = False

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

        value = self._icc_input_profile
        combobox = b.input_icc_profile
        for name in icc_profiles:
            combobox.append_text(str(name))
        try:
            index = icc_profiles.index(value)
            combobox.set_index(index)
        except Exception:
            pass
        combobox.add_callback('activated', self.set_icc_profile_cb)
        combobox.set_tooltip("ICC profile for the stage input")

        value = self._icc_output_profile
        combobox = b.output_icc_profile
        for name in icc_profiles:
            combobox.append_text(str(name))
        try:
            index = icc_profiles.index(value)
            combobox.set_index(index)
        except Exception:
            pass
        combobox.add_callback('activated', self.set_icc_profile_cb)
        combobox.set_tooltip("ICC profile for the stage output")

        value = self._icc_output_intent
        combobox = b.rendering_intent
        for name in icc_intents:
            combobox.append_text(name)
        try:
            index = icc_intents.index(value)
            combobox.set_index(index)
        except Exception:
            pass
        combobox.add_callback('activated', self.set_icc_profile_cb)
        combobox.set_tooltip("Rendering intent for the viewer display")

        value = self._icc_proof_profile
        combobox = b.proof_icc_profile
        for name in icc_profiles:
            combobox.append_text(str(name))
        try:
            index = icc_profiles.index(value)
            combobox.set_index(index)
        except Exception:
            pass
        combobox.add_callback('activated', self.set_icc_profile_cb)
        combobox.set_tooltip("ICC profile for soft proofing")

        value = self._icc_proof_intent
        combobox = b.proof_intent
        for name in icc_intents:
            combobox.append_text(name)
        try:
            index = icc_intents.index(value)
            combobox.set_index(index)
        except Exception:
            pass
        combobox.add_callback('activated', self.set_icc_profile_cb)
        combobox.set_tooltip("Rendering intent for soft proofing")

        value = self._icc_black_point_compensation
        b.black_point_compensation.set_state(value)
        b.black_point_compensation.add_callback(
            'activated', self.set_icc_profile_cb)
        b.black_point_compensation.set_tooltip("Use black point compensation")

        fr = Widgets.Frame()
        fr.set_widget(w)

        container.set_widget(fr)

    @property
    def icc_input_profile(self):
        return self._icc_input_profile

    @icc_input_profile.setter
    def icc_input_profile(self, val):
        self._icc_input_profile = val
        if self.gui_up:
            idx = icc_profiles.index(val)
            self.w.input_icc_profile.set_index(idx)

    @property
    def icc_output_profile(self):
        return self._icc_output_profile

    @icc_output_profile.setter
    def icc_output_profile(self, val):
        self._icc_output_profile = val
        if self.gui_up:
            idx = icc_profiles.index(val)
            self.w.output_icc_profile.set_index(idx)

    @property
    def icc_output_intent(self):
        return self._icc_output_intent

    @icc_output_intent.setter
    def icc_output_intent(self, val):
        self._icc_output_intent = val
        if self.gui_up:
            idx = icc_intents.index(val)
            self.w.rendering_intent.set_index(idx)

    @property
    def icc_proof_profile(self):
        return self._icc_proof_profile

    @icc_proof_profile.setter
    def icc_proof_profile(self, val):
        self._icc_proof_profile = val
        if self.gui_up:
            idx = icc_profiles.index(val)
            self.w.proof_icc_profile.set_index(idx)

    @property
    def icc_proof_intent(self):
        return self._icc_proof_intent

    @icc_proof_intent.setter
    def icc_proof_intent(self, val):
        self._icc_proof_intent = val
        if self.gui_up:
            idx = icc_intents.index(val)
            self.w.proof_intent.set_index(idx)

    @property
    def icc_black_point_compensation(self):
        return self._icc_black_point_compensation

    @icc_black_point_compensation.setter
    def icc_black_point_compensation(self, val):
        self._icc_black_point_compensation = val
        if self.gui_up:
            self.w.black_point_compensation.set_state(val)

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

        old = dict(icc_input_profile=self._icc_input_profile,
                   icc_output_profile=self._icc_output_profile,
                   icc_output_intent=self._icc_output_intent,
                   icc_proof_profile=self._icc_proof_profile,
                   icc_proof_intent=self._icc_proof_intent,
                   icc_black_point_compensation=self._icc_black_point_compensation)
        self._icc_input_profile = input_profile_name
        self._icc_output_profile = output_profile_name
        self._icc_output_intent = intent_name
        self._icc_proof_profile = proof_profile_name
        self._icc_proof_intent = proof_intent
        self._icc_black_point_compensation = bpc
        new = dict(icc_input_profile=self._icc_input_profile,
                   icc_output_profile=self._icc_output_profile,
                   icc_output_intent=self._icc_output_intent,
                   icc_proof_profile=self._icc_proof_profile,
                   icc_proof_intent=self._icc_proof_intent,
                   icc_black_point_compensation=self._icc_black_point_compensation)
        self.pipeline.push(StageAction(self, old, new,
                                       descr="iccprof / change"))

        self.pipeline.run_from(self)

    def run(self, prev_stage):
        data = self.pipeline.get_data(prev_stage)
        self.verify_2d(data)

        input_profile = self._icc_input_profile
        if input_profile == 'working':
            input_profile = rgb_cms.working_profile
        # TODO
        #if input_profile is None:
        #    input_profile = 'sRGB'

        output_profile = self._icc_output_profile
        if output_profile == 'working':
            output_profile = rgb_cms.working_profile

        if (self._bypass or data is None or
            None in [input_profile, output_profile] or
            input_profile == output_profile):
            self.pipeline.set(icc_output_profile=output_profile)
            self.pipeline.send(res_np=data)
            return

        # color profiling will not work with other types, currently
        data = data.astype(np.uint8)

        alpha = None
        ht, wd, dp = data.shape
        if dp > 3:
            # color profile conversion does not handle an alpha layer
            alpha = data[:, :, 3]
            data = data[:, :, 0:3]

        try:
            arr = rgb_cms.convert_profile_fromto(data,
                                                 input_profile,
                                                 output_profile,
                                                 to_intent=self._icc_output_intent,
                                                 proof_name=self._icc_proof_profile,
                                                 proof_intent=self._icc_proof_intent,
                                                 use_black_pt=self._icc_black_point_compensation,
                                                 logger=self.logger)

            self.pipeline.set(icc_output_profile=output_profile)
            self.logger.debug("Converted from '%s' to '%s' profile" % (
                input_profile, output_profile))

        except Exception as e:
            self.logger.warning("Error converting between profiles: %s" % (str(e)))
            # TODO: maybe should have a traceback here
            self.logger.info("Stage output left unprofiled")
            self.pipeline.set(icc_output_profile=input_profile)
            arr = data

        if alpha is not None:
            arr = trcalc.add_alpha(arr, alpha)

        self.pipeline.send(res_np=arr)

    def _get_state(self):
        return dict(icc_input_profile=self._icc_input_profile,
                    icc_output_profile=self._icc_output_profile,
                    icc_output_intent=self._icc_output_intent,
                    icc_proof_profile=self._icc_proof_profile,
                    icc_proof_intent=self._icc_proof_intent,
                    icc_black_point_compensation=self._icc_black_point_compensation)

    def export_as_dict(self):
        d = super().export_as_dict()
        d.update(self._get_state())
        return d

    def import_from_dict(self, d):
        super().import_from_dict(d)
        self.icc_input_profile = d['icc_input_profile']
        self.icc_output_profile = d['icc_output_profile']
        self.icc_output_intent = d['icc_output_intent']
        self.icc_proof_profile = d['icc_proof_profile']
        self.icc_proof_intent = d['icc_proof_intent']
        self.icc_black_point_compensation = d['icc_black_point_compensation']
