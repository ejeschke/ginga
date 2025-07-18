#
# syncops.py -- Specialty synchronization classes
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import threading


class BusyError(Exception):
    pass


class Shelf:
    def __init__(self, lock=None):
        if lock is None:
            lock = threading.RLock()
        self._cond = threading.Condition(lock=lock)
        self._is_blocked = False

    def is_blocked(self):
        with self._cond:
            return self._is_blocked

    def block(self):
        with self._cond:
            self._is_blocked = True
        return self

    def unblock(self):
        with self._cond:
            self._is_blocked = False

    def get_stocker(self):
        return Stocker(self)


class Stocker:
    def __init__(self, shelf):
        self.shelf = shelf

    def __enter__(self):
        self.shelf.block()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shelf.unblock()
        return False
