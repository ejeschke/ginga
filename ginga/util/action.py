#
# action.py -- Base classes for undo/redo actions in Ginga
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from collections import deque

#from ginga.misc import Bunch, Callback

__all__ = ['ActionStack', 'Action', 'AttrAction']


class ActionStack:

    def __init__(self):
        super(ActionStack, self).__init__()

        # TODO; add optional limit on stack size
        self._undo = deque()
        self._redo = deque()

    def push(self, action):
        self._undo.append(action)
        self._redo.clear()

    def pop(self):
        action = self._undo.pop()
        self._redo.append(action)
        return action

    def undo(self):
        action = self.pop()
        action.undo()
        return action

    def redo(self):
        action = self._redo.pop()
        self._undo.append(action)
        action.redo()
        return action


class Action:

    def __init__(self, descr=None):
        super(Action, self).__init__()

        self.description = descr

    def undo(self):
        pass

    def redo(self):
        pass


class AttrAction(Action):

    def __init__(self, obj, old, new, descr=None):
        """old and new are dicts mapping attribute names to values.
        """
        super(AttrAction, self).__init__(descr=descr)

        self.obj = obj
        self.old = old
        self.new = new

    def undo(self):
        for name, val in self.old.items():
            setattr(self.obj, name, val)

    def redo(self):
        for name, val in self.new.items():
            setattr(self.obj, name, val)
