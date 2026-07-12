簡単な天文の恒星解析を実行します。

**プラグインの種類: ローカル**

``Pick`` はローカルプラグインで、チャンネルに関連付けられています。
シングルトンではないため、チャンネルごとに複数のインスタンスを開けます。

**使い方**

``Pick`` プラグインは、恒星オブジェクトについて簡単な天文データ品質解析を実行する
ために使います。描いた箱の中で恒星候補を見つけ、一連の検索設定に基づいて最も
可能性の高い候補を選びます。候補オブジェクトについて半値全幅（FWHM）が報告され、
検出器のプレートスケールに基づくそのサイズも報告されます。背景・空レベル・明るさの
おおまかな測定も行われます。

**Pick 領域を定義する**

既定の Pick 領域は、検索領域を囲むおよそ 30x30 ピクセルの箱として定義されます。

プラグイン下部の移動／描画／編集セレクタは、Pick 領域に対してどの操作を行うかを
決めるために使います:

.. figure:: figures/pick-move-draw-edit.png
   :width: 400px
   :align: center
   :alt: 「移動」「描画」「編集」ボタン

   「移動」「描画」「編集」ボタン。

* 「移動」が選択されている場合、既存の Pick 領域をドラッグして移動したり、中心を
  置きたい場所をクリックしたりできます。既存の領域がない場合は、既定の領域が作成
  されます。
* 「描画」が選択されている場合、カーソルで形状を描いて新しい Pick 領域を囲んで
  定義できます。既定の形状は箱ですが、「Settings」タブで他の形状を選べます。
* 「編集」が選択されている場合、コントロール点をドラッグして Pick 領域を編集したり、
  バウンディングボックス内をドラッグして移動したりできます。

領域を移動・描画・編集した後、``Pick`` は領域内のすべてのピークを検索し、UI の
「Settings」タブの基準（下記「Settings タブ」参照）に基づいてピークを評価し、設定に
最も一致する最良の候補を見つけようとします。

.. note:: 「Quick Mode」と「From Peak」チェックボックスは Ginga リリース v4.0 で
          削除されました。

**候補が見つかった場合**

候補は、水平・垂直の FWHM 測定によって決められたオブジェクトを中心に、チャンネル
ビューアのキャンバスに点（通常は「X」）でマークされます。

UI の上部のタブ群は、次のように埋められます:

.. figure:: figures/pick-cutout.png
   :width: 400px
   :align: center
   :alt: Pick 領域の Image タブ

   ``Pick`` 領域の「Image」タブ。

「Image」タブは切り出し領域の内容を表示します。このタブのウィジェットは Ginga
ウィジェットなので、通常のキーボード・マウスのバインディング（例: スクロール
ホイール）でズームやパンができます。オブジェクトを中心とした点でもマークされ、
さらにパン位置が見つかった中心に設定されます。

.. figure:: figures/pick-contour.png
   :width: 300px
   :align: center
   :alt: Pick 領域の Contour タブ

   ``Pick`` 領域の「Contour」タブ。

「Contour」タブは等高線プロットを表示します。これは候補のすぐ周囲の領域の等高線
プロットで、通常は Pick 領域の全体を含みません。スクロールホイールでプロットを
ズームでき、スクロールホイールのクリック（マウスボタン 2）でプロット内のパン位置を
設定できます。

.. figure:: figures/pick-fwhm.png
   :width: 400px
   :align: center
   :alt: Pick 領域の FWHM タブ

   ``Pick`` 領域の「FWHM」タブ。

「FWHM」タブは FWHM プロットを表示します。紫の線は X 方向の測定、緑の線は Y 方向の
測定を示します。実線は実際のピクセル値、点線は当てはめた 1D 関数を示します。陰影の
ついた紫と緑の領域は、それぞれの軸の FWHM 測定を示します。

.. figure:: figures/pick-radial.png
   :width: 400px
   :align: center
   :alt: Pick 領域の Radial タブ

   ``Pick`` 領域の「Radial」タブ。

「Radial」タブは動径プロファイルプロットを含みます。紫でプロットされた点はデータ値
で、データに線が当てはめられます。

.. figure:: figures/pick-ee.png
   :width: 600px
   :align: center
   :alt: Pick 領域の EE タブ

   ``Pick`` 領域の「EE」タブ。

「EE」タブは、選んだターゲットについて、それぞれ紫と緑で、割合としての囲み円内・
囲み四角内エネルギー（EE）のプロットを含みます。EE 値を測定する前に、FWHM 計算と
整合する方法で単純な背景減算が行われます。黒の破線で示されるサンプリング半径と
全体半径は「Settings」タブで設定でき、これらを変更したら「Redo Pick」をクリックして
プロットと測定を更新します。指定したサンプリング半径での測定 EE 値は「Readout」
タブにも表示されます。レポートが要求されると、指定したサンプリング半径での EE 値と
半径自体が、他の情報とともに「Report」テーブルに記録されます。

