
``Contents`` プラグインは、プログラム開始以降に表示したすべての画像に対する目次の
ようなインターフェースを提供します。``Thumbs`` とは異なり、``Contents`` はチャン
ネル順に並べられます。内容には、画像から取得した構成可能なメタデータも表示され
ます。

**プラグインの種類: グローバル**

``Contents`` はグローバルプラグインです。開けるインスタンスは 1 つだけです。

**使い方**

列の見出しをクリックすると、表をその列で並べ替えます。もう一度クリックすると逆順に
並べ替えます。

.. note:: 列とその値は、該当する場合は FITS ヘッダから取得されます。これは、設定
          ファイル「plugin_Contents.cfg」の「columns」パラメータを設定することで
          カスタマイズできます。

現在フォーカスされているチャンネルのアクティブな画像は、通常ハイライトされます。
画像をダブルクリックすると、その画像が関連するチャンネルに強制的に表示されます。
いずれかの画像をシングルクリックすると、UI 下部のボタンが有効になります:

* 「表示」: その画像をアクティブな画像にします。
* 「移動」: 画像を別のチャンネルに移動します。
* 「コピー」: 画像を別のチャンネルにコピーします。
* 「削除」: 画像をチャンネルから削除します。

Ginga で変更された画像（使用していれば ``ChangeHistory`` にエントリを持つはず）に
対して「移動」や「コピー」を行うと、変更履歴も保持されます。チャンネルから画像を
削除すると、保存されていない変更はすべて失われます。

このプラグインは通常、閉じられるようには構成されていませんが、設定ファイルで
「closeable」設定を True にすることで、そうできます。すると UI の下部に「閉じる」
ボタンと「ヘルプ」ボタンが追加されます。

**Contents から画像を除外する**

.. note:: これは ``Thumbs`` の動作も制御します。

既定の動作では、リファレンスビューアに読み込まれたすべての画像が ``Contents`` に
表示されますが、これが望ましくない場合もあります（例: 何らかの自動プロセスによって
多数の画像が周期的な間隔で読み込まれる場合）。そのような場合、特定の画像が
``Contents`` に表示されないよう抑制する仕組みが 2 つあります:

* チャンネルの設定で「genthumb」設定を False にする（例えば ``Preferences``
  プラグインの「General」設定から）と、そのチャンネル自体とそのすべての画像を除外
  します。
* 画像ラッパーのメタデータで「nothumb」キーワードを設定する（FITS ヘッダではなく、
  例えば ``image.set(nothumb=True)`` で）と、そのチャンネルの「genthumb」設定が
  True であっても、その特定の画像を ``Contents`` から除外します。

``~/.ginga/plugin_Contents.cfg`` を使ってカスタマイズできます。``~`` はあなたの
HOME ディレクトリです:

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
