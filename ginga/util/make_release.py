from __future__ import print_function
import os
import time

major = 2
minor = 5

rlfile = 'version.py'
backup = 'version.py.bak'

def make_release():
    release = time.strftime("%Y%m%d%H%M%S", time.gmtime(time.time()))
    release = int(release)

    if os.path.exists(backup):
        os.remove(backup)

    if os.path.exists(rlfile):
        os.rename(rlfile, backup)

    with open(rlfile, 'w') as out_f:
        out_f.write("# this file was automatically generated\n")
        out_f.write("major = %d\n" % major)
        out_f.write("minor = %d\n" % minor)
        out_f.write("release = %d\n" % release)
        out_f.write("\n")
        out_f.write("version = '%d.%d.%d' % (major, minor, release)\n")
        out_f.write("\n")

if __name__ == "__main__":
    print(make_release())
