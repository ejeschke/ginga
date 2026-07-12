
在图像上显示来自文件的掩码（非交互模式）。

**插件类型：本地**

``TVMask`` 是本地插件，这意味着它与某个通道相关联。
可以为每个通道打开一个实例。

**用法**

此插件通过读取 FITS 文件来实现掩码的非交互式显示，其中非零值被假定为掩码数据。

要显示不同的掩码（例如，如上所示，一些掩码为绿色，一些为粉色）：

1. 从下拉菜单中选择绿色。或者，输入所需的 alpha 值。
2. 使用「加载掩码」按钮，加载相关的 FITS 文件。
3. 重复 (1)，但现在从下拉菜单中选择粉色。
4. 重复 (2)，但选择另一个 FITS 文件。
5. 要将第三个掩码也显示为粉色，请在不更改下拉菜单的情况下重复 (4)。

从表列表中选择一个条目（或多个条目）将高亮显示图像上的掩码。高亮使用预定义的
颜色和 alpha（可在下面自定义）。

在此插件处于活动状态时，您还可以通过在图像上绘制矩形，在图像和表列表中同时高亮
显示某个区域内的所有掩码。

按「隐藏」按钮将隐藏掩码，但不会清除插件的内存；也就是说，当您按「显示」时，相同的
掩码将重新出现在同一图像上。但是，按「忘记」将从显示和内存中都清除掩码；也就是说，
您需要重新加载文件才能重新创建掩码。

要用不同的颜色或 alpha 重新绘制相同的掩码，请按「忘记」并根据需要重复上述步骤。

如果在同一通道中显示指向/尺寸差异很大的图像，则属于某一图像但落在另一图像之外的
掩码将不会出现在后者中。

要创建此插件可读取的掩码，除了使用 ``astropy.io.fits`` 等手工创建 FITS 文件之外，
还可以使用 ``Drawing`` 插件的结果（绘制后按「创建掩码」，并使用 ``SaveImage``
保存掩码）。

与 ``TVMark`` 一起使用时，您可以在 Ginga 中同时叠加点源和掩码区域。

它可使用 ``~/.ginga/plugin_TVMask.cfg`` 进行自定义，其中 ``~`` 是您的 HOME
目录：

.. code-block:: Python

  #
  # TVMask plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_TVMask.cfg"

  # Mask color -- Any color name accepted by Ginga
  maskcolor = 'green'

  # Mask alpha (transparency) -- 0=transparent, 1=opaque
  maskalpha = 0.5

  # Highlighted mask color and alpha
  hlcolor = 'white'
  hlalpha = 1.0
