
Ein Plugin zum Erzeugen eines Diagramms der Werte entlang einer Linie oder
eines Pfades.

**Plugin-Typ: Lokal**

``Cuts`` ist ein lokales Plugin, das heißt, es ist einem Kanal zugeordnet.
Es ist kein Singleton, das heißt, für jeden Kanal können mehrere Instanzen
geöffnet werden.

**Verwendung**

``Cuts`` stellt ein einfaches Diagramm von Pixelwerten gegen den Index für eine
durch das Bild gezeichnete Linie dar.  Es können mehrere Schnitte dargestellt
werden.

Es sind vier Arten von Schnitten verfügbar: line, path, freepath und
beziercurve:

* Der „line“-Schnitt ist eine gerade Linie zwischen zwei Punkten.
* Der „path“-Schnitt wird wie ein offenes Polygon mit geraden Segmenten dazwischen
  gezeichnet.
* Der „freepath“-Schnitt ist wie ein path-Schnitt, wird aber mit einem
  freihändigen Strich entlang der Cursorbewegung gezeichnet.
* Der „beziercurve“-Pfad ist eine kubische Bézierkurve.

Wird dem Kanal ein neues Bild hinzugefügt, während das Plugin aktiv ist, wird es
mit den neu berechneten Schnitten auf dem neuen Bild aktualisiert.

Ist die Einstellung „enable slit“ aktiviert, erlaubt dieses Plugin auch die
Slit-Bild-Funktionalität (für mehrdimensionale Bilder) über einen „Slit“-Reiter.
Wählen Sie in der Reiter-Oberfläche eine Achse aus der „Axes“-Liste und zeichnen
Sie eine Linie.  Dies erzeugt ein 2D-Bild, das annimmt, dass die ersten beiden
Achsen räumlich sind, und die Daten entlang der gewählten Achse indiziert.  Ähnlich
wie bei ``Cuts`` können Sie die anderen Slit-Bilder über das Schnittauswahlmenü
betrachten.

**Schnitte zeichnen**

Über das Menü „New Cut Type“ können Sie wählen, welche Art von Schnitt Sie
zeichnen möchten.

Wählen Sie „New Cut“ aus dem „Cut“-Dropdown-Menü, wenn Sie einen neuen Schnitt
zeichnen möchten.  Andernfalls, wenn ein bestimmter benannter Schnitt ausgewählt
ist, wird dieser durch jeden neu gezeichneten Schnitt ersetzt.

Während Sie einen path- oder beziercurve-Schnitt zeichnen, drücken Sie „v“, um
einen Scheitelpunkt hinzuzufügen, oder „z“, um den zuletzt hinzugefügten
Scheitelpunkt zu entfernen.

**Tastenkürzel**

Während Sie den Cursor darüber bewegen, drücken Sie „h“ für einen vollen
horizontalen Schnitt und „j“ für einen vollen vertikalen Schnitt.

**Schnitte löschen**

Um einen Schnitt zu löschen, wählen Sie seinen Namen aus dem „Cut“-Dropdown und
klicken Sie auf die Schaltfläche „Löschen“.  Um alle Schnitte zu löschen,
drücken Sie „Alle löschen“.

**Schnitte bearbeiten**

Mit der Leinwand-Bearbeitungsfunktion können Sie einem vorhandenen Pfad neue
Scheitelpunkte hinzufügen und Scheitelpunkte verschieben.  Klicken Sie auf die
Optionsschaltfläche „Bearbeiten“, um die Leinwand in den Bearbeitungsmodus zu
versetzen.  Wird ein Schnitt nicht automatisch ausgewählt, können Sie nun die
Linie, den Pfad oder die Kurve durch Anklicken auswählen, wodurch die
Kontrollpunkte an den Enden oder Scheitelpunkten aktiviert werden sollten -- Sie
können diese herumziehen.  Um einem Pfad einen neuen Scheitelpunkt hinzuzufügen,
bewegen Sie den Cursor sorgfältig auf die Linie, wo Sie den neuen Scheitelpunkt
möchten, und drücken Sie „v“.  Um einen Scheitelpunkt zu entfernen, bewegen Sie
den Cursor darüber und drücken Sie „z“.

Sie werden bei den meisten Objekten einen zusätzlichen Kontrollpunkt bemerken,
dessen Mitte eine andere Farbe hat -- dies ist ein Bewegungskontrollpunkt, um im
Bearbeitungsmodus das gesamte Objekt über das Bild zu bewegen.

Sie können auch „Verschieben“ wählen, um einen Schnitt einfach unverändert zu
verschieben.

**Breite der Schnitte ändern**

Die Breite von „line“-Schnitten kann über das Menü „Width Type“ geändert werden:

* „none“ bedeutet einen Schnitt mit Radius null; d. h. es werden nur die
  Pixelwerte entlang der Linie gezeigt
* „x“ plottet die Summe der Werte entlang der zum Schnitt orthogonalen X-Achse.
* „y“ plottet die Summe der Werte entlang der zum Schnitt orthogonalen Y-Achse.
* „perpendicular“ plottet die Summe der Werte entlang einer zum Schnitt
  senkrechten Achse.

Der „Width radius“ steuert die Breite der orthogonalen Summierung um einen
Betrag zu beiden Seiten des Schnitts -- 1 wären 3 Pixel, 2 wären 5 Pixel usw.

**Schnitte speichern**

Verwenden Sie die Schaltfläche „Speichern“, um das ``Cuts``-Diagramm als Bild
und die Daten als komprimiertes Numpy-Archiv zu speichern.

**Schnitte kopieren**

Um einen Schnitt zu kopieren, wählen Sie seinen Namen aus dem „Cut“-Dropdown und
klicken Sie auf die Schaltfläche „Schnitt kopieren“.  Daraus wird ein neuer
Schnitt erstellt.  Sie können den neuen Schnitt dann unabhängig bearbeiten.

**Benutzerkonfiguration**

Es ist über ``~/.ginga/plugin_Cuts.cfg`` anpassbar, wobei ``~`` Ihr
HOME-Verzeichnis ist:

.. code-block:: Python

  #
  # Cuts plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_Cuts.cfg"

  # If set to True will always select a cut after drawing it
  select_new_cut = True

  # If set to True will automatically change to "move" mode after draw
  draw_then_move = True

  # If set to True will label cuts with a text annotation
  label_cuts = True

  # If set to True will add a legend to the cuts plot
  show_cuts_legend = False

  # If set to True will add Slit tab
  enable_slit = False

  # Default cut colors
  colors = ['magenta', 'skyblue2', 'chartreuse2', 'cyan', 'pink', 'burlywood2', 'yellow3', 'turquoise', 'coral1', 'mediumpurple2']

  # If set to True, will update graph continuously as cursor is dragged
  # around image
  drag_update = False
