"""
Test program for trying widgets in the different wrapped toolkits supported
by Ginga.

Usage:
  $ python widgets.py <toolkit-name> [logging options]

Examples:
  $ python widgets.py -t qt5
  $ python widgets.py -t gtk3
  $ python widgets.py -t pg
"""
import sys
import os

from ginga.misc import log
from ginga.util.paths import icondir  # noqa

top = None


def quit(*args):
    if top is not None:
        top.delete()
    sys.exit()


def popup_dialog(parent):
    from ginga.gw import Widgets
    dia = Widgets.Dialog(title="Dialog Title",
                         buttons=[('ok', 0), ('cancel', 1)],
                         parent=parent, modal=True)
    cntr = dia.get_content_area()
    cntr.add_widget(Widgets.Label("My Dialog Content"))
    parent.add_dialog(dia)
    dia.show()


def button_test(w):
    if w.get_text().lower() == 'foo':
        w.set_text('bar')
    else:
        w.set_text('foo')


def setting_limits(textentry, spinbox):
    limits = textentry.get_text().split(",")
    spinbox.set_limits(float(limits[0]), float(limits[1]), float(limits[2]))


def grid_helper(textentry, gridbox):
    from ginga.gw import Widgets
    indices = textentry.get_text().split(",")
    gridbox.add_widget(Widgets.Label("Added widget"), int(indices[0]), int(indices[1]))


