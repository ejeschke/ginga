#
# LineHistory.py -- class implementing a text line based history
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
class LineHistory(object):

    def __init__(self, numlines=1000):
        super(LineHistory, self).__init__()

        self.history = []
        self.histidx = 0
        self.histlimit = numlines

    def set_limit(self, numlines):
        self.histlimit = numlines

    def get_history(self):
        return self.history

    def set_history(self, lines):
        self.history = list(lines)

    def append(self, text):
        self.history.append(text)
        i = self.histlimit - len(self.history)
        if i < 0:
            self.history = self.history[abs(i):]
        self.histidx = len(self.history)

    def prev(self):
        i = self.histidx - 1
        if i >= 0:
            self.histidx = i
            return self.history[i]

        raise ValueError("At beginning")

    def next(self):
        i = self.histidx + 1
        if i < len(self.history):
            self.histidx = i
            return self.history[i]

        raise ValueError("At end")

    def save(self, path):
        with open(path, 'w') as out_f:
            out_f.write('\n'.join(self.history))

    def load(self, path):
        with open(path, 'r') as in_f:
            buf = in_f.read()
        self.history = buf.split('\n')

#END
