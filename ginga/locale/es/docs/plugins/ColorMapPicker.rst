El complemento ``ColorMapPicker`` se usa para explorar y seleccionar
gráficamente un mapa de colores para un visor de imágenes de canal.

**Tipo de complemento: Global o Local**

``ColorMapPicker`` es un complemento híbrido global/local, lo que significa que
puede invocarse de cualquiera de las dos formas.  Si se invoca como complemento
local, está asociado a un canal y se puede abrir una instancia para cada canal.
También puede abrirse como complemento global.

**Uso**

El funcionamiento del complemento es muy sencillo: los mapas de colores se
muestran en forma de barras de color y etiquetas en el panel de vista principal
del complemento.  Haga clic en cualquiera de las barras para establecer el mapa
de colores del canal asociado (si se invoca como complemento local) o del canal
actualmente activo (si se invoca como complemento global).

Puede desplazarse verticalmente o usar las barras de desplazamiento para
recorrer las muestras de barras de color.

.. note:: Cuando el complemento se inicia por primera vez, generará una imagen
          RGB de mapa de bits con barras de color y etiquetas correspondientes
          a todos los mapas de colores disponibles.  Esto puede tardar unos
          segundos según el número de mapas de colores instalados.

          Los mapas de colores se muestran con el mapa de intensidad «ramp»
          aplicado.
