执行快速的天文恒星分析。

**插件类型：本地**

``Pick`` 是本地插件，这意味着它与某个通道相关联。
它不是单例，这意味着可以为每个通道打开多个实例。

**用法**

``Pick`` 插件用于对恒星对象执行快速的天文数据质量分析。它在绘制的框内定位恒星
候选者，并根据一组搜索设置挑选最可能的候选者。会报告候选对象的半高全宽（FWHM），
以及基于探测器板刻度的其大小。还会对背景、天空水平和亮度进行粗略测量。

**定义拾取区域**

默认拾取区域定义为一个约 30x30 像素的框，它包围搜索区域。

插件底部的移动/绘制/编辑选择器用于确定对拾取区域执行什么操作：

.. figure:: figures/pick-move-draw-edit.png
   :width: 400px
   :align: center
   :alt: 移动、绘制和编辑按钮

   「移动」、「绘制」和「编辑」按钮。

* 如果选择「移动」，则可以通过拖动现有拾取区域或单击您希望放置其中心的位置来移动
  它。如果没有现有区域，将创建一个默认区域。
* 如果选择「绘制」，则可以用光标绘制一个形状以包围并定义一个新的拾取区域。默认形状
  是框，但可以在「Settings」选项卡中选择其他形状。
* 如果选择「编辑」，则可以通过拖动其控制点来编辑拾取区域，或通过在边界框中拖动来
  移动它。

在移动、绘制或编辑区域后，``Pick`` 将在该区域中搜索所有峰值，并根据界面「Settings」
选项卡中的标准（见下文「Settings 选项卡」）评估这些峰值，并尝试定位与设置匹配的
最佳候选者。

.. note:: 「Quick Mode」和「From Peak」复选框已在 Ginga v4.0 版本中移除。

**如果找到候选者**

候选者将在通道查看器画布中用一个点（通常是「X」）标记，以由水平和垂直 FWHM 测量
确定的对象为中心。

界面顶部的选项卡集将按如下方式填充：

.. figure:: figures/pick-cutout.png
   :width: 400px
   :align: center
   :alt: Pick 区域的 Image 选项卡

   ``Pick`` 区域的「Image」选项卡。

「Image」选项卡将显示裁剪区域的内容。此选项卡中的小部件是一个 Ginga 小部件，因此
可以使用通常的键盘和鼠标绑定（例如滚轮）进行缩放和平移。它还将用以对象为中心的点
标记，此外平移位置将设置为找到的中心。

.. figure:: figures/pick-contour.png
   :width: 300px
   :align: center
   :alt: Pick 区域的 Contour 选项卡

   ``Pick`` 区域的「Contour」选项卡。

「Contour」选项卡将显示等高线图。这是候选者紧邻周围区域的等高线图，通常不包含拾取
区域的整个区域。您可以使用滚轮缩放该图，并单击滚轮（鼠标按钮 2）来设置图中的平移
位置。

.. figure:: figures/pick-fwhm.png
   :width: 400px
   :align: center
   :alt: Pick 区域的 FWHM 选项卡

   ``Pick`` 区域的「FWHM」选项卡。

「FWHM」选项卡将显示 FWHM 图。紫线显示 X 方向的测量，绿线显示 Y 方向的测量。实线
表示实际像素值，虚线表示拟合的 1D 函数。阴影的紫色和绿色区域表示各自轴的 FWHM
测量。

.. figure:: figures/pick-radial.png
   :width: 400px
   :align: center
   :alt: Pick 区域的 Radial 选项卡

   ``Pick`` 区域的「Radial」选项卡。

「Radial」选项卡包含径向轮廓图。以紫色绘制的点是数据值，并对数据拟合一条线。

.. figure:: figures/pick-ee.png
   :width: 600px
   :align: center
   :alt: Pick 区域的 EE 选项卡

   ``Pick`` 区域的「EE」选项卡。

「EE」选项卡包含针对所选目标的分数圆内和方内包围能量（EE）图，分别以紫色和绿色
表示。在测量 EE 值之前，会以与 FWHM 计算一致的方式进行简单的背景减除。以黑色虚线
显示的采样半径和总半径可在「Settings」选项卡中设置；更改这些值时，请单击「Redo
Pick」以更新图和测量。给定采样半径处测得的 EE 值也会显示在「Readout」选项卡中。
当请求报告时，给定采样半径处的 EE 值和半径本身将连同其他信息一起记录在「Report」
表中。

