#
# Bindings.py -- Bindings classes for Ginga viewer.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import os.path
import itertools

from ginga.misc import Bunch, Settings, Callback
from ginga.util.paths import icondir


class ImageViewBindings(object):
    """Configurable event handling (bindings) for UI events.

    This module handles the mapping of user interface events (keyboard,
    mouse, trackpad, gestures) to operations on a Ginga viewer.
    """

    action_prefixes = ['kp_', 'ms_', 'sc_', 'pi_', 'pa_']

    def __init__(self, logger, settings=None):
        super(ImageViewBindings, self).__init__()

        self.logger = logger

        if settings is None:
            # No settings passed.  Set up defaults.
            settings = Settings.SettingGroup(name='bindings',
                                             logger=self.logger)
            #self.initialize_settings(settings)
        self.settings = settings

        self.features = dict(pan=False, zoom=False, cut=False, cmap=False,
                             flip=False, rotate=False)
        self.cursor_map = {}
        self._modes = {}
        self._cur_mode = None

    def initialize_settings(self, settings):
        settings.add_settings(
            # You should rarely have to change these.
            btn_nobtn=0x0,
            btn_left=0x1,
            btn_middle=0x2,
            btn_right=0x4,
            btn_back=0x8,
            btn_forward=0x10,

            # Set up our standard modifiers
            mod_shift=['shift_l', 'shift_r'],
            mod_ctrl=['control_l', 'control_r'],
            mod_win=['meta_right'],

            default_mode_type='locked',
            default_lock_mode_type='locked',

            # MOUSE/BUTTON
            ms_none=['nobtn'],
            ms_cursor=['left'],
            ms_wheel=[],
        )

    def get_settings(self):
        return self.settings

    def add_mode_obj(self, mode_obj):
        #self.settings.add_defaults(**mode_obj.actions)
        self._modes[str(mode_obj)] = mode_obj

    def get_mode_obj(self, mode_name):
        return self._modes[mode_name]

    def window_map(self, viewer):
        #self.to_default_mode(viewer)
        pass

    def set_bindings(self, viewer):
        viewer.add_callback('map', self.window_map)

        bindmap = viewer.get_bindmap()
        bindmap.clear_button_map()
        bindmap.clear_event_map()

        bindmap.add_callback('mode-set', self.mode_set_cb, viewer)

        # Set up bindings
        self.setup_settings_events(viewer, bindmap)

    def set_mode(self, viewer, name, mode_type='oneshot'):
        bindmap = viewer.get_bindmap()
        bindmap.set_mode(name, mode_type=mode_type)

    def mode_set_cb(self, bm, mode, mode_type, viewer):
        self.logger.debug(f'mode change to {mode}')

        if mode != self._cur_mode:
            if self._cur_mode not in ('meta', None):
                try:
                    self._modes[self._cur_mode].stop()
                except Exception as e:
                    self.logger.error("Error stopping mode '{}': {}".format(self._cur_mode, e),
                                      exc_info=True)

            self._cur_mode = mode
            if self._cur_mode not in ('meta', None):
                try:
                    self._modes[self._cur_mode].start()
                except Exception as e:
                    self.logger.error("Error starting mode '{}': {}".format(self._cur_mode, e),
                                      exc_info=True)

    def parse_combo(self, combo, modes_set, modifiers_set, pfx):
        """
        Parse a string into a mode, a set of modifiers and a trigger.
        """
        mode, mods, trigger = None, set([]), combo
        if '+' in combo:
            if combo.endswith('+'):
                # special case: probably contains the keystroke '+'
                trigger, combo = '+', combo[:-1]
                if '+' in combo:
                    items = set(combo.split('+'))
                else:
                    items = set(combo)
            else:
                # trigger is always specified last
                items = combo.split('+')
                trigger, items = items[-1], set(items[:-1])

            if '*' in items:
                items.remove('*')
                # modifier wildcard
                mods = '*'
            else:
                mods = items.intersection(modifiers_set)

            mode = items.intersection(modes_set)
            if len(mode) == 0:
                mode = None
            else:
                mode = mode.pop()

        if pfx is not None:
            trigger = pfx + trigger

        return (mode, mods, trigger)

    def setup_settings_events(self, viewer, bindmap):

        self.initialize_settings(self.settings)

        # merge in all default settings from various modes, being
        # careful not to override any user preferences
        act_d = dict()
        from ginga.modes.modeinfo import available_modes
        for mode_class in available_modes:
            mode_obj = mode_class(viewer, settings=self.settings)
            for name, value in mode_obj.actions.items():
                pfx = name[:3]
                if pfx not in self.action_prefixes:
                    act_d.setdefault(name, value)
                    continue
                # a binding
                act_l = act_d.setdefault(name, [])
                for trigger in value:
                    if trigger not in act_l:
                        act_l.append(trigger)
            self.add_mode_obj(mode_obj)

        self.settings.add_defaults(**act_d)

        # Now settings should have all available modes defined
        d = self.settings.get_dict()

        # First scan settings for buttons and modes
        bindmap.clear_button_map()
        bindmap.clear_modifier_map()
        bindmap.clear_mode_map()
        bindmap.clear_event_map()

        mode_type = self.settings.get('default_mode_type', 'oneshot')
        bindmap.set_default_mode_type(mode_type)

        for name, value in d.items():
            if name.startswith('mod_'):
                modname = name[4:]
                for combo in value:
                    # NOTE: for now no chorded combinations to make modifiers
                    keyname = combo
                    bindmap.add_modifier(keyname, modname)

            elif name.startswith('cur_'):
                curname = name[4:]
                self.add_cursor(viewer, curname, value)

            elif name.startswith('btn_'):
                btnname = name[4:]
                bindmap.map_button(value, btnname)

            elif name.startswith('dmod_'):
                mode_name = name[5:]
                keyname, mode_type, curname = value
                bindmap.add_mode(keyname, mode_name, mode_type=mode_type,
                                 msg=None)
                if curname is not None:
                    self.cursor_map[mode_name] = curname

        self.merge_actions(viewer, bindmap, self, d.items())

        # merge in specific actions for each mode
        for mode_obj in self._modes.values():
            actions = mode_obj.actions
            d = {key: self.settings[key]
                 for key in actions.keys() if key in self.settings}
            self.merge_actions(viewer, bindmap, mode_obj, d.items())

    def merge_actions(self, viewer, bindmap, obj, tups):

        modes_set = bindmap.get_modes()
        modifiers_set = bindmap.get_modifiers()

        # Add events
        for name, value in tups:
            if len(name) <= 3:
                continue

            pfx = name[:3]
            if pfx not in self.action_prefixes:
                continue

            evname = name[3:]
            for combo in value:
                mode, modifiers, trigger = self.parse_combo(combo, modes_set,
                                                            modifiers_set, pfx)
                if modifiers == '*':
                    # wildcard; register for all modifier combinations
                    modifiers_poss = set([])
                    for i in range(len(modifiers_set) + 1):
                        modifiers_poss = modifiers_poss.union(
                            itertools.combinations(modifiers_set, i))
                    for modifiers in modifiers_poss:
                        bindmap.map_event(mode, modifiers, trigger, evname)
                else:
                    bindmap.map_event(mode, modifiers, trigger, evname)

            # Register for this symbolic event if we have a handler for it
            try:
                cb_method = getattr(obj, name)

            except AttributeError:
                # Do we need a warning here?
                #self.logger.warning("No method found matching '%s'" % (name))
                cb_method = None

            if pfx == 'kp_':
                # keyboard event
                event = 'keydown-%s' % (evname)
                viewer.enable_callback(event)
                if cb_method is not None and viewer.num_callbacks(event) == 0:
                    viewer.add_callback(event, cb_method)

            elif pfx == 'ms_':
                # mouse/button event
                for action in ('down', 'move', 'up'):
                    event = '%s-%s' % (evname, action)
                    viewer.enable_callback(event)
                    if cb_method is not None and viewer.num_callbacks(event) == 0:
                        viewer.add_callback(event, cb_method)

            elif pfx == 'sc_':
                # scrolling event
                event = '%s-scroll' % evname
                viewer.enable_callback(event)
                if cb_method is not None and viewer.num_callbacks(event) == 0:
                    viewer.add_callback(event, cb_method)

            elif pfx == 'pi_':
                # pinch event
                event = '%s-pinch' % evname
                viewer.enable_callback(event)
                if cb_method is not None and viewer.num_callbacks(event) == 0:
                    viewer.add_callback(event, cb_method)

            elif pfx == 'pa_':
                # pan event
                event = '%s-pan' % evname
                viewer.enable_callback(event)
                if cb_method is not None and viewer.num_callbacks(event) == 0:
                    viewer.add_callback(event, cb_method)

    def reset(self, viewer):
        bindmap = viewer.get_bindmap()
        bindmap.reset_mode(viewer)
        viewer.onscreen_message(None)

    def add_cursor(self, viewer, curname, curpath):
        if not curpath.startswith('/'):
            curpath = os.path.join(icondir, curpath)
        cursor = viewer.make_cursor(curpath, 8, 8)
        viewer.define_cursor(curname, cursor)

    #####  ENABLERS #####
    # These methods are a quick way to enable or disable certain user
    # interface features in a ImageView window

    def enable_pan(self, tf):
        """Enable the image to be panned interactively (True/False)."""
        self.enable(pan=tf)

    def enable_zoom(self, tf):
        """Enable the image to be zoomed interactively (True/False)."""
        self.enable(zoom=tf)

    def enable_cuts(self, tf):
        """Enable the cuts levels to be set interactively (True/False)."""
        self.enable(cut=tf)

    def enable_cmap(self, tf):
        """Enable the color map to be warped interactively (True/False)."""
        self.enable(cmap=tf)

    def enable_flip(self, tf):
        """Enable the image to be flipped interactively (True/False)."""
        self.enable(flip=tf)

    def enable_rotate(self, tf):
        """Enable the image to be rotated interactively (True/False)."""
        self.enable(rotate=tf)

    def enable(self, **kwargs):
        """General enable function encompassing all user interface features.
        Usage (e.g.): viewer.enable(rotate=False, flip=True)
        """
        for feat, value in kwargs.items():
            feat = feat.lower()
            if feat not in self.features:
                raise ValueError("'%s' is not a feature. Must be one of %s" % (
                    feat, str(list(self.features.keys()))))

            self.features[feat] = bool(value)

    def enable_all(self, tf):
        for feat in list(self.features.keys()):
            self.features[feat] = tf

    def get_feature_allow(self, feat_name):
        return self.features[feat_name]

    def get_direction(self, direction, rev=False):
        """Translate a direction in compass degrees into 'up' or 'down'."""
        # TODO: merge with the one in mode_base
        if (direction < 90.0) or (direction >= 270.0):
            if not rev:
                return 'up'
            else:
                return 'down'
        elif (90.0 <= direction < 270.0):
            if not rev:
                return 'down'
            else:
                return 'up'
        else:
            return 'none'


