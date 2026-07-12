
``Thumbs`` 플러그인은 프로그램이 시작된 이후 본 모든 이미지의 썸네일 인덱스를
제공합니다.

**플러그인 유형: 전역**

``Thumbs`` 는 전역 플러그인입니다. 하나의 인스턴스만 열 수 있습니다.

**사용법**

기본적으로 ``Thumbs`` 는 시간순 보기 기록으로 나타나며, 가장 새로운 이미지가 아래,
가장 오래된 이미지가 위에 옵니다. 정렬은 「plugin_Thumbs.cfg」 구성 파일의 설정으로
영숫자순으로 만들 수 있습니다.

썸네일을 클릭하면 연결된 채널의 그 이미지로 바로 이동합니다. 썸네일 위에 커서를
올리면 이미지에서 가져온 몇 가지 유용한 메타데이터가 담긴 도구 설명이 표시됩니다.

「자동 스크롤」 체크박스가 선택되어 있으면 ``Thumbs`` 창이 활성 이미지까지
스크롤됩니다.

이 플러그인은 보통 닫을 수 있도록 구성되어 있지 않지만, 사용자가 구성 파일에서
「closeable」 설정을 True로 설정하여 그렇게 만들 수 있습니다. 그러면 UI 하단에
닫기 및 도움말 버튼이 추가됩니다.

**Thumbs에서 이미지 제외**

.. note:: 이는 ``Contents`` 의 동작도 제어합니다.

기본 동작은 참조 뷰어에 불러온 모든 이미지가 ``Thumbs`` 에 표시되는 것이지만,
이것이 바람직하지 않은 경우가 있을 수 있습니다(예: 어떤 자동화된 프로세스에 의해
많은 이미지가 주기적으로 불러와지는 경우). 그러한 경우 특정 이미지가 ``Thumbs``
에 표시되지 않도록 억제하는 두 가지 메커니즘이 있습니다:

* 채널 설정에서 「genthumb」 설정을 False로 지정하면(예를 들어 ``Preferences``
  플러그인의 「General」 설정에서) 채널 자체와 그 모든 이미지가 제외됩니다.
* 이미지 래퍼의 메타데이터에서 「nothumb」 키워드를 설정하면(FITS 헤더가 아니라
  예를 들어 ``image.set(nothumb=True)`` 로) 해당 채널의 「genthumb」 설정이
  True이더라도 그 특정 이미지가 ``Thumbs`` 에서 제외됩니다.

``~/.ginga/plugin_Thumbs.cfg`` 를 사용하여 사용자 지정할 수 있으며, 여기서 ``~``
는 사용자의 HOME 디렉터리입니다:

.. code-block:: Python

  #
  # Thumbs plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_Thumbs.cfg"

  # If you revisit the same directories frequently
  # caching thumbs saves a lot of time when they need to be regenerated
  cache_thumbs = False

  # cache location-- "local" puts them in a .thumbs subfolder, otherwise
  # they are cached in ~/.ginga/thumbs
  cache_location = 'local'

  # Scroll the pane automatically when new thumbnails arrive
  auto_scroll = True

  # Keywords to extract and show if we mouse over the thumbnail
  tt_keywords = ['OBJECT', 'FRAMEID', 'UT', 'DATE-OBS']

  # Mandatory unique image identifier in tooltip
  mouseover_name_key = 'NAME'

  # How many seconds to wait after an image is altered to begin trying
  # to rebuild a matching thumb.  Usually a few seconds is good in case
  # there is ongoing adjustment of the image
  rebuild_wait = 0.5

  # Max length of thumb on the long side
  thumb_length = 180

  # Separation between thumbs in pixels
  thumb_hsep = 15
  thumb_vsep = 15

  # Sort the thumbs alphabetically: 'alpha' or None
  sort_order = None

  # Thumbnail label length in num of characters (None = no limit)
  label_length = 25

  # Cut off long label ('left', 'right', or None)
  label_cutoff = 'right'

  # Option to highlight images that are displayed in channels.
  # If set to True this option will only highlight the image that is in the
  # channel with the keyboard focus
  highlight_tracks_keyboard_focus = True

  # Highlighted label colors
  label_bg_color = 'lightgreen'
  label_font_color = 'white'

  label_font_size = 10

  # Load visible thumbs in the background to replace placeholder icons
  autoload_visible_thumbs = True

  # Length of time to wait after scrolling to begin autoloading
  autoload_interval = 1.0

  # list of attributes to transfer from the channel viewer to the
  # thumbnail generator if the channel has an image in it
  transfer_attrs = ['transforms', 'cutlevels', 'rgbmap']

  # Add a close button to this plugin, so that it can be stopped
  closeable = False
