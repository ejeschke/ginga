在 UI 中以图形方式更改通道设置。

**插件类型：本地**

``Preferences`` 是本地插件，这意味着它与某个通道相关联。
可以为每个通道打开一个实例。

**用法**

``Preferences`` 插件*按通道*设置首选项。在使用此插件显式设置并保存之前，给定通道的
首选项从「Image」通道继承。

如果按下「Save Settings」，它会将设置保存到用户的 $HOME/.ginga 文件夹（每个通道 NAME
对应一个「channel_NAME.cfg」文件），以便将来 Ginga 会话中创建同名通道时会获得相同的
设置。

**颜色分布首选项**

.. figure:: figures/cdist-prefs.png
   :width: 400px
   :align: center
   :alt: 颜色分布首选项

   「Color Distribution」首选项。

「Color Distribution」首选项控制用于数据值到颜色索引转换的首选项，该转换在应用剪切
级别之后、执行最终颜色映射之前发生。它关系到低剪切级别和高剪切级别之间的值如何分配
到颜色和强度映射阶段。

「Algorithm」控件用于设置映射所用的算法。单击该控件以显示列表，或只需在控件上悬停
光标时滚动鼠标滚轮。有八种可用算法：linear、log、power、sqrt、squared、asinh、sinh
和 histeq。每种算法的名称表明数据如何映射到色彩映射中的颜色。「linear」是默认值。

**颜色映射首选项**

.. figure:: figures/cmap-prefs.png
   :width: 400px
   :align: center
   :alt: 颜色映射首选项

   「Color Mapping」首选项。

「Color Mapping」首选项控制用于色彩映射和强度映射的首选项，这些映射在颜色映射过程的
最终阶段使用。与「Color Distribution」首选项一起，它们控制将数据值映射为 24 bpp RGB
视觉表示。

「Colormap」控件选择应加载并使用哪个色彩映射。单击该控件以显示列表，或只需在控件上
悬停光标时滚动鼠标滚轮。

.. note:: Ginga 附带了一组不错的色彩映射，但如果您想要更多，可以添加自定义的；或者，
          如果安装了 ``matplotlib``，您可以加载它拥有的所有映射。有关详细信息，请参见
          「Customizing Ginga」。

「Intensity」控件选择应与色彩映射一起使用哪个强度映射。强度映射在色彩映射之前应用，
可用于将标准线性值刻度更改为反转刻度、对数刻度等。

「Invert CMap」复选框可用于反转所选的色彩映射（请注意，许多色彩映射也可以从「Colormap」
控件中以反转形式选择）。

「Rotate」控件可用于旋转色彩映射，而「Unrotate CMap」按钮将把旋转恢复到其默认的未旋转
状态。

「Color Defaults」按钮将所有颜色映射控件重置为默认值：「gray」色彩映射、「ramp」（线性）
强度，以及色彩映射无反转或旋转。

**对比度和亮度（偏置）首选项**

.. figure:: figures/contrast-prefs.png
   :width: 400px
   :align: center
   :alt: 对比度和亮度（偏置）首选项

   「Contrast and Brightness (Bias)」首选项。

「Contrast」和「Brightness」控件将设置查看器的对比度和亮度（又称「偏置」）。它们提供了
以下操作的替代方案：1) 使用查看器窗口内的对比度模式，或 2) 通过拖动（设置亮度/偏置）
或滚动（设置对比度）来操作色条。

「Default Contrast」和「Default Brightness」控件将其各自的设置恢复为默认值。

**自动剪切首选项**

.. figure:: figures/autocuts-prefs.png
   :width: 400px
   :align: center
   :alt: 自动剪切首选项

   「Auto Cuts」首选项。

「Auto Cuts」首选项控制在按下自动剪切级别按钮或键时，或在启用自动剪切的情况下加载新
图像时，视图的剪切级别的计算。您也可以从此处手动设置剪切级别。

「Cut Low」和「Cut High」字段可用于手动指定较低和较高的剪切级别。按「Cut Levels」将
手动把级别设置为这些值。如果缺少某个值，则假定它默认为当前的值。

按「Auto Levels」将根据算法计算级别。「Auto Method」控件用于选择使用哪种自动剪切算法：
「minmax」（最小最大值）、「median」（基于中值滤波）、「histogram」（基于图像直方图）、
「stddev」（基于像素值的标准差）或「zscale」（基于 IRAF 推广的 ZSCALE 算法）。当算法
更改时，其下方的框也可能会更改，以允许对每种算法特有的参数进行更改。

**变换首选项**

.. figure:: figures/transform-prefs.png
   :width: 400px
   :align: center
   :alt: 变换首选项

   「Transform」首选项。

