.. _sec-plugins-RC:

RC
==

The RC (Remote Control) plugin provides a way to control Ginga remotely
through the use of an XML-RPC interface.  Start the plugin from the
`Plugins` menu (invoke "Start RC") or launch ginga with the "--modules=RC"
command line option to start it automatically.

By default, the plugin starts up with server running on port 9000 bound
to the localhost interface--this allows connections only from the local
host.  If you want to change this, set the host and port in the `Set
Addr` control and press Enter--you should see the address update in the
"Addr:" display field.

Please note that the host part (before the colon) does not indicate
*which* host you want to allow access from, but to which interface to
bind.  If you want to allow any host to connect, leave it blank (but
include the colon and port number) to allow the server to bind on all
interfaces. Press `Restart` to then restart the server at the new
address.

Once the plugin is started, you can use the `ggrc` script (included when
ginga is installed) to control Ginga.  Take a look at the script if you
want to see how to write your own programmatic interface.

Show example usage::

    $ ggrc help

Show help for a specific ginga method::

    $ ggrc help ginga <method>

Show help for a specific channel method::

    $ ggrc help channel <chname> <method>

Ginga (viewer shell) methods can be called like this::

    $ ggrc ginga <method> <arg1> <arg2> ...

Per-channel methods can be called like this::

    $ ggrc channel <chname> <method> <arg1> <arg2> ...

Calls can be made from a remote host by adding the options::

    --host=<hostname> --port=9000

(in the plugin GUI be sure to remove the 'localhost' prefix
from the addr, but leave the colon and port)

Examples

Create a new channel::

    $ ggrc ginga add_channel FOO

Load a file::

    $ ggrc ginga load_file /home/eric/testdata/SPCAM/SUPA01118797.fits

Load a file into a specific channel::

    $ ggrc ginga load_file /home/eric/testdata/SPCAM/SUPA01118797.fits FOO

Cut levels::

    $ ggrc channel FOO cut_levels 163 1300

Auto cut levels::

    $ ggrc channel FOO auto_levels

Zoom to a specific level::

    $ ggrc -- channel FOO zoom_to -7

(note the use of -- to allow us to pass a parameter beginning with "-").

Zoom to fit::

    $ ggrc channel FOO zoom_fit

Transform (args are boolean triplet: flipx flipy swapxy)::

    $ ggrc channel FOO transform 1 0 1

Rotate::

    $ ggrc channel FOO rotate 37.5

Change color map::

    $ ggrc channel FOO set_color_map rainbow3

Change color distribution algorithm::

    $ ggrc channel FOO set_color_algorithm log

Change intensity map::

    $ ggrc channel FOO set_intensity_map neg

In some cases, you may need to resort to shell escapes to be able to
pass certain characters to Ginga.  For example, a leading dash character is
usually interpreted as a program option.  In order to pass a signed
integer you may need to do something like::

    $ ggrc -- channel FOO zoom -7


Interfacing from within Python
------------------------------

It is also possible to control Ginga in RC mode
from within Python.   The following describes
some of the functionality.

Connecting
^^^^^^^^^^

One first launches Ginga and starts the RC plugin.
This can be done from the command line::

    ginga --modules=RC

From within Python, connect with a RemoteClient object as
follows::

    from ginga.util import grc
    host='localhost'
    port=9000
    viewer = grc.RemoteClient(host, port)

This viewer object is now linked to the Ginga using RC.

Load an Image
^^^^^^^^^^^^^

One can load an image from memory in a channel of
one's choosing.  First connect to a Channel::

    ch = viewer.channel('Image')

Then load a numpy image (i.e. any 2D ndarray)::

    img = np.random.rand(500, 500) * 10000.0
    ch.load_np('Image_Name', img, 'fits', {})

The image will display in Ginga and can be manipulated
as usual.

Overlay a Canvas Object
^^^^^^^^^^^^^^^^^^^^^^^

It is possible to add objects to the Canvas in a given
Channel.  First connect::

    canvas = viewer.canvas('Image')

This connects to the Channel named "Image".  One can
clear the objects drawn in the Canvas::

    canvas.clear()

Or add any basic Canvas object.  The key issue to keep in
mind is that the objects input must pass through the XMLRC
protocol.  This means simple data types:  float, int, lists, str.
No arrays.  Here is an example to plot a line through a series
of points defined by two Numpy arrays::

    x = np.arange(100)
    y = np.sqrt(x)
    points = list(zip(x.tolist(), y.tolist()))
    canvas.add('path', points, color='red')

This will draw a red line on the image.
