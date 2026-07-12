Hacer cambios en los ajustes del canal gráficamente en la interfaz.

**Tipo de complemento: Local**

``Preferences`` es un complemento local, lo que significa que está asociado a un
canal.  Se puede abrir una instancia para cada canal.

**Uso**

El complemento ``Preferences`` establece las preferencias *por canal*.  Las
preferencias de un canal dado se heredan del canal «Image» hasta que se
establecen y guardan explícitamente usando este complemento.

Si se pulsa «Save Settings», se guardarán los ajustes en la carpeta
$HOME/.ginga del usuario (un archivo «channel_NAME.cfg» para cada canal NAME) de
modo que cuando se cree un canal con el mismo nombre en futuras sesiones de
Ginga, obtendrá los mismos ajustes.

**Preferencias de distribución de color**

.. figure:: figures/cdist-prefs.png
   :width: 400px
   :align: center
   :alt: Preferencias de distribución de color

   Preferencias de «Color Distribution».

Las preferencias de «Color Distribution» controlan las preferencias usadas para
la conversión de valor de dato a índice de color que ocurre después de aplicar
los niveles de corte y justo antes de realizar el mapeo de color final.  Se
refiere a cómo se distribuyen los valores entre los niveles de corte bajo y alto
a la fase de mapeo de color e intensidad.

El control «Algorithm» se usa para establecer el algoritmo usado para el mapeo.
Haga clic en el control para mostrar la lista, o simplemente desplace la rueda
del ratón mientras pasa el cursor sobre el control.  Hay ocho algoritmos
disponibles: linear, log, power, sqrt, squared, asinh, sinh y histeq.  El nombre
de cada algoritmo es indicativo de cómo se mapean los datos a los colores del
mapa de color.  «linear» es el predeterminado.

**Preferencias de mapeo de color**

.. figure:: figures/cmap-prefs.png
   :width: 400px
   :align: center
   :alt: Preferencias de mapeo de color

   Preferencias de «Color Mapping».

Las preferencias de «Color Mapping» controlan las preferencias usadas para el
mapa de color y el mapa de intensidad, usados durante la fase final del proceso
de mapeo de color.  Junto con las preferencias de «Color Distribution», estas
controlan el mapeo de valores de dato a una representación visual RGB de 24 bpp.

El control «Colormap» selecciona qué mapa de color debe cargarse y usarse.  Haga
clic en el control para mostrar la lista, o simplemente desplace la rueda del
ratón mientras pasa el cursor sobre el control.

.. note:: Ginga viene con una buena selección de mapas de color, pero si desea
          más, puede añadir personalizados o, si ``matplotlib`` está instalado,
          puede cargar todos los que este tenga.  Consulte «Customizing Ginga»
          para más detalles.

El control «Intensity» selecciona qué mapa de intensidad debe usarse con el mapa
de color.  El mapa de intensidad se aplica justo antes del mapa de color, y
puede usarse para cambiar la escala lineal estándar de valores a una escala
invertida, logarítmica, etc.

La casilla «Invert CMap» se puede usar para invertir el mapa de color
seleccionado (note que varios mapas de color también son seleccionables desde el
control «Colormap» en forma invertida).

El control «Rotate» se puede usar para rotar el mapa de color, mientras que el
botón «Unrotate CMap» restaurará la rotación a su estado predeterminado, sin
rotar.

El botón «Color Defaults» restablecerá todos los controles de mapeo de color a
los valores predeterminados: mapa de color «gray», intensidad «ramp» (lineal), y
sin inversión ni rotación del mapa de color.

**Preferencias de contraste y brillo (bias)**

.. figure:: figures/contrast-prefs.png
   :width: 400px
   :align: center
   :alt: Preferencias de contraste y brillo (bias)

   Preferencias de «Contrast and Brightness (Bias)».

Los controles «Contrast» y «Brightness» establecerán el contraste y el brillo
(alias «bias») del visor.  Ofrecen una alternativa a 1) usar el modo de
contraste dentro de la ventana del visor, o 2) manipular la barra de color
arrastrando (para establecer brillo/bias) o desplazando (para establecer
contraste).

