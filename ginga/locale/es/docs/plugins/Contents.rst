
El complemento ``Contents`` proporciona una interfaz tipo tabla de contenidos
para todas las imágenes vistas desde que se inició el programa.  A diferencia de
``Thumbs``, ``Contents`` está ordenado por canal.  El contenido también muestra
algunos metadatos configurables de la imagen.

**Tipo de complemento: Global**

``Contents`` es un complemento global.  Solo se puede abrir una instancia.

**Uso**

Haga clic en el encabezado de una columna para ordenar la tabla por esa columna;
haga clic de nuevo para ordenar en sentido contrario.

.. note:: Las columnas y sus valores se toman de la cabecera FITS, si procede.
          Esto se puede personalizar estableciendo el parámetro «columns» en el
          archivo de ajustes «plugin_Contents.cfg».

La imagen activa en el canal actualmente enfocado normalmente estará resaltada.
Un doble clic en una imagen forzará que esa imagen se muestre en el canal
asociado.  Un solo clic en cualquier imagen activa los botones de la parte
inferior de la interfaz:

* «Mostrar»: Hace que la imagen sea la imagen activa.
* «Mover»: Mueve la imagen a otro canal.
* «Copiar»: Copia la imagen a otro canal.
* «Quitar»: Quita la imagen del canal.

Si se hace «Mover» o «Copiar» en una imagen que se ha modificado en Ginga (que
tendría una entrada en ``ChangeHistory``, si se usa), el historial de
modificaciones también se conservará.  Quitar una imagen de un canal destruye
cualquier cambio no guardado.

Este complemento no suele configurarse para poder cerrarse, pero el usuario
puede hacer que lo sea estableciendo el ajuste «closeable» en True en el archivo
de configuración; entonces se añadirán los botones Cerrar y Ayuda en la parte
inferior de la interfaz.

**Excluir imágenes de Contents**

.. note:: Esto también controla el comportamiento de ``Thumbs``.

Aunque el comportamiento predeterminado es que toda imagen que se carga en el
visor de referencia aparezca en ``Contents``, puede haber casos en los que esto
sea indeseable (p. ej., cuando algún proceso automatizado carga muchas imágenes
a un ritmo periódico).  En tales casos hay dos mecanismos para suprimir que
ciertas imágenes aparezcan en ``Contents``:

* Asignar el ajuste «genthumb» a False en los ajustes de un canal (por ejemplo,
  desde el complemento ``Preferences``, bajo los ajustes «General») excluirá el
  canal en sí y cualquiera de sus imágenes.
* Establecer la palabra clave «nothumb» en los metadatos de un envoltorio de
  imagen (no en la cabecera FITS, sino p. ej. mediante ``image.set(nothumb=True)``)
  excluirá esa imagen en particular de ``Contents``, incluso si el ajuste
  «genthumb» es True para ese canal.

Es personalizable usando ``~/.ginga/plugin_Contents.cfg``, donde ``~`` es su
directorio HOME:

.. code-block:: Python

  #
  # Contents plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_Contents.cfg"

  # columns to show from metadata -- NAME and MODIFIED recommended
  # format: [(col header, keyword1), ... ]
  columns = [ ('Name', 'NAME'), ('Object', 'OBJECT'), ('Filter', 'FILTER01'), ('Date', 'DATE-OBS'), ('Time UT', 'UT'), ('Modified', 'MODIFIED')]

  # If set to True, will always expand the tree in Contents when new entries are added
  always_expand = True

  # Option to highlight images that are displayed in channels.
  # If set to True this option will only highlight the image that is in the
  # channel with the keyboard focus
  highlight_tracks_keyboard_focus = False

  # If True, color every other row in alternating shades to improve
  # readability of long tables
  color_alternate_rows = True

  # Highlighted row colors (in addition to bold text)
  row_font_color = 'green'

  # Maximum number of rows that will turn off auto column resizing (for speed)
  max_rows_for_col_resize = 100

  # Add a close button to this plugin, so that it can be stopped
  closeable = False
