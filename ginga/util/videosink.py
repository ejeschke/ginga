# Uses Voki Codder's solution
# http://vokicodder.blogspot.in/2011/02/numpy-arrays-to-video.html

import subprocess

class VideoSink(object):

    def __init__(self, size, filename="output", rate=2, byteorder="Y8"):
        self.size = size
        cmdstring = ('mencoder', '/dev/stdin', '-demuxer', 'rawvideo',
                     '-rawvideo', 'w=%i:h=%i' % size[::-1] + ":fps=%i:format=%s" % (rate, byteorder),
                     '-o', filename+'.avi', '-ovc', 'lavc')
        self.p = subprocess.Popen(cmdstring, stdin=subprocess.PIPE, shell=False)

    def run(self, image):
        assert image.shape == self.size
        self.p.stdin.write(image.tostring())

    def close(self):
        self.p.stdin.close()