「Transform」首选项提供通过在 X 或 Y 中翻转视图、交换 X 和 Y 轴，或以任意量旋转图像来
变换图像视图。

「Flip X」和「Flip Y」复选框使图像视图在相应轴中翻转。

「Swap XY」复选框通过交换 X 和 Y 轴来改变图像视图。这可以与「Flip X」和「Flip Y」结合
以 90 度增量旋转图像。与使用「Rotate」控件的任意旋转相比，这些视图会更快地渲染。

「Rotate」控件将把图像视图旋转指定的量。该值应以度指定。「Rotate」可以与翻转和交换
一起指定。

「Restore」按钮将把视图恢复为默认视图，即未翻转、未交换且未旋转。

**WCS 首选项**

.. figure:: figures/wcs-prefs.png
   :width: 400px
   :align: center
   :alt: WCS 首选项

   「WCS」首选项。

「WCS」首选项控制用于报告图像中光标位置的世界坐标系（WCS）计算的显示首选项。

「WCS Coords」控件用于选择显示结果所用的坐标系。

「WCS Display」控件用于选择六十进制（``H:M:S``）读出或十进制度读出。

**缩放首选项**

.. figure:: figures/zoom-prefs.png
   :width: 400px
   :align: center
   :alt: 缩放首选项

   「Zoom」首选项。

「Zoom」首选项控制 Ginga 的缩放/比例行为。Ginga 支持两种缩放算法，使用「Zoom Alg」
控件选择：

* 「step」算法以 1X、2X、3X 等离散步长向内放大图像，或以 1/2X、1/3X、1/4X 等步长
  向外缩小。此算法在视觉上产生的伪影最少，但在使用滚动动作缩放大范围时会稍慢，因为
  实现大的缩放变化需要更多的「行程」（如果使用缩放快捷键，如数字键，则不是这种情况）。

* 「rate」算法通过以「Zoom Rate」框中的值定义的速率推进比例来缩放图像。此速率默认为
  2 的平方根。较大的数字会导致缩放级别之间的比例变化更大。如果您喜欢快速缩放图像，
  以图像质量的小代价，您可能会想选择此选项。

请注意，无论为缩放算法选择哪种方法，都可以在滚动时按住 ``Ctrl``（粗略）或
``Shift``（精细）来约束缩放速率，从而控制缩放（假定为默认鼠标绑定）。

「Stretch XY」控件可用于相对于另一个轴拉伸其中一个轴（X 或 Y）。用此控件选择一个轴，
并在「Stretch Factor」控件上悬停时滚动滚轮，以拉伸所选轴中的像素。

「Scale X」和「Scale Y」控件提供对底层比例的直接访问，绕过离散的缩放步长。在这里，
可以键入精确的值来缩放图像。反之，当图像被缩放时，您会看到这些值发生变化。

「Scale Min」和「Scale Max」控件可用于对图像可缩放的程度设置限制。

「Interpolation」控件允许您选择图像将如何插值。根据安装了哪些支持包，可以进行以下
选择：

* 「basic」是使用内置算法的最近邻，它始终可用，速度相当快，并且是默认值。
* 「area」
* 「bicubic」
* 「lanczos」
* 「linear」
* 「nearest」是最近邻（使用支持包）

「Zoom Defaults」按钮将把控件恢复为 Ginga 默认值。

**平移首选项**

.. figure:: figures/pan-prefs.png
   :width: 400px
   :align: center
   :alt: 平移首选项

   「Pan」首选项。

「Pan」首选项控制 Ginga 的平移行为。

「Pan X」和「Pan Y」控件提供直接访问以设置图像中的平移位置（位于窗口中心的图像部分）
——当您在图像中平移时，可以看到它们发生变化。您可以设置这些值，然后按「Apply Pan」
平移到该精确位置。

如果「Pan Coord」控件设置为「data」，则平移由图像中的数据坐标控制；如果设置为「WCS」，
则「Pan X」和「Pan Y」控件中显示的值将为 WCS 坐标（假定图像中有有效的 WCS）。在后一种
情况下，可以保持「WCS sexagesimal」控件未勾选以度显示/设置坐标，或勾选以标准六十进制
表示法显示/设置值。

「Center Image」按钮通过将 X 和 Y 的尺寸减半来计算图像的中心，将平移位置设置到该中心。

勾选「Mark Center」复选框时，会使 Ginga 在图像中心绘制一个小的十字丝。这对于了解平移
位置和调试很有用。

**常规首选项**

.. figure:: figures/general-prefs.png
   :width: 400px
   :align: center
   :alt: 常规首选项

   「General」首选项。

