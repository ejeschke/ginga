
Plugin zum Erstellen eines Bildmosaiks mit der Collage-Methode.

**Plugin-Typ: Lokal**

``Collage`` ist ein lokales Plugin, das heißt, es ist einem Kanal zugeordnet.
Für jeden Kanal kann eine Instanz geöffnet werden.

**Verwendung**

Dieses Plugin dient dazu, im Kanalbetrachter automatisch eine Mosaik-Collage aus
vom Benutzer bereitgestellten Bildern zu erstellen.  Die Position eines Bildes
auf der Collage wird durch sein WCS ohne Verzeichnungskorrektur bestimmt.  Dies
ist als Schnellansicht-Werkzeug gedacht, nicht als Ersatz für ein
Image-Drizzling, das Bildverzeichnung usw. berücksichtigt.

Die Collage existiert nur als Plot auf der Ginga-Leinwand.  Es wird kein neues
Einzelbild erstellt (wenn Sie das möchten, siehe das Plugin „Mosaic“).  Einige
Plugins, die auf Einzelbildern arbeiten sollen, funktionieren mit einer Collage
möglicherweise nicht korrekt.

Um eine neue Collage zu erstellen, klicken Sie auf die Schaltfläche „Neue
Collage“ und ziehen Sie Dateien auf das Anzeigefenster (z. B. können Dateien aus
dem `FBrowser`-Plugin gezogen werden).  Die Bilder müssen ein funktionierendes
WCS besitzen.  Das zuerst verarbeitete Bild wird geladen, und sein WCS wird zur
Ausrichtung der anderen Kacheln verwendet.  Sie können einer vorhandenen Collage
neue Bilder hinzufügen, indem Sie einfach weitere Dateien ziehen.

**Steuerelemente**

Das Steuerelement „Methode“ dient zur Wahl einer Methode zum Mosaizieren der
Bilder in der Collage.  Es hat zwei Werte: 'simple' und 'warp':

- 'simple' versucht, die Bilder gemäß dem WCS zu drehen und zu spiegeln.  Es ist
  eine schnelle Methode auf Kosten der Genauigkeit.  Es behandelt keine
  Verzeichnungen am Feldrand, die das Bild verzerren sollten.
- 'warp' verwendet das WCS, um jedes Pixel im Bild gemäß dem WCS des
  Referenzbildes vollständig zu verschieben.  Dabei können leere Pixel im Bild
  entstehen, die durch Abtasten der umliegenden Pixel aufgefüllt werden.  Dies
  ist langsamer als die einfache Methode, und die Zeit wächst linear mit der
  Größe der Bilder.

Aktivieren Sie die Schaltfläche „Collage-HDUs“, damit `Collage` versucht, alle
Bild-HDUs in einer gezogenen Datei zu plotten, statt nur der ersten gefundenen.

Aktivieren Sie „Bilder beschriften“, damit das Plugin den Namen jedes Bildes
über jede geplottete Kachel zeichnet.

Ist „Hintergrund angleichen“ aktiviert, wird der Hintergrund jeder Kachel
relativ zum Median der zuerst geplotteten Kachel angepasst (eine Art grobe
Glättung).

Das Feld „Anzahl Threads“ legt fest, wie viele Threads aus dem Thread-Pool zum
Laden der Daten verwendet werden.  Die Verwendung mehrerer Threads beschleunigt
das Laden vieler Dateien in der Regel.

**Unterschied zum Plugin `Mosaic`**

- Reserviert kein großes Array für den gesamten Mosaikinhalt
- Kein Bedarf, ein Ausgabe-FOV anzugeben oder sich darum zu kümmern
- Kann das Ergebnis schneller anzeigen (hängt ein wenig von den Einzelbildern ab)
- Einige Plugins funktionieren mit einer Collage nicht korrekt oder sind langsamer
- Kann die Collage nicht als Datendatei speichern (Sie können aber „ScreenShot“
  verwenden)

Es ist über ``~/.ginga/plugin_Collage.cfg`` anpassbar, wobei ``~`` Ihr
HOME-Verzeichnis ist:

.. code-block:: Python

  #
  # Collage plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_Collage.cfg"

  # Set to True when you want to collage image HDUs in a file
  collage_hdus = False

  # annotate images with their names
  annotate_images = False

  # Try to match backgrounds
  match_bg = False

  # Number of threads to devote to opening images
  num_threads = 4
