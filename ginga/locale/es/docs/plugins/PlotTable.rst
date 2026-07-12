Un complemento para mostrar un gráfico básico de dos columnas seleccionadas
cualesquiera de una tabla.

**Tipo de complemento: Local**

``PlotTable`` es un complemento local, lo que significa que está asociado a un
canal.  No es un singleton, lo que significa que se pueden abrir varias
instancias para cada canal.

**Uso**

``PlotTable`` es un complemento diseñado para representar dos columnas
seleccionadas cualesquiera de un HDU de tabla FITS dado (accesible mediante
``MultiDim``).
En las columnas enmascaradas no se muestran los datos enmascarados (aunque solo
uno del par ``(X, Y)`` esté enmascarado).
Está pensado como una forma de examinar rápidamente los datos de una tabla, no
para un análisis científico detallado.
