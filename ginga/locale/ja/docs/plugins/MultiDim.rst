
FITS ファイル内の HDU や、3D キューブ以上の次元のデータセットのプレーンを
ナビゲートするためのプラグインです。

**プラグインの種類: ローカル**

``MultiDim`` はローカルプラグインで、チャンネルに関連付けられています。
チャンネルごとに 1 つのインスタンスを開けます。

**使い方**

``MultiDim`` は、データキューブや複数 HDU の FITS ファイルを扱うために設計された
プラグインです。そのような画像を Ginga で開いている場合、このプラグインを起動する
と、キューブの他のスライスに移動したり、他の HDU を表示したりできます。

データキューブでは、「スライスを保存」ボタンでスライスを画像として保存したり、
「動画を保存」ボタンで「開始」と「終了」のスライスインデックスを入力して動画を
作成したりできます。この機能には ``mencoder`` のインストールが必要です。

FITS テーブルの場合、そのデータは Astropy テーブルを使って読み込まれます。列の
単位はメインヘッダのすぐ下に表示されます（単位がない場合は「None」）。マスクされた
列では、マスクされた値が事前定義された充填値に置き換えられます。

**HDU の閲覧**

UI の上部にある HDU ドロップダウンリストを使って、チャンネルで開く HDU を閲覧・
選択します。

**キューブのナビゲート**

UI の下部にあるコントロールを使って軸を選択し、その軸のプレーンを 1 枚ずつ
進めます。

**ユーザー構成**

``~/.ginga/plugin_MultiDim.cfg`` を使ってカスタマイズできます。``~`` はあなたの
HOME ディレクトリです:

.. code-block:: Python

  #
  # MultiDim plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_MultiDim.cfg"

  # Sort option for HDU listing.
  # Available attributes:
  #   'index' -- Extension index
  #   'name' -- Extension name
  #   'extver' -- Extension version number
  #   'htype' -- HDU type (PrimaryHDU, ImageHDU, TableHDU)
  #   'dtype' -- Data type
  # Example to sort by HDU name and extver:
  #   sort_keys = ['name', 'extver']
  # Default is to sort by index only:
  sort_keys = ['index']

  # Reverse for HDU listing?
  sort_reverse = False
