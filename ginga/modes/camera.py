#
# camera.py -- mode for operating OpenGL camera
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""Camera Mode enables bindings that can manipulate the camera in
a Ginga image viewer operating with a OpenGL backend.

.. note:: Camera Mode does not work unless the viewer is using an
          OpenGL backend.

Enter the mode by
-----------------
* Space, then "c"

Exit the mode by
----------------
* Esc

Default bindings in mode
------------------------
* s : save the current camera settings, to restore later
* r : reset to the saved camera settings
* 3 : change the camera view into 3D mode
* scroll : track camera (dolly in and out)
* left drag : camera orbit the view
* right drag : camera pan the view

"""
from ginga.modes.mode_base import Mode


class CameraMode(Mode):

    def __init__(self, viewer, settings=None):
        super().__init__(viewer, settings=settings)

        self.actions = dict(
            dmod_camera=['__c', None, 'pan'],

            kp_camera_save=['camera+s'],
            kp_camera_reset=['camera+r'],
            kp_camera_toggle3d=['camera+3'],

            sc_camera_track=['camera+scroll'],

            ms_camera_orbit=['camera+left'],
            ms_camera_pan_delta=['camera+right'])

    def __str__(self):
        return 'camera'

    def start(self):
        pass

    def stop(self):
        self.onscreen_message(None)

    def get_camera(self, viewer):
        renderer = viewer.renderer
        if not hasattr(renderer, 'camera'):
            return None, None
        return renderer.camera

    #####  KEYBOARD ACTION CALLBACKS #####

    def kp_camera_reset(self, viewer, event, data_x, data_y):
        event.accept()
        camera = self.get_camera(viewer)
        if camera is None:
            # this viewer doesn't have a camera
            return False

        camera.reset()
        camera.calc_gl_transform()
        self.onscreen_message("Reset camera", delay=0.5)
        viewer.update_widget()

    def kp_camera_save(self, viewer, event, data_x, data_y):
        event.accept()
        camera = self.get_camera(viewer)
        if camera is None:
            # this viewer doesn't have a camera
            return False

        camera.save_positions()
        self.onscreen_message("Saved camera position", delay=0.5)

    def kp_camera_toggle3d(self, viewer, event, data_x, data_y):
        event.accept()
        camera = self.get_camera(viewer)
        if camera is None:
            # this viewer doesn't have a camera
            return False

        renderer = viewer.renderer
        renderer.mode3d = not renderer.mode3d
        viewer.update_widget()

    #####  SCROLL ACTION CALLBACKS #####

    def sc_camera_track(self, viewer, event, msg=True):
        camera = self.get_camera(viewer)
        if camera is None:
            # this viewer doesn't have a camera
            return False
        event.accept()

        zoom_accel = self.settings.get('scroll_zoom_acceleration', 6.0)
        delta = event.amount * zoom_accel

        direction = self.get_direction(event.direction)
        if direction == 'down':
            delta = - delta

        camera.track(delta)
        camera.calc_gl_transform()

        scales = camera.get_scale_2d()
        # TODO: need to set scale in viewer settings, without triggering a
        # scale operation on this viewer
        viewer.update_widget()

    #####  MOUSE ACTION CALLBACKS #####

    def ms_camera_orbit(self, viewer, event, data_x, data_y, msg=True):
        camera = self.get_camera(viewer)
        if camera is None:
            # this viewer doesn't have a camera
            return False
        event.accept()

        x, y = self.get_win_xy(viewer)

        if event.state == 'move':
            camera.orbit(self._start_x, self._start_y, x, y)
            self._start_x, self._start_y = x, y
            camera.calc_gl_transform()
            ## pos = tuple(camera.position.get())
            ## mst = "Camera position: (%.4f, %.4f, %.4f)" % pos
            ## if msg:
            ##     self.onscreen_message(mst, delay=0.5)
            tup = camera.position.get()

        elif event.state == 'down':
            self._start_x, self._start_y = x, y

        ## else:
        ##     self.onscreen_message(None)

        viewer.update_widget()

    def ms_camera_pan_delta(self, viewer, event, data_x, data_y, msg=True):
        camera = self.get_camera(viewer)
        if camera is None:
            # this viewer doesn't have a camera
            return False
        event.accept()

        x, y = self.get_win_xy(viewer)

        if event.state == 'move':
            dx, dy = x - self._start_x, self._start_y - y
            camera.pan_delta(dx, dy)
            self._start_x, self._start_y = x, y
            camera.calc_gl_transform()

        elif event.state == 'down':
            self._start_x, self._start_y = x, y
            ## if msg:
            ##     self.onscreen_message("Camera translate", delay=1.0)

        ## else:
        ##     self.onscreen_message(None)

        # TODO: need to get the updated pan position and set it in
        # viewer's settings without triggering a callback to the viewer
        # itself
        tup = camera.position.get()
        data_x, data_y = viewer.tform['data_to_native'].from_(tup[:2])

        viewer.update_widget()
