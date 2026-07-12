将图像保存到输出文件。

**插件类型：全局**

``SaveImage`` 是全局插件。只能打开一个实例。

**用法**

此全局插件用于将在 Ginga 中所做的任何更改保存回输出图像。例如，由 ``Mosaic``
插件创建的拼接图像。目前仅支持 FITS 图像（单个或多个扩展）。

给定输出目录（例如 ``/mypath/outputs/``）、后缀（例如 ``ginga``）、图像通道
（``Image``）和选定的图像（例如 ``image1.fits``），输出文件将是
``/mypath/outputs/image1_ginga_Image.fits``。是否包含通道名称是可选的，可以
使用插件配置文件 ``plugin_SaveImage.cfg`` 将其省略。
修改过的扩展将具有从 Ginga 提取的新头或数据，而未修改的扩展则保持不变。来自
全局插件 ``ChangeHistory`` 的相关更改日志条目将插入其 ``PRIMARY`` 头的历史中。

.. note:: 无论在 ``general.cfg`` 配置文件中为 ``FITSpkg`` 选择了什么，此插件
          都使用 ``astropy.io.fits`` 模块来写入输出图像。