class UIEvent:
    """Base class for user interface events."""
    def __init__(self, viewer=None):
        self.viewer = viewer
        self.handled = False

    def accept(self):
        self.handled = True

    def was_handled(self):
        return self.handled


class KeyEvent(UIEvent):
    """A key press or release event in a Ginga viewer.

    Attributes
    ----------
    key : str
        The key as it is known to Ginga

    state: str
        'down' if a key press, 'up' if a key release

    mode : str
        The mode name of the mode that was active when the event happened

    modifiers : set of str
        A set of names of modifier keys that were pressed at the time

    data_x : float
        X part of the data coordinates of the viewer under the cursor

    data_y : float
        Y part of the data coordinates of the viewer under the cursor

    viewer : subclass of `~ginga.ImageView.ImageViewBase`
        The viewer in which the event happened
    """
    def __init__(self, key=None, state=None, mode=None, modifiers=None,
                 data_x=None, data_y=None, viewer=None):
        super().__init__(viewer=viewer)
        self.key = key
        self.state = state
        self.mode = mode
        self.modifiers = modifiers
        self.data_x = data_x
        self.data_y = data_y


class PointEvent(UIEvent):
    """A mouse/pointer/cursor event in a Ginga viewer.

    Attributes
    ----------
    button : str
        The name of the button as set up in the configuration

    state: str
        'down' if a press, 'move' if being dragged, 'up' if a release

    mode : str
        The mode name of the mode that was active when the event happened

    modifiers : set of str
        A set of names of modifier keys that were pressed at the time

    data_x : float
        X part of the data coordinates of the viewer under the cursor

    data_y : float
        Y part of the data coordinates of the viewer under the cursor

    viewer : subclass of `~ginga.ImageView.ImageViewBase`
        The viewer in which the event happened
    """
    def __init__(self, button=None, state=None, mode=None, modifiers=None,
                 data_x=None, data_y=None, viewer=None):
        super().__init__(viewer=viewer)
        self.button = button
        self.state = state
        self.mode = mode
        self.modifiers = modifiers
        self.data_x = data_x
        self.data_y = data_y