当「Show Candidates」处于活动状态时，边界框边缘附近的候选者将没有 EE 值（设为 0）。

.. figure:: figures/pick-readout.png
   :width: 400px
   :align: center
   :alt: Pick 区域的 Readout 选项卡

   ``Pick`` 区域的「Readout」选项卡。

「Readout」选项卡将填充测量摘要。此选项卡中有两个按钮和三个复选框：

* 「Default Region」按钮将拾取区域恢复为默认形状和大小。
* 「Pan to pick」按钮将把通道查看器平移到定位的中心。
* 如果勾选「Center on pick」，则形状将在定位的中心处重新居中（如果找到）（即形状
  「跟踪」拾取）。

.. figure:: figures/pick-controls.png
   :width: 400px
   :align: center
   :alt: Pick 区域的 Controls 选项卡

   ``Pick`` 区域的「Controls」选项卡。

「Controls」选项卡有几个将根据测量工作的按钮。

* 「Bg cut」按钮将把通道查看器的低剪切级别设置为测得的背景水平。可以通过在「Delta
  bg」框中设置一个值来对此值应用增量（按「Enter」更改设置）。
* 「Sky cut」按钮将把通道查看器的低剪切级别设置为测得的天空水平。可以通过在「Delta
  sky」框中设置一个值来对此值应用增量（按「Enter」更改设置）。
* 「Bright cut」按钮将把通道查看器的高剪切级别设置为测得的天空+亮度水平。可以通过在
  「Delta bright」框中设置一个值来对此值应用增量（按「Enter」更改设置）。

.. figure:: figures/pick-report.png
   :width: 400px
   :align: center
   :alt: Pick 区域的 Report 选项卡

   ``Pick`` 区域的「Report」选项卡。

「Report」选项卡用于以表格形式记录有关测量的信息。

通过按「Add Pick」按钮，有关最近候选者的信息将添加到表中。如果勾选「Record Picks
automatically」复选框，则任何候选者都会自动添加到表中。

.. note:: 如果勾选了「Settings」选项卡中的「Show Candidates」复选框，则将向表中添加
          区域中找到的*所有*对象（根据设置），而不仅仅是选定的候选者。

您可以随时按「Clear Log」按钮清除该表。可以通过在「File:」框中输入有效的路径和文件
名并按「Save table」将日志保存到表中。文件类型由给定的扩展名自动确定（例如，
「.fits」为 FITS，「.txt」为纯文本）。

**如果未找到候选者**

如果找不到候选者（基于设置），则拾取区域将用一个以拾取区域为中心的红点标记。

.. figure:: figures/pick-no-candidate.png
   :width: 800px
   :align: center
   :alt: 未找到候选者时的标记

   未找到候选者时的标记。

图像裁剪将从此中心区域获取，因此「Image」选项卡仍将有内容。它还将用一个中央红色
「X」标记。

等高线图仍将从裁剪中生成。

.. figure:: figures/pick-contour-no-candidate.png
   :width: 400px
   :align: center
   :alt: 未找到候选者时的等高线。

   未找到候选者时的等高线。

所有其他图都将被清除。

**Settings 选项卡**

.. figure:: figures/pick-settings.png
   :width: 400px
   :align: center
   :alt: Pick 插件的 Settings 选项卡

   ``Pick`` 插件的「Settings」选项卡。

「Settings」选项卡控制拾取区域内搜索的各个方面：

* 「Show Candidates」复选框控制是否标记所有检测到的源（如下图所示）。此外，如果
  勾选，则在使用「Report」控件时，所有找到的对象都会添加到拾取日志表中。
* 「Draw type」参数用于选择要绘制的拾取区域的形状。
* 「Radius」参数设置在图像中查找和评估明亮峰值时要使用的半径。
* 「Threshold」参数用于设置峰值查找的阈值；如果设置为「None」，则会选择一个合理的
  默认值。
* 「Min FWHM」和「Max FWHM」参数可用于排除某些尺寸的对象成为候选者。
* 「Ellipticity」参数用于根据候选者形状的不对称性来排除候选者。
* 「Edge」参数用于根据候选者离裁剪边缘有多近来排除候选者。*注意：目前这仅对未旋转
  的矩形形状可靠地工作。*
