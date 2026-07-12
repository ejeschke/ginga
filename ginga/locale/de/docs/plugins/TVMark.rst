
Punkte aus einer Datei (nicht-interaktiver Modus) auf einem Bild markieren.

**Plugin-Typ: Lokal**

``TVMark`` ist ein lokales Plugin, das heißt, es ist einem Kanal zugeordnet.
Für jeden Kanal kann eine Instanz geöffnet werden.

**Verwendung**

Dieses Plugin ermöglicht das nicht-interaktive Markieren von interessierenden
Punkten durch Einlesen einer Datei, die eine Tabelle mit RA- und DEC-Positionen
dieser Punkte enthält.  Jede Text- oder FITS-Tabellendatei, die von
``astropy.table`` gelesen werden kann, ist zulässig, doch der Benutzer *muss* die
Spaltennamen in der Plugin-Konfigurationsdatei korrekt definieren (siehe unten).
Es wird versucht, RA- und DEC-Werte in Grad umzuwandeln.  Schlägt die
Einheitenumrechnung fehl, wird angenommen, dass sie bereits in Grad vorliegen.

Alternativ können Sie, wenn die Datei Spalten mit den direkten Pixelpositionen
enthält, diese Spalten stattdessen einlesen, indem Sie das Kästchen „RADEC
verwenden“ deaktivieren.  Auch hier müssen die Spaltennamen in der
Plugin-Konfigurationsdatei korrekt definiert sein (siehe unten).  Pixelwerte
können 0- oder 1-indiziert sein (d. h., ob das erste Pixel 0 oder 1 ist) und
sind konfigurierbar (siehe unten).  Dies ist nützlich, wenn Sie die physischen
Pixel unabhängig vom WCS markieren möchten (z. B. das Markieren von Hot-Pixeln
auf einem Detektor).  RA und DEC werden weiterhin angezeigt, wenn das Bild
WCS-Informationen hat, aber sie beeinflussen die Markierungen nicht.

Um verschiedene Gruppen zu markieren (z. B. Galaxien als grüne Kreise und
Hintergrund als cyanfarbene Kreuze, wie oben gezeigt):

1. Wählen Sie grünen Kreis aus den Auswahlmenüs.  Alternativ geben Sie die
   gewünschte Größe oder Breite ein.
2. Stellen Sie sicher, dass das Kästchen „RADEC verwenden“ aktiviert ist, falls
   zutreffend.
3. Laden Sie mit der Schaltfläche „Koordinaten laden“ die Datei mit den RA- und
   DEC- (oder X- und Y-) Positionen *nur* für Galaxien.
4. Wiederholen Sie Schritt 1, wählen aber nun cyanfarbenes Kreuz aus den
   Auswahlmenüs.
5. Wiederholen Sie Schritt 2, wählen aber die Datei mit *nur* den
   Hintergrundpositionen.

Das Auswählen eines Eintrags (oder mehrerer Einträge) aus der Tabellenliste hebt
die Markierung(en) auf dem Bild hervor.  Die Hervorhebung verwendet dieselbe
Form und Farbe, aber eine etwas dickere Linie.

Sie können auch alle Markierungen innerhalb eines Bereichs sowohl auf dem Bild
als auch in der Tabellenliste hervorheben, indem Sie ein Rechteck auf dem Bild
zeichnen, während dieses Plugin aktiv ist.

Das Drücken der Schaltfläche „Verbergen“ verbirgt die Markierungen, löscht aber
nicht den Speicher des Plugins; das heißt, wenn Sie „Anzeigen“ drücken,
erscheinen dieselben Markierungen wieder auf demselben Bild.  Das Drücken von
„Vergessen“ löscht die Markierungen jedoch sowohl aus der Anzeige als auch aus
dem Speicher; das heißt, Sie müssen Ihre Datei(en) neu laden, um die
Markierungen wiederherzustellen.

Um dieselben Positionen mit anderen Markierungsparametern neu zu zeichnen,
drücken Sie „Vergessen“ und wiederholen die obigen Schritte nach Bedarf.  Wenn
Sie jedoch lediglich die Linienbreite (Dicke) ändern möchten, genügt es,
„Verbergen“ und dann „Anzeigen“ zu drücken, nachdem Sie den neuen Breitenwert
eingegeben haben.

Wenn Bilder mit sehr unterschiedlichen Ausrichtungen/Abmessungen im selben Kanal
angezeigt werden, erscheinen Markierungen, die zu einem Bild gehören, aber
außerhalb eines anderen liegen, in Letzterem nicht.

Um eine Tabelle zu erstellen, die dieses Plugin lesen kann, können Sie
Ergebnisse des ``Pick``-Plugins verwenden, oder eine Tabelle von Hand mit
``astropy.table`` usw. erstellen.

Zusammen mit ``TVMask`` verwendet, können Sie in Ginga sowohl Punktquellen als
auch maskierte Bereiche überlagern.

Es ist über ``~/.ginga/plugin_TVMark.cfg`` anpassbar, wobei ``~`` Ihr
HOME-Verzeichnis ist:

.. code-block:: Python

  #
  # TVMark plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_TVMark.cfg"

  # Marking type -- 'circle' or 'cross'
  marktype = 'circle'

  # Marking color -- Any color name accepted by Ginga
  markcolor = 'green'

  # Marking size or radius
  marksize = 5

  # Marking line width (thickness)
  markwidth = 1

  # Specify whether pixel values are 0- or 1-indexed
  pixelstart = 1

  # True -- Use 'ra' and 'dec' columns to extract RA/DEC positions. This option
  #         uses image WCS to convert to pixel locations.
  # False -- Use 'x' and 'y' columns to extract pixel locations directly.
  #          This does not use WCS.
  use_radec = True

  # Columns to load into table listing (case-sensitive).
  # Whether RA/DEC or X/Y columns are used depend on associated GUI selection.
  ra_colname = 'ra'
  dec_colname = 'dec'
  x_colname = 'x'
  y_colname = 'y'
  # Extra columns to display; e.g., ['colname1', 'colname2']
  extra_columns = []