class ScrollEvent(UIEvent):
    """A mouse or trackpad scroll event in a Ginga viewer.

    Attributes
    ----------
    button : str
        The name of the button as set up in the configuration

    state: str
        Always 'scroll'

    mode : str
        The mode name of the mode that was active when the event happened

    modifiers : set of str
        A set of names of modifier keys that were pressed at the time

    direction : float
        A direction in compass degrees of the scroll

    amount : float
        The amount of the scroll

    data_x : float
        X part of the data coordinates of the viewer under the cursor

    data_y : float
        Y part of the data coordinates of the viewer under the cursor

    viewer : subclass of `~ginga.ImageView.ImageViewBase`
        The viewer in which the event happened
    """
    def __init__(self, button=None, state=None, mode=None, modifiers=None,
                 direction=None, amount=None, data_x=None, data_y=None,
                 viewer=None):
        super().__init__(viewer=viewer)
        self.button = button
        self.state = state
        self.mode = mode
        self.modifiers = modifiers
        self.direction = direction
        self.amount = amount
        self.data_x = data_x
        self.data_y = data_y


class PinchEvent(UIEvent):
    """A pinch event in a Ginga viewer.

    Attributes
    ----------
    button : str
        The name of the button as set up in the configuration

    state: str
        'start' (gesture starting), 'move' (in action) or 'stop' (done)

    mode : str
        The mode name of the mode that was active when the event happened

    modifiers : set of str
        A set of names of modifier keys that were pressed at the time

    rot_deg : float
        Amount of rotation in degrees

    scale : float
        Scale of the pinch shrink or enlargement

    data_x : float
        X part of the data coordinates of the viewer under the cursor

    data_y : float
        Y part of the data coordinates of the viewer under the cursor

    viewer : subclass of `~ginga.ImageView.ImageViewBase`
        The viewer in which the event happened
    """
    def __init__(self, button=None, state=None, mode=None, modifiers=None,
                 rot_deg=None, scale=None, data_x=None, data_y=None,
                 viewer=None):
        super().__init__(viewer=viewer)
        self.button = button
        self.state = state
        self.mode = mode
        self.modifiers = modifiers
        self.rot_deg = rot_deg
        self.scale = scale
        self.data_x = data_x
        self.data_y = data_y


