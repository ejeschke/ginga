
``Histogram`` 은 이미지에 그린 영역 또는 이미지 전체에 대한 히스토그램을
플롯합니다.

**플러그인 유형: 로컬**

``Histogram`` 은 로컬 플러그인으로, 채널에 연결되어 있습니다.
싱글턴이 아니므로 각 채널마다 여러 인스턴스를 열 수 있습니다.

**사용법**

클릭하고 끌어서 히스토그램 계산에 사용할 영역을 이미지 안에 정의하십시오. 전체
이미지의 히스토그램을 취하려면 UI에서 「전체 이미지」라고 표시된 버튼을
클릭하십시오.

.. note:: 이미지 크기에 따라 전체 히스토그램 계산에 시간이 걸릴 수 있습니다.

채널에 새 이미지가 선택되면 히스토그램 플롯이 새 데이터로 현재 매개변수에 기반하여
다시 계산됩니다.

히스토그램 플러그인의 설정 파일에서 비활성화하지 않는 한, 상자에 대한 간단한 통계
한 줄이 계산되어 플롯 아래 줄에 표시됩니다.

**UI 컨트롤**

UI 하단의 세 개의 라디오 버튼은 클릭/끌기 동작의 효과를 제어하는 데 사용됩니다:

* 영역을 다른 위치로 끌려면 「이동」을 선택하십시오
* 새 영역을 그리려면 「그리기」를 선택하십시오
* 영역을 편집하려면 「편집」을 선택하십시오

히스토그램의 로그 플롯을 만들려면 「로그 히스토그램」 체크박스를 선택하십시오. 컷
값 범위 내가 아니라 이미지의 전체 값 범위로 플롯하려면 「컷으로 플롯」 체크박스의
선택을 해제하십시오.

「NumBins」 매개변수는 히스토그램 계산에 사용되는 빈의 수를 결정합니다. 상자에
숫자를 입력하고 「Enter」를 눌러 기본값을 변경하십시오.

**컷 레벨 편의 컨트롤**

히스토그램은 컷 레벨을 설정하는 데 유용한 피드백이므로, UI에는 이미지의 낮은 및
높은 컷 레벨을 설정하는 컨트롤과, 채널 기본 설정의 자동 컷 레벨 설정에 따라 자동
컷 레벨을 수행하는 컨트롤이 제공됩니다.

히스토그램 플롯을 클릭하여 컷 레벨을 설정할 수 있습니다:

* 왼쪽 클릭: 낮은 컷 설정
* 가운데 클릭: 재설정(자동 컷 레벨)
* 오른쪽 클릭: 높은 컷 설정

또한, 플롯에서 휠을 스크롤하여 낮은 컷과 높은 컷 사이의 간격(즉, 히스토그램 플롯
곡선의 「너비」)을 동적으로 조정할 수 있습니다. 이는 이미지 내의 대비를 늘리거나
줄이는 효과가 있습니다. 각 휠 클릭마다 변경되는 양은 플러그인 구성 파일 설정
``scroll_pct`` 로 설정됩니다. 기본값은 10 %입니다.

**사용자 구성**

``~/.ginga/plugin_Histogram.cfg`` 를 사용하여 사용자 지정할 수 있으며, 여기서
``~`` 는 사용자의 HOME 디렉터리입니다:

.. code-block:: Python

  #
  # Histogram plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_Histogram.cfg"

  # Switch to "move" mode after selection
  draw_then_move = True

  # Number of bins for histogram
  num_bins = 2048

  # Histogram color
  hist_color = 'aquamarine'

  # Calculate extra statistics on box
  show_stats = True

  # Controls formatting (width) of statistics numbers
  maxdigits = 7

  # percentage to adjust cuts gap when scrolling in histogram
  scroll_pct = 0.10
