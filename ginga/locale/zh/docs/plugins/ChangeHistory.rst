跟踪缓冲区更改历史。

**插件类型：全局**

``ChangeHistory`` 是全局插件。只能打开一个实例。

此插件用于记录对数据缓冲区的任何更改。例如，如果通过 ``Mosaic`` 插件向拼接图中
添加了一幅新图像，更改日志便会显示在这里。与 ``Contents`` 一样，日志按通道排序，
然后按图像名称排序。

**用法**

无论哪个通道或图像处于活动状态，历史都应保留。可以添加新历史，但除非删除图像/
通道本身，否则无法删除旧历史。

``redo()`` 方法会捕获一个 ``'add-image-info'`` 事件，并在此处显示相关元数据。
元数据按如下方式获取::

        channel = self.fv.get_channel_info(chname)
        iminfo = channel.get_image_info(imname)
        timestamp = iminfo.time_modified
        description = iminfo.reason_modified  # Optional

``'time_modified'`` 和 ``'reason_modified'`` 都必须由调用插件在发出
``'add-image-info'`` 回调的同一方法中显式设置，如下所示::

        # 这会更改数据缓冲区
        image.set_data(new_data, ...)
        # 为 ChangeHistory 添加描述
        info = dict(time_modified=datetime.now(tz=tz.UTC),
                    reason_modified='Data has changed')
        self.fv.update_image_info(image, info)
