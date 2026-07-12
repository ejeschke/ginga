
``Crosshair`` は、十字の位置をピクセル座標、WCS 座標、または十字位置のデータ値で
ラベル付けした照準線を描くシンプルなプラグインです。

**プラグインの種類: ローカル**

``Crosshair`` はローカルプラグインで、チャンネルに関連付けられています。
チャンネルごとに 1 つのインスタンスを開けます。

**使い方**

UI の「Format」ドロップダウンボックスで適切な出力タイプを選びます: ピクセル座標
なら「xy」、WCS 座標なら「coords」、照準線位置の値なら「value」。

「ドラッグのみ」がチェックされている場合、照準線はウィンドウ内でカーソルがクリック
またはドラッグされたときにのみ更新されます。チェックされていない場合、照準線は
チャンネルビューアウィンドウ内でカーソルを動かすだけで配置されます。

「Cuts」タブには、「Quick Cuts」がチェックされているときに表示される可視ボックス
境界で表される垂直・水平カットのプロファイルプロットが含まれます。このプロットは、
照準線が動かされるとリアルタイムで更新されます。「Quick Cuts」がチェックされて
いない場合、プロットは更新されません。

ボックスのサイズは「radius」パラメータによって決まります。

「警告レベル」コントロールは、それを超えると Cuts プロットに黄色の線と黄色に変わる
背景で警告が示されるフラックスレベルを設定するために使えます。X または Y カットに
沿ったいずれかの値が警告レベルのしきい値を超えると、警告がトリガーされます。

「アラートレベル」コントロールは似ていますが、赤い線と桃色に変わる背景で表され
ます。X または Y カットに沿ったいずれかの値がアラートレベルのしきい値を超えると、
警告がトリガーされます。アラートは警告より優先されます。

「警告」機能と「アラート」機能の両方は、空の値を設定するだけでオフにできます。
既定ではオフです。

Cuts プロットは対話的ですが、それを使うのは「ドラッグのみ」がチェックされている
場合にのみ意味があります。プロットウィンドウで「x」または「y」を押すと、いずれかの
軸の自動軸スケーリング機能のオン／オフを切り替えられ、プロット内でスクロールすると
X 軸をズームできます（スクロール中に Ctrl を押し続けると Y 軸をズーム）。

Crosshair は Pick プラグインとの連携機能を提供します: 照準線がオブジェクトの上に
あるとき、チャンネルビューアウィンドウで「r」を押すと、その特定の位置で Pick
プラグインを呼び出せます。そのチャンネルで Pick がまだ開かれていない場合は、先に
開かれます。

**ユーザー構成**

``~/.ginga/plugin_Crosshair.cfg`` を使ってカスタマイズできます。``~`` はあなたの
HOME ディレクトリです:

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
