# Uses Voki Codder's solution
# http://vokicodder.blogspot.in/2011/02/numpy-arrays-to-video.html

import subprocess

class VideoSink(object):

    def __init__(self, size, filename="output", rate=2, byteorder="Y8"):
        self.size = size
        self.cmdstring = ('mencoder', '/dev/stdin', '-demuxer', 'rawvideo',
                     '-rawvideo', 'w=%i:h=%i' % size[::-1] + ":fps=%i:format=%s" % (rate, byteorder),
                     '-o', filename, '-ovc', 'lavc')

    def open(self):
        self.p = subprocess.Popen(self.cmdstring, stdin=subprocess.PIPE, shell=False)

    def write(self, image):
        assert image.shape == self.size
        self.p.stdin.write(image.tostring())

    def close(self):
        self.p.stdin.close()
