
``RC`` プラグインは、Ginga ビューアのためのリモート制御インターフェースを実装し
ます。

**プラグインの種類: グローバル**

``RC`` はグローバルプラグインです。開けるインスタンスは 1 つだけです。

**使い方**

``RC``（Remote Control）プラグインは、XML-RPC インターフェースを使って Ginga を
リモートで制御する方法を提供します。「Plugins」メニューからプラグインを起動する
（「Start RC」を呼び出す）か、``--modules=RC`` コマンドラインオプションを付けて
ginga を起動して自動的に起動します。

既定では、プラグインはポート 11771 で localhost インターフェースにバインドされた
サーバーが動作した状態で起動します -- これはローカルホストからの接続のみを許可
します。これを変更したい場合は、「Set Addr」コントロールでホストとポートを設定し、
``Enter`` を押します -- 「Addr:」表示フィールドでアドレスが更新されるのが見える
はずです。

ホスト部分（コロンの前）は、*どの*ホストからのアクセスを許可したいかを示すのでは
なく、どのインターフェースにバインドするかを示す点に注意してください。任意の
ホストの接続を許可したい場合は、空のままにして（ただしコロンとポート番号は含める）、
サーバーがすべてのインターフェースにバインドできるようにします。次に「Restart」を
押して、新しいアドレスでサーバーを再起動します。

プラグインが起動したら、``ggrc`` スクリプト（``ginga`` のインストール時に含まれる）
を使って Ginga を制御できます。独自のプログラム的インターフェースの書き方を見たい
場合は、このスクリプトを見てください。

使用例を表示::

        $ ggrc help

特定の Ginga メソッドのヘルプを表示::

        $ ggrc help ginga <method>

特定のチャンネルメソッドのヘルプを表示::

        $ ggrc help channel <chname> <method>

Ginga（ビューアシェル）メソッドは、次のように呼び出せます::

        $ ggrc ginga <method> <arg1> <arg2> ...

チャンネルごとのメソッドは、次のように呼び出せます::

        $ ggrc channel <chname> <method> <arg1> <arg2> ...

オプションを追加することで、リモートホストから呼び出しを行えます::

        --host=<hostname> --port=11771

（プラグイン GUI では、「addr」から「localhost」プレフィックスを必ず削除し、
コロンとポートは残してください。）

**例**

新しいチャンネルを作成::

        $ ggrc ginga add_channel FOO

ファイルを読み込む::

        $ ggrc ginga load_file /home/eric/testdata/SPCAM/SUPA01118797.fits

特定のチャンネルにファイルを読み込む::

        $ ggrc ginga load_file /home/eric/testdata/SPCAM/SUPA01118797.fits FOO

カットレベル::

        $ ggrc channel FOO cut_levels 163 1300

自動カットレベル::

        $ ggrc channel FOO auto_levels

特定のレベルにズーム::

        $ ggrc -- channel FOO zoom_to -7

（``-`` で始まるパラメータを渡せるようにするための ``--`` の使用に注意して
ください。）

フィットするようにズーム::

        $ ggrc channel FOO zoom_fit

変換（引数はブール値の 3 つ組: ``flipx`` ``flipy`` ``swapxy``）::

        $ ggrc channel FOO transform 1 0 1

回転::

        $ ggrc channel FOO rotate 37.5

カラーマップを変更::

        $ ggrc channel FOO set_color_map rainbow3

色分布アルゴリズムを変更::

        $ ggrc channel FOO set_color_algorithm log

強度マップを変更::

        $ ggrc channel FOO set_intensity_map neg

場合によっては、特定の文字を Ginga に渡せるようにするためにシェルのエスケープに
頼る必要があるかもしれません。例えば、先頭のダッシュ文字は通常プログラムオプション
として解釈されます。符号付き整数を渡すには、次のようなことをする必要があるかも
しれません::

        $ ggrc -- channel FOO zoom -7

**Python 内からのインターフェース**

Python 内から RC モードで Ginga を制御することもできます。以下は、機能の一部を
説明します。

*接続*

まず、Ginga を起動して ``RC`` プラグインを起動します。これはコマンドラインから
行えます::

        ginga --modules=RC

Python 内から、次のように ``RemoteClient`` オブジェクトで接続します::

        from ginga.util import grc
        host = 'localhost'
        port = grc.default_rc_port
        viewer = grc.RemoteClient(host, port)

この viewer オブジェクトは、``RC`` を使って Ginga にリンクされました。

*画像を読み込む*

好きなチャンネルにメモリから画像を読み込めます。まず、チャンネルに接続します::

        ch = viewer.channel('Image')

次に、Numpy 画像（すなわち任意の 2D ``ndarray``）を読み込みます::

        import numpy as np
        img = np.random.rand(500, 500) * 10000.0
        ch.load_np('Image_Name', img, 'fits', {})

画像は Ginga に表示され、通常どおり操作できます。

*キャンバスオブジェクトを重ねる*

指定したチャンネルのキャンバスにオブジェクトを追加できます。まず、接続します::

        canvas = viewer.canvas('Image')

これは「Image」という名前のチャンネルに接続します。キャンバスに描かれた
オブジェクトを消去できます::

        canvas.clear()

任意の基本的なキャンバスオブジェクトを追加することもできます。念頭に置くべき重要な
点は、入力するオブジェクトが XMLRC プロトコルを通過しなければならないことです。
これは単純なデータ型（``float``、``int``、``list``、``str``）を意味します。配列は
不可です。次は、2 つの Numpy 配列で定義された一連の点を通る線をプロットする例です::

        x = np.arange(100)
        y = np.sqrt(x)
        points = list(zip(x.tolist(), y.tolist()))
        canvas.add('path', points, color='red')

これは画像上に赤い線を描きます。
