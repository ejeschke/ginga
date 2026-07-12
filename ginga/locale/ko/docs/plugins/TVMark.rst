
파일에서 점(비대화형 모드)을 이미지 위에 표시합니다.

**플러그인 유형: 로컬**

``TVMark`` 은 로컬 플러그인으로, 채널에 연결되어 있습니다.
각 채널마다 하나의 인스턴스를 열 수 있습니다.

**사용법**

이 플러그인은 관심 지점의 RA 및 DEC 위치가 담긴 표를 포함하는 파일을 읽어 관심
지점을 비대화형으로 표시할 수 있게 합니다. ``astropy.table`` 로 읽을 수 있는 모든
텍스트나 FITS 테이블 파일을 사용할 수 있지만, 사용자는 플러그인 구성 파일에서 열
이름을 올바르게 정의*해야 합니다*(아래 참조). RA 및 DEC 값을 도로 변환하려고
시도합니다. 단위 변환이 실패하면 이미 도 단위인 것으로 가정합니다.

또는 파일에 직접적인 픽셀 위치가 담긴 열이 있으면 「RADEC 사용」 상자의 선택을
해제하여 대신 이 열들을 읽을 수 있습니다. 이 경우에도 열 이름은 플러그인 구성
파일에서 올바르게 정의되어야 합니다(아래 참조). 픽셀 값은 0 또는 1로 인덱싱될 수
있으며(즉, 첫 픽셀이 0인지 1인지) 구성 가능합니다(아래 참조). 이는 WCS와 관계없이
물리적 픽셀을 표시하려는 경우에 유용합니다(예: 검출기의 핫 픽셀 표시). 이미지에
WCS 정보가 있으면 RA와 DEC가 여전히 표시되지만 표시에는 영향을 주지 않습니다.

서로 다른 그룹을 표시하려면(예: 위에 표시된 것처럼 은하를 녹색 원으로, 배경을
시안색 십자로 표시):

1. 드롭다운 메뉴에서 녹색 원을 선택하십시오. 또는 원하는 크기나 너비를
   입력하십시오.
2. 해당하는 경우 「RADEC 사용」 상자가 선택되어 있는지 확인하십시오.
3. 「좌표 불러오기」 버튼을 사용하여 은하*만*의 RA 및 DEC(또는 X 및 Y) 위치가 담긴
   파일을 불러오십시오.
4. 1단계를 반복하되 이번에는 드롭다운 메뉴에서 시안색 십자를 선택하십시오.
5. 2단계를 반복하되 배경*만*의 위치가 담긴 파일을 선택하십시오.

표 목록에서 항목(또는 여러 항목)을 선택하면 이미지의 표시가 강조됩니다. 강조는
같은 모양과 색상을 사용하지만 약간 더 굵은 선을 사용합니다.

이 플러그인이 활성 상태일 때 이미지에 사각형을 그려서 이미지와 표 목록 모두에서
어떤 영역 내의 모든 표시를 강조할 수도 있습니다.

「숨기기」 버튼을 누르면 표시가 숨겨지지만 플러그인의 메모리는 지워지지 않습니다.
즉, 「표시」를 누르면 같은 표시가 같은 이미지에 다시 나타납니다. 그러나 「잊기」를
누르면 표시가 표시와 메모리 모두에서 지워집니다. 즉, 표시를 다시 만들려면 파일을
다시 불러와야 합니다.

같은 위치를 다른 표시 매개변수로 다시 그리려면 「잊기」를 누르고 필요에 따라 위
단계를 반복하십시오. 다만, 단순히 선 너비(굵기)를 바꾸려는 경우에는 새 너비 값을
입력한 후 「숨기기」를 누른 다음 「표시」를 누르면 충분합니다.

지향/차원이 매우 다른 이미지가 같은 채널에 표시되는 경우, 한 이미지에 속하지만
다른 이미지의 밖으로 벗어나는 표시는 후자에 나타나지 않습니다.

이 플러그인이 읽을 수 있는 표를 만들려면 ``Pick`` 플러그인의 결과를 사용하거나,
``astropy.table`` 등을 사용하여 손으로 표를 만들 수 있습니다.

``TVMask`` 와 함께 사용하면 Ginga에서 점원과 마스크된 영역을 모두 겹쳐 표시할 수
있습니다.

``~/.ginga/plugin_TVMark.cfg`` 를 사용하여 사용자 지정할 수 있으며, 여기서 ``~``
는 사용자의 HOME 디렉터리입니다:

.. code-block:: Python

  #
  # TVMark plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_TVMark.cfg"

  # Marking type -- 'circle' or 'cross'
  marktype = 'circle'

  # Marking color -- Any color name accepted by Ginga
  markcolor = 'green'

  # Marking size or radius
  marksize = 5

  # Marking line width (thickness)
  markwidth = 1

  # Specify whether pixel values are 0- or 1-indexed
  pixelstart = 1

  # True -- Use 'ra' and 'dec' columns to extract RA/DEC positions. This option
  #         uses image WCS to convert to pixel locations.
  # False -- Use 'x' and 'y' columns to extract pixel locations directly.
  #          This does not use WCS.
  use_radec = True

  # Columns to load into table listing (case-sensitive).
  # Whether RA/DEC or X/Y columns are used depend on associated GUI selection.
  ra_colname = 'ra'
  dec_colname = 'dec'
  x_colname = 'x'
  y_colname = 'y'
  # Extra columns to display; e.g., ['colname1', 'colname2']
  extra_columns = []
