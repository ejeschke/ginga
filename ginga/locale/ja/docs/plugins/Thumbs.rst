
``Thumbs`` プラグインは、プログラム開始以降に表示したすべての画像のサムネイル
インデックスを提供します。

**プラグインの種類: グローバル**

``Thumbs`` はグローバルプラグインです。開けるインスタンスは 1 つだけです。

**使い方**

既定では、``Thumbs`` は時系列の表示履歴で現れ、最新の画像が下、最も古い画像が上に
なります。並べ替えは、構成ファイル「plugin_Thumbs.cfg」の設定で英数字順にできます。

サムネイルをクリックすると、関連するチャンネルのその画像に直接移動します。
サムネイルの上にカーソルを重ねると、画像からの便利なメタデータをいくつか含む
ツールチップが表示されます。

「自動スクロール」チェックボックスがチェックされている場合、``Thumbs`` のペインが
アクティブな画像までスクロールします。

このプラグインは通常、閉じられるようには構成されていませんが、設定ファイルで
「closeable」設定を True にすることで、そうできます。すると UI の下部に「閉じる」
ボタンと「ヘルプ」ボタンが追加されます。

**Thumbs から画像を除外する**

.. note:: これは ``Contents`` の動作も制御します。

既定の動作では、リファレンスビューアに読み込まれたすべての画像が ``Thumbs`` に
表示されますが、これが望ましくない場合もあります（例: 何らかの自動プロセスによって
多数の画像が周期的な間隔で読み込まれる場合）。そのような場合、特定の画像が
``Thumbs`` に表示されないよう抑制する仕組みが 2 つあります:

* チャンネルの設定で「genthumb」設定を False にする（例えば ``Preferences``
  プラグインの「General」設定から）と、そのチャンネル自体とそのすべての画像を除外
  します。
* 画像ラッパーのメタデータで「nothumb」キーワードを設定する（FITS ヘッダではなく、
  例えば ``image.set(nothumb=True)`` で）と、そのチャンネルの「genthumb」設定が
  True であっても、その特定の画像を ``Thumbs`` から除外します。

``~/.ginga/plugin_Thumbs.cfg`` を使ってカスタマイズできます。``~`` はあなたの
HOME ディレクトリです:

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
