Un complemento para navegar por el sistema de archivos local y cargar archivos.

**Tipo de complemento: Global o Local**

``FBrowser`` es un complemento híbrido global/local, lo que significa que puede
invocarse de cualquiera de las dos formas.  Si se invoca como complemento local,
está asociado a un canal y se puede abrir una instancia para cada canal.
También puede abrirse como complemento global.

**Uso**

Navegue por el árbol de directorios hasta llegar a la ubicación de los archivos
que desea cargar.  Puede hacer doble clic en un archivo para cargarlo en el
canal asociado, o arrastrar un archivo a una ventana de visor de canal para
cargarlo en cualquier visor de canal.

Se pueden seleccionar varios archivos manteniendo pulsado ``Ctrl`` (``Command``
en Mac), o haciendo ``Shift``-clic para seleccionar un rango contiguo de
archivos.

También puede introducir la ruta completa de las imágenes deseadas en el cuadro
de texto, como ``/mi/ruta/a/imagen.fits``, ``/mi/ruta/a/imagen.fits[ext]`` o
``/mi/ruta/a/imagen*.fits[extname,*]``.

Como es un complemento local, ``FBrowser`` recordará su último directorio si se
cierra y luego se reinicia.
