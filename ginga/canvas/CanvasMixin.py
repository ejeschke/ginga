#
# CanvasMixin.py -- enable canvas like capabilities.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.canvas.CompoundMixin import CompoundMixin

__all__ = ['CanvasMixin']


class CanvasError(Exception):
    pass


class CanvasMixin(object):
    """A CanvasMixin is combined with the CompoundMixin to make a
    tag-addressible canvas-like interface.  This mixin should precede the
    CompoundMixin in the inheritance (and so, method resolution) order.
    """

    def __init__(self):
        assert isinstance(self, CompoundMixin), "Missing CompoundMixin class"
        # holds the list of tags
        self.tags = {}
        self.count = 0

        for name in ('modified', ):
            self.enable_callback(name)

    def update_canvas(self, whence=3):
        self.make_callback('modified', whence)

    def redraw(self, whence=3):
        self.make_callback('modified', whence)

    def subcanvas_updated_cb(self, canvas, whence):
        """
        This is a notification that a subcanvas (a canvas contained in
        our canvas) has been modified.  We in turn signal that our canvas
        has been modified.
        """
        # avoid self-referential loops
        if canvas != self:
            #print("%s subcanvas %s was updated" % (self.name, canvas.name))
            self.make_callback('modified', whence)

    def add(self, obj, tag=None, tagpfx=None, belowThis=None, redraw=True):
        self.count += 1
        if tag:
            # user supplied a tag
            if tag in self.tags:
                raise CanvasError("Tag already used: '%s'" % (tag))
        else:
            if tagpfx:
                # user supplied a tag prefix
                if tagpfx.startswith('@'):
                    raise CanvasError("Tag prefix may not begin with '@'")
                tag = '%s%d' % (tagpfx, self.count)
            else:
                # make up our own tag
                tag = '@%d' % (self.count)

        obj.tag = tag
        self.tags[tag] = obj
        self.add_object(obj, belowThis=belowThis)

        # propagate change notification on this canvas
        if obj.has_callback('modified'):
            obj.add_callback('modified', self.subcanvas_updated_cb)

        if redraw:
            self.update_canvas(whence=3)
        return tag

    def delete_objects_by_tag(self, tags, redraw=True):
        for tag in tags:
            try:
                obj = self.tags[tag]
                del self.tags[tag]
                super(CanvasMixin, self).delete_object(obj)
            except Exception as e:
                continue

        if redraw:
            self.update_canvas(whence=3)

    def delete_object_by_tag(self, tag, redraw=True):
        self.delete_objects_by_tag([tag], redraw=redraw)

    def get_object_by_tag(self, tag):
        obj = self.tags[tag]
        return obj

    def lookup_object_tag(self, obj):
        # TODO: we may need to have a reverse index eventually
        res = list(zip(*self.tags.items()))
        if len(res) == 0:
            return None
        tags, objs = res
        try:
            idx = objs.index(obj)
            return tags[idx]
        except ValueError:
            return None

    def get_tags_by_tag_pfx(self, tagpfx):
        return [key for key in self.tags if key.startswith(tagpfx)]

    def get_tags(self):
        return list(self.tags.keys())

    def has_tag(self, tag):
        return tag in self.tags

    def get_objects_by_tag_pfx(self, tagpfx):
        return [self.tags[k] for k in self.get_tags_by_tag_pfx(tagpfx)]

    def delete_all_objects(self, redraw=True):
        self.tags.clear()
        CompoundMixin.delete_all_objects(self)

        if redraw:
            self.update_canvas(whence=3)

    def delete_objects(self, objects, redraw=True):
        res = list(zip(*self.tags.items()))
        if len(res) == 0:
            tags, objs = [], []
        else:
            tags, objs = res
        for obj in objects:
            try:
                idx = objs.index(obj)
                tag = tags[idx]
            except ValueError:
                tag = None
            if tag is not None:
                self.delete_object_by_tag(tag, redraw=False)
            else:
                CompoundMixin.delete_object(self, obj)

        if redraw:
            self.update_canvas(whence=3)

    def delete_object(self, obj, redraw=True):
        self.delete_objects([obj], redraw=redraw)

    def raise_object_by_tag(self, tag, aboveThis=None, redraw=True):
        obj1 = self.get_object_by_tag(tag)
        if aboveThis is None:
            self.raise_object(obj1)
        else:
            obj2 = self.get_object_by_tag(aboveThis)
            self.raise_object(obj1, obj2)

        if redraw:
            self.update_canvas(whence=3)

    def lower_object_by_tag(self, tag, belowThis=None, redraw=True):
        obj1 = self.get_object_by_tag(tag)
        if belowThis is None:
            self.lower_object(obj1)
        else:
            obj2 = self.get_object_by_tag(belowThis)
            self.lower_object(obj1, obj2)

        if redraw:
            self.update_canvas(whence=3)
