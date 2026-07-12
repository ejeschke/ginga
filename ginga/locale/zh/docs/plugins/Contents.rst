
``Contents`` 插件为自程序启动以来查看的所有图像提供了一个类似目录的界面。与
``Thumbs`` 不同，``Contents`` 按通道排序。内容还显示图像中一些可配置的元数据。

**插件类型：全局**

``Contents`` 是全局插件。只能打开一个实例。

**用法**

单击列标题以按该列对表格排序；再次单击以按相反方向排序。

.. note:: 如适用，列及其值取自 FITS 头。这可以通过在「plugin_Contents.cfg」设置
          文件中设置「columns」参数来自定义。

当前聚焦通道中的活动图像通常会被高亮显示。双击某幅图像将强制在关联通道中显示该
图像。单击任意图像可激活界面底部的按钮：

* 「显示」：将图像设为活动图像。
* 「移动」：将图像移动到另一个通道。
* 「复制」：将图像复制到另一个通道。
* 「移除」：将图像从通道中移除。

如果对已在 Ginga 中修改过的图像（如果使用，它会在 ``ChangeHistory`` 下有一个条目）
执行「移动」或「复制」，修改历史也会被保留。从通道中移除图像会破坏所有未保存的
更改。

此插件通常未配置为可关闭，但用户可以通过在配置文件中将「closeable」设置设为 True
来使其可关闭——然后界面底部将添加「关闭」和「帮助」按钮。

**从 Contents 中排除图像**

.. note:: 这也控制 ``Thumbs`` 的行为。

尽管默认行为是加载到参考查看器中的每幅图像都会显示在 ``Contents`` 中，但在某些
情况下这可能是不希望的（例如，当某个自动化进程以周期性速率加载许多图像时）。在
这种情况下，有两种机制可以抑制某些图像显示在 ``Contents`` 中：

* 在通道的设置中将「genthumb」设置指定为 False（例如从 ``Preferences`` 插件的
  「General」设置下）将排除通道本身及其任何图像。
* 在图像包装器的元数据中设置「nothumb」关键字（不是 FITS 头，而是例如通过
  ``image.set(nothumb=True)``）将从 ``Contents`` 中排除该特定图像，即使该通道的
  「genthumb」设置为 True。

它可使用 ``~/.ginga/plugin_Contents.cfg`` 进行自定义，其中 ``~`` 是您的 HOME
目录：

.. code-block:: Python

  #
  # Contents plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_Contents.cfg"

  # columns to show from metadata -- NAME and MODIFIED recommended
  # format: [(col header, keyword1), ... ]
  columns = [ ('Name', 'NAME'), ('Object', 'OBJECT'), ('Filter', 'FILTER01'), ('Date', 'DATE-OBS'), ('Time UT', 'UT'), ('Modified', 'MODIFIED')]

  # If set to True, will always expand the tree in Contents when new entries are added
  always_expand = True

  # Option to highlight images that are displayed in channels.
  # If set to True this option will only highlight the image that is in the
  # channel with the keyboard focus
  highlight_tracks_keyboard_focus = False

  # If True, color every other row in alternating shades to improve
  # readability of long tables
  color_alternate_rows = True

  # Highlighted row colors (in addition to bold text)
  row_font_color = 'green'

  # Maximum number of rows that will turn off auto column resizing (for speed)
  max_rows_for_col_resize = 100

  # Add a close button to this plugin, so that it can be stopped
  closeable = False
