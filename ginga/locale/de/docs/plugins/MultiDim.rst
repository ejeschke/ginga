
Ein Plugin zum Navigieren durch HDUs in einer FITS-Datei oder durch Ebenen in
einem 3D-Würfel oder einem Datensatz höherer Dimension.

**Plugin-Typ: Lokal**

``MultiDim`` ist ein lokales Plugin, das heißt, es ist einem Kanal zugeordnet.
Für jeden Kanal kann eine Instanz geöffnet werden.

**Verwendung**

``MultiDim`` ist ein Plugin, das für Datenwürfel und FITS-Dateien mit mehreren
HDUs ausgelegt ist.  Wenn Sie ein solches Bild in Ginga geöffnet haben, können
Sie durch das Starten dieses Plugins zu anderen Schnitten des Würfels
navigieren oder andere HDUs betrachten.

Bei einem Datenwürfel können Sie einen Schnitt mit der Schaltfläche „Schnitt
speichern“ als Bild speichern oder mit der Schaltfläche „Film speichern“ einen
Film erstellen, indem Sie die Schnittindizes „Start“ und „Ende“ eingeben.
Diese Funktion setzt voraus, dass ``mencoder`` installiert ist.

Bei einer FITS-Tabelle werden ihre Daten mit einer Astropy-Tabelle eingelesen.
Die Spalteneinheiten werden direkt unter der Hauptüberschrift angezeigt („None“,
wenn keine Einheit vorhanden ist).  Bei maskierten Spalten werden maskierte
Werte durch vordefinierte Füllwerte ersetzt.

**HDUs durchsuchen**

Verwenden Sie die HDU-Auswahlliste im oberen Teil der Benutzeroberfläche, um
eine HDU zum Öffnen im Kanal zu durchsuchen und auszuwählen.

**Würfel navigieren**

Verwenden Sie die Steuerelemente im unteren Teil der Benutzeroberfläche, um die
Achse auszuwählen und die Ebenen entlang dieser Achse durchzugehen.

**Benutzerkonfiguration**

Es ist über ``~/.ginga/plugin_MultiDim.cfg`` anpassbar, wobei ``~`` Ihr
HOME-Verzeichnis ist:

.. code-block:: Python

  #
  # MultiDim plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_MultiDim.cfg"

  # Sort option for HDU listing.
  # Available attributes:
  #   'index' -- Extension index
  #   'name' -- Extension name
  #   'extver' -- Extension version number
  #   'htype' -- HDU type (PrimaryHDU, ImageHDU, TableHDU)
  #   'dtype' -- Data type
  # Example to sort by HDU name and extver:
  #   sort_keys = ['name', 'extver']
  # Default is to sort by index only:
  sort_keys = ['index']

  # Reverse for HDU listing?
  sort_reverse = False
