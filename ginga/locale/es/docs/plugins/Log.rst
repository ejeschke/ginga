Vea la salida de registro del visor de referencia.

**Tipo de complemento: Global**

``Log`` es un complemento global.  Solo se puede abrir una instancia.

**Uso**

El complemento ``Log`` construye una interfaz que incluye un gran widget de
texto desplazable que muestra la salida activa del registrador.  La salida más
reciente aparece en la parte inferior.  Esto puede ser útil para resolver
problemas.

Hay cuatro controles:

* El cuadro combinado de la parte inferior izquierda permite elegir el nivel de
  registro deseado.  Los cuatro niveles, en orden de verbosidad, son: «debug»,
  «info», «warn» y «error».
* El cuadro con el número de la parte inferior derecha permite establecer
  cuántas líneas de entrada conservar en el búfer de visualización (p. ej.,
  conservar solo las últimas 1000 líneas).
* La casilla «Desplazamiento automático», si está marcada, hará que el gran
  widget de texto se desplace hasta el final a medida que se añadan nuevos
  mensajes de registro.  Desmárquela si desea examinar y estudiar los mensajes
  más antiguos.
* El botón «Borrar» se usa para borrar el widget de texto, de modo que solo
  aparezca el registro nuevo.
