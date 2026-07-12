
在图像上标记来自文件的点（非交互模式）。

**插件类型：本地**

``TVMark`` 是本地插件，这意味着它与某个通道相关联。
可以为每个通道打开一个实例。

**用法**

此插件通过读取包含这些点的 RA 和 DEC 位置的表的文件，实现对关注点的非交互式标记。
任何可由 ``astropy.table`` 读取的文本或 FITS 表文件都可接受，但用户*必须*在插件
配置文件中正确定义列名（见下文）。将尝试将 RA 和 DEC 值转换为度。如果单位转换
失败，将假定它们已经是度。

或者，如果文件包含直接像素位置的列，您可以通过取消勾选「使用 RADEC」框来改为读取
这些列。同样，列名必须在插件配置文件中正确定义（见下文）。像素值可以从 0 或从 1
开始索引（即第一个像素是 0 还是 1），并且可配置（见下文）。当您想不论 WCS 如何都
标记物理像素时（例如，在探测器上标记热像素），这很有用。如果图像有 WCS 信息，RA
和 DEC 仍会显示，但它们不会影响标记。

要标记不同的组（例如，如上所示，将星系显示为绿色圆圈，将背景显示为青色十字）：

1. 从下拉菜单中选择绿色圆圈。或者，输入所需的大小或宽度。
2. 如适用，确保「使用 RADEC」框已勾选。
3. 使用「加载坐标」按钮，加载*仅*包含星系 RA 和 DEC（或 X 和 Y）位置的文件。
4. 重复步骤 1，但现在从下拉菜单中选择青色十字。
5. 重复步骤 2，但选择*仅*包含背景位置的文件。

从表列表中选择一个条目（或多个条目）将高亮显示图像上的标记。高亮使用相同的形状和
颜色，但线条略粗。

在此插件处于活动状态时，您还可以通过在图像上绘制矩形，在图像和表列表中同时高亮
显示某个区域内的所有标记。

按「隐藏」按钮将隐藏标记，但不会清除插件的内存；也就是说，当您按「显示」时，相同的
标记将重新出现在同一图像上。但是，按「忘记」将从显示和内存中都清除标记；也就是说，
您需要重新加载文件才能重新创建标记。

要用不同的标记参数重新绘制相同的位置，请按「忘记」并根据需要重复上述步骤。但是，
如果您只是想更改线宽（粗细），在输入新的宽度值后按「隐藏」然后「显示」即可。

如果在同一通道中显示指向/尺寸差异很大的图像，则属于某一图像但落在另一图像之外的
标记将不会出现在后者中。

要创建此插件可读取的表，除了使用 ``astropy.table`` 等手工创建表之外，还可以使用
``Pick`` 插件的结果。

与 ``TVMask`` 一起使用时，您可以在 Ginga 中同时叠加点源和掩码区域。

它可使用 ``~/.ginga/plugin_TVMark.cfg`` 进行自定义，其中 ``~`` 是您的 HOME
目录：

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
