
El complemento ``Thumbs`` proporciona un índice de miniaturas de todas las
imágenes vistas desde que se inició el programa.

**Tipo de complemento: Global**

``Thumbs`` es un complemento global.  Solo se puede abrir una instancia.

**Uso**

De forma predeterminada, las ``Thumbs`` aparecen en el historial de
visualización cronológico, con las imágenes más nuevas en la parte inferior y
las más antiguas en la parte superior.  La ordenación se puede hacer
alfanumérica mediante un ajuste en el archivo de configuración
«plugin_Thumbs.cfg».

Hacer clic en una miniatura le lleva directamente a esa imagen en el canal
asociado.  Pasar el cursor sobre una miniatura mostrará una información sobre
herramientas que contiene un par de datos útiles de la imagen.

La casilla «Desplazamiento automático», si está marcada, hará que la vista de
``Thumbs`` se desplace hasta la imagen activa.

Este complemento no suele configurarse para poder cerrarse, pero el usuario
puede hacer que lo sea estableciendo el ajuste «closeable» en True en el archivo
de configuración; entonces se añadirán los botones Cerrar y Ayuda en la parte
inferior de la interfaz.

**Excluir imágenes de Thumbs**

.. note:: Esto también controla el comportamiento de ``Contents``.

Aunque el comportamiento predeterminado es que toda imagen que se carga en el
visor de referencia aparezca en ``Thumbs``, puede haber casos en los que esto
sea indeseable (p. ej., cuando algún proceso automatizado carga muchas imágenes
a un ritmo periódico).  En tales casos hay dos mecanismos para suprimir que
ciertas imágenes aparezcan en ``Thumbs``:

* Asignar el ajuste «genthumb» a False en los ajustes de un canal (por ejemplo,
  desde el complemento ``Preferences``, bajo los ajustes «General») excluirá el
  canal en sí y cualquiera de sus imágenes.
* Establecer la palabra clave «nothumb» en los metadatos de un envoltorio de
  imagen (no en la cabecera FITS, sino p. ej. mediante ``image.set(nothumb=True)``)
  excluirá esa imagen en particular de ``Thumbs``, incluso si el ajuste
  «genthumb» es True para ese canal.

Es personalizable usando ``~/.ginga/plugin_Thumbs.cfg``, donde ``~`` es su
directorio HOME:

.. code-block:: Python

  #
  # Thumbs plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_Thumbs.cfg"

  # If you revisit the same directories frequently
  # caching thumbs saves a lot of time when they need to be regenerated
  cache_thumbs = False

  # cache location-- "local" puts them in a .thumbs subfolder, otherwise
  # they are cached in ~/.ginga/thumbs
  cache_location = 'local'

  # Scroll the pane automatically when new thumbnails arrive
  auto_scroll = True

  # Keywords to extract and show if we mouse over the thumbnail
  tt_keywords = ['OBJECT', 'FRAMEID', 'UT', 'DATE-OBS']

  # Mandatory unique image identifier in tooltip
  mouseover_name_key = 'NAME'

  # How many seconds to wait after an image is altered to begin trying
  # to rebuild a matching thumb.  Usually a few seconds is good in case
  # there is ongoing adjustment of the image
  rebuild_wait = 0.5

  # Max length of thumb on the long side
  thumb_length = 180

  # Separation between thumbs in pixels
  thumb_hsep = 15
  thumb_vsep = 15

  # Sort the thumbs alphabetically: 'alpha' or None
  sort_order = None

  # Thumbnail label length in num of characters (None = no limit)
  label_length = 25

  # Cut off long label ('left', 'right', or None)
  label_cutoff = 'right'

  # Option to highlight images that are displayed in channels.
  # If set to True this option will only highlight the image that is in the
  # channel with the keyboard focus
  highlight_tracks_keyboard_focus = True

  # Highlighted label colors
  label_bg_color = 'lightgreen'
  label_font_color = 'white'

  label_font_size = 10

  # Load visible thumbs in the background to replace placeholder icons
  autoload_visible_thumbs = True

  # Length of time to wait after scrolling to begin autoloading
  autoload_interval = 1.0

  # list of attributes to transfer from the channel viewer to the
  # thumbnail generator if the channel has an image in it
  transfer_attrs = ['transforms', 'cutlevels', 'rgbmap']

  # Add a close button to this plugin, so that it can be stopped
  closeable = False
