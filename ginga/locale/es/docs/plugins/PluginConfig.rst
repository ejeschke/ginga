
El complemento ``PluginConfig`` le permite configurar los complementos que
son visibles en sus menús.

**Tipo de complemento: Global**

``PluginConfig`` es un complemento global.  Solo se puede abrir una instancia.

**Uso**

``PluginConfig`` se usa para configurar los complementos que se utilizarán en
Ginga.  Los elementos que se pueden configurar para cada complemento incluyen:

* si está habilitado (y, por tanto, si aparece en los menús)
* la categoría del complemento (usada para construir la jerarquía de menús)
* el espacio de trabajo en el que se abrirá el complemento
* si es un complemento global, si se inicia automáticamente cuando arranca el
  visor de referencia
* si el nombre del complemento debe ocultarse (no aparecer en los menús de
  activación de complementos)

Cuando ``PluginConfig`` se inicia, mostrará una tabla de complementos.  Para
editar los atributos anteriores de los complementos, haga clic en «Editar»,
lo que abrirá un diálogo para editar la tabla.

Para cada complemento que desee configurar, haga clic en una entrada de la
tabla principal y luego ajuste los parámetros en el diálogo; después haga clic
en «Establecer» en el diálogo para reflejar los cambios de vuelta en la tabla.
Si no hace clic en «Establecer», no se cambia nada en la tabla.  Cuando
termine de editar las configuraciones, haga clic en «Cerrar» en el diálogo
para cerrar el diálogo de edición.

.. note:: No se recomienda cambiar el espacio de trabajo de un complemento a
          menos que elija un espacio de trabajo de tamaño compatible con el
          original, ya que el complemento podría no mostrarse correctamente.
          En caso de duda, deje el espacio de trabajo sin cambios.  Además,
          deshabilitar complementos de la categoría «Systems» puede provocar
          que algunas funciones esperadas dejen de funcionar.


.. important:: Para que los cambios persistan entre reinicios de Ginga, haga
               clic en «Guardar» para guardar los ajustes (en
               `$HOME/.ginga/plugins.json`).  Reinicie Ginga para ver los
               cambios en los menús (mediante cambios de «category»).
               **Elimine este archivo manualmente si desea restablecer las
               configuraciones de los complementos a los valores
               predeterminados**.
