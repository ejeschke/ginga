
``Thumbs`` 插件为自程序启动以来查看的所有图像提供缩略图索引。

**插件类型：全局**

``Thumbs`` 是全局插件。只能打开一个实例。

**用法**

默认情况下，``Thumbs`` 按时间顺序的查看历史显示，最新的图像在底部，最旧的在顶部。
可以通过「plugin_Thumbs.cfg」配置文件中的设置使排序变为字母数字顺序。

单击缩略图会直接将您导航到关联通道中的该图像。将光标悬停在缩略图上会显示一个工具
提示，其中包含图像的几条有用元数据。

如果勾选「自动滚动」复选框，将使 ``Thumbs`` 窗格滚动到活动图像。

此插件通常未配置为可关闭，但用户可以通过在配置文件中将「closeable」设置设为 True
来使其可关闭——然后界面底部将添加「关闭」和「帮助」按钮。

**从 Thumbs 中排除图像**

.. note:: 这也控制 ``Contents`` 的行为。

尽管默认行为是加载到参考查看器中的每幅图像都会显示在 ``Thumbs`` 中，但在某些情况下
这可能是不希望的（例如，当某个自动化进程以周期性速率加载许多图像时）。在这种情况下，
有两种机制可以抑制某些图像显示在 ``Thumbs`` 中：

* 在通道的设置中将「genthumb」设置指定为 False（例如从 ``Preferences`` 插件的
  「General」设置下）将排除通道本身及其任何图像。
* 在图像包装器的元数据中设置「nothumb」关键字（不是 FITS 头，而是例如通过
  ``image.set(nothumb=True)``）将从 ``Thumbs`` 中排除该特定图像，即使该通道的
  「genthumb」设置为 True。

它可使用 ``~/.ginga/plugin_Thumbs.cfg`` 进行自定义，其中 ``~`` 是您的 HOME
目录：

.. code-block:: Python

  #
  # Thumbs plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_Thumbs.cfg"

  # If you revisit the same directories frequently
  # caching thumbs saves a lot of time when they need to be regenerated
  cache_thumbs = False

  # cache location-- "local" puts them in a .thumbs subfolder, otherwise
  # they are cached in ~/.ginga/thumbs
  cache_location = 'local'

  # Scroll the pane automatically when new thumbnails arrive
  auto_scroll = True

  # Keywords to extract and show if we mouse over the thumbnail
  tt_keywords = ['OBJECT', 'FRAMEID', 'UT', 'DATE-OBS']

  # Mandatory unique image identifier in tooltip
  mouseover_name_key = 'NAME'

  # How many seconds to wait after an image is altered to begin trying
  # to rebuild a matching thumb.  Usually a few seconds is good in case
  # there is ongoing adjustment of the image
  rebuild_wait = 0.5

  # Max length of thumb on the long side
  thumb_length = 180

  # Separation between thumbs in pixels
  thumb_hsep = 15
  thumb_vsep = 15

  # Sort the thumbs alphabetically: 'alpha' or None
  sort_order = None

  # Thumbnail label length in num of characters (None = no limit)
  label_length = 25

  # Cut off long label ('left', 'right', or None)
  label_cutoff = 'right'

  # Option to highlight images that are displayed in channels.
  # If set to True this option will only highlight the image that is in the
  # channel with the keyboard focus
  highlight_tracks_keyboard_focus = True

  # Highlighted label colors
  label_bg_color = 'lightgreen'
  label_font_color = 'white'

  label_font_size = 10

  # Load visible thumbs in the background to replace placeholder icons
  autoload_visible_thumbs = True

  # Length of time to wait after scrolling to begin autoloading
  autoload_interval = 1.0

  # list of attributes to transfer from the channel viewer to the
  # thumbnail generator if the channel has an image in it
  transfer_attrs = ['transforms', 'cutlevels', 'rgbmap']

  # Add a close button to this plugin, so that it can be stopped
  closeable = False