「Show Candidates」が有効な場合、バウンディングボックスの端に近い候補は EE 値を持ち
ません（0 に設定）。

.. figure:: figures/pick-readout.png
   :width: 400px
   :align: center
   :alt: Pick 領域の Readout タブ

   ``Pick`` 領域の「Readout」タブ。

「Readout」タブは、測定の要約で埋められます。このタブには 2 つのボタンと 3 つの
チェックボックスがあります:

* 「Default Region」ボタンは、Pick 領域を既定の形状とサイズに戻します。
* 「Pan to pick」ボタンは、チャンネルビューアを見つかった中心にパンします。
* 「Center on pick」がチェックされている場合、形状は見つかった中心に再センタリング
  されます（見つかった場合。すなわち形状が Pick に「追従」します）。

.. figure:: figures/pick-controls.png
   :width: 400px
   :align: center
   :alt: Pick 領域の Controls タブ

   ``Pick`` 領域の「Controls」タブ。

「Controls」タブには、測定に基づいて動作するいくつかのボタンがあります。

* 「Bg cut」ボタンは、チャンネルビューアの低カットレベルを測定された背景レベルに
  設定します。この値へのデルタは、「Delta bg」ボックスに値を設定して適用できます
  （設定を変更するには「Enter」を押します）。
* 「Sky cut」ボタンは、チャンネルビューアの低カットレベルを測定された空レベルに
  設定します。この値へのデルタは、「Delta sky」ボックスに値を設定して適用できます
  （設定を変更するには「Enter」を押します）。
* 「Bright cut」ボタンは、チャンネルビューアの高カットレベルを測定された空＋明るさ
  レベルに設定します。この値へのデルタは、「Delta bright」ボックスに値を設定して
  適用できます（設定を変更するには「Enter」を押します）。

.. figure:: figures/pick-report.png
   :width: 400px
   :align: center
   :alt: Pick 領域の Report タブ

   ``Pick`` 領域の「Report」タブ。

「Report」タブは、測定に関する情報を表形式で記録するために使います。

「Add Pick」ボタンを押すと、最新の候補に関する情報が表に追加されます。「Record
Picks automatically」チェックボックスがチェックされている場合、どの候補も自動的に
表に追加されます。

.. note:: 「Settings」タブの「Show Candidates」チェックボックスがチェックされて
          いる場合、選択された候補だけでなく、（設定に従って）領域内で見つかった
          *すべての*オブジェクトが表に追加されます。

「Clear Log」ボタンを押すことで、いつでも表をクリアできます。ログは、「File:」
ボックスに有効なパスとファイル名を入力して「Save table」を押すことで表に保存でき
ます。ファイルタイプは、与えられた拡張子によって自動的に決まります（例: 「.fits」
は FITS、「.txt」はプレーンテキスト）。

**候補が見つからなかった場合**

（設定に基づいて）候補が見つからない場合、Pick 領域は、Pick 領域を中心とした赤い
点でマークされます。

.. figure:: figures/pick-no-candidate.png
   :width: 800px
   :align: center
   :alt: 候補が見つからない場合のマーカー

   候補が見つからない場合のマーカー。

画像の切り出しはこの中央領域から取られるので、「Image」タブには依然として内容が
あります。中央の赤い「X」でもマークされます。

等高線プロットは引き続き切り出しから生成されます。

.. figure:: figures/pick-contour-no-candidate.png
   :width: 400px
   :align: center
   :alt: 候補が見つからない場合の等高線。

   候補が見つからない場合の等高線。

他のすべてのプロットはクリアされます。

**Settings タブ**

.. figure:: figures/pick-settings.png
   :width: 400px
   :align: center
   :alt: Pick プラグインの Settings タブ

   ``Pick`` プラグインの「Settings」タブ。

「Settings」タブは、Pick 領域内での検索の側面を制御します:

* 「Show Candidates」チェックボックスは、検出されたすべてのソースをマークするか
  どうかを制御します（下図参照）。さらに、チェックされている場合、「Report」
  コントロールを使うときに、見つかったすべてのオブジェクトが Pick ログテーブルに
  追加されます。
* 「Draw type」パラメータは、描く Pick 領域の形状を選ぶために使います。
* 「Radius」パラメータは、画像内の明るいピークを見つけて評価する際に使う半径を設定
  します。
* 「Threshold」パラメータは、ピーク検出のしきい値を設定するために使います。「None」
  に設定すると、妥当な既定値が選ばれます。
* 「Min FWHM」と「Max FWHM」パラメータは、特定のサイズのオブジェクトを候補から除外
  するために使えます。
* 「Ellipticity」パラメータは、形状の非対称性に基づいて候補を除外するために使い
  ます。
