
Un complemento para trazar las ubicaciones de objetos de un catálogo en una
imagen.

**Tipo de complemento: Local**

``Catalogs`` es un complemento local, lo que significa que está asociado a un
canal.  Se puede abrir una instancia para cada canal.

.. note:: Para usar ``Catalogs``, es necesario instalar el paquete
          ``astroquery``.

.. warning:: La configuración de ``Catalogs`` mediante la técnica
          ``ginga_config.py`` en Ginga 3.2 o posterior no está oficialmente
          soportada y puede no funcionar como en versiones anteriores.  Consulte
          las nuevas instrucciones de configuración del usuario más abajo.

**Uso**

**Obtener una imagen**

* Por resolvedor de nombres: Usando el cuadro «Name Server», elija un servidor y
  escriba un nombre en el campo «Name».  Pulse «Search name».  Si el nombre se
  resuelve, los campos «ra» y «dec» del cuadro «Image Server» se rellenarán.
  Seleccione un servidor, ajuste la anchura y/o la altura, y pulse «Get Image».
* Por imagen existente en el canal: Dibuje una forma en la imagen mostrada (se
  puede elegir «rectangle» o «circle» en la parte inferior de la GUI del
  complemento) y ajuste los parámetros de búsqueda como desee.  Cuando esté
  listo, pulse «Get Image» para realizar la búsqueda.

.. note:: La descarga de la imagen puede tardar algún tiempo en terminar, según
          el tamaño del campo, las condiciones de la red, etc.  Normalmente, si
          la búsqueda o la descarga falla, aparecerá un error en el complemento
          Errors.

Si la imagen se descarga correctamente, debería aparecer en el visor de canal.

**Obtener y trazar objetos de catálogos**

Para trazar objetos, el complemento Catalogs necesita una imagen con un WCS
válido cargada en el canal.  Puede cargar su propia imagen u obtener una de un
servidor de imágenes como se describe en «Obtener una imagen» más arriba.

Elegir un centro:

* Por resolvedor de nombres: Usando el cuadro «Name Server», elija un servidor y
  escriba un nombre en el campo «Name».  Pulse «Search name».  Si el nombre se
  resuelve, los campos «ra» y «dec» del cuadro «Catalog Server» se rellenarán.
  Seleccione un servidor, ajuste la anchura y/o la altura, y pulse «Search
  catalog».
* Por imagen existente en el canal: Dibuje una forma en la imagen mostrada (se
  puede elegir «rectangle» o «circle» en la parte inferior de la GUI del
  complemento) y ajuste los parámetros de búsqueda como desee.  Cuando esté
  listo, pulse «Search catalog» para realizar la búsqueda.

.. note:: El resultado de la búsqueda puede tardar algún tiempo en terminar,
          según el tamaño del campo, las condiciones de la red, etc.
          Normalmente, si la búsqueda falla, aparecerá un error en el
          complemento Errors.

Cuando los resultados de la búsqueda estén disponibles, se mostrarán en la
imagen y también se listarán en una tabla de la GUI del complemento.  Puede hacer
clic en la tabla o en la imagen para resaltar la selección.

**Configuración del usuario**

Es personalizable usando ``~/.ginga/plugin_Catalogs.cfg``, donde ``~`` es su
directorio HOME:

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
