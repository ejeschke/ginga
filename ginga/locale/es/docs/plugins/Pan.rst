El complemento ``Pan`` proporciona una pequeña imagen de panorámica que ofrece
una vista general «a vista de pájaro» de la imagen de canal que tuvo el foco por
última vez.  Si la imagen del canal está ampliada 2X o más, la región de
panorámica se muestra gráficamente en la imagen ``Pan`` mediante un rectángulo.

**Tipo de complemento: Local**

``Pan`` es un complemento global.  Solo se puede abrir una instancia.

**Uso**

La imagen del canal se puede desplazar haciendo clic y/o arrastrando para
colocar el rectángulo.  Usar el botón derecho del ratón para arrastrar un
rectángulo obligará al visor de imágenes del canal a intentar coincidir con la
región (teniendo en cuenta las diferencias de proporción entre el rectángulo
dibujado y las dimensiones de la ventana).  Desplazarse en la imagen ``Pan``
hará zoom en la imagen del canal.

El mapa de color/intensidad y los niveles de corte de la imagen ``Pan`` se
actualizan cuando se cambian en la imagen de canal correspondiente.
La imagen ``Pan`` también muestra la brújula del sistema de coordenadas mundial
(WCS), si hay metadatos WCS válidos en el HDU FITS que se está viendo en el
canal.

El complemento ``Pan`` suele aparecer como un subpanel bajo la pestaña «Info»,
junto al complemento ``Info``.

Este complemento no suele configurarse como cerrable, pero el usuario puede
hacerlo estableciendo el ajuste «closeable» en True en el archivo de
configuración; entonces se añadirán los botones Cerrar y Ayuda en la parte
inferior de la interfaz.