def show_example(cbox, top, logger):
    from ginga.gw import Widgets
    wname = cbox.get_text()
    vbox = Widgets.VBox()
    vbox.set_border_width(2)
    vbox.set_spacing(1)

    if wname == 'label':
        _vbox = Widgets.VBox()
        label = Widgets.Label("Hello World label")
        label.set_color('white', 'blue')
        label.set_font("Times New Roman")
        _vbox.add_widget(label, stretch=1)
        # Allow user to select different font
        fontbox = Widgets.ComboBox()
        _vbox.add_widget(fontbox, stretch=0)
        for name in ["Times New Roman", "Arial", "Courier"]:
            fontbox.append_text(name)
        fontbox.add_callback('activated', lambda r, val: label.set_font(r.get_text()))
        fontbox.add_callback('activated',
                             lambda w, val: logger.info("chose '{}'".format(w.get_text())))
        # ...FOR HALIGN...
        alignbox = Widgets.ComboBox()
        _vbox.add_widget(alignbox, stretch=0)
        for name in ["Left", "Center", "Right"]:
            alignbox.append_text(name)
        alignbox.add_callback('activated', lambda r, val: label.set_halign(r.get_text()))
        alignbox.add_callback('activated',
                              lambda w, val: logger.info("chose '{}'".format(w.get_text())))
        label.set_halign('Left')
        vbox.add_widget(_vbox)

    elif wname == 'button':
        w = Widgets.Button("Press me")
        w.add_callback('activated', lambda w: logger.info("button was clicked"))
        w.add_callback('activated', button_test)
        #w.add_callback('activated', lambda w: popup_dialog(top))
        vbox.add_widget(w, stretch=1)

    elif wname == 'textentry':
        _vbox = Widgets.VBox()
        # Read only text entry
        w2 = Widgets.TextEntry("Read only", editable=False)
        _vbox.add_widget(w2, stretch=1)
        # Regular text entry
        w = Widgets.TextEntry("Hello, World!")
        w.set_font("Times New Roman")
        w.add_callback('activated',
                       lambda w: logger.info("said '{}'".format(w.get_text())))
        w.add_callback('activated', lambda r: w.set_text(r.get_text()))
        _vbox.add_widget(w, stretch=1)
        # Allow user to select different font
        fontbox = Widgets.ComboBox()
        _vbox.add_widget(fontbox, stretch=0)
        for name in ["Times New Roman", "Helvetica", "Courier"]:
            fontbox.append_text(name)
        fontbox.add_callback('activated', lambda r, val: w.set_font(r.get_text()))
        # Set length
        hbox = Widgets.HBox()
        label = Widgets.Label("Set length: ")
        enter_limit = Widgets.TextEntrySet()
        enter_limit.add_callback('activated', lambda r: w.set_length(int(enter_limit.get_text())))
        hbox.add_widget(label)
        hbox.add_widget(enter_limit)
        _vbox.add_widget(hbox, stretch=0)

        vbox.add_widget(_vbox, stretch=1)

    elif wname == 'textentryset':
        _vbox = Widgets.VBox()
        # Read only text entry
        w2 = Widgets.TextEntrySet("Read only", editable=False)
        _vbox.add_widget(w2, stretch=1)
        # Editable text entry
        w = Widgets.TextEntrySet()
        w.set_text("This text entry fits 35 characters!")
        w.set_length(35)
        w.set_font("Georgia")
        w.add_callback('activated',
                       lambda w: logger.info("said '{}'".format(w.get_text())))
        _vbox.add_widget(w, stretch=1)
        vbox.add_widget(_vbox, stretch=1)

    elif wname == 'textarea':
        _vbox = Widgets.VBox()
        # Read only text area
        w2 = Widgets.TextArea(editable=False)
        w2.set_text("READ ONLY")
        _vbox.add_widget(w2, stretch=1)
        # Editable text area
        w = Widgets.TextArea(editable=True)
        w.set_text("Hello, World!")
        w.set_wrap(False)
        _vbox.add_widget(w, stretch=1)
        # Set wrap
        b2 = Widgets.ToggleButton("Toggle wrap on/off")
        b2.add_callback('activated', lambda r, val: w.set_wrap(b2.get_state()))
        _vbox.add_widget(b2)
        # Clear text
        b = Widgets.Button("Clear")
        b.add_callback('activated', lambda r: w.clear())
        _vbox.add_widget(b)
        # Select font
        fontbox = Widgets.ComboBox()
        w.set_font("Arial")
        for name in ["Times New Roman", "Helvetica", "Courier"]:
            fontbox.append_text(name)
        fontbox.add_callback('activated', lambda r, val: w.set_font(r.get_text()))
        _vbox.add_widget(fontbox, stretch=0)

        vbox.add_widget(_vbox)

    elif wname == 'checkbox':
        w = Widgets.CheckBox("Check me")
        w.set_state(True)
        w.add_callback('activated',
                       lambda w, val: logger.info("value changed to '{}'".format(w.get_state())))
        vbox.add_widget(w, stretch=1)

    elif wname == 'dial':
        w = Widgets.Dial()
        w.set_limits(-20, 20, incr_value=1)
        w.add_callback('value-changed',
                       lambda w, val: logger.info("value changed to '{}'".format(w.get_value())))
        vbox.add_widget(w)

    elif wname == 'togglebutton':
        w = Widgets.ToggleButton("Toggle me")
        w.set_state(True)
        w.add_callback('activated',
                       lambda w, val: logger.info("value changed to '{}'".format(w.get_state())))
        vbox.add_widget(w, stretch=1)

    elif wname == 'radiobutton':
        w = Widgets.RadioButton("Option 1")
        w.add_callback('activated',
                       lambda w, val: logger.info("chose option 1"))
        vbox.add_widget(w)
        w2 = Widgets.RadioButton("Option 2", group=w)
        w2.add_callback('activated',
                        lambda w, val: logger.info("chose option 2"))
        vbox.add_widget(w2)
        w3 = Widgets.RadioButton("Option 3", group=w)
        w3.set_state(True)
        w3.add_callback('activated',
                        lambda w, val: logger.info("chose option 3"))
        vbox.add_widget(w3)

    elif wname == 'combobox':
        w = Widgets.ComboBox()
        for name in ["Larry", "Curly", "Moe"]:
            w.append_text(name)
        w.add_callback('activated',
                       lambda w, val: logger.info("chose '{}'".format(w.get_text())))
        vbox.add_widget(w, stretch=0)
        # Test insert_alpha
        hbox1 = Widgets.HBox()
        label1 = Widgets.Label("Add Choice: ")
        insert = Widgets.TextEntrySet()
        insert.add_callback('activated', lambda r: w.insert_alpha(r.get_text()))
        hbox1.add_widget(label1, stretch=0)
        hbox1.add_widget(insert, stretch=0)
        vbox.add_widget(hbox1, stretch=0)
        # Test delete_alpha
        hbox2 = Widgets.HBox()
        label2 = Widgets.Label("Delete choice: ")
        delete = Widgets.TextEntrySet()
        delete.add_callback('activated', lambda r: w.delete_alpha(r.get_text()))
        hbox2.add_widget(label2, stretch=0)
        hbox2.add_widget(delete, stretch=0)
        vbox.add_widget(hbox2, stretch=0)
        # Test clear method
        clearbutton = Widgets.Button("Clear choices")
        clearbutton.add_callback('activated', lambda r: w.clear())
        vbox.add_widget(clearbutton, stretch=0)

    elif wname == 'spinbox':
        w = Widgets.SpinBox(dtype=float)
        w.set_limits(-10, 10, incr_value=0.1)
        w.set_value(5.5)
        # Displaying changing value
        w.add_callback('value-changed',
                       lambda w, val: logger.info("chose {}".format(val)))
        vbox.add_widget(w)
        value_label = Widgets.Label("Value: {}".format(w.get_value()))
        w.add_callback('value-changed', lambda r, val: value_label.set_text("Value: {}".format(val)))
        vbox.add_widget(value_label, stretch=1)
        # Test set_limits dynamically
        limits_label = Widgets.Label("Set limits (min, max, incr): ")
        change_limits = Widgets.TextEntrySet()
        hbox = Widgets.HBox()
        hbox.add_widget(limits_label, stretch=1)
        hbox.add_widget(change_limits, stretch=1)
        change_limits.add_callback('activated', lambda r: setting_limits(r, w))
        vbox.add_widget(hbox, stretch=1)

    elif wname == 'slider':
        _vbox = Widgets.VBox()
        w = Widgets.Slider(orientation='horizontal')
        w.set_limits(0, 5, incr_value=1)
        w.set_value(4)
        w.set_tracking(True)
        w.add_callback('value-changed',
                       lambda w, val: logger.info("chose {}".format(val)))
        _vbox.add_widget(w)
        # Display current value
        value_label = Widgets.Label("Value: {}".format(w.get_value()))
        w.add_callback('value-changed', lambda r, val: value_label.set_text("Value: {}".format(val)))
        _vbox.add_widget(value_label)
        # Test set_tracking
        b = Widgets.Button("Tracking on/off")
        b.add_callback('activated', lambda r: w.set_tracking(not(w.track)))
        _vbox.add_widget(b)
        # Test set_value dynamically
        hbox = Widgets.HBox()
        set_label = Widgets.Label("Set value: ")
        change_val = Widgets.TextEntrySet()
        change_val.add_callback('activated', lambda r: w.set_value(int(r.get_text())))
        hbox.add_widget(set_label)
        hbox.add_widget(change_val, stretch=1)
        _vbox.add_widget(hbox, stretch=1)
        # Test set_limits dynamically
        hbox2 = Widgets.HBox()
        limits_label = Widgets.Label("Set limits (min, max, incr): ")
        change_limits = Widgets.TextEntrySet()
        hbox2.add_widget(limits_label)
        hbox2.add_widget(change_limits)
        change_limits.add_callback('activated', lambda r: setting_limits(r, w))
        _vbox.add_widget(hbox2, stretch=1)
        vbox.add_widget(_vbox)

    elif wname == 'scrollbar':
        _vbox = Widgets.VBox()
        w = Widgets.ScrollBar(orientation='horizontal')
        _vbox.add_widget(w, stretch=0)
        _ent = Widgets.TextEntrySet()
        _vbox.add_widget(_ent, stretch=0)
        _ent.add_callback('activated', lambda r: w.set_value(float(r.get_text())))
        w.set_value(0.40)
        w.add_callback('activated', lambda w, val: logger.info("value is %.2f" % val))
        vbox.add_widget(_vbox)

    elif wname == 'progressbar':
        _vbox = Widgets.VBox()
        w = Widgets.ProgressBar()
        _vbox.add_widget(w, stretch=0)
        _ent = Widgets.TextEntrySet()
        _vbox.add_widget(_ent, stretch=0)
        _ent.add_callback('activated', lambda r: w.set_value(float(r.get_text())))
        w.set_value(0.6)
        vbox.add_widget(_vbox)

    elif wname == 'statusbar':
        w = Widgets.StatusBar()
        w.set_message("Hello, World! is my status")
        vbox.add_widget(w)

    elif wname == 'image':
        w = Widgets.Image()
        w.load_file(os.path.join(icondir, 'ginga-512x512.png'))
        vbox.add_widget(w)

    elif wname == 'treeview':
        w = Widgets.TreeView(selection='single', sortable=True,
                             use_alt_row_color=True)
        columns = [("Meal", 'meal'), ("Critic 1", 'review1'),
                   ("Critic 2", 'review2'), ("Critic 3", 'review3')]
        w.setup_table(columns, 1, 'meal')
        tree = dict(Breakfast=dict(meal='Breakfast', review1="Delish!",
                                   review2="Ugh!", review3="Meh"),
                    Lunch=dict(meal='Lunch', review1="Gross!",
                               review2="Interesting...", review3="Meh"),
                    Supper=dict(meal='Supper', review1="Meh",
                                review2="Meh", review3="Jolly good!"))
        w.set_tree(tree)
        vbox.add_widget(w, stretch=1)

    elif wname == 'webview':
        w = Widgets.WebView()
        w.load_url("http://www.google.com/")
        vbox.add_widget(w)

    elif wname == 'frame':
        w = Widgets.Frame(title="Frame Title")
        slider = Widgets.Slider(orientation='horizontal')
        slider.set_limits(-10, 10, incr_value=1)
        w.set_widget(slider)
        vbox.add_widget(w)
        # Test set_widget
        button = Widgets.Button("Press me to set to another widget!")
        button.add_callback('activated', lambda r: w.set_widget(Widgets.TextArea(editable=True)))
        # Test set_text to change header inside frame widget
        change_text = Widgets.TextEntrySet("Change text")
        change_text.add_callback('activated', lambda r: w.set_text(r.get_text()))
        vbox.add_widget(change_text)
        vbox.add_widget(button)

    elif wname == 'expander':
        w = Widgets.Expander(title="Expander Title")
        layout = Widgets.VBox()
        layout.add_widget(Widgets.Label("Expander content"))
        layout.add_widget(Widgets.Button("Button"))
        w.set_widget(layout)
        # Testing set_widget
        button = Widgets.Button("Click to test set_widget")
        button.add_callback('activated', lambda r: w.set_widget(Widgets.Label("Set widget")))
        vbox.add_widget(button)
        vbox.add_widget(w)

    elif wname == 'hbox':
        w = Widgets.HBox()
        w.add_widget(Widgets.Label("Item 1"), stretch=1)
        w.add_widget(Widgets.Label("Item 2"), stretch=1)
        # Test add_widget
        grid = Widgets.GridBox(rows=2, columns=1)
        button = Widgets.Button("Click to add widget")
        button.add_callback('activated', lambda r: w.add_widget(Widgets.Label("Item 3"), stretch=1))
        grid.add_widget(button, 0, 0)
        # Test insert_widget
        label = Widgets.Label("Enter index to insert a widget: ")
        insert = Widgets.TextEntrySet()
        insert.add_callback('activated', lambda r: w.insert_widget(int(r.get_text()), Widgets.Label("Inserted widget"), stretch=1))
        hbox = Widgets.HBox()
        hbox.add_widget(label)
        hbox.add_widget(insert)
        grid.add_widget(hbox, 1, 0)
        vbox.add_widget(w)
        vbox.add_widget(grid)

    elif wname == 'vbox':
        w = Widgets.VBox()
        w.add_widget(Widgets.Label("Item 1"), stretch=0)
        w.add_widget(Widgets.Label("Item 2"), stretch=1)
        # Test add_widget
        grid = Widgets.GridBox(rows=2, columns=1)
        button = Widgets.Button("Click to add widget")
        button.add_callback('activated', lambda r: w.add_widget(Widgets.Label("Item 3"), stretch=1))
        grid.add_widget(button, 0, 0)
        # Test insert_widget
        label = Widgets.Label("Enter index to insert a widget: ")
        insert = Widgets.TextEntrySet()
        insert.add_callback('activated', lambda r: w.insert_widget(int(r.get_text()), Widgets.Label("Inserted widget"), stretch=1))
        hbox = Widgets.HBox()
        hbox.add_widget(label)
        hbox.add_widget(insert)
        grid.add_widget(hbox, 1, 0)
        vbox.add_widget(w)
        vbox.add_widget(grid)

    elif wname == 'splitter':
        w = Widgets.Splitter(orientation='horizontal')
        w.add_widget(Widgets.Label('Content of Pane 1'))
        w.add_widget(Widgets.TextArea())
        # w.add_widget(Widgets.Slider())
        w.add_widget(Widgets.Button("????"))

        w.set_sizes([10, 20, 20])
        vbox.add_widget(w, stretch=1)

    elif wname == 'scrollarea':
        grid = Widgets.GridBox(rows=2, columns=2)
        # Test scroll_to_end
        b = Widgets.Button("Scroll to bottom")
        b.add_callback('activated', lambda r: w.scroll_to_end())
        grid.add_widget(b, 0, 0)
        b = Widgets.Button("Scroll to right")
        b.add_callback('activated', lambda r: w.scroll_to_end(vertical=False, horizontal=True))
        grid.add_widget(b, 0, 1)
        # Test scroll_to_pct
        vert_pct = Widgets.TextEntrySet()
        vert_pct.add_callback('activated', lambda r: w.scroll_to_pct(int(r.get_text())))
        grid.add_widget(vert_pct, 1, 0)
        hori_pct = Widgets.TextEntrySet()
        hori_pct.add_callback('activated', lambda r: w.scroll_to_pct(int(r.get_text()), vertical=False, horizontal=True))
        grid.add_widget(hori_pct, 1, 1)
        vbox.add_widget(grid)
        # Adding multiple widgets to test scrollarea
        a = Widgets.Label("Hello!")
        s = Widgets.Slider(orientation='horizontal')
        s.set_limits(-10, 10, incr_value=1)
        s.set_value(4)
        s.set_tracking(True)
        w = Widgets.ScrollArea()
        img = Widgets.Image()
        img.load_file(os.path.join(icondir, 'ginga-512x512.png'))
        _vbox = Widgets.VBox()
        _vbox.add_widget(img, stretch=0)
        _vbox.add_widget(a, stretch=0)
        _vbox.add_widget(s, stretch=0)
        w.set_widget(_vbox)
        vbox.add_widget(w, stretch=1)

    elif wname == 'tabwidget':
        w = Widgets.TabWidget()
        w.add_widget(Widgets.Label('Content of Tab 1'), title='Tab 1')
        w.add_widget(Widgets.Label('Content of Tab 2'), title='Tab 2')
        hbox = Widgets.HBox()
        sbox = Widgets.SpinBox(dtype=int)
        sbox.set_limits(0, 1, incr_value=1)
        sbox.set_value(0)
        sbox.add_callback('value-changed', lambda sbx, val: w.set_index(val))
        hbox.add_widget(sbox)
        vbox.add_widget(w, stretch=1)
        vbox.add_widget(hbox, stretch=0)

    elif wname == 'stackwidget':
        w = Widgets.StackWidget()
        w.add_widget(Widgets.TextArea(editable=True))
        w.add_widget(Widgets.Label('Content of Stack 1'))
        # Testing set_index
        hbox = Widgets.HBox()
        label = Widgets.Label("Set index to be visible: ")
        set_index = Widgets.TextEntrySet()
        set_index.add_callback('activated', lambda r: w.set_index(int(r.get_text())))
        hbox.add_widget(label)
        hbox.add_widget(set_index)
        # Testing add_widget
        button2 = Widgets.Button("Press to add another widget")
        button2.add_callback('activated', lambda r: w.add_widget(Widgets.Label("Content of inserted widget")))

        vbox.add_widget(hbox, stretch=0)
        vbox.add_widget(button2, stretch=0)
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
        # Test set row and column spacing methods
        row_button = Widgets.Button("Press to change row spacing to 50px")
        row_button.add_callback('activated', lambda r: w.set_row_spacing(50))
        col_button = Widgets.Button("Press to change column spacing to 50px")
        col_button.add_callback('activated', lambda r: w.set_column_spacing(50))
        both_button = Widgets.Button("Press to change row and column spacing to 20px")
        both_button.add_callback('activated', lambda r: w.set_spacing(20))
        # Test insert_row
        hbox = Widgets.HBox()
        label = Widgets.Label("Enter index to insert a row: ")
        insert_row = Widgets.TextEntrySet()
        insert_row.add_callback('activated', lambda r: w.insert_row(int(r.get_text())))
        hbox.add_widget(label)
        hbox.add_widget(insert_row)
        # Test delete_row
        hbox2 = Widgets.HBox()
        label = Widgets.Label("Enter index to delete a row: ")
        delete_row = Widgets.TextEntrySet()
        delete_row.add_callback('activated', lambda r: w.delete_row(int(r.get_text())))
        hbox2.add_widget(label)
        hbox2.add_widget(delete_row)
        # Test append_row
        append_button = Widgets.Button("Press to append a row")
        append_button.add_callback('activated', lambda r: w.append_row())
        # Test add_widget
        hbox3 = Widgets.HBox()
        label = Widgets.Label("Enter indices to add widget (row,column): ")
        add_widget = Widgets.TextEntrySet()
        add_widget.add_callback('activated', lambda r: grid_helper(r, w))
        hbox3.add_widget(label)
        hbox3.add_widget(add_widget)

        vbox.add_widget(w, stretch=1)
        vbox.add_widget(row_button, stretch=1)
        vbox.add_widget(col_button, stretch=1)
        vbox.add_widget(both_button, stretch=1)
        vbox.add_widget(hbox, stretch=1)
        vbox.add_widget(hbox2, stretch=1)
        vbox.add_widget(hbox3, stretch=1)
        vbox.add_widget(append_button, stretch=1)

    elif wname == 'menubar':
        w = Widgets.Menubar()
        menu = w.add_name('Menu 1')
        menu.add_name('Larry').add_callback('activated',
                                            lambda *args: print("chose Larry"))
        menu.add_name('Curly').add_callback('activated',
                                            lambda *args: logger.info("chose Curly"))
        menu.add_name('Moe').add_callback('activated',
                                          lambda *args: logger.info("chose Moe"))

        menu = w.add_name('3Amigos')
        menu.add_name('Hector').add_callback('activated',
                                             lambda *args: print("chose Hector"))
        menu.add_name('Manuel').add_callback('activated',
                                             lambda *args: logger.info("chose Manuel"))
        menu.add_name('Roberto').add_callback('activated',
                                              lambda *args: logger.info("chose Roberto"))
        vbox.add_widget(w)
        vbox.add_widget(Widgets.Label("App content"), stretch=1)

    elif wname == 'toolbar':
        w = Widgets.Toolbar()
        menu = w.add_menu('Menu Type 1', mtype='tool')
        menu.add_name('Larry').add_callback('activated',
                                            lambda w: logger.info("chose Larry"))
        menu.add_name('Curly').add_callback('activated',
                                            lambda w: logger.info("chose Curly"))
        menu.add_name('Moe').add_callback('activated',
                                          lambda w: logger.info("chose Moe"))
        menu = w.add_menu('Menu Type 2', mtype='mbar')
        menu.add_name('Frank')
        menu.add_name('Dean')
        menu.add_name('Sammy')
        w.add_widget(Widgets.Button('A Button'))
        w.add_separator()
        w.add_action("Toggle me", toggle=True)
        w.add_action(None, iconpath=os.path.join(icondir, 'hand_48.png'))
        vbox.add_widget(w)
        vbox.add_widget(Widgets.Label("App content"), stretch=1)

    elif wname == 'dialog':
        dia = Widgets.Dialog(title="Dialog Title",
                             buttons=[('ok', 0), ('cancel', 1)],
                             parent=top, modal=False)
        dia.add_callback('activated',
                         lambda w, rsp: logger.info("user chose %s" % (rsp)))
        top.add_dialog(dia)
        cntr = dia.get_content_area()
        cntr.add_widget(Widgets.Label("My Dialog Content"))

        # add some content to main app widget
        w = Widgets.Label("Hello World label")
        vbox.add_widget(w, stretch=1)
        hbox = Widgets.HBox()
        w = Widgets.Button("Open Dialog")
        w.add_callback('activated', lambda w: dia.show())
        hbox.add_widget(w)
        w = Widgets.Button("Close Dialog")
        w.add_callback('activated', lambda w: dia.hide())
        hbox.add_widget(w)
        vbox.add_widget(hbox)

    else:
        # default to label
        logger.error("Don't understand kind of widget '%s'" % (wname))
        w = Widgets.Label("Hello World label")
        vbox.add_widget(w, stretch=1)

    dia = Widgets.Dialog(title="Example: " + wname,
                         parent=top, modal=False)
    dia.add_callback('close', lambda *args: dia.delete())
    cntr = dia.get_content_area()
    cntr.add_widget(vbox)
    if hasattr(top, 'add_dialog'):
        top.add_dialog(dia)
    dia.show()


