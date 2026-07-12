
Ein Plugin zum Plotten von Objektpositionen aus einem Katalog auf einem Bild.

**Plugin-Typ: Lokal**

``Catalogs`` ist ein lokales Plugin, das heißt, es ist einem Kanal zugeordnet.
Für jeden Kanal kann eine Instanz geöffnet werden.

.. note:: Um ``Catalogs`` zu verwenden, muss das Paket ``astroquery``
          installiert sein.

.. warning:: Die Konfiguration von ``Catalogs`` über die
          ``ginga_config.py``-Technik in Ginga 3.2 oder später wird nicht
          offiziell unterstützt und funktioniert möglicherweise nicht wie in
          früheren Versionen.  Siehe die neuen Anweisungen zur
          Benutzerkonfiguration unten.

**Verwendung**

**Ein Bild abrufen**

* Über Namensauflöser: Wählen Sie im Feld „Name Server“ einen Server und geben
  Sie einen Namen in das Feld „Name“ ein.  Drücken Sie „Search name“.  Wird der
  Name aufgelöst, werden die Felder „ra“ und „dec“ im Feld „Image Server“
  ausgefüllt.  Wählen Sie einen Server, passen Sie Breite und/oder Höhe an und
  drücken Sie „Get Image“.
* Über vorhandenes Bild im Kanal: Zeichnen Sie eine Form auf dem angezeigten Bild
  („rectangle“ oder „circle“ kann am unteren Rand der Plugin-GUI gewählt werden)
  und passen Sie die Suchparameter nach Wunsch an.  Wenn Sie bereit sind, drücken
  Sie „Get Image“, um die Suche durchzuführen.

.. note:: Der Bilddownload kann je nach Größe des Feldes, Netzwerkbedingungen
          usw. einige Zeit dauern.  Schlägt die Suche oder der Download fehl,
          wird normalerweise ein Fehler im Errors-Plugin angezeigt.

Wird das Bild erfolgreich heruntergeladen, sollte es im Kanalbetrachter
erscheinen.

**Objekte aus Katalogen abrufen und plotten**

Um Objekte zu plotten, benötigt das Catalogs-Plugin ein in den Kanal geladenes
Bild mit einem gültigen WCS.  Sie können entweder Ihr eigenes Bild laden oder
eines von einem Bildserver abrufen, wie oben unter „Ein Bild abrufen“
beschrieben.

Ein Zentrum wählen:

* Über Namensauflöser: Wählen Sie im Feld „Name Server“ einen Server und geben
  Sie einen Namen in das Feld „Name“ ein.  Drücken Sie „Search name“.  Wird der
  Name aufgelöst, werden die Felder „ra“ und „dec“ im Feld „Catalog Server“
  ausgefüllt.  Wählen Sie einen Server, passen Sie Breite und/oder Höhe an und
  drücken Sie „Search catalog“.
* Über vorhandenes Bild im Kanal: Zeichnen Sie eine Form auf dem angezeigten Bild
  („rectangle“ oder „circle“ kann am unteren Rand der Plugin-GUI gewählt werden)
  und passen Sie die Suchparameter nach Wunsch an.  Wenn Sie bereit sind, drücken
  Sie „Search catalog“, um die Suche durchzuführen.

.. note:: Das Suchergebnis kann je nach Größe des Feldes, Netzwerkbedingungen
          usw. einige Zeit dauern.  Schlägt die Suche fehl, wird normalerweise
          ein Fehler im Errors-Plugin angezeigt.

Wenn Suchergebnisse verfügbar sind, werden sie auf dem Bild angezeigt und
außerdem in einer Tabelle in der Plugin-GUI aufgelistet.  Sie können entweder auf
die Tabelle oder das Bild klicken, um die Auswahl hervorzuheben.

**Benutzerkonfiguration**

Es ist über ``~/.ginga/plugin_Catalogs.cfg`` anpassbar, wobei ``~`` Ihr
HOME-Verzeichnis ist:

