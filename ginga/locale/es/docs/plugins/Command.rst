Este complemento proporciona una interfaz de línea de comandos para el visor de
referencia.

.. note:: La línea de comandos es para usarse *dentro* de la interfaz del
          complemento.  Si busca una interfaz de línea de comandos *remota*,
          consulte el complemento ``RC``.

**Tipo de complemento: Global**

``Command`` es un complemento global.  Solo se puede abrir una instancia.

**Uso**

Obtener una lista de comandos y parámetros::

        g> help

Ejecutar un comando de shell::

        g> !cmd arg arg ...

**Notas**

Una herramienta especialmente potente es usar los comandos ``reload_local`` y
``reload_global`` para recargar un complemento cuando lo está desarrollando.
Esto evita tener que reiniciar el visor de referencia y recargar laboriosamente
los datos, etc.  Simplemente cierre el complemento, ejecute el comando «reload»
apropiado (¡vea la ayuda!) y luego vuelva a iniciar el complemento.

.. note:: Si ha modificado módulos *distintos* del complemento en sí, estos no
          serán recargados por estos comandos.