class PanEvent(UIEvent):
    """A pinch event in a Ginga viewer.

    Attributes
    ----------
    button : str
        The name of the button as set up in the configuration

    state: str
        'start' (gesture starting), 'move' (in action) or 'stop' (done)

    mode : str
        The mode name of the mode that was active when the event happened

    modifiers : set of str
        A set of names of modifier keys that were pressed at the time

    delta_x : float
        Amount of scroll movement in the X direction

    delta_y : float
        Amount of scroll movement in the Y direction

    data_x : float
        X part of the data coordinates of the viewer under the cursor

    data_y : float
        Y part of the data coordinates of the viewer under the cursor

    viewer : subclass of `~ginga.ImageView.ImageViewBase`
        The viewer in which the event happened
    """
    def __init__(self, button=None, state=None, mode=None, modifiers=None,
                 delta_x=None, delta_y=None, data_x=None, data_y=None,
                 viewer=None):
        super().__init__(viewer=viewer)
        self.button = button
        self.state = state
        self.mode = mode
        self.modifiers = modifiers
        self.delta_x = delta_x
        self.delta_y = delta_y
        self.data_x = data_x
        self.data_y = data_y


class BindingMapError(Exception):
    pass


class BindingMapper(Callback.Callbacks):
    """Map physical events to logical events.

    The BindingMapper class maps physical events (key presses, button
    clicks, mouse movement, etc) into logical events.  By registering for
    logical events, plugins and other event handling code doesn't need to
    care about the physical controls bindings.  The bindings can be changed
    and everything continues to work.
    """

    def __init__(self, logger, btnmap=None, mode_map=None, modifier_map=None):
        Callback.Callbacks.__init__(self)

        self.logger = logger

        # For event mapping
        self.event_names = ['keydown', 'keyup',
                            'btn-down', 'btn-move', 'btn-up',
                            'scroll', 'pinch', 'pan']
        self.eventmap = {}

        self._kbdmode = None
        self._kbdmode_types = ('held', 'oneshot', 'locked')
        self._kbdmode_type = 'held'
        self._kbdmode_type_default = 'locked'
        self._delayed_reset = False
        self._modifiers = frozenset([])

        # Set up button mapping
        if btnmap is None:
            btnmap = {0x1: 'cursor', 0x2: 'wheel', 0x4: 'draw'}
        self.btnmap = btnmap
        self._button = 0

        # Set up modifier mapping
        if modifier_map is None:
            self.modifier_map = {}
            for keyname in ('shift_l', 'shift_r'):
                self.add_modifier(keyname, 'shift')
            for keyname in ('control_l', 'control_r'):
                self.add_modifier(keyname, 'ctrl')
            for keyname in ('meta_right',):
                self.add_modifier(keyname, 'win')
        else:
            self.modifier_map = modifier_map

        # Set up mode mapping
        if mode_map is None:
            self.mode_map = {}
        else:
            self.mode_map = mode_map

        self._empty_set = frozenset([])
        self.mode_tbl = dict()

        # For callbacks
        for name in ('mode-set', ):
            self.enable_callback(name)

    def add_modifier(self, keyname, modname):
        bnch = Bunch.Bunch(name=modname)
        self.modifier_map[keyname] = bnch
        self.modifier_map['mod_%s' % modname] = bnch

    def get_modifiers(self):
        return set([bnch.name for keyname, bnch
                    in self.modifier_map.items()])

    def clear_modifier_map(self):
        self.modifier_map = {}

    def set_mode_map(self, mode_map):
        self.mode_map = mode_map

    def clear_mode_map(self):
        self.mode_map = {}

    def has_mode(self, mode_name):
        key = 'mode_%s' % mode_name
        return key in self.mode_map

    def remove_mode(self, mode_name):
        key = 'mode_%s' % mode_name
        del self.mode_map[key]

    def current_mode(self):
        return (self._kbdmode, self._kbdmode_type)

    def get_modes(self):
        return set([bnch.name for keyname, bnch in self.mode_map.items()])

    def add_mode(self, keyname, mode_name, mode_type='held', msg=None):
        if mode_type is not None:
            if mode_type not in self._kbdmode_types:
                raise ValueError("Bad mode type '%s': must be one of %s" % (
                    mode_type, self._kbdmode_types))

        bnch = Bunch.Bunch(name=mode_name, type=mode_type, msg=msg)
        if keyname is not None:
            # Key to launch this mode
            if keyname[0:2] == '__':
                keyname = keyname[2]
                self.mode_tbl[keyname] = bnch
            else:
                self.mode_map[keyname] = bnch
        self.mode_map['mode_%s' % mode_name] = bnch

    def set_mode(self, name, mode_type=None):
        if mode_type is None:
            mode_type = self._kbdmode_type_default
        if mode_type not in self._kbdmode_types:
            raise ValueError("Bad mode type '%s': must be one of %s" % (
                mode_type, self._kbdmode_types))
        self._kbdmode = name
        if name is None:
            # like a reset_mode()
            mode_type = 'held'
            self._delayed_reset = False
        self._kbdmode_type = mode_type
        self.logger.info("set keyboard mode to '%s' type=%s" % (name, mode_type))
        self.make_callback('mode-set', self._kbdmode, self._kbdmode_type)

    def set_default_mode_type(self, mode_type):
        if mode_type not in self._kbdmode_types:
            raise ValueError("Bad mode type '%s': must be one of %s" % (
                mode_type, self._kbdmode_types))
        self._kbdmode_type_default = mode_type

    def get_default_mode_type(self):
        return self._kbdmode_type_default

    def reset_mode(self, viewer):
        try:
            bnch = self.mode_map['mode_%s' % self._kbdmode]
        except Exception:
            bnch = None
        self._kbdmode = None
        self._kbdmode_type = 'held'
        self._delayed_reset = False
        self.logger.debug("set keyboard mode reset")
        # clear onscreen message, if any
        if (bnch is not None) and (bnch.msg is not None):
            viewer.onscreen_message(None)
        self.make_callback('mode-set', self._kbdmode, self._kbdmode_type)

    def clear_button_map(self):
        self.btnmap = {}

    def map_button(self, btncode, alias):
        """For remapping the buttons to different names. 'btncode' is a
        fixed button code and 'alias' is a logical name.
        """
        self.btnmap[btncode] = alias

    def get_buttons(self):
        return set([alias for keyname, alias in self.btnmap.items()])

    def get_button(self, btncode):
        return self.btnmap.get(btncode, None)

    def clear_event_map(self):
        self.eventmap = {}

    def map_event(self, mode, modifiers, trigger, eventname):
        self.eventmap[(mode, frozenset(tuple(modifiers)),
                       trigger)] = Bunch.Bunch(name=eventname)

    def register_for_events(self, viewer):
        # Add callbacks for interesting events
        viewer.add_callback('motion', self.window_motion)
        viewer.add_callback('button-press', self.window_button_press)
        viewer.add_callback('button-release', self.window_button_release)
        viewer.add_callback('key-press', self.window_key_press)
        viewer.add_callback('key-release', self.window_key_release)
        ## viewer.add_callback('drag-drop', self.window_drag_drop)
        viewer.add_callback('scroll', self.window_scroll)
        viewer.add_callback('map', self.window_map)
        viewer.add_callback('focus', self.window_focus)
        viewer.add_callback('enter', self.window_enter)
        viewer.add_callback('leave', self.window_leave)
        if viewer.has_callback('pinch'):
            viewer.add_callback('pinch', self.window_pinch)
        if viewer.has_callback('pan'):
            viewer.add_callback('pan', self.window_pan)

        for pfx in self.event_names:
            # TODO: add moded versions of callbacks?
            viewer.enable_callback('%s-none' % (pfx))

    def mode_key_down(self, viewer, keyname):
        """This method is called when a key is pressed and was not handled
        by some other handler with precedence, such as a subcanvas.
        """
        # Is this a mode key?
        if keyname not in self.mode_map:
            if (self._kbdmode != 'meta') or (keyname not in self.mode_tbl):
                # No
                return False
            bnch = self.mode_tbl[keyname]
        else:
            bnch = self.mode_map[keyname]

        mode_name = bnch.name
        self.logger.debug("cur mode='%s' mode pressed='%s'" % (
            self._kbdmode, mode_name))

        if self._delayed_reset:
            # <== this shouldn't happen, but put here to reset handling
            # of delayed_reset just in case (see cursor up handling)
            self._delayed_reset = False
            return True

        if ((self._kbdmode in (None, 'meta')) or
            (self._kbdmode_type != 'locked') or (mode_name == 'meta')):
            if self._kbdmode is not None:
                self.reset_mode(viewer)

            # activate this mode
            if self._kbdmode in (None, 'meta'):
                mode_type = bnch.type
                if mode_type is None:
                    mode_type = self._kbdmode_type_default
                self.set_mode(mode_name, mode_type)
                if bnch.msg is not None:
                    viewer.onscreen_message(bnch.msg)

                return True

        return False

    def mode_key_up(self, viewer, keyname):
        """This method is called when a key is pressed in a mode and was
        not handled by some other handler with precedence, such as a
        subcanvas.
        """
        # Is this a mode key?
        if keyname not in self.mode_map:
            # <== no
            return False

        bnch = self.mode_map[keyname]
        if self._kbdmode == bnch.name:
            # <-- the current mode key is being released
            if bnch.type == 'held':
                if self._button == 0:
                    # if no button is being held, then reset mode
                    self.reset_mode(viewer)
                else:
                    self._delayed_reset = True
            return True

        return False

    def window_map(self, viewer):
        return True

    def window_focus(self, viewer, has_focus):
        if not has_focus:
            # fixes a problem with not receiving key release events when the
            # window loses focus
            self._modifiers = frozenset([])
        return False

    def window_enter(self, viewer):
        return False

    def window_leave(self, viewer):
        return False

    def window_key_press(self, viewer, keyname):
        self.logger.debug("keyname=%s" % (keyname))
        # Is this a modifer key?
        if keyname in self.modifier_map:
            bnch = self.modifier_map[keyname]
            self._modifiers = self._modifiers.union(set([bnch.name]))
            return True

        if self.mode_key_down(viewer, keyname):
            return True

        trigger = 'kp_' + keyname
        last_x, last_y = viewer.get_last_data_xy()

        event = KeyEvent(key=keyname, state='down', mode=self._kbdmode,
                         modifiers=self._modifiers, viewer=viewer,
                         data_x=last_x, data_y=last_y)

        if self._kbdmode is None:
            cbname = 'key-down-none'

        else:
            if keyname == 'escape':
                idx = (None, self._empty_set, trigger)
            else:
                idx = (self._kbdmode, self._modifiers, trigger)

            if idx in self.eventmap:
                emap = self.eventmap[idx]
                cbname = 'keydown-%s' % (emap.name)
            else:
                # TEMP: hack to get around the issue of how keynames
                # are generated--shifted characters with no modifiers
                idx = (self._kbdmode, self._empty_set, trigger)
                if idx in self.eventmap:
                    emap = self.eventmap[idx]
                    cbname = 'keydown-%s' % (emap.name)
                else:
                    cbname = 'key-down-%s' % str(self._kbdmode).lower()

        res = viewer.make_ui_callback_viewer(viewer, cbname, event,
                                             last_x, last_y)

        if not event.was_handled() and not res:
            # no response for this canvas or mode, try non-mode entry
            idx = (None, self._modifiers, trigger)
            if idx in self.eventmap:
                emap = self.eventmap[idx]
                cbname = 'keydown-%s' % (emap.name)
                viewer.make_ui_callback_viewer(viewer, cbname, event,
                                               last_x, last_y)
            else:
                # TEMP: hack to get around the issue of how keynames
                # are generated--shifted characters with no modifiers
                idx = (None, self._empty_set, trigger)
                if idx in self.eventmap:
                    emap = self.eventmap[idx]
                    cbname = 'keydown-%s' % (emap.name)
                    viewer.make_ui_callback_viewer(viewer, cbname, event,
                                                   last_x, last_y)

        return True

    def window_key_release(self, viewer, keyname):
        self.logger.debug("keyname=%s" % (keyname))

        # Is this a modifer key?
        if keyname in self.modifier_map:
            bnch = self.modifier_map[keyname]
            self._modifiers = self._modifiers.difference(set([bnch.name]))
            return True

        if self.mode_key_up(viewer, keyname):
            return True

        trigger = 'kp_' + keyname
        last_x, last_y = viewer.get_last_data_xy()

        event = KeyEvent(key=keyname, state='up', mode=self._kbdmode,
                         modifiers=self._modifiers, viewer=viewer,
                         data_x=last_x, data_y=last_y)

        if self._kbdmode is None:
            cbname = 'key-up-none'

        else:
            idx = (self._kbdmode, self._modifiers, trigger)
            if idx in self.eventmap:
                emap = self.eventmap[idx]
                cbname = 'keyup-%s' % (emap.name)

            else:
                # TEMP: hack to get around the issue of how keynames
                # are generated--shifted characters with no modifiers
                idx = (self._kbdmode, self._empty_set, trigger)
                if idx in self.eventmap:
                    emap = self.eventmap[idx]
                    cbname = 'keyup-%s' % (emap.name)

                else:
                    cbname = 'key-up-%s' % str(self._kbdmode).lower()

        res = viewer.make_ui_callback_viewer(viewer, cbname, event,
                                             last_x, last_y)

        if not event.was_handled() and not res:
            # no response for this canvas or mode, try non-mode entry
            idx = (None, self._modifiers, trigger)
            if idx in self.eventmap:
                emap = self.eventmap[idx]
                cbname = 'keyup-%s' % (emap.name)
                viewer.make_ui_callback_viewer(viewer, cbname, event,
                                               last_x, last_y)
            else:
                # TEMP: hack to get around the issue of how keynames
                # are generated--shifted characters with no modifiers
                idx = (None, self._empty_set, trigger)
                if idx in self.eventmap:
                    emap = self.eventmap[idx]
                    cbname = 'keyup-%s' % (emap.name)
                    viewer.make_ui_callback_viewer(viewer, cbname, event,
                                                   last_x, last_y)
        return True

    def window_button_press(self, viewer, btncode, data_x, data_y):
        self.logger.debug("x,y=%d,%d btncode=%s" % (data_x, data_y,
                                                    hex(btncode)))
        self._button |= btncode
        button = self.get_button(btncode)
        if button is None:
            self.logger.error("unrecognized button code (%x)" % (btncode))
            return False

        trigger = 'ms_' + button
        event = PointEvent(button=button, state='down', mode=self._kbdmode,
                           modifiers=self._modifiers, viewer=viewer,
                           data_x=data_x, data_y=data_y)

        if self._kbdmode is None:
            cbname = 'btn-down-none'

        else:
            idx = (self._kbdmode, self._modifiers, trigger)
            if idx in self.eventmap:
                emap = self.eventmap[idx]
                cbname = '%s-down' % (emap.name)

            else:
                cbname = 'btn-down-%s' % str(self._kbdmode).lower()

        self.logger.debug("making callback for %s (mode=%s)" % (
            cbname, self._kbdmode))

        res = viewer.make_ui_callback_viewer(viewer, cbname, event,
                                             data_x, data_y)

        if not event.was_handled() and not res:
            # no entry for this mode, try non-mode entry
            idx = (None, self._modifiers, trigger)
            if idx in self.eventmap:
                emap = self.eventmap[idx]
                cbname = '%s-down' % (emap.name)
                viewer.make_ui_callback_viewer(viewer, cbname, event,
                                               data_x, data_y)
        return True

    def window_motion(self, viewer, btncode, data_x, data_y):

        button = self.get_button(btncode)
        if button is None:
            self.logger.error("unrecognized button code (%x)" % (btncode))
            return False

        trigger = 'ms_' + button
        event = PointEvent(button=button, state='move', mode=self._kbdmode,
                           modifiers=self._modifiers, viewer=viewer,
                           data_x=data_x, data_y=data_y)

        if self._kbdmode is None:
            cbname = 'btn-move-none'

        else:
            idx = (self._kbdmode, self._modifiers, trigger)
            if idx in self.eventmap:
                emap = self.eventmap[idx]
                cbname = '%s-move' % (emap.name)

            else:
                cbname = 'btn-move-%s' % str(self._kbdmode).lower()

        ## self.logger.debug("making callback for %s (mode=%s)" % (
        ##     cbname, self._kbdmode))
        res = viewer.make_ui_callback_viewer(viewer, cbname, event,
                                             data_x, data_y)

        if not event.was_handled() and not res:
            # no entry for this mode, try non-mode entry
            idx = (None, self._modifiers, trigger)
            if idx in self.eventmap:
                emap = self.eventmap[idx]
                cbname = '%s-move' % (emap.name)
                viewer.make_ui_callback_viewer(viewer, cbname, event,
                                               data_x, data_y)
        return True

    def window_button_release(self, viewer, btncode, data_x, data_y):
        self.logger.debug("x,y=%d,%d button=%s" % (data_x, data_y,
                                                   hex(btncode)))
        self._button &= ~btncode
        button = self.get_button(btncode)
        if button is None:
            self.logger.error("unrecognized button code (%x)" % (btncode))
            return False

        trigger = 'ms_' + button
        event = PointEvent(button=button, state='up', mode=self._kbdmode,
                           modifiers=self._modifiers, viewer=viewer,
                           data_x=data_x, data_y=data_y)

        if self._kbdmode is None:
            cbname = 'btn-up-none'

        else:
            idx = (self._kbdmode, self._modifiers, trigger)
            if idx in self.eventmap:
                # release mode if this is a oneshot mode
                if (self._kbdmode_type == 'oneshot') or (self._delayed_reset):
                    self.reset_mode(viewer)
                emap = self.eventmap[idx]
                cbname = '%s-up' % (emap.name)

            else:
                cbname = 'btn-up-%s' % str(self._kbdmode).lower()

        res = viewer.make_ui_callback_viewer(viewer, cbname, event,
                                             data_x, data_y)

        if not event.was_handled() and not res:
            # no entry for this mode, try non-mode entry
            idx = (None, self._modifiers, trigger)
            if idx in self.eventmap:
                emap = self.eventmap[idx]
                cbname = '%s-up' % (emap.name)
                viewer.make_ui_callback_viewer(viewer, cbname, event,
                                               data_x, data_y)
        return True

    def window_scroll(self, viewer, direction, amount, data_x, data_y):
        trigger = 'sc_scroll'
        event = ScrollEvent(button='scroll', state='scroll', mode=self._kbdmode,
                            modifiers=self._modifiers, viewer=viewer,
                            direction=direction, amount=amount,
                            data_x=data_x, data_y=data_y)

        if self._kbdmode is None:
            cbname = 'scroll-none'

        else:
            idx = (self._kbdmode, self._modifiers, trigger)
            if idx in self.eventmap:
                emap = self.eventmap[idx]
                cbname = '%s-scroll' % (emap.name)

            else:
                cbname = 'scroll-%s' % str(self._kbdmode).lower()

        res = viewer.make_ui_callback_viewer(viewer, cbname, event)

        if not event.was_handled() and not res:
            # no entry for this mode, try non-mode entry
            idx = (None, self._modifiers, trigger)
            if idx in self.eventmap:
                emap = self.eventmap[idx]
                cbname = '%s-scroll' % (emap.name)
                viewer.make_ui_callback_viewer(viewer, cbname, event)
        return True

    def window_pinch(self, viewer, state, rot_deg, scale):
        btncode = 0
        button = self.get_button(btncode)
        if button is None:
            self.logger.error("unrecognized button code (%x)" % (btncode))
            return False

        trigger = 'pi_pinch'
        last_x, last_y = viewer.get_last_data_xy()
        event = PinchEvent(button=button, state=state, mode=self._kbdmode,
                           modifiers=self._modifiers, viewer=viewer,
                           rot_deg=rot_deg, scale=scale,
                           data_x=last_x, data_y=last_y)

        if self._kbdmode is None:
            cbname = 'pinch-none'

        else:
            idx = (self._kbdmode, self._modifiers, trigger)
            if idx in self.eventmap:
                emap = self.eventmap[idx]
                cbname = '%s-pinch' % (emap.name)

            else:
                cbname = 'pinch-%s' % (str(self._kbdmode).lower())

        self.logger.debug("making callback for %s (mode=%s)" % (
            cbname, self._kbdmode))
        res = viewer.make_ui_callback_viewer(viewer, cbname, event)

        if not event.was_handled() and not res:
            # no entry for this mode, try non-mode entry
            idx = (None, self._modifiers, trigger)
            if idx in self.eventmap:
                emap = self.eventmap[idx]
                cbname = '%s-pinch' % (emap.name)
                viewer.make_ui_callback_viewer(viewer, cbname, event)
        return True

    def window_pan(self, viewer, state, delta_x, delta_y):
        btncode = 0
        button = self.get_button(btncode)
        if button is None:
            self.logger.error("unrecognized button code (%x)" % (btncode))
            return False

        trigger = 'pa_pan'
        last_x, last_y = viewer.get_last_data_xy()
        event = PanEvent(button=button, state=state, mode=self._kbdmode,
                         modifiers=self._modifiers, viewer=viewer,
                         delta_x=delta_x, delta_y=delta_y,
                         data_x=last_x, data_y=last_y)

        if self._kbdmode is None:
            cbname = 'pan-none'

        else:
            idx = (self._kbdmode, self._modifiers, trigger)
            if idx in self.eventmap:
                emap = self.eventmap[idx]
                cbname = '%s-pan' % (emap.name)

            else:
                cbname = 'pan-%s' % (str(self._kbdmode).lower())

        self.logger.debug("making callback for %s (mode=%s)" % (
            cbname, self._kbdmode))
        res = viewer.make_ui_callback_viewer(viewer, cbname, event)

        if not event.was_handled() and not res:
            # no entry for this mode, try non-mode entry
            idx = (None, self._modifiers, trigger)
            if idx in self.eventmap:
                emap = self.eventmap[idx]
                cbname = '%s-pan' % (emap.name)
                viewer.make_ui_callback_viewer(viewer, cbname, event)
        return True
