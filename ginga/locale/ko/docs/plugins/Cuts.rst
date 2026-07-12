
선이나 경로를 따라 값의 플롯을 생성하는 플러그인입니다.

**플러그인 유형: 로컬**

``Cuts`` 은 로컬 플러그인으로, 채널에 연결되어 있습니다.
싱글턴이 아니므로 각 채널마다 여러 인스턴스를 열 수 있습니다.

**사용법**

``Cuts`` 은 이미지를 가로질러 그린 선에 대해 픽셀 값 대 인덱스의 간단한 그래프를
플롯합니다. 여러 컷을 플롯할 수 있습니다.

사용할 수 있는 컷에는 네 가지가 있습니다: line, path, freepath, beziercurve:

* 「line」 컷은 두 점 사이의 직선입니다.
* 「path」 컷은 사이에 직선 세그먼트가 있는 열린 다각형처럼 그려집니다.
* 「freepath」 컷은 path 컷과 비슷하지만, 커서 움직임을 따르는 자유형 스트로크로
  그려집니다.
* 「beziercurve」 경로는 3차 베지에 곡선입니다.

플러그인이 활성 상태일 때 채널에 새 이미지가 추가되면 새 이미지에서 새로 계산된
컷으로 업데이트됩니다.

「enable slit」 설정이 활성화되어 있으면 이 플러그인은 「Slit」 탭을 통해 슬릿
이미지 기능(다차원 이미지용)도 허용합니다. 탭 UI에서 「Axes」 목록에서 축 하나를
선택하고 선을 그리십시오. 이렇게 하면 처음 두 축이 공간적이라고 가정하고 선택한
축을 따라 데이터를 인덱싱하는 2D 이미지가 만들어집니다. ``Cuts`` 과 마찬가지로 컷
선택 드롭다운 상자를 사용하여 다른 슬릿 이미지를 볼 수 있습니다.

**컷 그리기**

「New Cut Type」 메뉴로 어떤 종류의 컷을 그릴지 선택할 수 있습니다.

새 컷을 그리려면 「Cut」 드롭다운 메뉴에서 「New Cut」을 선택하십시오. 그렇지
않고 특정 이름의 컷이 선택되어 있으면 새로 그린 컷으로 대체됩니다.

path 또는 beziercurve 컷을 그리는 동안 「v」를 눌러 정점을 추가하거나, 「z」를 눌러
마지막으로 추가한 정점을 제거하십시오.

**키보드 단축키**

커서를 올린 상태에서 「h」를 누르면 전체 수평 컷, 「j」를 누르면 전체 수직 컷이
됩니다.

**컷 삭제**

컷을 삭제하려면 「Cut」 드롭다운에서 그 이름을 선택하고 「삭제」 버튼을
클릭하십시오. 모든 컷을 삭제하려면 「모두 삭제」를 누르십시오.

**컷 편집**

캔버스 편집 기능을 사용하면 기존 경로에 새 정점을 추가하고 정점을 이동할 수
있습니다. 「편집」 라디오 버튼을 클릭하여 캔버스를 편집 모드로 전환하십시오. 컷이
자동으로 선택되지 않으면 이제 선, 경로 또는 곡선을 클릭하여 선택할 수 있으며, 그
끝이나 정점의 제어점이 활성화되어야 합니다 -- 이것들을 끌 수 있습니다. 경로에 새
정점을 추가하려면 새 정점을 원하는 선 위에 커서를 조심스럽게 올리고 「v」를
누르십시오. 정점을 없애려면 그 위에 커서를 올리고 「z」를 누르십시오.

대부분의 객체에서 중심이 다른 색인 추가 제어점 하나를 볼 수 있습니다 -- 이것은
편집 모드에서 전체 객체를 이미지 위에서 이동시키기 위한 이동 제어점입니다.

「이동」을 선택하여 컷을 변경 없이 그냥 이동할 수도 있습니다.

**컷의 너비 변경**

「line」 컷의 너비는 「Width Type」 메뉴를 사용하여 변경할 수 있습니다:

* 「none」은 반지름이 0인 컷을 나타냅니다. 즉, 선을 따라 픽셀 값만 표시합니다
* 「x」는 컷에 직교하는 X축을 따라 값의 합을 플롯합니다.
* 「y」는 컷에 직교하는 Y축을 따라 값의 합을 플롯합니다.
* 「perpendicular」는 컷에 수직인 축을 따라 값의 합을 플롯합니다.

「Width radius」는 컷의 양쪽으로 일정량만큼 직교 합산의 너비를 제어합니다 --
1은 3픽셀, 2는 5픽셀 등이 됩니다.

**컷 저장**

「저장」 버튼을 사용하여 ``Cuts`` 플롯을 이미지로, 데이터를 Numpy 압축 아카이브로
저장하십시오.

**컷 복사**

컷을 복사하려면 「Cut」 드롭다운에서 그 이름을 선택하고 「컷 복사」 버튼을
클릭하십시오. 그것으로부터 새 컷이 만들어집니다. 그런 다음 새 컷을 독립적으로
조작할 수 있습니다.

**사용자 구성**

``~/.ginga/plugin_Cuts.cfg`` 를 사용하여 사용자 지정할 수 있으며, 여기서 ``~`` 는
사용자의 HOME 디렉터리입니다:

.. code-block:: Python

  #
  # Cuts plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_Cuts.cfg"

  # If set to True will always select a cut after drawing it
  select_new_cut = True

  # If set to True will automatically change to "move" mode after draw
  draw_then_move = True

  # If set to True will label cuts with a text annotation
  label_cuts = True

  # If set to True will add a legend to the cuts plot
  show_cuts_legend = False

  # If set to True will add Slit tab
  enable_slit = False

  # Default cut colors
  colors = ['magenta', 'skyblue2', 'chartreuse2', 'cyan', 'pink', 'burlywood2', 'yellow3', 'turquoise', 'coral1', 'mediumpurple2']

  # If set to True, will update graph continuously as cursor is dragged
  # around image
  drag_update = False
