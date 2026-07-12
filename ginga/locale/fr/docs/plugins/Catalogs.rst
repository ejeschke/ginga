
Un plugin pour tracer les emplacements d'objets d'un catalogue sur une image.

**Type de plugin : Local**

``Catalogs`` est un plugin local, ce qui signifie qu'il est associé à un canal.
Une instance peut être ouverte pour chaque canal.

.. note:: Pour utiliser ``Catalogs``, il est nécessaire d'installer le paquet
          ``astroquery``.

.. warning:: La configuration de ``Catalogs`` via la technique
          ``ginga_config.py`` dans Ginga 3.2 ou ultérieur n'est pas
          officiellement prise en charge et peut ne pas fonctionner comme dans
          les versions précédentes.  Voir les nouvelles instructions de
          configuration de l'utilisateur ci-dessous.

**Utilisation**

**Récupérer une image**

* Par résolveur de noms : À l'aide de la case « Name Server », choisissez un
  serveur et saisissez un nom dans le champ « Name ».  Appuyez sur « Search
  name ».  Si le nom est résolu, les champs « ra » et « dec » de la case « Image
  Server » seront remplis.  Sélectionnez un serveur, ajustez la largeur et/ou la
  hauteur, et appuyez sur « Get Image ».
* Par image existante dans le canal : Dessinez une forme sur l'image affichée
  (« rectangle » ou « circle » peut être choisi en bas de l'interface du plugin)
  et ajustez les paramètres de recherche comme souhaité.  Quand vous êtes prêt,
  appuyez sur « Get Image » pour effectuer la recherche.

.. note:: Le téléchargement de l'image peut prendre un certain temps, selon la
          taille du champ, les conditions du réseau, etc.  Normalement, si la
          recherche ou le téléchargement échoue, une erreur apparaîtra dans le
          plugin Errors.

Si l'image est téléchargée avec succès, elle devrait apparaître dans le
visualiseur de canal.

**Récupérer et tracer des objets à partir de catalogues**

Pour tracer des objets, le plugin Catalogs a besoin d'une image avec un WCS
valide chargée dans le canal.  Vous pouvez soit charger votre propre image, soit
en récupérer une depuis un serveur d'images comme décrit dans « Récupérer une
image » ci-dessus.

Choisir un centre :

* Par résolveur de noms : À l'aide de la case « Name Server », choisissez un
  serveur et saisissez un nom dans le champ « Name ».  Appuyez sur « Search
  name ».  Si le nom est résolu, les champs « ra » et « dec » de la case
  « Catalog Server » seront remplis.  Sélectionnez un serveur, ajustez la largeur
  et/ou la hauteur, et appuyez sur « Search catalog ».
* Par image existante dans le canal : Dessinez une forme sur l'image affichée
  (« rectangle » ou « circle » peut être choisi en bas de l'interface du plugin)
  et ajustez les paramètres de recherche comme souhaité.  Quand vous êtes prêt,
  appuyez sur « Search catalog » pour effectuer la recherche.

.. note:: Le résultat de la recherche peut prendre un certain temps, selon la
          taille du champ, les conditions du réseau, etc.  Normalement, si la
          recherche échoue, une erreur apparaîtra dans le plugin Errors.

Lorsque les résultats de la recherche sont disponibles, ils s'affichent sur
l'image et sont aussi listés dans une table de l'interface du plugin.  Vous
pouvez cliquer sur la table ou sur l'image pour mettre en surbrillance la
sélection.

**Configuration de l'utilisateur**

Il est personnalisable à l'aide de ``~/.ginga/plugin_Catalogs.cfg``, où ``~``
est votre répertoire HOME :

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
