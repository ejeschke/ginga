El complemento ``Zoom`` muestra una imagen ampliada de una región recortada
centrada bajo la posición del cursor en la imagen del canal asociado.  A medida
que el cursor se mueve por la imagen, la imagen de zoom se actualiza para
permitir una inspección detallada de los píxeles o un control preciso junto con
otras operaciones de complementos.

**Tipo de complemento: Global**

``Zoom`` es un complemento global.  Solo se puede abrir una instancia.

**Uso**

La ampliación de la ventana de zoom se puede cambiar ajustando el control
deslizante «Cantidad de zoom».

Son posibles dos modos de operación: zoom absoluto y relativo:

* En modo absoluto, la cantidad de zoom controla exactamente el nivel de zoom
  mostrado en el recorte; por ejemplo, la imagen del canal puede estar ampliada
  a 10X, pero la imagen de zoom solo mostrará una imagen 3X si la cantidad de
  zoom está establecida en 3X.

* En modo relativo, el ajuste de cantidad de zoom se interpreta como relativo al
  ajuste de zoom de la imagen del canal.  Si la cantidad de zoom está
  establecida en 3X y la imagen del canal está ampliada a 10X, la imagen de zoom
  mostrada será 13X (10X + 3X).  Tenga en cuenta que el ajuste de cantidad de
  zoom puede ser < 1, de modo que un ajuste de 1/3X con un zoom de 3X en la
  imagen del canal producirá una imagen de zoom 1X.

El ajuste «Intervalo de actualización» controla la rapidez con la que el
complemento ``Zoom`` responde al movimiento del cursor al actualizar la imagen
de zoom.  El valor se especifica en milisegundos.

.. tip:: Normalmente, establecer un intervalo de actualización pequeño *mejora*
         la capacidad de respuesta general de la imagen de zoom, y el valor
         predeterminado de 20 es razonable.  Puede experimentar con el valor si
         la imagen de zoom parece demasiado entrecortada o desincronizada con el
         movimiento del ratón en la ventana de la imagen del canal.

El botón «Predeterminados» restaura los ajustes predeterminados de los
controles.

Es personalizable usando ``~/.ginga/plugin_Zoom.cfg``, donde ``~`` es su
directorio HOME:

.. code-block:: Python

  #
  # Zoom plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_Zoom.cfg"

  # default zoom level
  zoom_amount = 3

  # refresh interval (sec)
  # NOTE: usually a small delay speeds things up
  refresh_interval = 0.02
