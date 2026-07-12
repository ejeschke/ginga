``SAMP`` 插件为 Ginga 参考查看器实现 SAMP 接口。

.. note:: 要运行此插件，您需要安装带有 ``samp`` 模块的 ``astropy``。

**插件类型：全局**

``SAMP`` 是全局插件。只能打开一个实例。

**用法**

Ginga 包含一个用于启用 SAMP（Simple Applications Messaging Protocol，简单应用
消息协议）支持的插件。有了 SAMP 支持，Ginga 可以被控制，并与其他天文桌面应用
程序互操作。

``SAMP`` 模块默认不启动。要在 Ginga 启动时启动它，请指定命令行选项::

        --modules=SAMP

否则，请使用「插件」菜单中的「启动 SAMP 中心」来启动它。

目前，SAMP 支持仅限于 ``image.load.fits`` 消息，这意味着 Ginga 在收到其中一条
消息时将加载一个 FITS 文件。

Ginga 的 ``SAMP`` 插件使用 ``astropy.samp`` 模块，因此您需要安装 ``astropy``
才能使用该插件。默认情况下，如果未发现正在运行的 SAMP 中心，Ginga 的 ``SAMP``
插件将尝试启动一个 SAMP 中心。
