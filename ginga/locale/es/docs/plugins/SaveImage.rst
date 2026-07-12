Guardar imágenes en archivos de salida.

**Tipo de complemento: Global**

``SaveImage`` es un complemento global.  Solo se puede abrir una instancia.

**Uso**

Este complemento global se usa para guardar en imágenes de salida cualquier
cambio realizado en Ginga.  Por ejemplo, una imagen de mosaico creada por el
complemento ``Mosaic``.  Actualmente solo se admiten imágenes FITS (con una o
varias extensiones).

Dado el directorio de salida (p. ej., ``/mypath/outputs/``), un sufijo (p. ej.,
``ginga``), un canal de imagen (``Image``) y una imagen seleccionada (p. ej.,
``image1.fits``), el archivo de salida será
``/mypath/outputs/image1_ginga_Image.fits``.  La inclusión del nombre del canal
es opcional y puede omitirse mediante el archivo de configuración del
complemento, ``plugin_SaveImage.cfg``.
Las extensiones modificadas tendrán la nueva cabecera o los nuevos datos
extraídos de Ginga, mientras que las no modificadas permanecerán intactas.  Las
entradas relevantes del registro de cambios del complemento global
``ChangeHistory`` se insertarán en el historial de su cabecera ``PRIMARY``.

.. note:: Este complemento usa el módulo ``astropy.io.fits`` para escribir las
          imágenes de salida, independientemente de lo que se elija para
          ``FITSpkg`` en el archivo de configuración ``general.cfg``.
