
``RC`` 插件为 Ginga 查看器实现了一个远程控制接口。

**插件类型：全局**

``RC`` 是全局插件。只能打开一个实例。

**用法**

``RC``（Remote Control）插件提供了一种通过使用 XML-RPC 接口远程控制 Ginga 的
方法。从「Plugins」菜单启动该插件（调用「Start RC」），或使用 ``--modules=RC``
命令行选项启动 ginga 以自动启动它。

默认情况下，插件启动时服务器在端口 11771 上运行，绑定到 localhost 接口——这仅允许
来自本地主机的连接。如果您想更改此设置，请在「Set Addr」控件中设置主机和端口并按
``Enter`` ——您应该会看到地址在「Addr:」显示字段中更新。

请注意，主机部分（冒号之前）指示的不是您想允许*从哪个*主机访问，而是绑定到哪个
接口。如果您想允许任何主机连接，请将其留空（但要包含冒号和端口号），以允许服务器
绑定到所有接口。然后按「Restart」以在新地址重启服务器。

插件启动后，您可以使用 ``ggrc`` 脚本（安装 ``ginga`` 时包含）来控制 Ginga。如果
您想了解如何编写自己的编程接口，请查看该脚本。

显示使用示例::

        $ ggrc help

显示特定 Ginga 方法的帮助::

        $ ggrc help ginga <method>

显示特定通道方法的帮助::

        $ ggrc help channel <chname> <method>

Ginga（查看器外壳）方法可以这样调用::

        $ ggrc ginga <method> <arg1> <arg2> ...

每通道方法可以这样调用::

        $ ggrc channel <chname> <method> <arg1> <arg2> ...

通过添加选项，可以从远程主机进行调用::

        --host=<hostname> --port=11771

（在插件 GUI 中，请务必从「addr」中删除「localhost」前缀，但保留冒号和端口。）

**示例**

创建新通道::

        $ ggrc ginga add_channel FOO

加载文件::

        $ ggrc ginga load_file /home/eric/testdata/SPCAM/SUPA01118797.fits

将文件加载到特定通道::

        $ ggrc ginga load_file /home/eric/testdata/SPCAM/SUPA01118797.fits FOO

剪切级别::

        $ ggrc channel FOO cut_levels 163 1300

自动剪切级别::

        $ ggrc channel FOO auto_levels

缩放到特定级别::

        $ ggrc -- channel FOO zoom_to -7

（请注意使用 ``--`` 以允许我们传递以 ``-`` 开头的参数。）

缩放以适应::

        $ ggrc channel FOO zoom_fit

变换（参数是一个布尔三元组：``flipx`` ``flipy`` ``swapxy``）::

        $ ggrc channel FOO transform 1 0 1

旋转::

        $ ggrc channel FOO rotate 37.5

更改色彩映射::

        $ ggrc channel FOO set_color_map rainbow3

更改颜色分布算法::

        $ ggrc channel FOO set_color_algorithm log

更改强度映射::

        $ ggrc channel FOO set_intensity_map neg

在某些情况下，您可能需要借助 shell 转义才能将某些字符传递给 Ginga。例如，开头的
短横线字符通常被解释为程序选项。为了传递带符号的整数，您可能需要做类似这样的
操作::

        $ ggrc -- channel FOO zoom -7

**从 Python 内部进行接口**

也可以从 Python 内部以 RC 模式控制 Ginga。以下描述了部分功能。

*连接*

首先，启动 Ginga 并启动 ``RC`` 插件。这可以从命令行完成::

        ginga --modules=RC

从 Python 内部，如下所示使用 ``RemoteClient`` 对象进行连接::

        from ginga.util import grc
        host = 'localhost'
        port = grc.default_rc_port
        viewer = grc.RemoteClient(host, port)

此 viewer 对象现在通过 ``RC`` 链接到 Ginga。

*加载图像*

您可以将图像从内存加载到您选择的通道中。首先，连接到一个通道::

        ch = viewer.channel('Image')

然后，加载一个 Numpy 图像（即任何 2D ``ndarray``）::

        import numpy as np
        img = np.random.rand(500, 500) * 10000.0
        ch.load_np('Image_Name', img, 'fits', {})

图像将在 Ginga 中显示，并可像往常一样进行操作。

*叠加画布对象*

可以将对象添加到给定通道的画布中。首先，连接::

        canvas = viewer.canvas('Image')

这会连接到名为「Image」的通道。您可以清除画布中绘制的对象::

        canvas.clear()

您也可以添加任何基本的画布对象。要记住的关键问题是，输入的对象必须通过 XMLRC
协议。这意味着简单的数据类型（``float``、``int``、``list`` 或 ``str``）；不能是
数组。下面是一个通过由两个 Numpy 数组定义的一系列点绘制一条线的示例::

        x = np.arange(100)
        y = np.sqrt(x)
        points = list(zip(x.tolist(), y.tolist()))
        canvas.add('path', points, color='red')

这将在图像上绘制一条红线。
