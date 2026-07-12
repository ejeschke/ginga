``WCSMatch`` es un complemento global para el visor de imágenes Ginga que le
permite alinear a grandes rasgos imágenes con diferentes escalas y
orientaciones utilizando el sistema de coordenadas mundial (WCS) de las
imágenes con fines de visualización.

**Tipo de complemento: Global**

``WCSMatch`` es un complemento global.  Solo se puede abrir una instancia.

**Uso**

Para usarlo, simplemente inicie el complemento y, desde la interfaz del
complemento, seleccione un canal en el menú desplegable «Canal de referencia».
La imagen contenida en ese canal se usará como referencia para sincronizar las
imágenes de los demás canales.

Los canales se sincronizarán en la visualización (panorámica, escala (zoom),
transformaciones (volteos) y rotación).  Las casillas «Igualar la panorámica»,
«Igualar la escala», «Igualar las transformaciones» e «Igualar la rotación»
pueden marcarse o no para controlar qué atributos se sincronizan entre canales.

Para «desbloquear» por completo la sincronización, simplemente seleccione
«None» en el menú desplegable «Canal de referencia».

Actualmente no hay forma de limitar los canales afectados por el complemento.
