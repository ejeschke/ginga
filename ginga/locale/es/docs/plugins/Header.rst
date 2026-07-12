El complemento ``Header`` proporciona un listado de los metadatos asociados a
la imagen.

**Tipo de complemento: Global**

``Header`` es un complemento global.  Solo se puede abrir una instancia.

**Uso**

El complemento ``Header`` muestra los metadatos de palabras clave FITS de la
imagen.  Inicialmente solo se muestran los metadatos del HDU primario.  Sin
embargo, junto con el complemento ``MultiDim``, se mostrarán los metadatos de
otros HDU.  Consulte ``MultiDim`` para más detalles.

Si la casilla «Ordenable» de la parte inferior izquierda de la interfaz está
marcada, al hacer clic en el encabezado de una columna se ordenará la tabla por
los valores de esa columna, lo que puede ser útil para localizar rápidamente
una palabra clave concreta.

La casilla «Incluir la cabecera primaria» alterna la inclusión o no de las
palabras clave del HDU primario.  Esta opción puede estar deshabilitada si la
imagen se creó con la opción de no guardar la cabecera primaria.