.. code-block:: Python

  #
  # Catalogs plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_Catalogs.cfg"

  draw_type = 'circle'

  select_color = 'skyblue'

  color_outline = 'aquamarine'

  click_radius = 10


  # NAME SOURCES
  # Name resolvers for astronomical object names
  #
  # Format: list of dicts
  # Each dict defines a source, and has the following fields:
  #   shortname: str
  #       the short name appearing in the control for selecting a source
  #       in the plugin
  #
  #   fullname: str
  #       the full name, should correspond *exactly* with the name required
  #       by astroquery.vo_conesearch "catalog" parameter
  #
  #   type: str
  #       should be "astroquery.names" for an astroquery.names function
  #
  name_sources = [
  {'shortname': "SIMBAD", 'fullname': "SIMBAD",
  'type': 'astroquery.names'},
  {'shortname': "NED", 'fullname': "NED",
  'type': 'astroquery.names'},
  ]


  # CATALOG SOURCES
  #
  # Format: list of dicts
  # Each dict defines a source, and has the following fields:
  #   shortname: str
  #       the short name appearing in the control for selecting a source
  #       in the plugin
  #
  #   fullname: str
  #       the full name, should correspond *exactly* with the name required
  #       by astroquery.vo_conesearch "catalog" parameter
  #
  #   type: str
  #       should be "astroquery.vo_conesearch" for an astroquery.vo_conesearch
  #       function
  #
  #   mapping: dict
  #       a nested dict providing the mapping for the return results to the GUI,
  #       in terms of field name to Ginga table.
  #       There must be keys for 'id', 'ra' and 'dec'. 'mag', if present, can be
  #       a list of field names that define magnitudes of the elements in various
  #       wavelengths.
  #
  catalog_sources = [
  {'shortname': "GSC 2.3",
  'fullname': "Guide Star Catalog 2.3 Cone Search 1",
  'type': 'astroquery.vo_conesearch',
  'mapping': {'id': 'objID', 'ra': 'ra', 'dec': 'dec', 'mag': ['Mag']}},
  {'shortname': "USNO-A2.0 1",
  'fullname': "The USNO-A2.0 Catalogue (Monet+ 1998) 1",
  'type': 'astroquery.vo_conesearch',
  'mapping': {'id': 'USNO-A2.0', 'ra': 'RAJ2000', 'dec': 'DEJ2000',
  'mag': ['Bmag', 'Rmag']}},
  {'shortname': "2MASS 1",
  'fullname': "Two Micron All Sky Survey (2MASS) 1",
  'type': 'astroquery.vo_conesearch',
  'mapping': {'id': 'htmID', 'ra': 'ra', 'dec': 'dec',
  'mag': ['h_m', 'j_m', 'k_m']}},
  ]


  # IMAGE SOURCES
  #
  # Format: list of dicts
  # Each dict defines a source, and has the following fields:
  #   shortname: str
  #       the string that should correspond *exactly* with the name required
  #       by astroquery.skyview "survey" parameter for get_image_list()
  #
  #   fullname: str
  #       the full name, mostly descriptive
  #
  #   type: str
  #       should be "astroquery.image"
  #
  #   source: str
  #       should be "skyview"
  #
  #
  image_sources = [
  {'shortname': "DSS",
  'fullname': "Digital Sky Survey 1",
  'type': 'astroquery.image',
  'source': 'skyview'},
  {'shortname': "DSS1 Blue",
  'fullname': "Digital Sky Survey 1 Blue",
  'type': 'astroquery.image',
  'source': 'skyview'},
  {'shortname': "DSS1 Red",
  'fullname': "Digital Sky Survey 1 Red",
  'type': 'astroquery.image',
  'source': 'skyview'},
  {'shortname': "DSS2 Red",
  'fullname': "Digital Sky Survey 2 Red",
  'type': 'astroquery.image',
  'source': 'skyview'},
  {'shortname': "DSS2 Blue",
  'fullname': "Digital Sky Survey 2 Blue",
  'type': 'astroquery.image',
  'source': 'skyview'},
  {'shortname': "DSS2 IR",
  'fullname': "Digital Sky Survey 2 Infrared",
  'type': 'astroquery.image',
  'source': 'skyview'},
  ]
