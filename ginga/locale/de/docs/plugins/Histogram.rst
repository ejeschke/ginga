
``Histogram`` stellt ein Histogramm für einen im Bild gezeichneten Bereich oder
für das gesamte Bild dar.

**Plugin-Typ: Lokal**

``Histogram`` ist ein lokales Plugin, das heißt, es ist einem Kanal zugeordnet.
Es ist kein Singleton, das heißt, für jeden Kanal können mehrere Instanzen
geöffnet werden.

**Verwendung**

Klicken und ziehen Sie, um einen Bereich innerhalb des Bildes zu definieren, der
zur Berechnung des Histogramms verwendet wird.  Um das Histogramm des gesamten
Bildes zu nehmen, klicken Sie auf die mit „Ganzes Bild“ beschriftete
Schaltfläche in der Benutzeroberfläche.

.. note:: Je nach Größe des Bildes kann die Berechnung des vollständigen
          Histogramms Zeit in Anspruch nehmen.

Wird für den Kanal ein neues Bild ausgewählt, wird das Histogrammdiagramm
basierend auf den aktuellen Parametern mit den neuen Daten neu berechnet.

Sofern nicht in der Einstellungsdatei für das Histogramm-Plugin deaktiviert,
wird eine Zeile einfacher Statistiken für den Kasten berechnet und in einer
Zeile unterhalb des Diagramms angezeigt.

**UI-Steuerelemente**

Drei Optionsschaltflächen am unteren Rand der Benutzeroberfläche steuern die
Auswirkungen der Klick-/Ziehaktion:

* Wählen Sie „Verschieben“, um den Bereich an eine andere Stelle zu ziehen
* Wählen Sie „Zeichnen“, um einen neuen Bereich zu zeichnen
* Wählen Sie „Bearbeiten“, um den Bereich zu bearbeiten

Um ein logarithmisches Diagramm des Histogramms zu erstellen, aktivieren Sie das
Kontrollkästchen „Log-Histogramm“.  Um über den vollen Wertebereich des Bildes
statt über den Bereich innerhalb der Cut-Werte zu plotten, deaktivieren Sie das
Kontrollkästchen „Nach Cuts plotten“.

Der Parameter „NumBins“ bestimmt, wie viele Klassen zur Berechnung des
Histogramms verwendet werden.  Geben Sie eine Zahl in das Feld ein und drücken
Sie „Enter“, um den Standardwert zu ändern.

**Komfort-Steuerelemente für Cut-Level**

Da ein Histogramm eine nützliche Rückmeldung zum Einstellen der Cut-Level ist,
sind in der Benutzeroberfläche Steuerelemente zum Einstellen des unteren und
oberen Cut-Levels im Bild sowie zum Durchführen von Auto-Cut-Levels gemäß den
Auto-Cut-Level-Einstellungen in den Kanaleinstellungen vorgesehen.

Sie können Cut-Level durch Klicken im Histogrammdiagramm einstellen:

* Linksklick: unteren Cut setzen
* Mittelklick: zurücksetzen (Auto-Cut-Level)
* Rechtsklick: oberen Cut setzen

Zusätzlich können Sie den Abstand zwischen unterem und oberem Cut dynamisch
anpassen, indem Sie mit dem Rad im Diagramm scrollen (d. h. die „Breite“ der
Histogramm-Kurve).  Dies bewirkt eine Erhöhung oder Verringerung des Kontrasts
im Bild.  Der Betrag, der bei jedem Radklick geändert wird, wird durch die
Einstellung ``scroll_pct`` in der Plugin-Konfigurationsdatei festgelegt.  Der
Standardwert beträgt 10 %.

**Benutzerkonfiguration**

Es ist über ``~/.ginga/plugin_Histogram.cfg`` anpassbar, wobei ``~`` Ihr
HOME-Verzeichnis ist:

.. code-block:: Python

  #
  # Histogram plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_Histogram.cfg"

  # Switch to "move" mode after selection
  draw_then_move = True

  # Number of bins for histogram
  num_bins = 2048

  # Histogram color
  hist_color = 'aquamarine'

  # Calculate extra statistics on box
  show_stats = True

  # Controls formatting (width) of statistics numbers
  maxdigits = 7

  # percentage to adjust cuts gap when scrolling in histogram
  scroll_pct = 0.10