Los controles «Default Contrast» y «Default Brightness» restablecen sus
respectivos ajustes al valor predeterminado.

**Preferencias de cortes automáticos**

.. figure:: figures/autocuts-prefs.png
   :width: 400px
   :align: center
   :alt: Preferencias de cortes automáticos

   Preferencias de «Auto Cuts».

Las preferencias de «Auto Cuts» controlan el cálculo de los niveles de corte para
la vista cuando se pulsa el botón o la tecla de niveles de corte automáticos, o
al cargar una nueva imagen con los cortes automáticos habilitados.  También puede
establecer los niveles de corte manualmente desde aquí.

Los campos «Cut Low» y «Cut High» se pueden usar para especificar manualmente los
niveles de corte inferior y superior.  Al pulsar «Cut Levels» se establecerán los
niveles a estos valores manualmente.  Si falta un valor, se asume que toma por
defecto el valor actual.

Al pulsar «Auto Levels» se calcularán los niveles según un algoritmo.  El control
«Auto Method» se usa para elegir qué algoritmo de cortes automáticos se usa:
«minmax» (valores mínimo máximo), «median» (basado en filtrado por mediana),
«histogram» (basado en un histograma de la imagen), «stddev» (basado en la
desviación estándar de los valores de píxel) o «zscale» (basado en el algoritmo
ZSCALE popularizado por IRAF).  A medida que se cambia el algoritmo, los cuadros
debajo de él también pueden cambiar para permitir cambios en parámetros
específicos de cada algoritmo.

**Preferencias de transformación**

.. figure:: figures/transform-prefs.png
   :width: 400px
   :align: center
   :alt: Preferencias de transformación

   Preferencias de «Transform».

Las preferencias de «Transform» permiten transformar la vista de la imagen
volteando la vista en X o Y, intercambiando los ejes X e Y, o rotando la imagen
en cantidades arbitrarias.

Las casillas «Flip X» y «Flip Y» hacen que la vista de la imagen se voltee en el
eje correspondiente.

La casilla «Swap XY» hace que la vista de la imagen se altere intercambiando los
ejes X e Y.  Esto se puede combinar con «Flip X» y «Flip Y» para rotar la imagen
en incrementos de 90 grados.  Estas vistas se renderizarán más rápidamente que
las rotaciones arbitrarias usando el control «Rotate».

El control «Rotate» rotará la vista de la imagen la cantidad especificada.  El
valor debe especificarse en grados.  «Rotate» se puede especificar junto con el
volteo y el intercambio.

El botón «Restore» restaurará la vista a la vista predeterminada, que es sin
voltear, sin intercambiar y sin rotar.

**Preferencias de WCS**

.. figure:: figures/wcs-prefs.png
   :width: 400px
   :align: center
   :alt: Preferencias de WCS

   Preferencias de «WCS».

Las preferencias de «WCS» controlan las preferencias de visualización de los
cálculos del Sistema de Coordenadas Mundial (WCS) usados para informar de la
posición del cursor en la imagen.

El control «WCS Coords» se usa para seleccionar el sistema de coordenadas en el
que mostrar el resultado.

El control «WCS Display» se usa para seleccionar una lectura sexagesimal
(``H:M:S``) o una lectura en grados decimales.

**Preferencias de zoom**

.. figure:: figures/zoom-prefs.png
   :width: 400px
   :align: center
   :alt: Preferencias de zoom

   Preferencias de «Zoom».

Las preferencias de «Zoom» controlan el comportamiento de zoom/escalado de Ginga.
Ginga admite dos algoritmos de zoom, elegidos usando el control «Zoom Alg»:

