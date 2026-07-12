
通过拼贴方法创建图像拼接的插件。

**插件类型：本地**

``Collage`` 是本地插件，这意味着它与某个通道相关联。
可以为每个通道打开一个实例。

**用法**

此插件用于使用用户提供的图像，在通道查看器中自动创建拼贴式拼接。图像在拼贴中的
位置由其 WCS 确定，不进行畸变校正。这旨在作为快速查看工具，而非考虑图像畸变等的
图像 drizzle 的替代品。

拼贴仅作为 Ginga 画布上的绘图存在。实际上不会构建新的单幅图像（如果您需要那样，
请参见「Mosaic」插件）。某些期望对单幅图像操作的插件可能无法在拼贴上正确工作。

要创建新的拼贴，请单击「新建拼贴」按钮并将文件拖到显示窗口上（例如，可以从
`FBrowser` 插件拖动文件）。图像必须具有可用的 WCS。处理的第一幅图像将被加载，
其 WCS 将用于确定其他图块的方向。只需拖动其他文件，您就可以向现有拼贴添加新图像。

**控件**

「方法」控件用于选择对拼贴中图像进行拼接的方法。它有两个值：'simple' 和 'warp'：

- 'simple' 将尝试根据 WCS 旋转和翻转图像。这是一种快速的方法，但以精度为代价。
  它不会处理视场边缘附近应使图像倾斜的畸变。
- 'warp' 将使用 WCS 根据参考图像的 WCS 完全移动图像中的每个像素。这可能会在图像
  中留下空像素，这些空像素通过从周围像素采样来填充。这将比简单方法慢，并且时间随
  图像大小线性增加。

勾选「拼贴 HDU」按钮，让 `Collage` 尝试绘制拖动文件中的所有图像 HDU，而不仅仅是
找到的第一个。

勾选「标注图像」，让插件在每个绘制的图块上绘制每幅图像的名称。

如果勾选「匹配背景」，则每个图块的背景将相对于第一个绘制图块的中位数进行调整
（一种粗略的平滑）。

「线程数」框分配将从线程池中使用多少个线程来加载数据。使用多个线程通常会加快许多
文件的加载。

**与 `Mosaic` 插件的区别**

- 不分配大数组来保存所有拼接内容
- 无需指定输出 FOV 或为其操心
- 可以更快地显示结果（略微取决于组成图像）
- 某些插件无法在拼贴上正确工作，或者会更慢
- 无法将拼贴保存为数据文件（不过您可以使用「ScreenShot」）

它可使用 ``~/.ginga/plugin_Collage.cfg`` 进行自定义，其中 ``~`` 是您的 HOME
目录：

.. code-block:: Python

  #
  # Collage plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_Collage.cfg"

  # Set to True when you want to collage image HDUs in a file
  collage_hdus = False

  # annotate images with their names
  annotate_images = False

  # Try to match backgrounds
  match_bg = False

  # Number of threads to devote to opening images
  num_threads = 4
