``Ruler`` es un complemento sencillo diseñado para medir distancias en una
imagen.

**Tipo de complemento: Local**

``Ruler`` es un complemento local, lo que significa que está asociado a un
canal.  No es un singleton, lo que significa que se pueden abrir varias
instancias para cada canal.

**Uso**

``Ruler`` mide la distancia calculando una triangulación esférica mediante el
mapeo WCS de tres puntos definidos por una única línea dibujada en la imagen.
De forma predeterminada, la distancia se muestra en arcominutos de cielo, pero
usando el control «Unidades», se puede cambiar para mostrar grados o distancia
en píxeles en su lugar.

Haga clic y arrastre para establecer una regla entre dos puntos.  Cuando termine
la operación de dibujo, la regla queda establecida y la interfaz del complemento
se actualizará para mostrar detalles sobre la línea, incluidas las posiciones de
los extremos y el ángulo de la línea.  Las unidades del ángulo se pueden
alternar entre grados y radianes usando el cuadro desplegable adyacente.

Para borrar la regla anterior y crear una nueva, haga clic y arrastre de nuevo.
Cuando se dibuja otra línea, esta reemplaza a la primera.  Cuando se cierra el
complemento, la superposición gráfica se elimina.  Si desea «reglas fijas», use
el complemento ``Drawing`` (y elija «Ruler» como tipo de dibujo).

**Edición**

Para editar una regla existente, haga clic en el botón de radio de la interfaz
del complemento etiquetado «Editar».  Si la regla no se selecciona de inmediato,
haga clic en la diagonal que conecta los dos puntos.  Esto debería establecer un
cuadro delimitador alrededor de la regla y mostrar sus puntos de control.
Arrastre dentro del cuadro delimitador para mover la regla, o haga clic y
arrastre los extremos para editar la regla.  La regla también se puede escalar o
rotar usando esos puntos de control.

**Interfaz**

Las unidades mostradas para la distancia se pueden seleccionar en el cuadro
desplegable de la interfaz.  Puede elegir entre «arcmin», «degrees» o «pixels».
Las dos primeras requieren un WCS válido y funcional en la imagen.

Los valores de los extremos se muestran en la interfaz, pero además se pueden
mostrar en el gráfico de la regla si se activa la casilla «Mostrar extremos».
Se mostrarán líneas de plomada si se activa la casilla «Mostrar plomada».

**Botones**

El botón «Desplazar al origen» desplazará la imagen principal al origen de la
línea dibujada, mientras que «Desplazar al destino» se desplazará al final.
«Desplazar al centro» establece la posición de desplazamiento en el punto
central de la línea.  Estos botones pueden ser útiles para el trabajo de primer
plano y con zoom en la imagen.  «Borrar» borra la regla de la imagen.

**Consejos**
Abra el complemento «Zoom» para ver con precisión el detalle del área del
cursor.  El complemento «Pick» también se puede usar junto con Ruler para
identificar el punto central de un objeto al alinear cualquiera de los extremos
de la regla.
