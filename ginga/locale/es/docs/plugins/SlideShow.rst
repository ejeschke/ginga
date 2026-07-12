Reproducir una presentación de diapositivas de imágenes.

**Tipo de complemento: Local**

``SlideShow`` es un complemento local, lo que significa que está asociado a un
canal.  No es un singleton, lo que significa que se pueden abrir varias
instancias para cada canal.

**Uso**

***Cargar una presentación***

Después de iniciar el complemento, puede usar el botón «Cargar» para cargar una
presentación (véase más abajo el formato de archivo de la presentación).  Luego
puede volver a cargar esta presentación tras editar externamente el archivo en
cualquier momento pulsando «Recargar».

***Reproducir una presentación***

Los botones «Anterior» y «Siguiente» pueden usarse para retroceder y avanzar
manualmente dentro de la lista.  El control de botón giratorio entre estos dos
botones le llevará a una diapositiva concreta dentro de la lista.

Los botones «Iniciar» y «Detener» se usan para iniciar o detener el avance
automático dentro de la presentación.

***Controlar la duración***

Cada diapositiva puede tener un parámetro «duration» separado (en segundos)
para controlar cuánto tiempo pasa antes de avanzar a la siguiente diapositiva,
pero si falta para una diapositiva se usa la duración predeterminada.  La
duración predeterminada se puede establecer mediante el control marcado
«Duración predeterminada».

Debajo del control de duración predeterminada hay una etiqueta que muestra la
duración de la diapositiva y la duración total de la presentación.

**Formato de archivo de la presentación**

El formato de archivo de la presentación es un archivo de texto plano separado
por comas (CSV) con una línea de encabezado.  El archivo debe contener al menos
una columna, titulada «file».  Esta columna contiene los nombres de archivo
(relativos o absolutos) de las rutas a los archivos que se cargarán para cada
diapositiva.

***Columnas opcionales***

* «duration»:  debe contener la duración (en segundos) de cada diapositiva
* «position»: indica la posición de la diapositiva en la presentación.
  Se pueden usar números de punto flotante para facilitar la reordenación de
  las diapositivas al editar el archivo de la presentación.
