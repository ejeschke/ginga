Un complemento para dibujar formas de lienzo (gráficos superpuestos).

**Tipo de complemento: Local**

``Drawing`` es un complemento local, lo que significa que está asociado a un
canal.  No es un singleton, lo que significa que se pueden abrir varias
instancias para cada canal.

**Uso**

Este complemento se puede usar para dibujar muchas formas diferentes en la
visualización de la imagen.  Cuando está en modo «dibujar», seleccione una forma
en el menú desplegable, ajuste los parámetros de la forma (si es necesario) y
dibuje en la imagen usando el botón izquierdo del ratón.  Puede elegir dibujar
en el espacio de píxeles o WCS.

Para mover o editar una forma existente, ponga el complemento en modo «editar» o
«mover», respectivamente.

Para guardar las formas dibujadas como imagen de máscara, haga clic en el botón
«Crear máscara» y verá una nueva imagen de máscara creada en Ginga.  Luego, use
el complemento ``SaveImage`` para guardarla como FITS de una sola extensión.
Tenga en cuenta que la máscara tomará el tamaño de la imagen mostrada.  Por lo
tanto, para crear máscaras de distintas dimensiones de imagen, debe repetir los
pasos varias veces.

Las formas dibujadas en el lienzo se pueden cargar y/o guardar en formato
astropy-regions (compatible con las regiones de DS9).  Para usarlo, necesita
tener instalado el paquete astropy-regions.  Simplemente dibuje objetos en el
lienzo, con coordenadas como «data» (píxel) o «wcs».  Tenga en cuenta que no
todos los objetos de lienzo de Ginga pueden convertirse en formas de regiones y
que algunos atributos pueden no guardarse, pueden ignorarse o pueden causar
errores al intentar cargar las formas de regiones en otro software.