def main(options, args):
    logger = log.get_logger('test', options=options)

    import ginga.toolkit as ginga_toolkit

    ginga_toolkit.use(options.toolkit)

    from ginga.gw import Widgets

    #app = Widgets.Application(host='', logger=logger)
    app = Widgets.Application(logger=logger)
    app.add_callback('shutdown', quit)

    page = None
    if hasattr(app, 'script_imports'):
        app.script_imports.append('jqx')

        top = Widgets.Page(title="Ginga Wrapped Widgets")
        app.add_window(top)
    else:
        top = app.make_window("Ginga Wrapped Widgets")

    top.add_callback('close', quit)

    hbox = Widgets.HBox()
    hbox.set_border_width(2)
    hbox.set_spacing(1)

    cbox = Widgets.ComboBox()
    for wname in ['label', 'button', 'textentry', 'textentryset', 'textarea',
                  'checkbox', 'togglebutton', 'radiobutton', 'combobox',
                  'spinbox', 'slider', 'scrollbar', 'progressbar', 'statusbar',
                  'image', 'treeview', 'webview', 'frame', 'expander',
                  'hbox', 'vbox', 'splitter', 'scrollarea', 'tabwidget',
                  'stackwidget', 'mdiwidget', 'gridbox', 'menubar', 'toolbar',
                  'dialog', 'dial']:
        cbox.insert_alpha(wname)

    hbox.add_widget(cbox)
    btn = Widgets.Button("Show Example")
    btn.add_callback('activated', lambda w: show_example(cbox, top, logger))
    hbox.add_widget(btn)

    top.set_widget(hbox)
    top.show()
    top.raise_()

    try:
        app.mainloop()

    except KeyboardInterrupt:
        print("Terminating viewer...")
        if top is not None:
            top.close()


if __name__ == "__main__":
    # Parse command line options
    from argparse import ArgumentParser

    argprs = ArgumentParser()

    argprs.add_argument("-t", "--toolkit", dest="toolkit", metavar="NAME",
                        default='qt',
                        help="Choose GUI toolkit (gtk|qt|pg)")
    log.addlogopts(argprs)

    (options, args) = argprs.parse_known_args(sys.argv[1:])

    main(options, args)