* El algoritmo «step» hace zoom en la imagen hacia dentro en pasos discretos de
  1X, 2X, 3X, etc. o hacia fuera en pasos de 1/2X, 1/3X, 1/4X, etc.  Este
  algoritmo produce visualmente la menor cantidad de artefactos, pero es un poco
  más lento para hacer zoom en rangos amplios cuando se usa un movimiento de
  desplazamiento, porque se requiere más «recorrido» para lograr un gran cambio
  de zoom (este no es el caso si se usan las teclas de acceso rápido de zoom,
  como las teclas de dígitos).

* El algoritmo «rate» hace zoom en la imagen avanzando el escalado a una tasa
  definida por el valor del cuadro «Zoom Rate».  Esta tasa es por defecto la raíz
  cuadrada de 2.  Números más grandes causan cambios más grandes en la escala
  entre niveles de zoom.  Si le gusta hacer zoom en sus imágenes rápidamente, a
  un pequeño costo en calidad de imagen, probablemente querría elegir esta
  opción.

Note que independientemente de qué método se elija para el algoritmo de zoom, el
zoom se puede controlar manteniendo pulsada ``Ctrl`` (grueso) o ``Shift`` (fino)
mientras se desplaza para restringir la tasa de zoom (asumiendo las asignaciones
de ratón predeterminadas).

El control «Stretch XY» se puede usar para estirar uno de los ejes (X o Y) en
relación con el otro.  Seleccione un eje con este control y ruede la rueda de
desplazamiento mientras pasa el cursor sobre el control «Stretch Factor» para
estirar los píxeles en el eje seleccionado.

Los controles «Scale X» y «Scale Y» ofrecen acceso directo al escalado
subyacente, evitando los pasos de zoom discretos.  Aquí, se pueden escribir
valores exactos para escalar la imagen.  A la inversa, verá estos valores cambiar
a medida que se hace zoom en la imagen.

Los controles «Scale Min» y «Scale Max» se pueden usar para poner un límite a
cuánto se puede escalar la imagen.

El control «Interpolation» le permite elegir cómo se interpolará la imagen.
Dependiendo de qué paquetes de soporte estén instalados, se pueden hacer las
siguientes elecciones:

* «basic» es vecino más cercano usando un algoritmo incorporado, este siempre
  está disponible, es razonablemente rápido y es el predeterminado.
* «area»
* «bicubic»
* «lanczos»
* «linear»
* «nearest» es vecino más cercano (usando un paquete de soporte)

El botón «Zoom Defaults» restaurará los controles a los valores predeterminados
de Ginga.

**Preferencias de desplazamiento (pan)**

.. figure:: figures/pan-prefs.png
   :width: 400px
   :align: center
   :alt: Preferencias de desplazamiento

   Preferencias de «Pan».

Las preferencias de «Pan» controlan el comportamiento de desplazamiento de Ginga.

Los controles «Pan X» y «Pan Y» ofrecen acceso directo para establecer la
posición de desplazamiento en la imagen (la parte de la imagen ubicada en el
centro de la ventana) -- puede verlos cambiar mientras se desplaza por la imagen.
Puede establecer estos valores y luego pulsar «Apply Pan» para desplazarse a esa
posición exacta.

Si el control «Pan Coord» está establecido en «data», entonces el desplazamiento
se controla por coordenadas de dato en la imagen; si se establece en «WCS»,
entonces los valores mostrados en los controles «Pan X» y «Pan Y» serán
coordenadas WCS (asumiendo un WCS válido en la imagen).  En el último caso, el
control «WCS sexagesimal» se puede dejar sin marcar para mostrar/establecer las
coordenadas en grados, o marcar para mostrar/establecer los valores en notación
sexagesimal estándar.

El botón «Center Image» establece la posición de desplazamiento en el centro de
la imagen, calculado dividiendo por la mitad las dimensiones en X e Y.

La casilla «Mark Center», cuando está marcada, hará que Ginga dibuje una pequeña
retícula en el centro de la imagen.  Esto es útil para conocer la posición de
desplazamiento y para depuración.

**Preferencias generales**

.. figure:: figures/general-prefs.png
   :width: 400px
   :align: center
   :alt: Preferencias generales

   Preferencias «General».

