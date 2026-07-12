
``Crosshair`` ist ein einfaches Plugin, das Fadenkreuze zeichnet, die mit der
Position des Kreuzes in Pixelkoordinaten, WCS-Koordinaten oder dem Datenwert an
der Kreuzposition beschriftet sind.

**Plugin-Typ: Lokal**

``Crosshair`` ist ein lokales Plugin, das heißt, es ist einem Kanal zugeordnet.
Für jeden Kanal kann eine Instanz geöffnet werden.

**Verwendung**

Wählen Sie den passenden Ausgabetyp im Auswahlmenü „Format“ in der
Benutzeroberfläche: „xy“ für Pixelkoordinaten, „coords“ für die
WCS-Koordinaten und „value“ für den Wert an der Fadenkreuzposition.

Ist „Nur Ziehen“ aktiviert, wird das Fadenkreuz nur aktualisiert, wenn der
Cursor im Fenster geklickt oder gezogen wird.  Ist es deaktiviert, wird das
Fadenkreuz einfach durch Bewegen des Cursors im Kanalbetrachter-Fenster
positioniert.

Der Reiter „Cuts“ enthält ein Profildiagramm für die vertikalen und
horizontalen Schnitte, die durch die sichtbare Kastengrenze dargestellt werden,
die vorhanden ist, wenn „Quick Cuts“ aktiviert ist.  Dieses Diagramm wird in
Echtzeit aktualisiert, während das Fadenkreuz bewegt wird.  Ist „Quick Cuts“
deaktiviert, wird das Diagramm nicht aktualisiert.

Die Größe des Kastens wird durch den Parameter „radius“ bestimmt.

Das Steuerelement „Warnstufe“ kann verwendet werden, um einen Flusspegel
festzulegen, oberhalb dessen im Cuts-Diagramm eine Warnung durch eine gelbe
Linie und einen gelb werdenden Hintergrund angezeigt wird.  Die Warnung wird
ausgelöst, wenn ein Wert entlang des X- oder Y-Schnitts die Warnstufen-Schwelle
überschreitet.

Das Steuerelement „Alarmstufe“ ist ähnlich, wird aber durch eine rote Linie und
einen rosa werdenden Hintergrund dargestellt.  Die Warnung wird ausgelöst, wenn
ein Wert entlang des X- oder Y-Schnitts die Alarmstufen-Schwelle überschreitet.
Alarme haben Vorrang vor Warnungen.

Sowohl die Funktion „Warn“ als auch „Alarm“ können durch einfaches Setzen eines
leeren Wertes ausgeschaltet werden.  Sie sind standardmäßig ausgeschaltet.

Das Cuts-Diagramm ist interaktiv, doch es ergibt eigentlich nur Sinn, dies zu
nutzen, wenn „Nur Ziehen“ aktiviert ist.  Sie können im Diagrammfenster „x“ oder
„y“ drücken, um die Autoachsen-Skalierung für die jeweilige Achse ein- und
auszuschalten, und im Diagramm scrollen, um die X-Achse zu zoomen (halten Sie
Strg beim Scrollen gedrückt, um die Y-Achse zu zoomen).

Crosshair bietet eine Pick-Plugin-Interaktionsfunktion: Wenn das Fadenkreuz über
einem Objekt liegt, können Sie im Kanalbetrachter-Fenster „r“ drücken, um das
Pick-Plugin an dieser bestimmten Position aufzurufen.  Ist auf diesem Kanal noch
kein Pick geöffnet, wird es zuerst geöffnet.

**Benutzerkonfiguration**

Es ist über ``~/.ginga/plugin_Crosshair.cfg`` anpassbar, wobei ``~`` Ihr
HOME-Verzeichnis ist:

.. code-block:: Python

  #
  # Crosshair plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_Crosshair.cfg"

  # color of the crosshair
  color = 'green'

  # text color of crosshair
  text_color = 'skyblue'

  # box color indicating cut radius
  box_color = 'aquamarine'

  # cut plot line colors for X and Y
  quick_h_cross_color = '#7570b3'
  quick_v_cross_color = '#1b9e77'

  # enable quick cuts plots by default
  quick_cuts = False

  # force drag only by default
  drag_only = False

  # set a warning level for the warning feature of the cuts plot
  warn_level = None

  # set an alery level for the alert feature of the cuts plot
  alert_level = None

  # set initial radius of the cuts box
  cuts_radius = 15