* 「Edge」パラメータは、切り出しの端にどれだけ近いかに基づいて候補を除外するために
  使います。*注: 現在、これは回転していない長方形の形状についてのみ確実に動作し
  ます。*
* 「Max side」パラメータは、Pick 形状で使えるバウンディングボックスのサイズを制限
  するために使います。サイズが大きいほど評価に時間がかかります。
* 「Coordinate Base」パラメータは、見つかったソースに適用するオフセットです。
  ソースのピクセル位置を FITS 準拠の方法で報告したい場合は「1」に、0 始まりの
  インデックスを好む場合は「0」に設定します。
* 「Calc center」パラメータは、中心を FWHM 当てはめ（「fwhm」）から計算するか、
  重心計算（「centroid」）から計算するかを決めるために使います。
* 「FWHM fitting」パラメータは、FWHM 当てはめにどの関数を使うか（「gaussian」または
  「moffat」）を決めるために使います。``~/.ginga/plugin_Pick.cfg`` で
  「calc_fwhm_lib」が「astropy」に設定されている場合は、「lorentz」を使う選択肢も
  利用できます。
* 「Contour Interpolation」パラメータは、「Contour」プロットで背景画像を描画する
  際に使う補間方法を設定するために使います。
* 「EE total radius」は、EE 割合が 1 になると予想される（すなわち点像分布関数の
  すべてのフラックスが含まれる）半径（囲み円エネルギー用）と箱の半幅（囲み四角
  エネルギー用）をピクセルで定義します。
* 「EE sampling radius」は、レポート用に測定 EE 曲線をサンプリングするために使う
  半径（ピクセル）です。

「Redo Pick」ボタンは検索操作をやり直します。いくつかのパラメータを変更し、現在の
Pick 領域を乱さずにその効果を見たい場合に便利です。

.. figure:: figures/pick-candidates.png
   :width: 600px
   :align: center
   :alt: 「Show Candidates」がチェックされているときのチャンネルビューア。

   「Show Candidates」がチェックされているときのチャンネルビューア。

**ユーザー構成**

``~/.ginga/plugin_Pick.cfg`` を使ってカスタマイズできます。``~`` はあなたの
HOME ディレクトリです:

.. code-block:: Python

  #
  # Pick plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_Pick.cfg"

  color_pick = 'green'
  shape_pick = 'box'
  color_candidate = 'purple'

  # Offset to add to Pick results. Default is 1.0 for FITS like indexing,
  # set to 0.0 here if you prefer numpy-like 0-based indexing
  pixel_coords_offset = 0.0

  # Maximum side for a pick region
  max_side = 1024

  # For image cutout viewer ("Image" tab)
  # you can set autozoom and autocuts preferences
  cutout_autozoom = 'override'
  cutout_autocuts = 'off'

  # For contour plot ("Contour" tab)
  # widget type: let choose automatically or force 'ginga' or 'matplotlib'
  # (choice of 'ginga' requires scikit-image to be installed)
  contour_widget = 'choose'
  # if ginga widget is chosen, you can set autozoom and autocuts preferences
  contour_autozoom = 'override'
  contour_autocuts = 'override'
  num_contours = 8
  # How big of a radius are we willing to consider from the center of the
  # pick?  bigger numbers == slower
  contour_size_min = 10
  contour_size_limit = 70

  # should the pick shape recenter on the found object center, if any?
  # useful for "tracking" an object that is moving from image to image
  center_on_pick = False

  # Star candidate search parameters
  radius = 10
  # Set threshold to None to auto calculate it
  threshold = None
  # Minimum and maximum fwhm to be considered a candidate
  min_fwhm = 1.5
  max_fwhm = 50.0
  # Minimum ellipticity to be considered a candidate
  min_ellipse = 0.5
  # Percentage from edge to be considered a candidate
  edge_width = 0.01
  # Graphically indicate all possible considered candidates
  show_candidates = False

  # Center of object is based on FWHM ("fwhm") or centroid ("centroid")
  # calculation:
  calc_center_alg = 'centroid'

  # Library to use for FWHM fitting ("native" or "astropy")
  calc_fwhm_lib = 'native'

  # Fitting function to use for FWHM ("gaussian" or "moffat")
  calc_fwhm_alg = 'gaussian'

  # Defaults for delta cut levels (in Controls tab)
  delta_sky = 0.0
  delta_bright = 0.0

  # Encircled and ensquared energy (EE) calculations:
  # a. Radius (pixel) where EE fraction is expected to be 1.
  ee_total_radius = 10.0
  # b. Radius (pixel) to sample EE for reporting.
  ee_sampling_radius = 2.5

  # use a different color/intensity map than channel image?
  pick_cmap_name = None
  pick_imap_name = None

  # For Reports tab
  record_picks = True

  # Set this to a file name, if None a filename will be automatically chosen
  report_log_path = None
