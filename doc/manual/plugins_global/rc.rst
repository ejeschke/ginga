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

Once the plugin is started, you can use the `grc` script (included when
ginga is installed) to control Ginga.  Take a look at the script if you
want to see how to write your own programmatic interface.

Show example usage::

    $ grc help

Show help for a specific ginga method::

    $ grc help ginga <method>

Show help for a specific channel method::

    $ grc help channel <chname> <method>

Ginga (viewer shell) methods can be called like this::

    $ grc ginga <method> <arg1> <arg2> ...

Per-channel methods can be called like this::

    $ grc channel <chname> <method> <arg1> <arg2> ...

Calls can be made from a remote host by adding the options::

    --host=<hostname> --port=9000

(in the plugin GUI be sure to remove the 'localhost' prefix
from the addr, but leave the colon and port)

Examples

Create a new channel::

    $ grc ginga add_channel FOO

Load a file::

    $ grc ginga load_file /home/eric/testdata/SPCAM/SUPA01118797.fits

Load a file into a specific channel::

    $ grc ginga load_file /home/eric/testdata/SPCAM/SUPA01118797.fits FOO

Cut levels::

    $ grc channel FOO cut_levels 163 1300

Auto cut levels::

    $ grc channel FOO auto_levels

Zoom to a specific level::

    $ grc -- channel FOO zoom_to -7

(note the use of -- to allow us to pass a parameter beginning with "-").

Zoom to fit::

    $ grc channel FOO zoom_fit

Transform (args are boolean triplet: flipx flipy swapxy)::

    $ grc channel FOO transform 1 0 1

Rotate::

    $ grc channel FOO rotate 37.5

Change color map::

    $ grc channel FOO set_color_map rainbow3

Change color distribution algorithm::

    $ grc channel FOO set_color_algorithm log

Change intensity map::

    $ grc channel FOO set_intensity_map neg

In some cases, you may need to resort to shell escapes to be able to
pass certain characters to Ginga.  For example, a leading dash character is
usually interpreted as a program option.  In order to pass a signed
integer you may need to do something like::

    $ grc -- channel FOO zoom -7
