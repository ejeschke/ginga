
用于生成沿线或路径的值的图的插件。

**插件类型：本地**

``Cuts`` 是本地插件，这意味着它与某个通道相关联。
它不是单例，这意味着可以为每个通道打开多个实例。

**用法**

``Cuts`` 为穿过图像绘制的一条线绘制像素值与索引的简单图形。可以绘制多个切割。

有四种可用的切割：line、path、freepath 和 beziercurve：

* 「line」切割是两点之间的直线。
* 「path」切割像开放多边形一样绘制，中间是直线段。
* 「freepath」切割类似于 path 切割，但使用跟随光标移动的自由笔触绘制。
* 「beziercurve」路径是三次贝塞尔曲线。

如果在插件处于活动状态时向通道添加新图像，它将用新图像上新计算的切割进行更新。

如果启用了「enable slit」设置，此插件还将通过「Slit」选项卡允许狭缝图像功能（用于
多维图像）。在选项卡界面中，从「Axes」列表中选择一个轴并绘制一条线。这将创建一幅
2D 图像，假定前两个轴是空间的，并沿所选轴对数据进行索引。与 ``Cuts`` 一样，您可以
使用切割选择下拉框查看其他狭缝图像。

**绘制切割**

「New Cut Type」菜单让您选择要绘制哪种切割。

如果要绘制新切割，请从「Cut」下拉菜单中选择「New Cut」。否则，如果选择了某个特定
命名的切割，则该切割将被任何新绘制的切割替换。

在绘制 path 或 beziercurve 切割时，按「v」添加一个顶点，或按「z」删除最后添加的
顶点。

**键盘快捷键**

在悬停光标时，按「h」进行完整的水平切割，按「j」进行完整的垂直切割。

**删除切割**

要删除切割，请从「Cut」下拉列表中选择其名称并单击「删除」按钮。要删除所有切割，
请按「全部删除」。

**编辑切割**

使用画布编辑功能，可以向现有路径添加新顶点并移动顶点。单击「编辑」单选按钮以将
画布置于编辑模式。如果切割未自动选中，您现在可以通过单击来选择线、路径或曲线，这
应会启用端点或顶点处的控制点——您可以拖动这些控制点。要向路径添加新顶点，请小心地
将光标悬停在您想要新顶点的线上并按「v」。要去除某个顶点，请将光标悬停在其上并
按「z」。

您会注意到大多数对象有一个额外的控制点，其中心为不同的颜色——这是一个移动控制点，
用于在编辑模式下在图像上移动整个对象。

您也可以选择「移动」以只是不加更改地移动切割。

**更改切割的宽度**

「line」切割的宽度可使用「Width Type」菜单更改：

* 「none」表示半径为零的切割；即仅显示沿线的像素值
* 「x」将绘制沿与切割正交的 X 轴的值之和。
* 「y」将绘制沿与切割正交的 Y 轴的值之和。
* 「perpendicular」将绘制沿与切割垂直的轴的值之和。

「Width radius」控制正交求和的宽度，在切割两侧各一定量——1 为 3 像素，2 为 5 像素，
依此类推。

**保存切割**

使用「保存」按钮将 ``Cuts`` 图保存为图像，并将数据保存为 Numpy 压缩存档。

**复制切割**

要复制切割，请从「Cut」下拉列表中选择其名称并单击「复制切割」按钮。将从中创建一个
新切割。然后您可以独立地操作新切割。

**用户配置**

它可使用 ``~/.ginga/plugin_Cuts.cfg`` 进行自定义，其中 ``~`` 是您的 HOME 目录：

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
