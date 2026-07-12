
카탈로그의 객체 위치를 이미지 위에 플롯하는 플러그인입니다.

**플러그인 유형: 로컬**

``Catalogs`` 은 로컬 플러그인으로, 채널에 연결되어 있습니다.
각 채널마다 하나의 인스턴스를 열 수 있습니다.

.. note:: ``Catalogs`` 을 사용하려면 ``astroquery`` 패키지를 설치해야 합니다.

.. warning:: Ginga 3.2 이상에서 ``ginga_config.py`` 기법을 통한 ``Catalogs`` 의
          구성은 공식적으로 지원되지 않으며 이전 릴리스에서처럼 작동하지 않을 수
          있습니다. 아래의 새로운 사용자 구성 지침을 참조하십시오.

**사용법**

**이미지 가져오기**

* 이름 리졸버로: 「Name Server」 상자를 사용하여 서버를 선택하고 「Name」 필드에
  이름을 입력하십시오. 「Search name」을 누르십시오. 이름이 해결되면 「Image
  Server」 상자의 「ra」와 「dec」 필드가 채워집니다. 서버를 선택하고 너비 및/또는
  높이를 조정한 다음 「Get Image」를 누르십시오.
* 채널의 기존 이미지로: 표시된 이미지에 도형을 그리고(플러그인 GUI 하단에서
  「rectangle」 또는 「circle」을 선택할 수 있음) 검색 매개변수를 원하는 대로
  조정하십시오. 준비가 되면 「Get Image」를 눌러 검색을 수행하십시오.

.. note:: 이미지 다운로드는 시야의 크기, 네트워크 상태 등에 따라 완료되는 데 시간이
          걸릴 수 있습니다. 보통 검색이나 다운로드가 실패하면 Errors 플러그인에
          오류가 팝업됩니다.

이미지가 성공적으로 다운로드되면 채널 뷰어에 나타나야 합니다.

**카탈로그에서 객체 가져오기 및 플롯**

객체를 플롯하려면 Catalogs 플러그인에 유효한 WCS를 가진 이미지가 채널에 불러와져
있어야 합니다. 자신의 이미지를 불러오거나 위의 「이미지 가져오기」에서 설명한 대로
이미지 서버에서 하나를 가져올 수 있습니다.

중심 선택:

* 이름 리졸버로: 「Name Server」 상자를 사용하여 서버를 선택하고 「Name」 필드에
  이름을 입력하십시오. 「Search name」을 누르십시오. 이름이 해결되면 「Catalog
  Server」 상자의 「ra」와 「dec」 필드가 채워집니다. 서버를 선택하고 너비 및/또는
  높이를 조정한 다음 「Search catalog」를 누르십시오.
* 채널의 기존 이미지로: 표시된 이미지에 도형을 그리고(플러그인 GUI 하단에서
  「rectangle」 또는 「circle」을 선택할 수 있음) 검색 매개변수를 원하는 대로
  조정하십시오. 준비가 되면 「Search catalog」을 눌러 검색을 수행하십시오.

.. note:: 검색 결과는 시야의 크기, 네트워크 상태 등에 따라 완료되는 데 시간이 걸릴
          수 있습니다. 보통 검색이 실패하면 Errors 플러그인에 오류가 팝업됩니다.

검색 결과가 사용 가능해지면 이미지에 표시되고 플러그인 GUI의 표에도 나열됩니다.
표나 이미지 중 하나를 클릭하여 선택을 강조할 수 있습니다.

**사용자 구성**

``~/.ginga/plugin_Catalogs.cfg`` 를 사용하여 사용자 지정할 수 있으며, 여기서
``~`` 는 사용자의 HOME 디렉터리입니다:

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
