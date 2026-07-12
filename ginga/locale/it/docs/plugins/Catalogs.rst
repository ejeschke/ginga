
Un plugin per tracciare le posizioni degli oggetti di un catalogo su
un'immagine.

**Tipo di plugin: Locale**

``Catalogs`` è un plugin locale, il che significa che è associato a un canale.
È possibile aprire un'istanza per ciascun canale.

.. note:: Per usare ``Catalogs``, è necessario installare il pacchetto
          ``astroquery``.

.. warning:: La configurazione di ``Catalogs`` tramite la tecnica
          ``ginga_config.py`` in Ginga 3.2 o successivo non è ufficialmente
          supportata e potrebbe non funzionare come nelle versioni precedenti.
          Vedi le nuove istruzioni di configurazione utente qui sotto.

**Uso**

**Recuperare un'immagine**

* Tramite risolutore di nomi: Usando la casella « Name Server », scegli un
  server e digita un nome nel campo « Name ».  Premi « Search name ».  Se il nome
  viene risolto, i campi « ra » e « dec » nella casella « Image Server » verranno
  compilati.  Seleziona un server, regola la larghezza e/o l'altezza, e premi
  « Get Image ».
* Tramite immagine esistente nel canale: Disegna una forma sull'immagine
  visualizzata (si può scegliere « rectangle » o « circle » nella parte
  inferiore della GUI del plugin) e regola i parametri di ricerca come desideri.
  Quando sei pronto, premi « Get Image » per eseguire la ricerca.

.. note:: Il download dell'immagine può richiedere del tempo per completarsi, a
          seconda della dimensione del campo, delle condizioni della rete, ecc.
          Normalmente, se la ricerca o il download falliscono, comparirà un
          errore nel plugin Errors.

Se l'immagine viene scaricata con successo, dovrebbe comparire nel
visualizzatore di canale.

**Recuperare e tracciare oggetti dai cataloghi**

Per tracciare oggetti, il plugin Catalogs necessita di un'immagine con un WCS
valido caricata nel canale.  Puoi caricare la tua immagine oppure recuperarne
una da un server di immagini come descritto in « Recuperare un'immagine » sopra.

Scegliere un centro:

* Tramite risolutore di nomi: Usando la casella « Name Server », scegli un
  server e digita un nome nel campo « Name ».  Premi « Search name ».  Se il nome
  viene risolto, i campi « ra » e « dec » nella casella « Catalog Server »
  verranno compilati.  Seleziona un server, regola la larghezza e/o l'altezza, e
  premi « Search catalog ».
* Tramite immagine esistente nel canale: Disegna una forma sull'immagine
  visualizzata (si può scegliere « rectangle » o « circle » nella parte
  inferiore della GUI del plugin) e regola i parametri di ricerca come desideri.
  Quando sei pronto, premi « Search catalog » per eseguire la ricerca.

.. note:: Il risultato della ricerca può richiedere del tempo per completarsi, a
          seconda della dimensione del campo, delle condizioni della rete, ecc.
          Normalmente, se la ricerca fallisce, comparirà un errore nel plugin
          Errors.

Quando i risultati della ricerca sono disponibili, verranno visualizzati
sull'immagine e anche elencati in una tabella nella GUI del plugin.  Puoi fare
clic sulla tabella o sull'immagine per evidenziare la selezione.

**Configurazione utente**

È personalizzabile usando ``~/.ginga/plugin_Catalogs.cfg``, dove ``~`` è la tua
directory HOME:

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