El ajuste «Num Images» especifica cuántas imágenes se pueden retener en búferes
en este canal antes de ser expulsadas.  Un valor de cero (0) significa
ilimitado: las imágenes nunca serán expulsadas.  Si una imagen se cargó desde
algún almacenamiento accesible y es expulsada, se volverá a cargar
automáticamente si se vuelve a visitar la imagen navegando por el canal.

El ajuste «Sort Order» determina si las imágenes se ordenan en el canal
alfabéticamente por nombre o por la hora en que se cargaron.  Esto afecta
principalmente al orden en que se recorren las imágenes al usar las teclas o
botones de «flecha» arriba/abajo, y no necesariamente a cómo se muestran en
complementos como «Contents» o «Thumbs» (que generalmente tienen su propia
preferencia de ajuste para el orden).

La casilla «Use scrollbars» controla si el visor de canal mostrará barras de
desplazamiento alrededor del borde del marco del visor para desplazar la imagen.

**Preferencias de reinicio (visor)**

.. figure:: figures/reset-prefs.png
   :width: 400px
   :align: center
   :alt: Preferencias de reinicio (visor)

   Preferencias de «Reset» (visor).

Cada visor de canal tiene un *perfil de visor* que se inicializa al estado del
visor justo después de la creación y la restauración de los ajustes guardados
para ese canal.  Al cambiar entre imágenes, los atributos del visor se pueden
reiniciar a este perfil según las casillas marcadas en esta sección.  *Si no se
marca nada, no se reiniciará nada del perfil de visor*.

Para usar esta función, establezca sus preferencias de visor como prefiera y haga
clic en el botón «Update Viewer Profile» en la parte inferior del complemento.
Ahora marque qué elementos deben reiniciarse a esos valores entre imágenes.
Finalmente, haga clic en el botón «Save Settings» en la parte inferior si desea
que estos ajustes sean persistentes entre reinicios de Ginga y se establezcan
como el perfil de usuario predeterminado para este canal cuando reinicie ginga y
vuelva a crear este canal.

* «Reset Scale» reiniciará el nivel de zoom (escala) al perfil de visor
* «Reset Pan» reiniciará la posición de desplazamiento al perfil de visor
* «Reset Transform» reiniciará cualquier transformación de volteo/intercambio al
  perfil de visor
* «Reset Rotation» reiniciará cualquier rotación al perfil de visor
* «Reset Cuts» reiniciará cualquier nivel de corte al perfil de visor
* «Reset Distribution» reiniciará cualquier distribución de color al perfil de
  visor
* «Reset Contrast» reiniciará cualquier contraste/bias al perfil de visor
* «Reset Color Map» reiniciará cualquier ajuste de mapa de color al perfil de
  visor

.. tip:: Si usa esta función, quizás también quiera establecer «Remember (Image)
         Preferences» (véase más abajo).

.. note:: El orden completo de los ajustes es:

          * cualquier elemento de reinicio del perfil de visor predeterminado, si
            lo hay
          * cualquier elemento recordado del perfil de imagen se aplica, si lo
            hay
          * cualquier ajuste automático (cuts/zoom/center) se aplica, si no fue
            anulado por un ajuste recordado

**Preferencias de recordar (imagen)**

.. figure:: figures/remember-prefs.png
   :width: 400px
   :align: center
   :alt: Preferencias de recordar (imagen)

   Preferencias de «Remember» (imagen).

Cuando se carga una imagen, se crea un *perfil de imagen* y se adjunta a los
metadatos de la imagen en el canal.  Estos perfiles se actualizan continuamente
con el estado del visor a medida que se manipula la imagen.  Las preferencias de
«Remember» controlan qué atributos de estos perfiles se restauran al estado del
visor cuando se navega (de vuelta) a la imagen en el canal:

* «Remember Scale» restaurará el nivel de zoom (escala) de la imagen
* «Remember Pan» restaurará la posición de desplazamiento en la imagen
* «Remember Transform» restaurará cualquier transformación de volteo o
  intercambio de ejes
