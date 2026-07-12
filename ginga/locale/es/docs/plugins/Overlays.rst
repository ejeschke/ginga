Un complemento para generar superposiciones de color que representan la
subexposición y la sobreexposición en la imagen cargada.

**Tipo de complemento: Local**

``Overlays`` es un complemento local, lo que significa que está asociado a un
canal.  Se puede abrir una instancia para cada canal.

**Uso**

Elija colores en los menús desplegables para el límite inferior y/o superior
(«Color inferior» y «Color superior», respectivamente).  Especifique los
límites para los valores bajos y altos en las casillas de límite («Límite
inferior» y «Límite superior», respectivamente).  Establezca la opacidad de las
superposiciones con un valor entre 0 y 1 en la casilla «Opacidad».  Por último,
pulse el botón «Rehacer».

La superposición de color debería mostrar las áreas por debajo del límite
inferior con un color inferior y las áreas por encima del límite superior con
el color superior.  Si omite un límite (deja la casilla en blanco), ese color
no se mostrará en la superposición.

Si se selecciona una nueva imagen para el canal, la imagen de superposición se
recalculará según los parámetros actuales con los nuevos datos.