「Num Images」设置指定在此通道中图像被弹出之前可以在缓冲区中保留多少幅。值为零（0）
表示无限制——图像永远不会被弹出。如果某幅图像从某个可访问的存储加载并被弹出，则在通过
浏览通道重新访问该图像时，它将自动重新加载。

「Sort Order」设置决定图像在通道中是按名称的字母顺序排序还是按加载时间排序。这主要
影响使用上/下「箭头」键或按钮时图像循环的顺序，而不一定影响它们在「Contents」或
「Thumbs」等插件中的显示方式（这些插件通常有自己的排序设置首选项）。

「Use scrollbars」复选框控制通道查看器是否会在查看器框架边缘周围显示滚动条以平移图像。

**重置（查看器）首选项**

.. figure:: figures/reset-prefs.png
   :width: 400px
   :align: center
   :alt: 重置（查看器）首选项

   「Reset」（查看器）首选项。

每个通道查看器都有一个*查看器配置文件*，它被初始化为创建之后以及恢复该通道的已保存
设置之后的查看器状态。在图像之间切换时，可以根据本节中勾选的框将查看器的属性重置为
此配置文件。*如果未勾选任何内容，则不会从查看器配置文件重置任何内容*。

要使用此功能，请按您的偏好设置查看器首选项，并单击插件底部的「Update Viewer Profile」
按钮。现在勾选在图像之间应将哪些项目重置为这些值。最后，如果您希望这些设置在 Ginga
重启后保持不变，并在您重启 ginga 并重新创建此通道时设置为此通道的默认用户配置文件，
请单击底部的「Save Settings」按钮。

* 「Reset Scale」会将缩放（比例）级别重置为查看器配置文件
* 「Reset Pan」会将平移位置重置为查看器配置文件
* 「Reset Transform」会将任何翻转/交换变换重置为查看器配置文件
* 「Reset Rotation」会将任何旋转重置为查看器配置文件
* 「Reset Cuts」会将任何剪切级别重置为查看器配置文件
* 「Reset Distribution」会将任何颜色分布重置为查看器配置文件
* 「Reset Contrast」会将任何对比度/偏置重置为查看器配置文件
* 「Reset Color Map」会将任何色彩映射设置重置为查看器配置文件

.. tip:: 如果您使用此功能，可能还需要设置「Remember (Image) Preferences」（见下文）。

.. note:: 调整的完整顺序是：

          * 来自默认查看器配置文件的任何重置项目（如有）
          * 来自图像配置文件的任何记住的项目被应用（如有）
          * 任何自动调整（cuts/zoom/center）被应用（如果它们未被记住的设置覆盖）

**记住（图像）首选项**

.. figure:: figures/remember-prefs.png
   :width: 400px
   :align: center
   :alt: 记住（图像）首选项

   「Remember」（图像）首选项。

当加载图像时，会创建一个*图像配置文件*并附加到通道中的图像元数据。随着图像被操作，
这些配置文件会持续用查看器状态更新。「Remember」首选项控制在通道中（返回）浏览到该
图像时，这些配置文件的哪些属性会恢复到查看器状态：

* 「Remember Scale」会恢复图像的缩放（比例）级别
* 「Remember Pan」会恢复图像中的平移位置
* 「Remember Transform」会恢复任何翻转或交换轴变换
* 「Remember Rotation」会恢复图像的任何旋转
* 「Remember Cuts」会恢复图像的任何剪切级别
* 「Remember Distribution」会恢复任何颜色分布（linear、log 等）
* 「Remember Contrast」会恢复任何对比度/偏置调整
* 「Remember Color Map」会恢复所做的任何色彩映射选择

*如果未勾选任何内容，则不会从图像配置文件恢复任何内容*。

.. note:: 这些项目将在进行任何自动（cut/zoom/center new）调整*之前*设置。如果设置了
          记住的项目，它将覆盖通道的任何自动调整设置。

.. tip:: 如果您使用此功能，可能还需要设置「Reset (Viewer) Preferences」（见上文）。

***一个示例***

作为使用 Reset 和 Remember 设置的示例，假设您经常使用对比度调整。您希望在再次查看某
幅图像时，恢复您为该图像设置的对比度。然而，当您查看新图像时，您希望对比度从某个正常
设置开始。

为实现此目的，请手动将对比度重置为所需的默认设置。勾选「Reset Contrast」，然后按
「Update Viewer Profile」。最后，勾选「Remember Contrast」。单击「Save Settings」以使
通道设置持久化。

**新图像首选项**

.. figure:: figures/newimages-prefs.png
   :width: 400px
   :align: center
   :alt: 新图像首选项

   「New Image」首选项。

