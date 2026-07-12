Un complemento para graficar los valores de los píxeles a lo largo de una línea
recta que biseca un cubo.

**Tipo de complemento: Local**

``LineProfile`` es un complemento local, lo que significa que está asociado a un
canal.  Se puede abrir una instancia para cada canal.

**Uso**

.. warning::

   No hay restricciones sobre qué ejes se pueden elegir.
   Por ello, el gráfico puede carecer de sentido.

El complemento ``LineProfile`` se usa para imágenes multidimensionales (es
decir, 3D o superior).  Representa los valores de los píxeles en la posición
actual del cursor a través del eje seleccionado; o, si se selecciona una región,
representa la media en cada fotograma.  Esto puede usarse para crear perfiles de
línea espectrales normales.  Se coloca un marcador en el punto de datos del
fotograma mostrado actualmente.

El eje X mostrado se construye usando las palabras clave ``CRVAL*``, ``CDELT*``,
``CRPIX*``, ``CTYPE*`` y ``CUNIT*`` de la cabecera FITS.  Si alguna de las
palabras clave no está disponible, el eje recurre a los valores ``NAXIS*`` en su
lugar.

El eje Y mostrado se construye usando ``BTYPE`` y ``BUNIT``.  Si no están
disponibles, simplemente etiqueta los valores de píxel como «Signal».

Para usar este complemento:

1. Seleccione un eje.
2. Elija un punto o dibuje una región con el cursor.
3. Use ``MultiDim`` para cambiar los valores de paso de los ejes, si procede.
