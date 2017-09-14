"""
Test program for trying widgets in the different wrapped toolkits supported
by Ginga.

Usage:
  $ python widgets.py <toolkit-name> <widget-name> [logging options]

Examples:
  $ python widgets.py qt5 gridbox
  $ python widgets.py gtk3 label
  $ python widgets.py pg button

Note that for pg widgets it will print the URL of the web address where
the app is running to the logger, so you need to add some logging options
so that you can find out where to point your web browser.
"""

import sys
from ginga.misc import log
import ginga.toolkit as ginga_toolkit

# decide our toolkit, then import
tkit = sys.argv[1]
wname = sys.argv[2]

ginga_toolkit.use(tkit)
from ginga.gw import Widgets, Viewers, GwHelp

top = None
def quit(*args):
    if top is not None:
        top.delete()
    sys.exit()

def popup_dialog(parent):
    dia = Widgets.Dialog(title="Dialog Title",
                         buttons=[('ok', 0), ('cancel', 1)],
                         parent=parent, modal=True)
    cntr = dia.get_content_area()
    cntr.add_widget(Widgets.Label("My Dialog Content"))
    dia.show()

logger = log.get_logger('test', log_stderr=True, level=20)

app = Widgets.Application(logger=logger)
app.add_callback('shutdown', quit)
top = app.make_window("Ginga example2")
top.add_callback('close', quit)

vbox = Widgets.VBox()
vbox.set_border_width(2)
vbox.set_spacing(1)

dia = None

if wname == 'label':
    w = Widgets.Label("Hello World label")
    vbox.add_widget(w, stretch=1)

elif wname == 'button':
    w = Widgets.Button("Press me")
    w.add_callback('activated', lambda w: popup_dialog(top))
    vbox.add_widget(w, stretch=1)

elif wname == 'textentry':
    w = Widgets.TextEntry()
    w.set_text("Hello, World!")
    vbox.add_widget(w, stretch=1)

elif wname == 'textarea':
    w = Widgets.TextArea(editable=True)
    w.set_text("Hello, World!")
    vbox.add_widget(w, stretch=1)

elif wname == 'checkbox':
    w = Widgets.CheckBox("Check me")
    vbox.add_widget(w, stretch=1)

elif wname == 'radiobutton':
    w = Widgets.RadioButton("Check me")
    vbox.add_widget(w, stretch=1)

elif wname == 'tabwidget':
    w = Widgets.TabWidget()
    w.add_widget(Widgets.Label('Content of Tab 1'), title='Tab 1')
    w.add_widget(Widgets.Label('Content of Tab 2'), title='Tab 2')
    vbox.add_widget(w, stretch=1)

elif wname == 'stackwidget':
    w = Widgets.StackWidget()
    w.add_widget(Widgets.Label('Content of Stack 1'))
    w.add_widget(Widgets.Label('Content of Stack 2'))
    vbox.add_widget(w, stretch=1)

elif wname == 'mdiwidget':
    w = Widgets.MDIWidget()
    w.add_widget(Widgets.Label('Content of MDI Area 1'))
    w.add_widget(Widgets.Label('Content of MDI Area 2'))
    vbox.add_widget(w, stretch=1)

elif wname == 'gridbox':
    w = Widgets.GridBox(rows=2, columns=2)
    w.add_widget(Widgets.Label('Content of Grid Area 1'), 0, 0)
    w.add_widget(Widgets.Label('Content of Grid Area 2'), 0, 1)
    w.add_widget(Widgets.Label('Content of Grid Area 3'), 1, 0)
    w.add_widget(Widgets.Label('Content of Grid Area 4'), 1, 1)
    vbox.add_widget(w, stretch=1)

elif wname == 'dialog':
    dia = Widgets.Dialog(title="Dialog Title",
                         buttons=[('ok', 0), ('cancel', 1)],
                         parent=top, modal=True)
    cntr = dia.get_content_area()
    cntr.add_widget(Widgets.Label("My Dialog Content"))

    # add some content to main app widget
    w = Widgets.Label("Hello World label")
    vbox.add_widget(w, stretch=1)

else:
    # default to label
    logger.error("Don't understand kind of widget '%s'" % (wname))
    w = Widgets.Label("Hello World label")
    vbox.add_widget(w, stretch=1)

top.set_widget(vbox)

top.show()
top.raise_()

if dia is not None:
    dia.show()

try:
    app.mainloop()

except KeyboardInterrupt:
    print("Terminating viewer...")
    if top is not None:
        top.close()