「New Images」首选项决定当新图像加载到通道时 Ginga 如何反应。*这包括通过单击
``Thumbs`` 插件中的缩略图或双击 ``Contents`` 插件中的名称来重新访问较旧图像时*。

「Cut New」设置控制应对新图像执行自动剪切级别计算，还是应应用当前设置的剪切级别。
可能的设置为：

* 「off」：始终使用当前设置的剪切级别；
* 「once」：为第一幅访问的图像计算新的剪切级别，然后转为「off」；
* 「override」：计算新的剪切级别，直到用户通过手动设置剪切级别来覆盖它，然后转为
  「off」；或
* 「on」：始终计算新的剪切级别。

.. tip:: 提供「override」设置是为了方便拥有自动剪切级别，同时防止在摄入新图像时覆盖
         手动设置的剪切。在图像窗口中键入时，分号键可用于将模式（从「off」）切换回
         override，而冒号会将首选项设置为「on」。``Info`` 插件（选项卡：Synopsis）
         显示此设置的状态。

「Zoom New」设置控制访问图像是否应设置缩放级别以使图像适应窗口。可能的设置为：

* 「off」：始终使用当前设置的缩放级别；
* 「once」：将第一幅图像适应窗口，然后转为「off」；
* 「override」：图像自动适应，直到手动更改缩放级别，然后模式自动更改为「off」；或
* 「on」：新图像始终缩放以适应。

.. tip:: 提供「override」设置是为了方便拥有自动缩放，同时防止在摄入新图像时覆盖手动
         设置的缩放级别。在图像窗口中键入时，撇号键（又称「单引号」）可用于将模式
         （从「off」）切换回「override」，而引号（又称双引号）会将首选项设置为「on」。
         ``Info`` 插件（选项卡：Synopsis）显示此设置的状态。

「Center New」设置控制访问图像是否应使平移位置重置为图像的中心。可能的设置为：

* 「off」：保持当前平移位置不变；
* 「once」：将第一幅访问的图像居中，然后转为「off」；
* 「override」：图像自动居中，直到手动更改平移位置，然后模式自动更改为「off」；或
* 「on」：新图像始终居中。

「Follow New」设置用于控制如果新图像加载到通道中 Ginga 是否会更改显示。如果未勾选，
则图像会被加载（例如，通过其在 ``Thumbs`` 选项卡中的出现可以看到），但显示不会更改
为新图像。此设置在以下情况下很有用：新图像正通过某种自动化手段加载到通道中，而用户
希望在不被打断的情况下研究当前图像。

「Raise New」设置控制当图像加载到某个通道时 Ginga 是否会提升该通道的选项卡。如果未
勾选，则当图像加载到该特定通道时，Ginga 不会提升选项卡。

「Create Thumbnail」设置控制 Ginga 是否会为加载到该通道的图像创建缩略图。在许多图像
频繁加载到通道的情况下（例如，低频视频源），为所有这些图像创建缩略图可能是不可取的。

「Auto Orient」设置控制 Ginga 是否应默认根据图像元数据尝试定向图像。这目前仅对包含此
类元数据的 RGB（例如 JPEG）图像有用。目前它不按 WCS 自动定向。

**ICC 配置文件首选项**

.. figure:: figures/icc-prefs.png
   :width: 400px
   :align: center
   :alt: ICC 配置文件首选项

   「ICC Profiles」首选项。

Ginga 可以使用 LittleCMS 库在渲染链中利用 ICC（色彩管理）配置文件。

.. note:: 要利用 ICC 配置文件，请在 Ginga 的「home」（通常为 $HOME/.ginga）中创建一个
          「profiles」文件夹，并将任何必要的配置文件放在那里。应通过在您的
          $HOME/.ginga/general.cfg 文件中为「icc_working_profile」添加一个值来设置
          工作配置文件——不要包含任何前导路径，只需 profiles 文件夹中 ICC 文件的
          文件名。这将用于将任何包含配置文件的 RGB 文件转换为工作配置文件。

您可以在 Preferences 插件的这一部分为任何通道设置输出配置文件。

「Output ICC profile」控件选择用于向显示器输出渲染的配置文件。选项来自您在
$HOME/.ginga/profiles 中的配置文件。通常这应该是显示配置文件。

「Rendering intent」控件选择在 ICC 转换过程中用于渲染颜色的算法。选项为：

* absolute_colorimetric
* perceptual
* relative_colorimetric
* saturation

「Proof ICC profile」和「Proof intent」是为打样类似地选择的。

「Black point compensation」复选框在色彩转换过程中打开或关闭此功能。有关这些选项的
详细信息，请参见 LittleCMS 或一般 ICC 色彩管理的文档。
