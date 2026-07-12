
``Crosshair`` 是一个简单的插件，用于绘制十字线，并以十字位置的像素坐标、WCS 坐标
或十字位置处的数据值进行标注。

**插件类型：本地**

``Crosshair`` 是本地插件，这意味着它与某个通道相关联。
可以为每个通道打开一个实例。

**用法**

在界面的「Format」下拉框中选择适当的输出类型：「xy」表示像素坐标，「coords」表示
WCS 坐标，「value」表示十字线位置处的值。

如果勾选「仅拖动」，则仅在窗口中单击或拖动光标时才更新十字线。如果不勾选，则只需
在通道查看器窗口中移动光标即可定位十字线。

「Cuts」选项卡包含垂直和水平切割的剖面图，这些切割由勾选「Quick Cuts」时存在的
可见框边界表示。此图会随着十字线的移动实时更新。当「Quick Cuts」未勾选时，该图
不更新。

框的大小由「radius」参数确定。

「警告级别」控件可用于设置一个通量级别，超过该级别时会在切割图中通过黄线和背景
变黄来指示警告。如果沿 X 或 Y 切割的任何值超过警告级别阈值，则触发警告。

「警报级别」控件类似，但通过红线和背景变粉来表示。如果沿 X 或 Y 切割的任何值超过
警报级别阈值，则触发警告。警报优先于警告。

「警告」和「警报」功能都可以通过简单地设置空值来关闭。它们默认是关闭的。

切割图是交互式的，但只有在勾选「仅拖动」时使用它才真正有意义。您可以在图窗口中按
「x」或「y」来打开和关闭任一轴的自动轴缩放功能，并在图中滚动以缩放 X 轴（滚动时
按住 Ctrl 可缩放 Y 轴）。

Crosshair 提供了一个 Pick 插件交互功能：当十字线位于某个对象上方时，您可以在通道
查看器窗口中按「r」，以便在该特定位置调用 Pick 插件。如果该通道上尚未打开 Pick，
则会先打开它。

**用户配置**

它可使用 ``~/.ginga/plugin_Crosshair.cfg`` 进行自定义，其中 ``~`` 是您的 HOME
目录：

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
