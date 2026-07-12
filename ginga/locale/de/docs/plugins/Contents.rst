
Das Plugin ``Contents`` bietet eine inhaltsverzeichnisartige Oberfläche für alle
seit dem Programmstart betrachteten Bilder.  Anders als ``Thumbs`` ist
``Contents`` nach Kanal sortiert.  Der Inhalt zeigt außerdem einige
konfigurierbare Metadaten aus dem Bild an.

**Plugin-Typ: Global**

``Contents`` ist ein globales Plugin.  Es kann nur eine Instanz geöffnet werden.

**Verwendung**

Klicken Sie auf eine Spaltenüberschrift, um die Tabelle nach dieser Spalte zu
sortieren; klicken Sie erneut, um in die andere Richtung zu sortieren.

.. note:: Die Spalten und ihre Werte werden gegebenenfalls aus dem FITS-Header
          bezogen.  Dies kann durch Setzen des Parameters „columns“ in der
          Einstellungsdatei „plugin_Contents.cfg“ angepasst werden.

Das aktive Bild im aktuell fokussierten Kanal wird normalerweise hervorgehoben.
Ein Doppelklick auf ein Bild erzwingt, dass dieses Bild im zugehörigen Kanal
angezeigt wird.  Ein einfacher Klick auf ein beliebiges Bild aktiviert die
Schaltflächen am unteren Rand der Benutzeroberfläche:

* „Anzeigen“: Macht das Bild zum aktiven Bild.
* „Verschieben“: Verschiebt das Bild in einen anderen Kanal.
* „Kopieren“: Kopiert das Bild in einen anderen Kanal.
* „Entfernen“: Entfernt das Bild aus dem Kanal.

Wird „Verschieben“ oder „Kopieren“ bei einem Bild ausgeführt, das in Ginga
verändert wurde (was einen Eintrag unter ``ChangeHistory`` hätte, falls
verwendet), bleibt auch die Änderungshistorie erhalten.  Das Entfernen eines
Bildes aus einem Kanal verwirft alle nicht gespeicherten Änderungen.

Dieses Plugin ist normalerweise nicht als schließbar konfiguriert, doch der
Benutzer kann dies erreichen, indem er in der Konfigurationsdatei die
Einstellung „closeable“ auf True setzt -- dann werden am unteren Rand der
Benutzeroberfläche die Schaltflächen „Schließen“ und „Hilfe“ hinzugefügt.

**Bilder aus Contents ausschließen**

.. note:: Dies steuert auch das Verhalten von ``Thumbs``.

Obwohl das Standardverhalten so ist, dass jedes in den Referenzbetrachter
geladene Bild in ``Contents`` erscheint, kann es Fälle geben, in denen dies
unerwünscht ist (z. B. wenn viele Bilder in einem periodischen Takt von einem
automatisierten Prozess geladen werden).  In solchen Fällen gibt es zwei
Mechanismen, um bestimmte Bilder davon abzuhalten, in ``Contents`` zu
erscheinen:

* Das Setzen der Einstellung „genthumb“ auf False in den Einstellungen eines
  Kanals (z. B. über das Plugin ``Preferences``, unter den „General“-
  Einstellungen) schließt den Kanal selbst und alle seine Bilder aus.
* Das Setzen des Schlüsselworts „nothumb“ in den Metadaten eines Bild-Wrappers
  (nicht im FITS-Header, sondern z. B. über ``image.set(nothumb=True)``)
  schließt dieses bestimmte Bild aus ``Contents`` aus, selbst wenn die
  Einstellung „genthumb“ für diesen Kanal True ist.

Es ist über ``~/.ginga/plugin_Contents.cfg`` anpassbar, wobei ``~`` Ihr
HOME-Verzeichnis ist:

.. code-block:: Python

  #
  # Contents plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_Contents.cfg"

  # columns to show from metadata -- NAME and MODIFIED recommended
  # format: [(col header, keyword1), ... ]
  columns = [ ('Name', 'NAME'), ('Object', 'OBJECT'), ('Filter', 'FILTER01'), ('Date', 'DATE-OBS'), ('Time UT', 'UT'), ('Modified', 'MODIFIED')]

  # If set to True, will always expand the tree in Contents when new entries are added
  always_expand = True

  # Option to highlight images that are displayed in channels.
  # If set to True this option will only highlight the image that is in the
  # channel with the keyboard focus
  highlight_tracks_keyboard_focus = False

  # If True, color every other row in alternating shades to improve
  # readability of long tables
  color_alternate_rows = True

  # Highlighted row colors (in addition to bold text)
  row_font_color = 'green'

  # Maximum number of rows that will turn off auto column resizing (for speed)
  max_rows_for_col_resize = 100

  # Add a close button to this plugin, so that it can be stopped
  closeable = False
