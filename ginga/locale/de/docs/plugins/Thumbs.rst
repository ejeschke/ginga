
Das Plugin ``Thumbs`` bietet einen Miniaturbild-Index aller seit dem
Programmstart betrachteten Bilder.

**Plugin-Typ: Global**

``Thumbs`` ist ein globales Plugin.  Es kann nur eine Instanz geöffnet werden.

**Verwendung**

Standardmäßig erscheinen die ``Thumbs`` in chronologischer Betrachtungshistorie,
mit den neuesten Bildern unten und den ältesten oben.  Die Sortierung kann durch
eine Einstellung in der Konfigurationsdatei „plugin_Thumbs.cfg“ alphanumerisch
gemacht werden.

Ein Klick auf ein Miniaturbild navigiert Sie direkt zu diesem Bild im
zugehörigen Kanal.  Das Bewegen des Cursors über ein Miniaturbild zeigt einen
Tooltip, der ein paar nützliche Metadaten aus dem Bild enthält.

Ist das Kontrollkästchen „Auto-Scrollen“ aktiviert, bewirkt es, dass der
``Thumbs``-Bereich zum aktiven Bild scrollt.

Dieses Plugin ist normalerweise nicht als schließbar konfiguriert, doch der
Benutzer kann dies erreichen, indem er in der Konfigurationsdatei die
Einstellung „closeable“ auf True setzt -- dann werden am unteren Rand der
Benutzeroberfläche die Schaltflächen „Schließen“ und „Hilfe“ hinzugefügt.

**Bilder aus Thumbs ausschließen**

.. note:: Dies steuert auch das Verhalten von ``Contents``.

Obwohl das Standardverhalten so ist, dass jedes in den Referenzbetrachter
geladene Bild in ``Thumbs`` erscheint, kann es Fälle geben, in denen dies
unerwünscht ist (z. B. wenn viele Bilder in einem periodischen Takt von einem
automatisierten Prozess geladen werden).  In solchen Fällen gibt es zwei
Mechanismen, um bestimmte Bilder davon abzuhalten, in ``Thumbs`` zu erscheinen:

* Das Setzen der Einstellung „genthumb“ auf False in den Einstellungen eines
  Kanals (z. B. über das Plugin ``Preferences``, unter den „General“-
  Einstellungen) schließt den Kanal selbst und alle seine Bilder aus.
* Das Setzen des Schlüsselworts „nothumb“ in den Metadaten eines Bild-Wrappers
  (nicht im FITS-Header, sondern z. B. über ``image.set(nothumb=True)``)
  schließt dieses bestimmte Bild aus ``Thumbs`` aus, selbst wenn die Einstellung
  „genthumb“ für diesen Kanal True ist.

Es ist über ``~/.ginga/plugin_Thumbs.cfg`` anpassbar, wobei ``~`` Ihr
HOME-Verzeichnis ist:

.. code-block:: Python

  #
  # Thumbs plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_Thumbs.cfg"

  # If you revisit the same directories frequently
  # caching thumbs saves a lot of time when they need to be regenerated
  cache_thumbs = False

  # cache location-- "local" puts them in a .thumbs subfolder, otherwise
  # they are cached in ~/.ginga/thumbs
  cache_location = 'local'

  # Scroll the pane automatically when new thumbnails arrive
  auto_scroll = True

  # Keywords to extract and show if we mouse over the thumbnail
  tt_keywords = ['OBJECT', 'FRAMEID', 'UT', 'DATE-OBS']

  # Mandatory unique image identifier in tooltip
  mouseover_name_key = 'NAME'

  # How many seconds to wait after an image is altered to begin trying
  # to rebuild a matching thumb.  Usually a few seconds is good in case
  # there is ongoing adjustment of the image
  rebuild_wait = 0.5

  # Max length of thumb on the long side
  thumb_length = 180

  # Separation between thumbs in pixels
  thumb_hsep = 15
  thumb_vsep = 15

  # Sort the thumbs alphabetically: 'alpha' or None
  sort_order = None

  # Thumbnail label length in num of characters (None = no limit)
  label_length = 25

  # Cut off long label ('left', 'right', or None)
  label_cutoff = 'right'

  # Option to highlight images that are displayed in channels.
  # If set to True this option will only highlight the image that is in the
  # channel with the keyboard focus
  highlight_tracks_keyboard_focus = True

  # Highlighted label colors
  label_bg_color = 'lightgreen'
  label_font_color = 'white'

  label_font_size = 10

  # Load visible thumbs in the background to replace placeholder icons
  autoload_visible_thumbs = True

  # Length of time to wait after scrolling to begin autoloading
  autoload_interval = 1.0

  # list of attributes to transfer from the channel viewer to the
  # thumbnail generator if the channel has an image in it
  transfer_attrs = ['transforms', 'cutlevels', 'rgbmap']

  # Add a close button to this plugin, so that it can be stopped
  closeable = False
