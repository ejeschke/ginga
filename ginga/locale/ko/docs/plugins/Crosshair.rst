
``Crosshair`` 은 십자의 위치를 픽셀 좌표, WCS 좌표 또는 십자 위치의 데이터 값으로
레이블한 십자선을 그리는 간단한 플러그인입니다.

**플러그인 유형: 로컬**

``Crosshair`` 은 로컬 플러그인으로, 채널에 연결되어 있습니다.
각 채널마다 하나의 인스턴스를 열 수 있습니다.

**사용법**

UI의 「Format」 드롭다운 상자에서 적절한 출력 유형을 선택하십시오: 픽셀 좌표는
「xy」, WCS 좌표는 「coords」, 십자선 위치의 값은 「value」.

「끌기만」이 선택되어 있으면 십자선은 창에서 커서를 클릭하거나 끌 때만
업데이트됩니다. 선택 해제되어 있으면 십자선은 채널 뷰어 창에서 커서를 움직이기만
하면 배치됩니다.

「Cuts」 탭에는 「Quick Cuts」가 선택되어 있을 때 나타나는 보이는 상자 경계로
표현되는 수직 및 수평 컷의 프로파일 플롯이 포함됩니다. 이 플롯은 십자선이 움직임에
따라 실시간으로 업데이트됩니다. 「Quick Cuts」가 선택 해제되어 있으면 플롯은
업데이트되지 않습니다.

상자의 크기는 「radius」 매개변수에 의해 결정됩니다.

「경고 수준」 컨트롤은 그것을 초과하면 Cuts 플롯에 노란색 선과 노란색으로 변하는
배경으로 경고가 표시되는 플럭스 수준을 설정하는 데 사용할 수 있습니다. X 또는 Y
컷을 따라 어떤 값이든 경고 수준 임계값을 초과하면 경고가 트리거됩니다.

「알림 수준」 컨트롤은 비슷하지만 빨간색 선과 분홍색으로 변하는 배경으로
표현됩니다. X 또는 Y 컷을 따라 어떤 값이든 알림 수준 임계값을 초과하면 경고가
트리거됩니다. 알림은 경고보다 우선합니다.

「경고」 기능과 「알림」 기능은 모두 빈 값을 설정하기만 하면 끌 수 있습니다.
기본적으로 꺼져 있습니다.

Cuts 플롯은 대화형이지만, 「끌기만」이 선택되어 있을 때만 사용하는 것이 실제로
의미가 있습니다. 플롯 창에서 「x」 또는 「y」를 누르면 어느 한 축의 자동 축 스케일링
기능을 켜고 끌 수 있으며, 플롯에서 스크롤하면 X축을 확대할 수 있습니다(스크롤하는
동안 Ctrl을 누르고 있으면 Y축 확대).

Crosshair 은 Pick 플러그인 상호 작용 기능을 제공합니다: 십자선이 객체 위에 있을 때
채널 뷰어 창에서 「r」을 누르면 그 특정 위치에서 Pick 플러그인이 호출됩니다. 그
채널에 Pick이 아직 열려 있지 않으면 먼저 열립니다.

**사용자 구성**

``~/.ginga/plugin_Crosshair.cfg`` 를 사용하여 사용자 지정할 수 있으며, 여기서
``~`` 는 사용자의 HOME 디렉터리입니다:

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
