#
# text_model.py -- toolkit-neutral text buffer model with tags and refs
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""A backend-neutral text buffer model.

``TextModel`` holds the content string, a set of live position references
(``TextBufferRef``) that follow edits, a named tag table with interval
bookkeeping, find/replace, and a model-level undo/redo stack.  None of it
depends on a GUI toolkit.

A toolkit widget (qt, gtk, ...) subclasses ``TextModel`` and implements the
small set of *render hooks* to reflect model changes in a native widget:

    _set_editor_text(text)              push the whole text into the widget
    _replace_editor_range(s, e, text)   edit just the changed span
    _apply_all_formats(region=None)     (re)apply tag styling to a range
    _apply_selection_to_editor()        mirror model selection into the widget
    _refresh_icon_gutter()              redraw ref-anchored gutter icons
    _mark_clean()                       clear the widget's "modified" flag

The default implementations are no-ops, so a bare ``TextModel`` is usable
headless (e.g. for tests or a non-visual buffer).
"""
import weakref

from ginga.misc import Callback


class TextBufferRef:
    """Live reference to a character offset in a text model buffer.

    The ref follows inserts and deletes performed through the owning buffer.
    Gravity controls how the ref behaves when text is inserted at exactly the
    ref's offset.
    """

    def __init__(self, buffer, offset, gravity='right'):
        if gravity not in ('left', 'right'):
            raise ValueError("gravity must be 'left' or 'right'")
        self._buffer = buffer
        self._offset = buffer._clamp_offset(offset)
        self._gravity = gravity
        self._valid = True

    def get_offset(self):
        return self._offset

    def get_gravity(self):
        return self._gravity

    def is_valid(self):
        return self._valid

    def get_line_column(self):
        self._check_valid()
        text = self._buffer.get_text()
        prefix = text[:self._offset]
        line = prefix.count('\n')
        last_nl = prefix.rfind('\n')
        col = self._offset if last_nl < 0 else self._offset - last_nl - 1
        return (line, col)

    def get_line(self):
        self._check_valid()
        return self._buffer._line_of_offset(self._offset)

    def set_offset(self, offset):
        self._check_valid()
        self._set_offset(offset)

    def set_line(self, lineno):
        self._check_valid()
        self._set_offset(self._buffer._offset_of_line_start(lineno))

    def to_ref(self, other):
        self._check_valid()
        if not isinstance(other, TextBufferRef):
            raise TypeError("to_ref requires a TextBufferRef")
        if other._buffer is not self._buffer:
            raise ValueError("TextBufferRef belongs to a different buffer")
        if not other._valid:
            raise ValueError("Source TextBufferRef has been invalidated")
        self._set_offset(other._offset)

    def copy(self):
        self._check_valid()
        return self._buffer.create_ref(self._offset, self._gravity)

    def to_line_start(self):
        self._check_valid()
        self._set_offset(self._buffer._offset_of_line_start(self.get_line()))

    def to_line_end(self):
        self._check_valid()
        text = self._buffer.get_text()
        idx = text.find('\n', self._offset)
        if idx < 0:
            idx = len(text)
        self._set_offset(idx)

    def to_next_line(self):
        self._check_valid()
        text = self._buffer.get_text()
        idx = text.find('\n', self._offset)
        if idx >= 0:
            self._set_offset(idx + 1)

    def to_prev_line(self):
        self._check_valid()
        line = self.get_line()
        if line > 0:
            self._set_offset(self._buffer._offset_of_line_start(line - 1))

    def to_next_char(self):
        self._check_valid()
        self._set_offset(self._offset + 1)

    def to_prev_char(self):
        self._check_valid()
        self._set_offset(self._offset - 1)

    def _check_valid(self):
        if not self._valid:
            raise ValueError("TextBufferRef has been invalidated")

    def _set_offset(self, new_offset):
        self._offset = self._buffer._clamp_offset(new_offset)
        self._buffer._refresh_icon_gutter()

    def _invalidate(self):
        self._valid = False


class TextModel(Callback.Callbacks):
    """Toolkit-neutral text buffer: content, refs, a tag table, find/replace
    and model-level undo/redo.  Subclass and implement the render hooks to
    drive a native widget."""

    def __init__(self):
        Callback.Callbacks.__init__(self)

        self._text = ''
        self._refs = weakref.WeakSet()
        self._named_refs = {}
        self._tag_defs = {}
        self._tags = []
        self._tag_seq = 0
        self._icon_refs = {}
        self._cursor = 0
        self._sel_start = 0
        self._sel_end = 0

        # Model-level undo/redo.  Each entry records a single _replace_range
        # edit as (start, old_text, new_text, cursor_before, cursor_after) so
        # it can be inverted with refs and tags kept consistent.
        self._undo_stack = []
        self._redo_stack = []
        self._undo_limit = 500
        self._in_undo_redo = False

        for name in ('changed', 'cursor-moved'):
            self.enable_callback(name)

    # ------------------------------------------------------------------
    # Render hooks -- subclasses override these to reflect model changes in
    # a native widget.  Defaults are no-ops so a bare model works headless.
    # ------------------------------------------------------------------
    def _set_editor_text(self, text):
        pass

    def _replace_editor_range(self, start, end, new_text):
        pass

    def _apply_all_formats(self, region=None):
        pass

    def _apply_selection_to_editor(self):
        pass

    def _refresh_icon_gutter(self):
        pass

    def _mark_clean(self):
        pass

    # ------------------------------------------------------------------
    # Content
    # ------------------------------------------------------------------
    def get_length(self):
        return len(self._text)

    def get_text(self):
        return self._text

    def get_text_range(self, start_ref, end_ref):
        """Return the text spanning ``[start_ref, end_ref)``."""
        start = self._offset_of(start_ref)
        end = self._offset_of(end_ref)
        if start > end:
            start, end = end, start
        return self._text[start:end]

    def clear(self):
        self.set_text('')

    def set_text(self, text):
        """Replace the full buffer contents.

        This is destructive with respect to refs and applied tags: existing
        refs are invalidated and applied tag intervals are cleared.
        """
        self._text = '' if text is None else str(text)
        self._cursor = 0
        self._sel_start = 0
        self._sel_end = 0
        self._tags = []
        self._undo_stack = []
        self._redo_stack = []
        self._invalidate_all_refs()
        self._named_refs.clear()
        self._icon_refs.clear()
        self._set_editor_text(self._text)
        self._apply_all_formats()
        self._refresh_icon_gutter()
        self._mark_clean()

    def insert_text(self, ref, text, tags=None):
        """Insert text at ``ref`` and optionally apply tags to that range."""
        if text is None or text == '':
            return
        offset = self._offset_of(ref)
        self._replace_range(offset, offset, str(text), tags=tags)

    def delete_range(self, start_ref, end_ref):
        """Delete the text spanning ``[start_ref, end_ref)``."""
        start = self._offset_of(start_ref)
        end = self._offset_of(end_ref)
        if start > end:
            start, end = end, start
        if start == end:
            return
        self._replace_range(start, end, '')

    # ------------------------------------------------------------------
    # Refs
    # ------------------------------------------------------------------
    def create_ref(self, offset, gravity='right'):
        """Create a live buffer ref at ``offset``."""
        ref = TextBufferRef(self, offset, gravity=gravity)
        self._refs.add(ref)
        return ref

    def remove_ref(self, ref):
        """Invalidate a ref and detach any named/icon bindings that use it."""
        if not isinstance(ref, TextBufferRef):
            return
        if not ref.is_valid():
            return
        for name, named_ref in list(self._named_refs.items()):
            if named_ref is ref:
                del self._named_refs[name]
        if ref in self._icon_refs:
            del self._icon_refs[ref]
        ref._invalidate()
        self._refresh_icon_gutter()

    def create_named_ref(self, name, offset, gravity='right'):
        """Create a live ref and bind it to ``name``."""
        existing = self._named_refs.get(name)
        if existing is not None:
            self.remove_ref(existing)
        ref = self.create_ref(offset, gravity=gravity)
        self._named_refs[name] = ref
        return ref

    def get_named_ref(self, name):
        return self._named_refs.get(name)

    def remove_named_ref(self, name):
        ref = self._named_refs.pop(name, None)
        if ref is not None:
            self.remove_ref(ref)

    def get_ref_start(self):
        return self.create_ref(0, 'right')

    def get_ref_end(self):
        return self.create_ref(len(self._text), 'right')

    def get_ref_bounds(self):
        return (self.get_ref_start(), self.get_ref_end())

    def get_ref_line_start(self, lineno):
        return self.create_ref(self._offset_of_line_start(lineno), 'right')

    def get_ref_line_end(self, lineno):
        start = self._offset_of_line_start(lineno)
        idx = self._text.find('\n', start)
        end = len(self._text) if idx < 0 else idx
        return self.create_ref(end, 'right')

    def set_icon(self, ref, image):
        """Associate an icon with a ref so it follows text movement by line."""
        if not isinstance(ref, TextBufferRef):
            raise TypeError("set_icon requires a TextBufferRef")
        if ref._buffer is not self:
            raise ValueError("TextBufferRef belongs to a different buffer")
        if image is None:
            self._icon_refs.pop(ref, None)
        else:
            self._icon_refs.pop(ref, None)
            self._icon_refs[ref] = image
        self._refresh_icon_gutter()

    # ------------------------------------------------------------------
    # Tags
    # ------------------------------------------------------------------
    def create_tag(self, name, attrs=None, **kwdargs):
        """Define or redefine a named display tag."""
        attrs = {} if attrs is None else dict(attrs)
        attrs.update(kwdargs)
        self._tag_defs[name] = attrs
        # A tag definition only affects rendering where the tag is applied.
        # Defining a brand-new (unapplied) tag needs no reformat, which keeps
        # bulk tag creation (e.g. one tag per AST node) cheap.
        if self.has_tag(name):
            self._apply_all_formats()

    def remove_tag_def(self, name):
        if name in self._tag_defs:
            del self._tag_defs[name]
        self._tags = [tag for tag in self._tags if tag['name'] != name]
        self._apply_all_formats()

    def has_tag(self, name):
        return any(tag['name'] == name for tag in self._tags)

    def apply_tag(self, name, start_ref, end_ref):
        """Apply a previously-defined tag across a buffer range."""
        if name not in self._tag_defs:
            raise ValueError("Unknown tag: %s" % (name,))
        start = self._offset_of(start_ref)
        end = self._offset_of(end_ref)
        if start > end:
            start, end = end, start
        if start == end:
            return
        self._add_tag_interval(name, start, end)
        self._apply_all_formats(region=(start, end))

    def remove_tag(self, name, start_ref, end_ref):
        """Clip a tag out of the given buffer range."""
        start = self._offset_of(start_ref)
        end = self._offset_of(end_ref)
        if start > end:
            start, end = end, start
        next_tags = []
        for tag in self._tags:
            if tag['name'] != name or tag['end'] <= start or tag['start'] >= end:
                next_tags.append(tag)
                continue
            if tag['start'] < start:
                next_tags.append(dict(tag, end=start))
            if tag['end'] > end:
                next_tags.append(dict(tag, start=end))
        self._tags = next_tags
        self._apply_all_formats(region=(start, end))

    def get_tags_at(self, ref):
        offset = self._offset_of(ref)
        names = []
        seen = set()
        for tag in self._tags:
            if tag['start'] <= offset < tag['end'] and tag['name'] not in seen:
                names.append(tag['name'])
                seen.add(tag['name'])
        return names

    def get_tags_range(self, start_ref, end_ref):
        start = self._offset_of(start_ref)
        end = self._offset_of(end_ref)
        if start > end:
            start, end = end, start
        names = []
        seen = set()
        for tag in self._tags:
            if tag['end'] <= start or tag['start'] >= end:
                continue
            if tag['name'] not in seen:
                names.append(tag['name'])
                seen.add(tag['name'])
        return names

    def get_tag_region(self, name):
        """Return the overall ``(start_ref, end_ref)`` span of a named tag.

        This mirrors the old GTK ``get_region`` helper: it returns a single
        ref pair covering from the first occurrence of the tag to the last.
        Returns ``None`` if the tag is not applied anywhere.
        """
        spans = [tag for tag in self._tags if tag['name'] == name]
        if not spans:
            return None
        start = min(tag['start'] for tag in spans)
        end = max(tag['end'] for tag in spans)
        return (self.create_ref(start, 'right'),
                self.create_ref(end, 'right'))

    def get_tag_regions(self, name):
        """Return a list of ``(start_ref, end_ref)`` pairs, one per maximal
        contiguous run of the named tag."""
        spans = sorted((tag for tag in self._tags if tag['name'] == name),
                       key=lambda tag: tag['start'])
        if not spans:
            return []
        merged = []
        cur_start, cur_end = spans[0]['start'], spans[0]['end']
        for tag in spans[1:]:
            if tag['start'] <= cur_end:
                cur_end = max(cur_end, tag['end'])
            else:
                merged.append((cur_start, cur_end))
                cur_start, cur_end = tag['start'], tag['end']
        merged.append((cur_start, cur_end))
        return [(self.create_ref(s, 'right'), self.create_ref(e, 'right'))
                for s, e in merged]

    # ------------------------------------------------------------------
    # Find / replace
    # ------------------------------------------------------------------
    def find(self, query, start=None, case_insensitive=False):
        """Return the first match as ``(start_ref, end_ref)`` or ``None``."""
        match = self._find_offset(query, start=start,
                                  case_insensitive=case_insensitive)
        if match is None:
            return None
        return (self.create_ref(match[0], 'right'),
                self.create_ref(match[1], 'right'))

    def find_all(self, query, start=None, case_insensitive=False):
        """Return all non-overlapping matches as ref pairs."""
        matches = self._find_all_offsets(query, start=start,
                                         case_insensitive=case_insensitive)
        return [(self.create_ref(start_off, 'right'),
                 self.create_ref(end_off, 'right'))
                for start_off, end_off in matches]

    def replace(self, query, replacement, all=False, start=None,
                case_insensitive=False):
        """Replace one or all matches and return the replacement count."""
        if not query:
            return 0
        if all:
            matches = self._find_all_offsets(query, start=start,
                                             case_insensitive=case_insensitive)
        else:
            match = self._find_offset(query, start=start,
                                      case_insensitive=case_insensitive)
            matches = [] if match is None else [match]
        for start_off, end_off in reversed(matches):
            self._replace_range(start_off, end_off, replacement)
        return len(matches)

    # ------------------------------------------------------------------
    # Cursor / selection
    # ------------------------------------------------------------------
    def get_cursor(self):
        return self.create_ref(self._cursor, 'right')

    def set_cursor(self, ref):
        """Move the editor cursor to ``ref`` and clear any selection."""
        offset = self._offset_of(ref)
        self._cursor = offset
        self._sel_start = offset
        self._sel_end = offset
        self._apply_selection_to_editor()

    def has_selection(self):
        return self._sel_start != self._sel_end

    def get_selection_range(self):
        if self._sel_start == self._sel_end:
            return None
        start = min(self._sel_start, self._sel_end)
        end = max(self._sel_start, self._sel_end)
        return (self.create_ref(start, 'right'),
                self.create_ref(end, 'right'))

    # get_selection_bounds() is the canonical accessor used by page code;
    # it returns a (start_ref, end_ref) pair or None when there is no
    # selection.  Callers guard with has_selection().
    get_selection_bounds = get_selection_range

    def set_selection_range(self, start_ref, end_ref):
        """Select the text spanning ``[start_ref, end_ref)``."""
        start = self._offset_of(start_ref)
        end = self._offset_of(end_ref)
        self._sel_start = start
        self._sel_end = end
        self._cursor = end
        self._apply_selection_to_editor()

    # ------------------------------------------------------------------
    # Undo / redo
    # ------------------------------------------------------------------
    def can_undo(self):
        return len(self._undo_stack) > 0

    def can_redo(self):
        return len(self._redo_stack) > 0

    def undo(self):
        if not self._undo_stack:
            return False
        start, old_text, new_text, cursor_before, cursor_after = \
            self._undo_stack.pop()
        self._in_undo_redo = True
        try:
            self._replace_range(start, start + len(new_text), old_text,
                                push_undo=False)
            self._cursor, self._sel_start, self._sel_end = cursor_before
            self._apply_selection_to_editor()
        finally:
            self._in_undo_redo = False
        self._redo_stack.append((start, old_text, new_text, cursor_before,
                                 cursor_after))
        return True

    def redo(self):
        if not self._redo_stack:
            return False
        start, old_text, new_text, cursor_before, cursor_after = \
            self._redo_stack.pop()
        self._in_undo_redo = True
        try:
            self._replace_range(start, start + len(old_text), new_text,
                                push_undo=False)
            self._cursor, self._sel_start, self._sel_end = cursor_after
            self._apply_selection_to_editor()
        finally:
            self._in_undo_redo = False
        self._undo_stack.append((start, old_text, new_text, cursor_before,
                                 cursor_after))
        return True

    # ------------------------------------------------------------------
    # Internal offset / ref / tag bookkeeping (pure)
    # ------------------------------------------------------------------
    def _clamp_offset(self, offset):
        try:
            offset = int(offset)
        except Exception:
            offset = 0
        return max(0, min(len(self._text), offset))

    def _offset_of(self, ref):
        if not isinstance(ref, TextBufferRef):
            raise TypeError("API requires a TextBufferRef")
        if ref._buffer is not self:
            raise ValueError("TextBufferRef belongs to a different buffer")
        if not ref.is_valid():
            raise ValueError("TextBufferRef has been invalidated")
        return self._clamp_offset(ref._offset)

    def _line_of_offset(self, offset):
        return self._text[:self._clamp_offset(offset)].count('\n')

    def _offset_of_line_start(self, lineno):
        if lineno <= 0:
            return 0
        offset = 0
        for _idx in range(lineno):
            nl = self._text.find('\n', offset)
            if nl < 0:
                return len(self._text)
            offset = nl + 1
        return offset

    def _replace_range(self, start, end, new_text, tags=None,
                       selection_after=None, sync_editor=True, push_undo=True):
        """Replace ``[start, end)`` in the model and synchronize the view.

        All ref and tag shifting happens here so every edit path shares the
        same semantics.  ``sync_editor`` is disabled only when the edit
        originated from the native widget (which already reflects the new
        text).  ``push_undo`` is disabled when the edit is itself the result
        of an undo/redo replay.
        """
        old_text = self._text[start:end]
        if old_text == new_text:
            if selection_after is not None:
                self._cursor, self._sel_start, self._sel_end = selection_after
            return

        cursor_before = (self._cursor, self._sel_start, self._sel_end)

        self._text = self._text[:start] + new_text + self._text[end:]
        if end > start:
            self._update_refs_on_delete(start, end)
            self._update_tags_on_delete(start, end)
        if new_text:
            self._update_refs_on_insert(start, len(new_text))
            self._update_tags_on_insert(start, len(new_text))
        if tags:
            for name in tags:
                self._add_tag_interval(name, start, start + len(new_text))
        if selection_after is None:
            new_pos = start + len(new_text)
            self._cursor = new_pos
            self._sel_start = new_pos
            self._sel_end = new_pos
        else:
            self._cursor, self._sel_start, self._sel_end = selection_after

        if not self._in_undo_redo and push_undo:
            self._undo_stack.append((start, old_text, new_text, cursor_before,
                                     (self._cursor, self._sel_start, self._sel_end)))
            if len(self._undo_stack) > self._undo_limit:
                self._undo_stack.pop(0)
            self._redo_stack = []

        if sync_editor:
            # Edit only the changed span in the editor (not the whole
            # document), preserving existing formatting outside it.
            self._replace_editor_range(start, end, new_text)
            self._apply_selection_to_editor()
        # Only the inserted span needs (re)formatting: on an incremental edit
        # the toolkit keeps the formatting of the surrounding text, which has
        # merely shifted.  This keeps appends O(edit) rather than O(buffer).
        self._apply_all_formats(region=(start, start + len(new_text)))
        self._refresh_icon_gutter()

        self.make_callback('changed')

    def _invalidate_all_refs(self):
        for ref in list(self._refs):
            ref._offset = 0
            ref._invalidate()

    def _update_refs_on_insert(self, offset, amount):
        for ref in list(self._refs):
            if not ref.is_valid():
                continue
            if ref._offset > offset or (
                    ref._offset == offset and ref.get_gravity() == 'right'):
                ref._offset += amount

    def _update_refs_on_delete(self, start, end):
        amount = end - start
        for ref in list(self._refs):
            if not ref.is_valid():
                continue
            if ref._offset <= start:
                continue
            if ref._offset >= end:
                ref._offset -= amount
            else:
                ref._offset = start

    def _add_tag_interval(self, name, start, end):
        self._tag_seq += 1
        self._tags.append(dict(name=name, start=start, end=end,
                               seq=self._tag_seq))

    def _update_tags_on_insert(self, offset, amount):
        for tag in self._tags:
            if tag['start'] >= offset:
                tag['start'] += amount
            if tag['end'] > offset or (
                    tag['end'] == offset and tag['start'] == tag['end']):
                tag['end'] += amount
            if tag['end'] < tag['start']:
                tag['end'] = tag['start']

    def _update_tags_on_delete(self, start, end):
        amount = end - start
        next_tags = []
        for tag in self._tags:
            tag_start = tag['start']
            tag_end = tag['end']
            if tag_end <= start:
                next_tags.append(tag)
                continue
            if tag_start >= end:
                next_tags.append(dict(tag, start=tag_start - amount,
                                      end=tag_end - amount))
                continue
            new_start = tag_start if tag_start < start else start
            new_end = tag_end - amount if tag_end > end else start
            if new_end > new_start:
                next_tags.append(dict(tag, start=new_start, end=new_end))
        self._tags = next_tags

    def _segments_for_range(self, start, end):
        """Split a range into maximal subranges sharing the same tag stack.

        Returns a list of ``(seg_start, seg_end, [tag_name, ...])`` with the
        tag names ordered by application sequence (so later tags win)."""
        points = {start, end}
        active = []
        for tag in self._tags:
            if tag['end'] <= start or tag['start'] >= end:
                continue
            active.append(tag)
            points.add(max(tag['start'], start))
            points.add(min(tag['end'], end))
        sorted_points = sorted(points)
        segments = []
        for idx in range(len(sorted_points) - 1):
            seg_start = sorted_points[idx]
            seg_end = sorted_points[idx + 1]
            if seg_start >= seg_end:
                continue
            in_seg = [tag for tag in active
                      if tag['start'] <= seg_start and tag['end'] >= seg_end]
            in_seg.sort(key=lambda item: item['seq'])
            segments.append((seg_start, seg_end,
                             [tag['name'] for tag in in_seg]))
        return segments

    def _merged_attrs(self, tag_names):
        """Merge the attr dicts of the given tags (later tags win)."""
        attrs = {}
        for name in tag_names:
            attrs.update(self._tag_defs.get(name, {}))
        return attrs

    def _style_list_from_attrs(self, attrs):
        style = []
        if attrs.get('bold'):
            style.append('bold')
        if attrs.get('italic'):
            style.append('italic')
        return style

    def _find_offset(self, query, start=None, case_insensitive=False):
        if not query:
            return None
        offset = 0 if start is None else self._offset_of(start)
        haystack = self._text
        needle = query
        if case_insensitive:
            haystack = haystack.lower()
            needle = needle.lower()
        idx = haystack.find(needle, offset)
        if idx < 0:
            return None
        return (idx, idx + len(query))

    def _find_all_offsets(self, query, start=None, case_insensitive=False):
        if not query:
            return []
        offsets = []
        offset = 0 if start is None else self._offset_of(start)
        haystack = self._text
        needle = query
        if case_insensitive:
            haystack = haystack.lower()
            needle = needle.lower()
        while True:
            idx = haystack.find(needle, offset)
            if idx < 0:
                break
            offsets.append((idx, idx + len(query)))
            offset = idx + max(1, len(query))
        return offsets
