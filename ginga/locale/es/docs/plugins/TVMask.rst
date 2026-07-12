
Mostrar máscaras desde un archivo (modo no interactivo) en una imagen.

**Tipo de complemento: Local**

``TVMask`` es un complemento local, lo que significa que está asociado a un
canal.  Se puede abrir una instancia para cada canal.

**Uso**

Este complemento permite la visualización no interactiva de una máscara leyendo
un archivo FITS, donde se asume que los valores distintos de cero son datos
enmascarados.

Para mostrar distintas máscaras (p. ej., algunas enmascaradas en verde y otras
en rosa, como se muestra arriba):

1. Seleccione verde en el menú desplegable.  Alternativamente, introduzca el
   valor alfa deseado.
2. Usando el botón «Cargar máscara», cargue el archivo FITS pertinente.
3. Repita (1) pero ahora seleccione rosa en el menú desplegable.
4. Repita (2) pero elija otro archivo FITS.
5. Para mostrar una tercera máscara también en rosa, repita (4) sin cambiar el
   menú desplegable.

Seleccionar una entrada (o varias entradas) de la lista de la tabla resaltará
la(s) máscara(s) en la imagen.  El resaltado usa un color y un alfa
predefinidos (personalizables más abajo).

También puede resaltar todas las máscaras dentro de una región, tanto en la
imagen como en la lista de la tabla, dibujando un rectángulo en la imagen
mientras este complemento está activo.

Pulsar el botón «Ocultar» ocultará las máscaras pero no borra la memoria del
complemento; es decir, cuando pulse «Mostrar», las mismas máscaras
reaparecerán en la misma imagen.  Sin embargo, pulsar «Olvidar» borrará las
máscaras tanto de la visualización como de la memoria; es decir, tendrá que
volver a cargar su(s) archivo(s) para recrear las máscaras.

Para volver a dibujar las mismas máscaras con distinto color o alfa, pulse
«Olvidar» y repita los pasos anteriores según sea necesario.

Si en el mismo canal se muestran imágenes de apuntados/dimensiones muy
diferentes, las máscaras que pertenecen a una imagen pero caen fuera de otra no
aparecerán en esta última.

Para crear una máscara que este complemento pueda leer, se pueden usar los
resultados del complemento ``Drawing`` (pulse «Crear máscara» después de dibujar
y guarde la máscara usando ``SaveImage``), además de crear un archivo FITS a
mano usando ``astropy.io.fits``, etc.

Usado junto con ``TVMark``, puede superponer en Ginga tanto fuentes puntuales
como regiones enmascaradas.

Es personalizable usando ``~/.ginga/plugin_TVMask.cfg``, donde ``~`` es su
directorio HOME:

.. code-block:: Python

  #
  # TVMask plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_TVMask.cfg"

  # Mask color -- Any color name accepted by Ginga
  maskcolor = 'green'

  # Mask alpha (transparency) -- 0=transparent, 1=opaque
  maskalpha = 0.5

  # Highlighted mask color and alpha
  hlcolor = 'white'
  hlalpha = 1.0
