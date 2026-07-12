
用于在 FITS 文件的 HDU 之间，或在 3D 立方体或更高维度数据集的平面之间导航的
插件。

**插件类型：本地**

``MultiDim`` 是本地插件，这意味着它与某个通道相关联。
可以为每个通道打开一个实例。

**用法**

``MultiDim`` 是为处理数据立方体和多 HDU FITS 文件而设计的插件。如果您在 Ginga
中打开了这样一幅图像，启动此插件将使您能够浏览到立方体的其他切片或查看其他 HDU。

对于数据立方体，您可以使用「保存切片」按钮将切片保存为图像，或通过输入「起始」和
「结束」切片索引，使用「保存影片」按钮创建影片。此功能需要安装 ``mencoder``。

对于 FITS 表，其数据使用 Astropy 表读入。列单位显示在主标题正下方（无单位时为
「None」）。对于掩码列，掩码值将替换为预定义的填充值。

**浏览 HDU**

使用界面上部的 HDU 下拉列表来浏览并选择要在通道中打开的 HDU。

**在立方体中导航**

使用界面下部的控件来选择轴，并逐一浏览该轴中的平面。

**用户配置**

它可使用 ``~/.ginga/plugin_MultiDim.cfg`` 进行自定义，其中 ``~`` 是您的 HOME
目录：

.. code-block:: Python

  #
  # MultiDim plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_MultiDim.cfg"

  # Sort option for HDU listing.
  # Available attributes:
  #   'index' -- Extension index
  #   'name' -- Extension name
  #   'extver' -- Extension version number
  #   'htype' -- HDU type (PrimaryHDU, ImageHDU, TableHDU)
  #   'dtype' -- Data type
  # Example to sort by HDU name and extver:
  #   sort_keys = ['name', 'extver']
  # Default is to sort by index only:
  sort_keys = ['index']

  # Reverse for HDU listing?
  sort_reverse = False
