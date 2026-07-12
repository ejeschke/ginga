Complemento para crear un mosaico de imágenes construyendo una imagen compuesta.

**Tipo de complemento: Local**

``Mosaic`` es un complemento local, lo que significa que está asociado a un
canal.  Se puede abrir una instancia para cada canal.

**Uso**

.. warning:: Esto puede consumir mucha memoria.

Este complemento se usa para construir automáticamente una imagen de mosaico en
el canal usando imágenes proporcionadas por el usuario (p. ej., usando
``FBrowser``).
La posición de una imagen en el mosaico se determina por su WCS sin corrección
de distorsión.  Está pensado como una herramienta de vista rápida, no como un
sustituto del «drizzling» de imágenes que tiene en cuenta la distorsión de la
imagen, etc.  El mosaico solo existe en memoria, pero puede guardarlo en un
archivo FITS usando ``SaveImage``.

Cuando un mosaico se sale de la memoria, deja de ser accesible en Ginga.  Para
evitarlo, debe configurar su sesión de modo que la caché de datos de Ginga sea
lo suficientemente grande (consulte «Customizing Ginga» en el manual).

Para crear un nuevo mosaico, establezca el FOV y arrastre archivos a la ventana
de visualización.  Las imágenes deben tener un WCS que funcione.  El WCS de la
primera imagen se usará para orientar las demás teselas.

**Diferencia con el complemento `Collage`**

- Asigna una única matriz grande para contener todo el contenido del mosaico
- Más lento de construir, pero puede ser más rápido manipular imágenes
  resultantes grandes
- Puede guardar el mosaico como un nuevo archivo de datos
- Rellena los valores entre teselas con un valor de relleno (puede ser `NaN`)