* 「Max side」参数用于限制拾取形状中可以使用的边界框大小。较大的尺寸评估起来需要
  更长时间。
* 「Coordinate Base」参数是应用于定位源的偏移量。如果您希望以符合 FITS 的方式报告
  源的像素位置，请设置为「1」；如果您更喜欢基于 0 的索引，请设置为「0」。
* 「Calc center」参数用于确定中心是从 FWHM 拟合（「fwhm」）还是从质心
  （「centroid」）计算。
* 「FWHM fitting」参数用于确定使用哪个函数进行 FWHM 拟合（「gaussian」或
  「moffat」）。如果在 ``~/.ginga/plugin_Pick.cfg`` 中将「calc_fwhm_lib」设置为
  「astropy」，则还可以使用「lorentz」选项。
* 「Contour Interpolation」参数用于设置在「Contour」图中渲染背景图像时使用的插值
  方法。
* 「EE total radius」定义了 EE 分数预期为 1（即点扩散函数的所有通量都包含在内）
  处的半径（用于圆内能量）和框半宽（用于方内能量），以像素为单位。
* 「EE sampling radius」是用于对测得的 EE 曲线进行采样以供报告的半径（以像素为
  单位）。

「Redo Pick」按钮将重做搜索操作。如果您更改了某些参数并希望在不干扰当前拾取区域的
情况下查看效果，这很方便。

.. figure:: figures/pick-candidates.png
   :width: 600px
   :align: center
   :alt: 勾选「Show Candidates」时的通道查看器。

   勾选「Show Candidates」时的通道查看器。

**用户配置**

它可使用 ``~/.ginga/plugin_Pick.cfg`` 进行自定义，其中 ``~`` 是您的 HOME 目录：

.. code-block:: Python

  #
  # Pick plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_Pick.cfg"

  color_pick = 'green'
  shape_pick = 'box'
  color_candidate = 'purple'

  # Offset to add to Pick results. Default is 1.0 for FITS like indexing,
  # set to 0.0 here if you prefer numpy-like 0-based indexing
  pixel_coords_offset = 0.0

  # Maximum side for a pick region
  max_side = 1024

  # For image cutout viewer ("Image" tab)
  # you can set autozoom and autocuts preferences
  cutout_autozoom = 'override'
  cutout_autocuts = 'off'

  # For contour plot ("Contour" tab)
  # widget type: let choose automatically or force 'ginga' or 'matplotlib'
  # (choice of 'ginga' requires scikit-image to be installed)
  contour_widget = 'choose'
  # if ginga widget is chosen, you can set autozoom and autocuts preferences
  contour_autozoom = 'override'
  contour_autocuts = 'override'
  num_contours = 8
  # How big of a radius are we willing to consider from the center of the
  # pick?  bigger numbers == slower
  contour_size_min = 10
  contour_size_limit = 70

  # should the pick shape recenter on the found object center, if any?
  # useful for "tracking" an object that is moving from image to image
  center_on_pick = False

  # Star candidate search parameters
  radius = 10
  # Set threshold to None to auto calculate it
  threshold = None
  # Minimum and maximum fwhm to be considered a candidate
  min_fwhm = 1.5
  max_fwhm = 50.0
  # Minimum ellipticity to be considered a candidate
  min_ellipse = 0.5
  # Percentage from edge to be considered a candidate
  edge_width = 0.01
  # Graphically indicate all possible considered candidates
  show_candidates = False

  # Center of object is based on FWHM ("fwhm") or centroid ("centroid")
  # calculation:
  calc_center_alg = 'centroid'

  # Library to use for FWHM fitting ("native" or "astropy")
  calc_fwhm_lib = 'native'

  # Fitting function to use for FWHM ("gaussian" or "moffat")
  calc_fwhm_alg = 'gaussian'

  # Defaults for delta cut levels (in Controls tab)
  delta_sky = 0.0
  delta_bright = 0.0

  # Encircled and ensquared energy (EE) calculations:
  # a. Radius (pixel) where EE fraction is expected to be 1.
  ee_total_radius = 10.0
  # b. Radius (pixel) to sample EE for reporting.
  ee_sampling_radius = 2.5

  # use a different color/intensity map than channel image?
  pick_cmap_name = None
  pick_imap_name = None

  # For Reports tab
  record_picks = True

  # Set this to a file name, if None a filename will be automatically chosen
  report_log_path = None
