#
# DrawingMixin.py -- enable drawing capabilities.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import time
import math

from ginga.misc.Bunch import Bunch
from ginga.Bindings import KeyEvent
from .CanvasMixin import CanvasMixin

class DrawingMixin(object):
    """The DrawingMixin is a mixin class that adds drawing capability for
    some of the basic CanvasObject-derived types.  The set_surface method is
    used to associate a ImageViewCanvas object for layering on.
    """

    def __init__(self):
        assert isinstance(self, CanvasMixin), "Missing CanvasMixin class"

        from .CanvasObject import drawCatalog
        # For interactive drawing
        self.candraw = False
        self.draw_dict = drawCatalog
        # canvas objects which we know how to draw have an "idraw"
        # class method
        self.drawtypes = [ key for key in self.draw_dict.keys()
                           if hasattr(self.draw_dict[key], 'idraw') ]
        self.drawtypes.sort()
        self.t_drawtype = 'point'
        self.t_drawparams = {}
        # holds the drawing context
        self._draw_cxt = None

        # For interactive editing
        self.canedit = False
        # Set to False to disable drag moves except from move control pt
        self.easymove = True
        self._start_x = 0
        self._start_y = 0
        self._cp_index = None
        self._edit_obj = None
        self._edit_status = False

        # For modes
        self._mode = 'draw'
        self._mode_tbl = Bunch()
        self.add_draw_mode(None)
        self.add_draw_mode('draw', down=self.draw_start,
                           move=self.draw_motion, up=self.draw_stop,
                           poly_add=self.draw_poly_add,
                           poly_delete=self.draw_poly_delete)
        self.add_draw_mode('edit', down=self.edit_start,
                           move=self.edit_motion, up=self.edit_stop,
                           poly_add=self.edit_poly_add,
                           poly_delete=self.edit_poly_delete)

        # For selection
        self._selected = []
        self.multi_select_ok = False

        # this controls whether an object is automatically selected for
        # editing immediately after being drawn
        self.edit_follows_draw = False

        self._process_time = 0.0
        # time delta threshold for deciding whether to update the image
        self._delta_time = 0.020
        self._draw_obj = None

        # NOTE: must be mixed in with a Callback.Callbacks
        for name in ('draw-event', 'draw-down', 'draw-move', 'draw-up',
                     'cursor-down', 'cursor-up', 'cursor-move',
                     'draw-scroll', 'keydown-poly_add', 'keydown-poly_del',
                     'keydown-edit_del', 'edit-event',
                     'edit-select', 'drag-drop'):
            self.enable_callback(name)

    def set_surface(self, viewer):
        self.viewer = viewer

        # register this canvas for events of interest
        canvas = self

        # for legacy drawing via draw mode in Bindmap
        canvas.add_callback('draw-down', self.draw_start, viewer)
        canvas.add_callback('draw-move', self.draw_motion, viewer)
        canvas.add_callback('draw-up', self.draw_stop, viewer)

        canvas.add_callback('key-press', self._draw_key, 'key', viewer)
        canvas.add_callback('keydown-poly_add', self._draw_op, 'poly_add',
                          viewer)
        canvas.add_callback('keydown-poly_del', self._draw_op, 'poly_delete',
                          viewer)
        canvas.add_callback('keydown-edit_del', self.edit_delete_cb, viewer)
        #canvas.add_callback('draw-scroll', self._edit_rotate_cb, viewer)
        #canvas.add_callback('draw-scroll', self._edit_scale_cb, viewer)

    def get_surface(self):
        return self.viewer

    def register_for_cursor_drawing(self, viewer):
        canvas = self
        canvas.add_callback('cursor-down', self._draw_op, 'down', viewer)
        canvas.add_callback('cursor-move', self._draw_op, 'move', viewer)
        canvas.add_callback('cursor-up', self._draw_op, 'up', viewer)

    ##### MODE LOGIC #####

    def add_draw_mode(self, name, **kwargs):
        try:
            bnch = self._mode_tbl[name]
        except KeyError:
            bnch = Bunch(name=name, **kwargs)
            self._mode_tbl[name] = bnch

        return bnch

    def set_draw_mode(self, mode):
        if not mode in self._mode_tbl:
            modes = list(self._mode_tbl.keys())
            raise ValueError("mode must be one of: %s" % (str(modes)))

        self._mode = mode
        if mode != 'edit':
            self.clear_selected()

        self.update_canvas()

    def get_draw_mode(self):
        return self._mode

    def _draw_op(self, canvas, event, data_x, data_y, opn, viewer):
        if viewer != event.viewer:
            return False

        mode = self._mode
        # Hack to handle legacy drawing using draw mode in Bindmap
        if self.is_drawing():
            mode = 'draw'

        try:
            method = self._mode_tbl[mode][opn]
        except KeyError:
            return False

        if method is not None:
            return method(canvas, event, data_x, data_y, viewer)
        return False

    def _draw_key(self, canvas, keyname, opn, viewer):
        # synthesize a KeyEvent
        # TODO: this is hacky--see if we can rethink how this is handled
        #  so that we get passed an event similar to _draw_op()
        last_x, last_y = viewer.get_last_data_xy()
        event = KeyEvent(key=keyname, state='down', mode=self._mode,
                         modifiers=[], viewer=viewer,
                         data_x=last_x, data_y=last_y)

        return self._draw_op(canvas, event, last_x, last_y, opn, viewer)

    ##### DRAWING LOGIC #####

    def _draw_update(self, data_x, data_y, cxt):

        ## self.logger.debug("drawing a '%s' x,y=%f,%f" % (
        ##     self.t_drawtype, data_x, data_y))

        klass = self.draw_dict[self.t_drawtype]
        obj = None

        # update the context with current position
        x, y = cxt.crdmap.data_to(data_x, data_y)
        cxt.setvals(x=x, y=y, data_x=data_x, data_y=data_y)

        obj = klass.idraw(self, cxt)

        # elif self.t_drawtype == 'equilateraltriangle':
        #         len_x = self._start_x - x
        #         len_y = self._start_y - y
        #         length = max(abs(len_x), abs(len_y))
        #         obj = klass(self._start_x, self._start_y,
        #                     length, length, **self.t_drawparams)

        if obj is not None:
            obj.initialize(None, cxt.viewer, self.logger)
            #obj.initialize(None, cxt.viewer, viewer.logger)
            self._draw_obj = obj
            if time.time() - self._process_time > self._delta_time:
                self.process_drawing()

        return True

    def draw_start(self, canvas, event, data_x, data_y, viewer):
        if not self.candraw:
            return False

        self._draw_obj = None
        # get the drawing coordinate type (default 'data')
        crdtype = self.t_drawparams.get('coord', 'data')
        crdmap = viewer.get_coordmap(crdtype)
        x, y = crdmap.data_to(data_x, data_y)
        # create the drawing context
        self._draw_cxt = Bunch(start_x=x, start_y=y, points=[(x, y)],
                               x=x, y=y, data_x=data_x, data_y=data_y,
                               drawparams=self.t_drawparams,
                               crdmap=crdmap, viewer=viewer,
                               logger=self.logger)

        self._draw_update(data_x, data_y, self._draw_cxt)
        self.process_drawing()
        return True

    def draw_stop(self, canvas, event, data_x, data_y, viewer):
        if not self.candraw:
            return False

        self._draw_update(data_x, data_y, self._draw_cxt)
        obj, self._draw_obj = self._draw_obj, None

        if obj:
            objtag = self.add(obj)
            self.make_callback('draw-event', objtag)

            if self.edit_follows_draw:
                #self.set_draw_mode('edit')
                self.clear_selected()
                self.edit_select(obj)
                self.make_callback('edit-select', self._edit_obj)
            return True
        else:
            self.process_drawing()

    def draw_motion(self, canvas, event, data_x, data_y, viewer):
        if not self.candraw:
            return False

        self._draw_update(data_x, data_y, self._draw_cxt)
        return True

    def draw_poly_add(self, canvas, event, data_x, data_y, viewer):
        if not self.candraw:
            return False

        cxt = self._draw_cxt
        if self.t_drawtype in ('polygon', 'path'):
            x, y = cxt.crdmap.data_to(data_x, data_y)
            cxt.points.append((x, y))
        elif self.t_drawtype == 'beziercurve' and len(cxt.points) < 3:
            x, y = cxt.crdmap.data_to(data_x, data_y)
            cxt.points.append((x, y))
        return True

    def draw_poly_delete(self, canvas, event, data_x, data_y, viewer):
        if not self.candraw:
            return False

        cxt = self._draw_cxt
        if self.t_drawtype in ('polygon', 'path', 'beziercurve'):
            if len(cxt.points) > 0:
                cxt.points.pop()
        return True

    def is_drawing(self):
        return self._draw_obj is not None

    def enable_draw(self, tf):
        self.candraw = tf

    def set_drawcolor(self, colorname):
        self.t_drawparams['color'] = colorname

    def set_drawtype(self, drawtype, **drawparams):
        drawtype = drawtype.lower()
        assert drawtype in self.drawtypes, \
               ValueError("Bad drawing type '%s': must be one of %s" % (
            drawtype, self.drawtypes))
        self.t_drawtype = drawtype
        self.t_drawparams = drawparams.copy()

    def get_drawtypes(self):
        return self.drawtypes

    def get_drawtype(self):
        return self.t_drawtype

    def get_draw_class(self, drawtype):
        drawtype = drawtype.lower()
        klass = self.draw_dict[drawtype]
        return klass

    def get_drawparams(self):
        return self.t_drawparams.copy()

    def process_drawing(self):
        self._process_time = time.time()
        #viewer.redraw(whence=3)
        #self.redraw(whence=3)
        self.update_canvas()

    def register_canvas_type(self, name, klass):
        drawtype = name.lower()
        self.draw_dict[drawtype] = klass
        if not drawtype in self.drawtypes:
            self.drawtypes.append(drawtype)
            self.drawtypes.sort()


    ##### EDITING LOGIC #####

    def get_edit_object(self):
        return self._edit_obj

    def is_editing(self):
        return self.get_edit_obj() is not None

    def enable_edit(self, tf):
        self.canedit = tf

    def _edit_update(self, data_x, data_y, viewer):
        if (not self.canedit) or (self._cp_index is None):
            return False

        x, y = self._edit_obj.crdmap.data_to(data_x, data_y)

        if self._cp_index < 0:
            if self.easymove:
                ## self._edit_obj.move_to(x - self._start_x,
                ##                        y - self._start_y)
                self._edit_obj.set_edit_point(0, (x - self._start_x,
                                                  y - self._start_y))
        else:
            # special hack for objects that have rot_deg attribute
            if hasattr(self._edit_obj, 'rot_deg') and (self._cp_index > 0):
                rot_deg = - self._edit_obj.rot_deg
                xoff, yoff = self._edit_obj.get_center_pt()
                x, y = self._edit_obj.crdmap.rotate_pt(x, y, rot_deg,
                                                       xoff=xoff, yoff=yoff)

            self._edit_obj.set_edit_point(self._cp_index, (x, y))

        #self._edit_obj.sync_state()

        if time.time() - self._process_time > self._delta_time:
            self.process_drawing()
        return True

    def _is_editable(self, obj, x, y, is_inside):
        return is_inside and obj.editable

    def _prepare_to_move(self, obj, data_x, data_y):
        #print(("moving an object", obj.editable))
        self.edit_select(obj)
        self._cp_index = -1
        ref_x, ref_y = self._edit_obj.get_reference_pt()
        x, y = obj.crdmap.data_to(data_x, data_y)
        self._start_x, self._start_y = x - ref_x, y - ref_y
        #print(("end moving an object", obj.editable))

    def edit_start(self, canvas, event, data_x, data_y, viewer):
        if not self.canedit:
            return False

        self._edit_tmp = self._edit_obj
        self._edit_status = False
        self._cp_index = None
        #shift_held = 'shift' in event.modifiers
        shift_held = False

        selects = self.get_selected()
        if len(selects) == 0:
            #print("no objects already selected")
            # <-- no objects already selected

            # check for objects at this location
            #print("getting items")
            objs = canvas.select_items_at(viewer, data_x, data_y,
                                          test=self._is_editable)
            #print("items: %s" % (str(objs)))

            if len(objs) == 0:
                # <-- no objects under cursor
                return False

            # pick top object
            obj = objs[-1]
            self._prepare_to_move(obj, data_x, data_y)

        else:
            self._edit_status = True

            # Ugh.  Check each selected object's control points
            # for a match
            contains = []
            for obj in selects:
                #print("editing: checking for cp")
                #edit_pts = self._edit_obj.get_edit_points()
                edit_pts = list(map(lambda pt: obj.crdmap.to_data(*pt),
                                    obj.get_edit_points()))
                #print((self._edit_obj, edit_pts))
                i = obj.get_pt(viewer, edit_pts, data_x, data_y,
                               obj.cap_radius)
                #print(('got point', i))
                if i is not None:
                    #print("editing cp #%d" % (i))
                    # editing a control point from an existing object
                    self._edit_obj = obj
                    self._cp_index = i
                    self._edit_update(data_x, data_y, viewer)
                    return True

                if obj.contains(data_x, data_y):
                    contains.append(obj)

            # <-- no control points match, is there an object that contains
            # this point?
            if len(contains) > 0:
                # TODO?: make a compound object of contains and move it?
                obj = contains[-1]
                if self.is_selected(obj) and shift_held:
                    # deselecting object
                    self.select_remove(obj)
                else:
                    self._prepare_to_move(obj, data_x, data_y)
                    ## Compound = self.get_draw_class('compoundobject')
                    ## c_obj = Compound(*self.get_selected())
                    ## c_obj.inherit_from(obj)
                    ## self._prepare_to_move(c_obj, data_x, data_y)

            else:
                # <-- user clicked outside any selected item's control pt
                # and outside any selected item
                if not shift_held:
                    self.clear_selected()

                # see now if there is an unselected item at this location
                objs = canvas.select_items_at(viewer, data_x, data_y,
                                              test=self._is_editable)
                #print("new items: %s" % (str(objs)))
                if len(objs) > 0:
                    # pick top object
                    obj = objs[-1]
                    #print(("top object", obj))
                    if self.num_selected() > 0:
                        #print("there are previously selected items")
                        # if there are already some selected items, then
                        # add this object to the selection, make a compound
                        # object
                        self.edit_select(obj)
                        Compound = self.get_draw_class('compoundobject')
                        c_obj = Compound(*self.get_selected())
                        c_obj.inherit_from(obj)
                        self._prepare_to_move(c_obj, data_x, data_y)
                    else:
                        # otherwise just start over with this new object
                        #print(("starting over"))
                        self._prepare_to_move(obj, data_x, data_y)

        self.process_drawing()
        return True

    def edit_stop(self, canvas, event, data_x, data_y, viewer):
        if not self.canedit:
            return False

        if (self._edit_tmp != self._edit_obj) or (
            (self._edit_obj is not None) and
            (self._edit_status != self.is_selected(self._edit_obj))):
            # <-- editing status has changed
            #print("making edit-select callback")
            self.make_callback('edit-select', self._edit_obj)

        if (self._edit_obj is not None) and (self._cp_index is not None):
            # <-- an object has been edited
            self._edit_update(data_x, data_y, viewer)
            self._cp_index = None
            self.make_callback('edit-event', self._edit_obj)

        return True

    def edit_motion(self, canvas, event, data_x, data_y, viewer):
        if not self.canedit:
            return False

        if (self._edit_obj is not None) and (self._cp_index is not None):
            self._edit_update(data_x, data_y, viewer)
            return True

        return False

    def edit_poly_add(self, canvas, event, data_x, data_y, viewer):
        if not self.canedit:
            return False
        obj = self._edit_obj
        if (obj is not None) and self.is_selected(obj) and \
               (obj.kind in ('polygon', 'path')):
            self.logger.debug("checking points")
            # determine which line we are adding a point to
            points = list(obj.get_points())
            if obj.kind == 'polygon':
                points = points + [points[0]]
            x0, y0 = obj.crdmap.to_data(*points[0])
            insert = None
            for i in range(1, len(points[1:])):
                x1, y1 = obj.crdmap.to_data(*points[i])
                self.logger.debug("checking line %d" % (i))
                if obj.within_line(viewer, data_x, data_y, x0, y0, x1, y1,
                                   8):
                    insert = i
                    break
                x0, y0 = x1, y1
            if insert is not None:
                self.logger.debug("inserting point")
                # Point near a line
                x, y = obj.crdmap.data_to(data_x, data_y)
                points.insert(insert, (x, y))
                obj.points = points
                self.process_drawing()
            else:
                self.logger.debug("cursor not near a line")

        return True

    def edit_poly_delete(self, canvas, event, data_x, data_y, viewer):
        if not self.canedit:
            return False
        obj = self._edit_obj
        if (obj is not None) and self.is_selected(obj) and \
               (obj.kind in ('polygon', 'path')):
            self.logger.debug("checking points")
            # determine which point we are deleting
            points = list(obj.get_points())
            delete = None
            for i in range(len(points)):
                x1, y1 = obj.crdmap.to_data(*points[i])
                self.logger.debug("checking vertex %d" % (i))
                if obj.within_radius(viewer, data_x, data_y, x1, y1,
                                     8):
                    delete = i
                    break
            if delete is not None:
                self.logger.debug("deleting point")
                points.pop(delete)
                obj.points = points
                self.process_drawing()
            else:
                self.logger.debug("cursor not near a point")

        return True

    def edit_rotate(self, delta_deg, viewer):
        if self._edit_obj is None:
            return False
        self._edit_obj.rotate_by(delta_deg)
        self.process_drawing()
        self.make_callback('edit-event', self._edit_obj)
        return True

    def _edit_rotate_cb(self, canvas, event, viewer, msg=True):
        if not self.canedit or (viewer != event.viewer):
            return False
        bd = viewer.get_bindings()
        amount = event.amount
        if bd.get_direction(event.direction) == 'down':
            amount = - amount
        return self.edit_rotate(amount)

    def edit_scale(self, delta_x, delta_y, viewer):
        if self._edit_obj is None:
            return False
        self._edit_obj.scale_by(delta_x, delta_y)
        self.process_drawing()
        self.make_callback('edit-event', self._edit_obj)
        return True

    def _edit_scale_cb(self, canvas, event, viewer, msg=True):
        if not self.canedit or (viewer != event.viewer):
            return False
        bd = viewer.get_bindings()
        if bd.get_direction(event.direction) == 'down':
            amount = 0.9
        else:
            amount = 1.1
        return self.edit_scale(amount, amount)

    def edit_delete(self):
        if (self._edit_obj is not None) and self.is_selected(self._edit_obj):
            self.select_remove(self._edit_obj)
            obj, self._edit_obj = self._edit_obj, None
            self.deleteObject(obj)
            self.make_callback('edit-event', self._edit_obj)
        return True

    def edit_delete_cb(self, canvas, event, data_x, data_y, viewer):
        if not self.canedit or (viewer != event.viewer):
            return False
        return self.edit_delete()

    def edit_select(self, newobj):
        if not self.canedit:
            return False

        if not self.multi_select_ok:
            self.clear_selected()

        # add new object to selection
        self.select_add(newobj)
        self._edit_obj = newobj
        return True

    ##### SELECTION LOGIC #####

    def _is_selectable(self, obj, x, y, is_inside):
        return is_inside and obj.editable
        #return is_inside

    def is_selected(self, obj):
        return obj in self._selected

    def get_selected(self):
        return self._selected

    def num_selected(self):
        return len(self._selected)

    def clear_selected(self):
        self._selected = []

    def select_remove(self, obj):
        try:
            self._selected.remove(obj)
        except:
            pass

    def select_add(self, obj):
        if obj not in self._selected:
            self._selected.append(obj)

    def select_stop(self, canvas, button, data_x, data_y, viewer):
        #print("getting items")
        objs = canvas.select_items_at(viewer, data_x, data_y,
                                      test=self._is_selectable)
        if len(objs) == 0:
            # no objects
            return False

        # pick top object
        obj = objs[-1]

        if obj not in self._selected:
            self._selected.append(obj)
        else:
            self._selected.remove(obj)
            obj = None

        self.logger.debug("selected: %s" % (str(self._selected)))
        self.process_drawing()

        #self.make_callback('edit-select', obj, self._selected)
        return True

    def group_selection(self):
        Compound = self.get_draw_class('compoundobject')
        c_obj = Compound(self._selected)
        self._selected = [ comp_obj ]


    # The canvas drawing

    def draw(self, viewer):
        # Draw everything else as usual
        super(DrawingMixin, self).draw(viewer)

        # Draw our current drawing object, if any
        if self._draw_obj:
            self._draw_obj.draw(viewer)

        # Draw control points on edited objects
        # TODO: there is a problem if the object has been removed from
        # the canvas but not removed from the selection--we still end
        # up drawing the control points for it
        selected = self.get_selected()
        if len(selected) > 0:
            for obj in selected:
                cr = viewer.renderer.setup_cr(obj)
                obj.draw_edit(cr, viewer)


    ### NON-PEP8 EQUIVALENTS -- TO BE DEPRECATED ###

    setSurface = set_surface
    getSurface = get_surface
    getDrawClass = get_draw_class


#END