* «Remember Rotation» restaurará cualquier rotación de la imagen
* «Remember Cuts» restaurará cualquier nivel de corte de la imagen
* «Remember Distribution» restaurará cualquier distribución de color (linear,
  log, etc.)
* «Remember Contrast» restaurará cualquier ajuste de contraste/bias
* «Remember Color Map» restaurará cualquier elección de mapa de color realizada

*Si no se marca nada, no se restaurará nada del perfil de imagen*.

.. note:: Estos elementos se establecerán ANTES de que se realice cualquier
          ajuste automático (cut/zoom/center new).  Si se establece un elemento
          recordado, anulará cualquier ajuste automático para el canal.

.. tip:: Si usa esta función, quizás también quiera establecer «Reset (Viewer)
         Preferences» (véase más arriba).

***Un ejemplo***

Como ejemplo del uso de los ajustes de Reset y Remember, suponga que usa con
frecuencia el ajuste de contraste.  Le gustaría que el contraste que establece
con una imagen en particular se restaure cuando esa imagen se vea de nuevo.  Sin
embargo, cuando ve una imagen nueva, le gustaría que el contraste empiece en un
ajuste normal.

Para lograr esto, reinicie manualmente el contraste al ajuste predeterminado
deseado.  Marque «Reset Contrast» y luego pulse «Update Viewer Profile».
Finalmente, marque «Remember Contrast».  Haga clic en «Save Settings» para hacer
persistentes los ajustes del canal.

**Preferencias de nueva imagen**

.. figure:: figures/newimages-prefs.png
   :width: 400px
   :align: center
   :alt: Preferencias de nueva imagen

   Preferencias de «New Image».

Las preferencias de «New Images» determinan cómo reacciona Ginga cuando se carga
una nueva imagen en el canal.  *Esto incluye cuando se vuelve a visitar una
imagen más antigua haciendo clic en su miniatura en el complemento ``Thumbs`` o
haciendo doble clic en su nombre en el complemento ``Contents``*.

El ajuste «Cut New» controla si se debe realizar un cálculo automático de niveles
de corte en la nueva imagen, o si se deben aplicar los niveles de corte
actualmente establecidos.  Los ajustes posibles son:

* «off»: usar siempre los niveles de corte actualmente establecidos;
* «once»: calcular nuevos niveles de corte para la primera imagen visitada, luego
  cambiar a «off»;
* «override»: calcular nuevos niveles de corte hasta que el usuario los anule
  estableciendo manualmente unos niveles de corte, luego cambiar a «off»; o
* «on»: calcular siempre nuevos niveles de corte.

.. tip:: El ajuste «override» se proporciona para la conveniencia de tener
         niveles de corte automáticos, a la vez que se evita que unos cortes
         establecidos manualmente sean anulados cuando se ingiere una nueva
         imagen.  Cuando se teclea en la ventana de imagen, la tecla de punto y
         coma se puede usar para volver a alternar el modo a override (desde
         «off»), mientras que los dos puntos establecerán la preferencia en «on».
         El complemento ``Info`` (pestaña: Synopsis) muestra el estado de este
         ajuste.

El ajuste «Zoom New» controla si visitar una imagen debe establecer el nivel de
zoom para ajustar la imagen a la ventana.  Los ajustes posibles son:

* «off»: usar siempre los niveles de zoom actualmente establecidos;
* «once»: ajustar la primera imagen a la ventana, luego cambiar a «off»;
* «override»: las imágenes se ajustan automáticamente hasta que se cambia el
  nivel de zoom manualmente, luego el modo cambia automáticamente a «off»; o
* «on»: la nueva imagen siempre se hace zoom para ajustar.

