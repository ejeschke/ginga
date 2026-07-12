
``PixTable`` bietet eine Möglichkeit, die Pixelwerte in einem Bereich zu prüfen
oder zu überwachen.

**Plugin-Typ: Lokal**

``PixTable`` ist ein lokales Plugin, das heißt, es ist einem Kanal zugeordnet.
Für jeden Kanal kann eine Instanz geöffnet werden.

**Grundlegende Verwendung**

In der grundlegendsten Verwendung bewegen Sie einfach den Cursor im
Kanalbetrachter umher; ein Array von Pixelwerten erscheint in der Anzeige „Pixel
Values“ in der Plugin-Oberfläche.  Der zentrale Wert ist hervorgehoben und
entspricht dem Wert unter dem Cursor.

Sie können über das linke Kombinationsfeld ein 3x3-, 5x5-, 7x7- oder 9x9-Gitter
wählen.  Es kann hilfreich sein, das Steuerelement „Schriftgröße“ anzupassen, um
zu verhindern, dass die Array-Werte an den Seiten abgeschnitten werden.  Sie
können auch den Plugin-Arbeitsbereich vergrößern, um mehr von der Tabelle zu
sehen.

.. note:: Die Reihenfolge der angezeigten Werttabelle stimmt nicht unbedingt mit
          dem Kanalbetrachter überein, wenn das Bild gespiegelt, transponiert
          oder gedreht ist.

**Marken verwenden**

Wenn Sie eine Marke setzen und auswählen, werden die Pixelwerte um die Marke
herum statt um den Cursor angezeigt.  Es kann beliebig viele Marken geben, und
jede ist mit einem nummerierten „X“ gekennzeichnet.  Ändern Sie einfach das
Marken-Dropdown-Steuerelement, um eine andere Marke auszuwählen und die Werte um
sie herum zu sehen.  Die aktuell ausgewählte Marke wird mit einer anderen Farbe
als die übrigen angezeigt.

Die Marken bleiben an ihrer Position, selbst wenn ein neues Bild geladen wird,
und sie zeigen die Werte für das neue Bild an.  So können Sie den Bereich um
einen Punkt überwachen, wenn das Bild häufig aktualisiert wird.

Ist das Kontrollkästchen „Zu Marke schwenken“ ausgewählt, schwenkt der
Kanalbetrachter zu dieser Marke, wenn Sie im Markensteuerelement eine andere
Marke auswählen.  Dies kann nützlich sein, um dieselben Stellen in mehreren
verschiedenen Bildern zu inspizieren, besonders wenn eng in das Bild gezoomt
ist.

.. note:: Wenn Sie das Markensteuerelement wieder auf „None“ setzen, wird die
          Pixeltabelle erneut aktualisiert, während Sie den Cursor im Betrachter
          umherbewegen.

Das Feld „Caption“ kann verwendet werden, um eine Textanmerkung festzulegen, die
beim Erstellen der nächsten Marke an die Markenbeschriftung angehängt wird.
Damit lässt sich zum Beispiel ein Merkmal im Bild beschriften.

**Marken löschen**

Um eine Marke zu löschen, wählen Sie sie im Markensteuerelement aus und drücken
Sie dann die mit „Löschen“ beschriftete Schaltfläche.  Um alle Marken zu
löschen, drücken Sie die mit „Alle löschen“ beschriftete Schaltfläche.

**Marken verschieben**

Wenn die Optionsschaltfläche „Verschieben“ aktiviert und eine Marke ausgewählt
ist, verschiebt ein Klick oder Ziehen an einer beliebigen Stelle im Bild die
Marke an diese Stelle und aktualisiert die Pixeltabelle.  Ist derzeit keine
Marke ausgewählt, wird eine neue erstellt und verschoben.

**Marken zeichnen**

Wenn die Optionsschaltfläche „Zeichnen“ aktiviert ist, erstellt Klicken und
Ziehen eine neue Marke.  Je länger der Zug, desto größer der Radius des „X“.

**Marken bearbeiten**

Wenn die Optionsschaltfläche „Bearbeiten“ aktiviert ist, nachdem eine Marke
ausgewählt wurde, können Sie die Kontrollpunkte der Marke ziehen, um den Radius
der Arme des X zu vergrößern, oder Sie können den Begrenzungsrahmen ziehen, um
die Marke zu verschieben.  Werden die Bearbeitungskontrollpunkte nicht
angezeigt, klicken Sie einfach auf die Mitte einer Marke, um sie zu aktivieren.

**Sondertasten**

Im Modus „Verschieben“ sind die folgenden Tasten aktiv:
- „n“ platziert eine neue Marke an der Cursorposition
- „m“ verschiebt die aktuelle Marke (falls vorhanden) an die Cursorposition
- „d“ löscht die aktuelle Marke (falls vorhanden)
- „j“ wählt die vorherige Marke aus (falls vorhanden)
- „k“ wählt die nächste Marke aus (falls vorhanden)

**Benutzerkonfiguration**

Es ist über ``~/.ginga/plugin_PixTable.cfg`` anpassbar, wobei ``~`` Ihr
HOME-Verzeichnis ist:

.. code-block:: Python

  #
  # PixTable plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_PixTable.cfg"

  # Default font
  font = 'fixed'

  # Default font size
  fontsize = 12

  # default size for mark point radius
  mark_radius = 10

  # style of point to draw
  mark_style = 'cross'

  # color of non-selected marks
  mark_color = 'purple'

  # color of selected mark
  select_color = 'cyan'

  # whether to update the pixel table when moving a mark around
  drag_update = True
