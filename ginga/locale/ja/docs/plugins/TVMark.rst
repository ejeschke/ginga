
ファイルからの点（非対話モード）を画像上にマークします。

**プラグインの種類: ローカル**

``TVMark`` はローカルプラグインで、チャンネルに関連付けられています。
チャンネルごとに 1 つのインスタンスを開けます。

**使い方**

このプラグインは、対象点の RA・DEC 位置を含む表を持つファイルを読み込むことで、
関心のある点の非対話的なマーキングを可能にします。``astropy.table`` で読める
テキストまたは FITS テーブルファイルであれば何でも使えますが、ユーザーは
プラグイン構成ファイルで列名を正しく定義*しなければなりません*（下記参照）。
RA・DEC 値は度に変換しようとします。単位変換に失敗した場合は、すでに度で表されて
いると見なされます。

あるいは、ファイルに直接のピクセル位置を含む列がある場合は、「RADEC を使用」
ボックスのチェックを外して、代わりにこれらの列を読み込めます。この場合も、列名は
プラグイン構成ファイルで正しく定義する必要があります（下記参照）。ピクセル値は
0 始まりでも 1 始まりでもよく（すなわち最初のピクセルが 0 か 1 か）、構成可能です
（下記参照）。これは、WCS に関係なく物理ピクセルをマークしたい場合に便利です
（例: 検出器上のホットピクセルをマーク）。画像に WCS 情報があれば RA・DEC は引き
続き表示されますが、マーキングには影響しません。

異なるグループをマークするには（例: 上に示すように、銀河を緑の円、背景をシアンの
十字で表示）:

1. 緑の円をドロップダウンメニューから選びます。または、希望のサイズや幅を入力
   します。
2. 該当する場合は「RADEC を使用」ボックスがチェックされていることを確認します。
3. 「座標を読み込み」ボタンを使って、銀河*のみ*の RA・DEC（または X・Y）位置を含む
   ファイルを読み込みます。
4. 手順 1 を繰り返しますが、今度はシアンの十字をドロップダウンメニューから選び
   ます。
5. 手順 2 を繰り返しますが、背景*のみ*の位置を含むファイルを選びます。

表のリストからエントリ（または複数のエントリ）を選択すると、画像上のマーキングが
ハイライトされます。ハイライトは同じ形と色を使いますが、少し太い線になります。

このプラグインがアクティブなときに画像上に長方形を描くことで、ある領域内の
すべてのマーキングを画像上と表のリストの両方でハイライトすることもできます。

「隠す」ボタンを押すとマーキングが隠れますが、プラグインのメモリは消去されません。
つまり、「表示」を押すと、同じマーキングが同じ画像上に再び現れます。ただし、
「忘れる」を押すと、マーキングは表示とメモリの両方から消去されます。つまり、
マーキングを再作成するにはファイルを再読み込みする必要があります。

同じ位置を別のマーキングパラメータで再描画するには、「忘れる」を押し、必要に応じて
上記の手順を繰り返します。ただし、単に線幅（太さ）を変えたいだけの場合は、新しい
幅の値を入力した後に「隠す」を押してから「表示」を押せば十分です。

指向／寸法が大きく異なる画像が同じチャンネルに表示されている場合、ある画像に属する
が別の画像の外に出るマーキングは、後者には表示されません。

このプラグインが読める表を作成するには、``Pick`` プラグインの結果を使うか、
``astropy.table`` などを使って手動で表を作成できます。

``TVMask`` と併用すると、Ginga で点源とマスク領域の両方を重ねて表示できます。

``~/.ginga/plugin_TVMark.cfg`` を使ってカスタマイズできます。``~`` はあなたの
HOME ディレクトリです:

.. code-block:: Python

  #
  # TVMark plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_TVMark.cfg"

  # Marking type -- 'circle' or 'cross'
  marktype = 'circle'

  # Marking color -- Any color name accepted by Ginga
  markcolor = 'green'

  # Marking size or radius
  marksize = 5

  # Marking line width (thickness)
  markwidth = 1

  # Specify whether pixel values are 0- or 1-indexed
  pixelstart = 1

  # True -- Use 'ra' and 'dec' columns to extract RA/DEC positions. This option
  #         uses image WCS to convert to pixel locations.
  # False -- Use 'x' and 'y' columns to extract pixel locations directly.
  #          This does not use WCS.
  use_radec = True

  # Columns to load into table listing (case-sensitive).
  # Whether RA/DEC or X/Y columns are used depend on associated GUI selection.
  ra_colname = 'ra'
  dec_colname = 'dec'
  x_colname = 'x'
  y_colname = 'y'
  # Extra columns to display; e.g., ['colname1', 'colname2']
  extra_columns = []