.. tip:: El ajuste «override» se proporciona para la conveniencia de tener un
         zoom automático, a la vez que se evita que un nivel de zoom establecido
         manualmente sea anulado cuando se ingiere una nueva imagen.  Cuando se
         teclea en la ventana de imagen, la tecla de apóstrofo (también «comilla
         simple») se puede usar para volver a alternar el modo a «override»
         (desde «off»), mientras que la comilla (también «comilla doble»)
         establecerá la preferencia en «on».  El complemento ``Info`` (pestaña:
         Synopsis) muestra el estado de este ajuste.

El ajuste «Center New» controla si visitar una imagen debe hacer que la posición
de desplazamiento se reinicie al centro de la imagen.  Los ajustes posibles son:

* «off»: dejar la posición de desplazamiento actual tal como está;
* «once»: centrar la primera imagen visitada, luego cambiar a «off»;
* «override»: las imágenes se centran automáticamente hasta que se cambia la
  posición de desplazamiento manualmente, luego el modo cambia automáticamente a
  «off»; o
* «on»: la nueva imagen siempre se centra.

El ajuste «Follow New» se usa para controlar si Ginga cambiará la visualización si
se carga una nueva imagen en el canal.  Si no está marcado, la imagen se carga
(como se ve, por ejemplo, por su aparición en la pestaña ``Thumbs``), pero la
visualización no cambiará a la nueva imagen.  Este ajuste es útil en casos donde
se están cargando nuevas imágenes por algún medio automatizado en un canal y el
usuario desea estudiar la imagen actual sin ser interrumpido.

El ajuste «Raise New» controla si Ginga elevará la pestaña de un canal cuando se
carga una imagen en ese canal.  Si no está marcado, entonces Ginga no elevará la
pestaña cuando se cargue una imagen en ese canal en particular.

El ajuste «Create Thumbnail» controla si Ginga creará una miniatura para las
imágenes cargadas en ese canal.  En casos donde se están cargando muchas imágenes
en un canal con frecuencia (p. ej., una transmisión de vídeo de baja
frecuencia), puede ser indeseable crear miniaturas para todas ellas.

El ajuste «Auto Orient» controla si Ginga debe intentar orientar las imágenes de
forma predeterminada según los metadatos de la imagen.  Esto actualmente solo es
útil para imágenes RGB (p. ej., JPEG) que contienen tales metadatos.  Por el
momento, no orienta automáticamente por WCS.

**Preferencias de perfiles ICC**

.. figure:: figures/icc-prefs.png
   :width: 400px
   :align: center
   :alt: Preferencias de perfiles ICC

   Preferencias de «ICC Profiles».

Ginga puede hacer uso de perfiles ICC (gestión de color) en la cadena de
renderizado usando la biblioteca LittleCMS.

.. note:: Para hacer uso de perfiles ICC, cree una carpeta «profiles» en el
          «home» de Ginga (normalmente $HOME/.ginga) y ponga allí los perfiles
          necesarios.  Se debe establecer un perfil de trabajo añadiendo un valor
          para «icc_working_profile» en su archivo $HOME/.ginga/general.cfg -- no
          incluya ninguna ruta inicial, solo el nombre de archivo de un archivo
          ICC en la carpeta profiles.  Esto se usará para convertir cualquier
          archivo RGB que contenga un perfil al perfil de trabajo.

Puede establecer los perfiles de salida para cualquier canal en esta sección del
complemento Preferences.

El control «Output ICC profile» selecciona qué perfil usar para el renderizado de
salida a la pantalla.  Las opciones son de sus archivos de perfil en
$HOME/.ginga/profiles.  Normalmente esto debería ser un perfil de pantalla.

El control «Rendering intent» elige el algoritmo usado para renderizar el color
en el proceso de conversión ICC.  Las opciones son:

* absolute_colorimetric
* perceptual
* relative_colorimetric
* saturation

«Proof ICC profile» y «Proof intent» se eligen de forma similar para las pruebas.

La casilla «Black point compensation» activa o desactiva esta función en el
proceso de conversión de color.  Consulte la documentación de LittleCMS o de la
gestión de color ICC en general para más detalles sobre estas opciones.
