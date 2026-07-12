
``Histogram`` 为图像中绘制的区域或整幅图像绘制直方图。

**插件类型：本地**

``Histogram`` 是本地插件，这意味着它与某个通道相关联。
它不是单例，这意味着可以为每个通道打开多个实例。

**用法**

单击并拖动以在图像中定义一个区域，该区域将用于计算直方图。要取整幅图像的直方图，
请单击界面中标有「整幅图像」的按钮。

.. note:: 根据图像的大小，计算完整直方图可能需要时间。

如果为通道选择了新图像，直方图将根据当前参数用新数据重新计算。

除非在直方图插件的设置文件中禁用，否则会为该框计算一行简单统计信息，并显示在图下
方的一行中。

**界面控件**

界面底部的三个单选按钮用于控制单击/拖动操作的效果：

* 选择「移动」以将区域拖到不同位置
* 选择「绘制」以绘制新区域
* 选择「编辑」以编辑区域

要绘制直方图的对数图，请勾选「对数直方图」复选框。要按图像中值的整个范围而不是按
剪切值范围内绘图，请取消勾选「按剪切绘图」复选框。

「NumBins」参数决定计算直方图时使用多少个箱。在框中输入一个数字并按「Enter」以
更改默认值。

**剪切级别便捷控件**

由于直方图是设置剪切级别的有用反馈，因此界面中提供了用于设置图像中低和高剪切级别
的控件，以及根据通道首选项中的自动剪切级别设置执行自动剪切级别的控件。

您可以通过在直方图中单击来设置剪切级别：

* 左键单击：设置低剪切
* 中键单击：重置（自动剪切级别）
* 右键单击：设置高剪切

此外，您可以通过在图中滚动滚轮来动态调整低剪切和高剪切之间的间隙（即直方图曲线的
「宽度」）。这会产生增大或减小图像内对比度的效果。每次滚轮单击更改的量由插件配置
文件设置 ``scroll_pct`` 设定。默认值为 10%。

**用户配置**

它可使用 ``~/.ginga/plugin_Histogram.cfg`` 进行自定义，其中 ``~`` 是您的 HOME
目录：

.. code-block:: Python

  #
  # Histogram plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_Histogram.cfg"

  # Switch to "move" mode after selection
  draw_then_move = True

  # Number of bins for histogram
  num_bins = 2048

  # Histogram color
  hist_color = 'aquamarine'

  # Calculate extra statistics on box
  show_stats = True

  # Controls formatting (width) of statistics numbers
  maxdigits = 7

  # percentage to adjust cuts gap when scrolling in histogram
  scroll_pct = 0.10
