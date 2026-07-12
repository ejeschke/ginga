
線またはパスに沿った値のプロットを生成するプラグインです。

**プラグインの種類: ローカル**

``Cuts`` はローカルプラグインで、チャンネルに関連付けられています。
シングルトンではないため、チャンネルごとに複数のインスタンスを開けます。

**使い方**

``Cuts`` は、画像を通して描いた線について、ピクセル値対インデックスの簡単な
グラフをプロットします。複数のカットをプロットできます。

カットには 4 種類あります: line、path、freepath、beziercurve:

* 「line」カットは 2 点間の直線です。
* 「path」カットは、間を直線セグメントでつないだ開いた多角形のように描かれます。
* 「freepath」カットは path カットに似ていますが、カーソルの動きに従う自由形状の
  ストロークで描かれます。
* 「beziercurve」パスは 3 次ベジェ曲線です。

プラグインがアクティブなときにチャンネルへ新しい画像が追加されると、新しい画像上で
新たに計算されたカットに更新されます。

「enable slit」設定が有効な場合、このプラグインは「Slit」タブを通じてスリット画像
機能（多次元画像用）も可能にします。タブの UI で「Axes」リストから 1 つの軸を選び、
線を描きます。これにより、最初の 2 軸が空間的であると仮定し、選択した軸に沿って
データをインデックスする 2D 画像が作られます。``Cuts`` と同様に、カット選択
ドロップダウンボックスで他のスリット画像を表示できます。

**カットを描く**

「New Cut Type」メニューで、どの種類のカットを描くかを選べます。

新しいカットを描きたい場合は、「Cut」ドロップダウンメニューから「New Cut」を
選びます。そうでない場合、特定の名前付きカットが選択されていると、それが新しく
描いたカットで置き換えられます。

path または beziercurve カットを描いているとき、「v」を押すと頂点を追加し、「z」を
押すと最後に追加した頂点を削除します。

**キーボードショートカット**

カーソルを重ねているとき、「h」を押すと完全な水平カット、「j」を押すと完全な垂直
カットになります。

**カットを削除する**

カットを削除するには、「Cut」ドロップダウンからその名前を選び、「削除」ボタンを
クリックします。すべてのカットを削除するには、「すべて削除」を押します。

**カットを編集する**

キャンバス編集機能を使うと、既存のパスに新しい頂点を追加したり、頂点を移動したり
できます。「編集」ラジオボタンをクリックして、キャンバスを編集モードにします。
カットが自動的に選択されない場合は、線・パス・曲線をクリックして選択でき、端点や
頂点のコントロール点が有効になるはずです -- これらをドラッグできます。パスに新しい
頂点を追加するには、新しい頂点が欲しい線の上に慎重にカーソルを合わせ、「v」を
押します。頂点を取り除くには、その上にカーソルを合わせ、「z」を押します。

ほとんどのオブジェクトには、中心が別の色になった追加のコントロール点があるのに
気づくでしょう -- これは、編集モードでオブジェクト全体を画像上で移動させるための
移動コントロール点です。

「移動」を選んで、カットをそのまま移動させることもできます。

**カットの幅を変える**

「line」カットの幅は「Width Type」メニューを使って変更できます:

* 「none」は半径ゼロのカットを示します。すなわち線に沿ったピクセル値のみを表示
  します
* 「x」はカットに直交する X 軸に沿った値の合計をプロットします。
* 「y」はカットに直交する Y 軸に沿った値の合計をプロットします。
* 「perpendicular」はカットに垂直な軸に沿った値の合計をプロットします。

「Width radius」は、カットの両側にある量だけ直交する総和の幅を制御します --
1 は 3 ピクセル、2 は 5 ピクセルなどになります。

**カットを保存する**

「保存」ボタンを使って、``Cuts`` プロットを画像として、データを Numpy 圧縮アーカイブ
として保存します。

**カットをコピーする**

カットをコピーするには、「Cut」ドロップダウンからその名前を選び、「カットをコピー」
ボタンをクリックします。それから新しいカットが作られます。その後、新しいカットを
独立して操作できます。

**ユーザー構成**

``~/.ginga/plugin_Cuts.cfg`` を使ってカスタマイズできます。``~`` はあなたの
HOME ディレクトリです:

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
