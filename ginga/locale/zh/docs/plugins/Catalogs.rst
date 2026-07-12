
用于将目录中的对象位置绘制到图像上的插件。

**插件类型：本地**

``Catalogs`` 是本地插件，这意味着它与某个通道相关联。
可以为每个通道打开一个实例。

.. note:: 要使用 ``Catalogs``，必须安装 ``astroquery`` 软件包。

.. warning:: 在 Ginga 3.2 或更高版本中通过 ``ginga_config.py`` 技术配置
          ``Catalogs`` 未获得官方支持，可能无法像以前的版本那样工作。请参见下面
          新的用户配置说明。

**用法**

**获取图像**

* 通过名称解析器：使用「Name Server」框，选择一个服务器并在「Name」字段中键入一个
  名称。按「Search name」。如果名称被解析，「Image Server」框中的「ra」和「dec」
  字段将被填充。选择一个服务器，调整宽度和/或高度，然后按「Get Image」。
* 通过通道中的现有图像：在显示的图像上绘制一个形状（可在插件 GUI 底部选择
  「rectangle」或「circle」），并根据需要调整搜索参数。准备就绪后，按「Get Image」
  执行搜索。

.. note:: 图像下载可能需要一些时间才能完成，具体取决于视场大小、网络状况等。通常，
          如果搜索或下载失败，将会在 Errors 插件中弹出错误。

如果图像下载成功，它应出现在通道查看器中。

**从目录获取并绘制对象**

要绘制对象，Catalogs 插件需要在通道中加载一幅具有有效 WCS 的图像。您可以加载自己
的图像，也可以按上文「获取图像」中所述从图像服务器获取一幅。

选择中心：

* 通过名称解析器：使用「Name Server」框，选择一个服务器并在「Name」字段中键入一个
  名称。按「Search name」。如果名称被解析，「Catalog Server」框中的「ra」和「dec」
  字段将被填充。选择一个服务器，调整宽度和/或高度，然后按「Search catalog」。
* 通过通道中的现有图像：在显示的图像上绘制一个形状（可在插件 GUI 底部选择
  「rectangle」或「circle」），并根据需要调整搜索参数。准备就绪后，按「Search
  catalog」执行搜索。

.. note:: 搜索结果可能需要一些时间才能完成，具体取决于视场大小、网络状况等。通常，
          如果搜索失败，将会在 Errors 插件中弹出错误。

当搜索结果可用时，它们将显示在图像上，并且也会在插件 GUI 的表格中列出。您可以单击
表格或图像来高亮显示选择。

**用户配置**

它可使用 ``~/.ginga/plugin_Catalogs.cfg`` 进行自定义，其中 ``~`` 是您的 HOME
目录：

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
