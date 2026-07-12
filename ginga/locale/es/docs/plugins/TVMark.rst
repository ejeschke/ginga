
Marcar puntos desde un archivo (modo no interactivo) en una imagen.

**Tipo de complemento: Local**

``TVMark`` es un complemento local, lo que significa que está asociado a un
canal.  Se puede abrir una instancia para cada canal.

**Uso**

Este complemento permite el marcado no interactivo de puntos de interés leyendo
un archivo que contiene una tabla con posiciones RA y DEC de esos puntos.  Se
acepta cualquier archivo de texto o de tabla FITS que pueda leer
``astropy.table``, pero el usuario *debe* definir correctamente los nombres de
las columnas en el archivo de configuración del complemento (véase más abajo).
Se intentará convertir los valores RA y DEC a grados.  Si la conversión de
unidades falla, se asumirá que ya están en grados.

Alternativamente, si el archivo tiene columnas que contienen las posiciones
directas de píxel, puede leer estas columnas en su lugar desmarcando la casilla
«Usar RADEC».  De nuevo, los nombres de las columnas deben definirse
correctamente en el archivo de configuración del complemento (véase más abajo).
Los valores de píxel pueden estar indexados en 0 o en 1 (es decir, si el primer
píxel es 0 o 1) y es configurable (véase más abajo).  Esto es útil cuando desea
marcar los píxeles físicos independientemente del WCS (p. ej., marcar píxeles
calientes en un detector).  RA y DEC seguirán mostrándose si la imagen tiene
información WCS, pero no afectarán a las marcas.

Para marcar distintos grupos (p. ej., mostrando galaxias como círculos verdes y
el fondo como cruces cian, como se muestra arriba):

1. Seleccione círculo verde en los menús desplegables.  Alternativamente,
   introduzca el tamaño o la anchura deseados.
2. Asegúrese de que la casilla «Usar RADEC» esté marcada, si procede.
3. Usando el botón «Cargar coordenadas», cargue el archivo que contiene las
   posiciones RA y DEC (o X e Y) *solo* de las galaxias.
4. Repita el paso 1 pero ahora seleccione cruz cian en los menús desplegables.
5. Repita el paso 2 pero elija el archivo que contiene *solo* las posiciones del
   fondo.

Seleccionar una entrada (o varias entradas) de la lista de la tabla resaltará
la(s) marca(s) en la imagen.  El resaltado usa la misma forma y color, pero una
línea ligeramente más gruesa.

También puede resaltar todas las marcas dentro de una región, tanto en la imagen
como en la lista de la tabla, dibujando un rectángulo en la imagen mientras este
complemento está activo.

Pulsar el botón «Ocultar» ocultará las marcas pero no borra la memoria del
complemento; es decir, cuando pulse «Mostrar», las mismas marcas reaparecerán en
la misma imagen.  Sin embargo, pulsar «Olvidar» borrará las marcas tanto de la
visualización como de la memoria; es decir, tendrá que volver a cargar su(s)
archivo(s) para recrear las marcas.

Para volver a dibujar las mismas posiciones con distintos parámetros de marca,
pulse «Olvidar» y repita los pasos anteriores según sea necesario.  Sin embargo,
si simplemente desea cambiar la anchura de línea (grosor), pulsar «Ocultar» y
luego «Mostrar» tras introducir el nuevo valor de anchura será suficiente.

Si en el mismo canal se muestran imágenes de apuntados/dimensiones muy
diferentes, las marcas que pertenecen a una imagen pero caen fuera de otra no
aparecerán en esta última.

Para crear una tabla que este complemento pueda leer, se pueden usar los
resultados del complemento ``Pick``, además de crear una tabla a mano, usando
``astropy.table``, etc.

Usado junto con ``TVMask``, puede superponer en Ginga tanto fuentes puntuales
como regiones enmascaradas.

Es personalizable usando ``~/.ginga/plugin_TVMark.cfg``, donde ``~`` es su
directorio HOME:

.. code-block:: Python

  #
  # TVMark plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_TVMark.cfg"

  # Marking type -- 'circle' or 'cross'
  marktype = 'circle'

  # Marking color -- Any color name accepted by Ginga
  markcolor = 'green'

  # Marking size or radius
  marksize = 5

  # Marking line width (thickness)
  markwidth = 1

  # Specify whether pixel values are 0- or 1-indexed
  pixelstart = 1

  # True -- Use 'ra' and 'dec' columns to extract RA/DEC positions. This option
  #         uses image WCS to convert to pixel locations.
  # False -- Use 'x' and 'y' columns to extract pixel locations directly.
  #          This does not use WCS.
  use_radec = True

  # Columns to load into table listing (case-sensitive).
  # Whether RA/DEC or X/Y columns are used depend on associated GUI selection.
  ra_colname = 'ra'
  dec_colname = 'dec'
  x_colname = 'x'
  y_colname = 'y'
  # Extra columns to display; e.g., ['colname1', 'colname2']
  extra_columns = []
