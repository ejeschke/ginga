
``Contents`` 플러그인은 프로그램이 시작된 이후 본 모든 이미지에 대한 목차와 같은
인터페이스를 제공합니다. ``Thumbs`` 와 달리 ``Contents`` 는 채널별로 정렬됩니다.
내용에는 이미지에서 가져온 일부 구성 가능한 메타데이터도 표시됩니다.

**플러그인 유형: 전역**

``Contents`` 는 전역 플러그인입니다. 하나의 인스턴스만 열 수 있습니다.

**사용법**

열 머리글을 클릭하면 표를 해당 열 기준으로 정렬합니다. 다시 클릭하면 반대 방향으로
정렬합니다.

.. note:: 열과 그 값은 해당하는 경우 FITS 헤더에서 가져옵니다. 이는 설정 파일
          「plugin_Contents.cfg」에서 「columns」 매개변수를 설정하여 사용자 지정할
          수 있습니다.

현재 포커스된 채널의 활성 이미지는 보통 강조 표시됩니다. 이미지를 더블 클릭하면 그
이미지가 연결된 채널에 강제로 표시됩니다. 어떤 이미지든 한 번 클릭하면 UI 하단의
버튼이 활성화됩니다:

* 「표시」: 이미지를 활성 이미지로 만듭니다.
* 「이동」: 이미지를 다른 채널로 이동합니다.
* 「복사」: 이미지를 다른 채널로 복사합니다.
* 「제거」: 채널에서 이미지를 제거합니다.

Ginga에서 수정된 이미지(사용했다면 ``ChangeHistory`` 아래에 항목이 있을)에 대해
「이동」이나 「복사」를 수행하면 수정 기록도 유지됩니다. 채널에서 이미지를 제거하면
저장되지 않은 모든 변경 사항이 파괴됩니다.

이 플러그인은 보통 닫을 수 있도록 구성되어 있지 않지만, 사용자가 구성 파일에서
「closeable」 설정을 True로 설정하여 그렇게 만들 수 있습니다. 그러면 UI 하단에
닫기 및 도움말 버튼이 추가됩니다.

**Contents에서 이미지 제외**

.. note:: 이는 ``Thumbs`` 의 동작도 제어합니다.

기본 동작은 참조 뷰어에 불러온 모든 이미지가 ``Contents`` 에 표시되는 것이지만,
이것이 바람직하지 않은 경우가 있을 수 있습니다(예: 어떤 자동화된 프로세스에 의해
많은 이미지가 주기적으로 불러와지는 경우). 그러한 경우 특정 이미지가 ``Contents``
에 표시되지 않도록 억제하는 두 가지 메커니즘이 있습니다:

* 채널 설정에서 「genthumb」 설정을 False로 지정하면(예를 들어 ``Preferences``
  플러그인의 「General」 설정에서) 채널 자체와 그 모든 이미지가 제외됩니다.
* 이미지 래퍼의 메타데이터에서 「nothumb」 키워드를 설정하면(FITS 헤더가 아니라
  예를 들어 ``image.set(nothumb=True)`` 로) 해당 채널의 「genthumb」 설정이
  True이더라도 그 특정 이미지가 ``Contents`` 에서 제외됩니다.

``~/.ginga/plugin_Contents.cfg`` 를 사용하여 사용자 지정할 수 있으며, 여기서
``~`` 는 사용자의 HOME 디렉터리입니다:

.. code-block:: Python

  #
  # Contents plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_Contents.cfg"

  # columns to show from metadata -- NAME and MODIFIED recommended
  # format: [(col header, keyword1), ... ]
  columns = [ ('Name', 'NAME'), ('Object', 'OBJECT'), ('Filter', 'FILTER01'), ('Date', 'DATE-OBS'), ('Time UT', 'UT'), ('Modified', 'MODIFIED')]

  # If set to True, will always expand the tree in Contents when new entries are added
  always_expand = True

  # Option to highlight images that are displayed in channels.
  # If set to True this option will only highlight the image that is in the
  # channel with the keyboard focus
  highlight_tracks_keyboard_focus = False

  # If True, color every other row in alternating shades to improve
  # readability of long tables
  color_alternate_rows = True

  # Highlighted row colors (in addition to bold text)
  row_font_color = 'green'

  # Maximum number of rows that will turn off auto column resizing (for speed)
  max_rows_for_col_resize = 100

  # Add a close button to this plugin, so that it can be stopped
  closeable = False
