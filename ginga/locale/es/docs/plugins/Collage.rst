
Complemento para crear un mosaico de imágenes mediante el método de collage.

**Tipo de complemento: Local**

``Collage`` es un complemento local, lo que significa que está asociado a un
canal.  Se puede abrir una instancia para cada canal.

**Uso**

Este complemento se usa para crear automáticamente un collage de mosaico en el
visor de canal usando imágenes proporcionadas por el usuario.  La posición de
una imagen en el collage se determina por su WCS sin corrección de distorsión.
Está pensado como una herramienta de vista rápida, no como un sustituto del
«drizzling» de imágenes que tiene en cuenta la distorsión de la imagen, etc.

El collage solo existe como un gráfico en el lienzo de Ginga.  No se construye
realmente ninguna imagen individual nueva (si desea eso, consulte el complemento
«Mosaic»).  Algunos complementos que esperan operar sobre imágenes individuales
pueden no funcionar correctamente con un collage.

Para crear un nuevo collage, haga clic en el botón «Nuevo collage» y arrastre
archivos a la ventana de visualización (p. ej., los archivos se pueden arrastrar
desde el complemento `FBrowser`).  Las imágenes deben tener un WCS que funcione.
La primera imagen procesada se cargará y su WCS se usará para orientar las demás
teselas.  Puede añadir nuevas imágenes a un collage existente simplemente
arrastrando archivos adicionales.

**Controles**

El control «Método» se usa para elegir un método para mosaicar las imágenes del
collage.  Tiene dos valores: 'simple' y 'warp':

- 'simple' intentará rotar y voltear las imágenes según el WCS.  Es un método
  rápido, a costa de la precisión.  No manejará las distorsiones cerca del borde
  del campo que deberían sesgar la imagen.
- 'warp' usará el WCS para mover por completo cada píxel de la imagen según el
  WCS de la imagen de referencia.  Esto puede dejar píxeles vacíos en la imagen
  que se rellenan muestreando de los píxeles circundantes.  Esto será más lento
  que el método simple, y el tiempo aumenta linealmente con el tamaño de las
  imágenes.

Marque el botón «HDU del collage» para que `Collage` intente representar todas
las HDU de imagen de un archivo arrastrado en lugar de solo la primera
encontrada.

Marque «Etiquetar imágenes» para que el complemento dibuje el nombre de cada
imagen sobre cada tesela representada.

Si «Igualar fondo» está marcado, el fondo de cada tesela se ajusta en relación
con la mediana de la primera tesela representada (una especie de suavizado
aproximado).

El cuadro «Número de hilos» asigna cuántos hilos del grupo de hilos se usarán
para cargar los datos.  Usar varios hilos suele acelerar la carga de muchos
archivos.

**Diferencia con el complemento `Mosaic`**

- No asigna una matriz grande para contener todo el contenido del mosaico
- No es necesario especificar el FOV de salida ni preocuparse por él
- Puede mostrar el resultado más rápido (depende un poco de las imágenes
  constituyentes)
- Algunos complementos no funcionarán correctamente con un collage, o serán más
  lentos
- No se puede guardar el collage como archivo de datos (aunque puede usar
  «ScreenShot»)

Es personalizable usando ``~/.ginga/plugin_Collage.cfg``, donde ``~`` es su
directorio HOME:

.. code-block:: Python

  #
  # Collage plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_Collage.cfg"

  # Set to True when you want to collage image HDUs in a file
  collage_hdus = False

  # annotate images with their names
  annotate_images = False

  # Try to match backgrounds
  match_bg = False

  # Number of threads to devote to opening images
  num_threads = 4
