
カタログのオブジェクト位置を画像上にプロットするためのプラグインです。

**プラグインの種類: ローカル**

``Catalogs`` はローカルプラグインで、チャンネルに関連付けられています。
チャンネルごとに 1 つのインスタンスを開けます。

.. note:: ``Catalogs`` を使うには、``astroquery`` パッケージをインストールする
          必要があります。

.. warning:: Ginga 3.2 以降での ``ginga_config.py`` 手法による ``Catalogs`` の
          構成は公式にはサポートされておらず、以前のリリースのようには動作しない
          ことがあります。下記の新しいユーザー構成の手順を参照してください。

**使い方**

**画像を取得する**

* 名前リゾルバによる: 「Name Server」ボックスでサーバーを選び、「Name」フィールドに
  名前を入力します。「Search name」を押します。名前が解決されると、「Image Server」
  ボックスの「ra」「dec」フィールドが埋められます。サーバーを選び、幅や高さを調整し、
  「Get Image」を押します。
* チャンネルの既存画像による: 表示された画像上に形状を描き（プラグイン GUI の下部で
  「rectangle」または「circle」を選べます）、検索パラメータを希望どおりに調整します。
  準備ができたら「Get Image」を押して検索を実行します。

.. note:: 画像のダウンロードは、視野の大きさやネットワーク状況などに応じて完了まで
          時間がかかることがあります。通常、検索やダウンロードが失敗すると、Errors
          プラグインにエラーがポップアップします。

画像のダウンロードに成功すると、チャンネルビューアに表示されるはずです。

**カタログからオブジェクトを取得してプロットする**

オブジェクトをプロットするには、Catalogs プラグインには、有効な WCS を持つ画像が
チャンネルに読み込まれている必要があります。自分の画像を読み込むか、上記の「画像を
取得する」で説明したように画像サーバーから取得できます。

中心を選ぶ:

* 名前リゾルバによる: 「Name Server」ボックスでサーバーを選び、「Name」フィールドに
  名前を入力します。「Search name」を押します。名前が解決されると、「Catalog
  Server」ボックスの「ra」「dec」フィールドが埋められます。サーバーを選び、幅や高さを
  調整し、「Search catalog」を押します。
* チャンネルの既存画像による: 表示された画像上に形状を描き（プラグイン GUI の下部で
  「rectangle」または「circle」を選べます）、検索パラメータを希望どおりに調整します。
  準備ができたら「Search catalog」を押して検索を実行します。

.. note:: 検索結果は、視野の大きさやネットワーク状況などに応じて完了まで時間がかかる
          ことがあります。通常、検索が失敗すると、Errors プラグインにエラーが
          ポップアップします。

検索結果が利用可能になると、画像上に表示され、プラグイン GUI の表にも一覧表示され
ます。表または画像のどちらかをクリックして選択をハイライトできます。

**ユーザー構成**

``~/.ginga/plugin_Catalogs.cfg`` を使ってカスタマイズできます。``~`` はあなたの
HOME ディレクトリです:

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
