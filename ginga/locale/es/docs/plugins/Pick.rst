Realizar un análisis estelar astronómico rápido.

**Tipo de complemento: Local**

``Pick`` es un complemento local, lo que significa que está asociado a un canal.
No es un singleton, lo que significa que se pueden abrir varias instancias para
cada canal.

**Uso**

El complemento ``Pick`` se usa para realizar un análisis rápido de la calidad de
los datos astronómicos de objetos estelares.  Localiza candidatos estelares
dentro de una caja dibujada y elige el candidato más probable basándose en un
conjunto de ajustes de búsqueda.  Se informa de la anchura a media altura (FWHM)
del objeto candidato, así como de su tamaño basándose en la escala de placa del
detector.  También se realiza una medición aproximada del fondo, el nivel de
cielo y el brillo.

**Definir el área de selección**

El área de selección predeterminada se define como una caja de aproximadamente
30x30 píxeles que encierra el área de búsqueda.

El selector mover/dibujar/editar en la parte inferior del complemento se usa
para determinar qué operación se está realizando sobre el área de selección:

.. figure:: figures/pick-move-draw-edit.png
   :width: 400px
   :align: center
   :alt: Botones Mover, Dibujar y Editar

   Botones «Mover», «Dibujar» y «Editar».

* Si se selecciona «mover», puede mover el área de selección existente
  arrastrándola o haciendo clic donde desee colocar su centro.  Si no hay un
  área existente, se creará una predeterminada.
* Si se selecciona «dibujar», puede dibujar una forma con el cursor para
  encerrar y definir una nueva área de selección.  La forma predeterminada es
  una caja, pero se pueden seleccionar otras formas en la pestaña «Settings».
* Si se selecciona «editar», puede editar el área de selección arrastrando sus
  puntos de control, o moverla arrastrando en el cuadro delimitador.

Después de mover, dibujar o editar el área, ``Pick`` buscará en el área todos los
picos y evaluará los picos basándose en los criterios de la pestaña «Settings»
de la interfaz (véase «La pestaña Settings» más abajo) e intentará localizar el
mejor candidato que coincida con los ajustes.

.. note:: Las casillas «Quick Mode» y «From Peak» se eliminaron en la versión
          v4.0 de Ginga.

**Si se encuentra un candidato**

El candidato se marcará con un punto (normalmente una «X») en el lienzo del visor
de canal, centrado en el objeto según lo determinado por las mediciones FWHM
horizontal y vertical.

El conjunto superior de pestañas de la interfaz se rellenará de la siguiente
manera:

.. figure:: figures/pick-cutout.png
   :width: 400px
   :align: center
   :alt: Pestaña Image del área de Pick

   Pestaña «Image» del área de ``Pick``.

La pestaña «Image» mostrará el contenido del área de recorte.  El widget de esta
pestaña es un widget de Ginga y por tanto se puede hacer zoom y desplazar con las
asignaciones habituales de teclado y ratón (p. ej., rueda de desplazamiento).
También se marcará con un punto centrado en el objeto y, además, la posición de
desplazamiento se establecerá en el centro encontrado.

.. figure:: figures/pick-contour.png
   :width: 300px
   :align: center
   :alt: Pestaña Contour del área de Pick

   Pestaña «Contour» del área de ``Pick``.

La pestaña «Contour» mostrará un gráfico de contorno.  Este es un gráfico de
contorno del área inmediatamente circundante al candidato, y normalmente no
abarca toda la región del área de selección.  Puede usar la rueda de
desplazamiento para hacer zoom en el gráfico y un clic de la rueda de
desplazamiento (botón 2 del ratón) para establecer la posición de desplazamiento
en el gráfico.

.. figure:: figures/pick-fwhm.png
   :width: 400px
   :align: center
   :alt: Pestaña FWHM del área de Pick

   Pestaña «FWHM» del área de ``Pick``.

La pestaña «FWHM» mostrará un gráfico FWHM.  Las líneas moradas muestran
mediciones en la dirección X y las líneas verdes muestran mediciones en la
dirección Y.  Las líneas continuas indican valores de píxel reales y las líneas
punteadas indican la función 1D ajustada.  Las regiones sombreadas moradas y
verdes indican las mediciones FWHM para los respectivos ejes.

.. figure:: figures/pick-radial.png
   :width: 400px
   :align: center
   :alt: Pestaña Radial del área de Pick

   Pestaña «Radial» del área de ``Pick``.

La pestaña «Radial» contiene un gráfico de perfil radial.  Los puntos trazados en
morado son valores de datos, y se ajusta una línea a los datos.

.. figure:: figures/pick-ee.png
   :width: 600px
   :align: center
   :alt: Pestaña EE del área de Pick

   Pestaña «EE» del área de ``Pick``.

La pestaña «EE» contiene un gráfico de las energías fraccionales encerradas en
círculo y en cuadrado (EE) en morado y verde, respectivamente, para el objetivo
elegido.  Se realiza una resta de fondo simple de manera coherente con los
cálculos FWHM antes de medir los valores EE.  Los radios de muestreo y total,
mostrados como líneas negras discontinuas, se pueden establecer en la pestaña
«Settings»; cuando se cambian, haga clic en «Redo Pick» para actualizar el
gráfico y las mediciones.  Los valores EE medidos al radio de muestreo dado
también se muestran en la pestaña «Readout».  Cuando se solicita el informe, los
valores EE al radio de muestreo dado y el propio radio se registrarán en la tabla
«Report», junto con otra información.

Cuando «Show Candidates» está activo, los candidatos cerca de los bordes del
cuadro delimitador no tendrán valores EE (establecidos en 0).

.. figure:: figures/pick-readout.png
   :width: 400px
   :align: center
   :alt: Pestaña Readout del área de Pick

   Pestaña «Readout» del área de ``Pick``.

La pestaña «Readout» se rellenará con un resumen de las mediciones.  Hay dos
botones y tres casillas en esta pestaña:

* El botón «Default Region» restaura la región de selección a la forma y el
  tamaño predeterminados.
* El botón «Pan to pick» desplazará el visor de canal al centro localizado.
* Si «Center on pick» está marcado, la forma se recentrará en el centro
  localizado, si se encuentra (es decir, la forma «sigue» la selección).

.. figure:: figures/pick-controls.png
   :width: 400px
   :align: center
   :alt: Pestaña Controls del área de Pick

   Pestaña «Controls» del área de ``Pick``.

La pestaña «Controls» tiene un par de botones que funcionarán a partir de las
mediciones.

* El botón «Bg cut» establecerá el nivel de corte bajo del visor de canal en el
  nivel de fondo medido.  Se puede aplicar un delta a este valor estableciendo un
  valor en el cuadro «Delta bg» (pulse «Enter» para cambiar el ajuste).
* El botón «Sky cut» establecerá el nivel de corte bajo del visor de canal en el
  nivel de cielo medido.  Se puede aplicar un delta a este valor estableciendo un
  valor en el cuadro «Delta sky» (pulse «Enter» para cambiar el ajuste).
* El botón «Bright cut» establecerá el nivel de corte alto del visor de canal en
  los niveles medidos de cielo+brillo.  Se puede aplicar un delta a este valor
  estableciendo un valor en el cuadro «Delta bright» (pulse «Enter» para cambiar
  el ajuste).

.. figure:: figures/pick-report.png
   :width: 400px
   :align: center
   :alt: Pestaña Report del área de Pick

   Pestaña «Report» del área de ``Pick``.

La pestaña «Report» se usa para registrar información sobre las mediciones en
forma tabular.

Al pulsar el botón «Add Pick», la información sobre el candidato más reciente se
añade a la tabla.  Si la casilla «Record Picks automatically» está marcada,
entonces cualquier candidato se añade a la tabla automáticamente.

.. note:: Si la casilla «Show Candidates» de la pestaña «Settings» está marcada,
          entonces se añadirán a la tabla *todos* los objetos encontrados en la
          región (según los ajustes) en lugar de solo el candidato seleccionado.

Puede borrar la tabla en cualquier momento pulsando el botón «Clear Log».  El
registro se puede guardar en una tabla poniendo una ruta y un nombre de archivo
válidos en el cuadro «File:» y pulsando «Save table».  El tipo de archivo se
determina automáticamente por la extensión dada (p. ej., «.fits» es FITS y «.txt»
es texto plano).

**Si no se encuentra ningún candidato**

Si no se puede encontrar ningún candidato (basándose en los ajustes), el área de
selección se marca con un punto rojo centrado en el área de selección.

.. figure:: figures/pick-no-candidate.png
   :width: 800px
   :align: center
   :alt: Marcador cuando no se encuentra ningún candidato

   Marcador cuando no se encuentra ningún candidato.

El recorte de imagen se tomará de esta área central y por tanto la pestaña
«Image» seguirá teniendo contenido.  También se marcará con una «X» roja central.

El gráfico de contorno seguirá produciéndose a partir del recorte.

.. figure:: figures/pick-contour-no-candidate.png
   :width: 400px
   :align: center
   :alt: Contorno cuando no se encuentra ningún candidato.

   Contorno cuando no se encuentra ningún candidato.

Todos los demás gráficos se borrarán.

**La pestaña Settings**

.. figure:: figures/pick-settings.png
   :width: 400px
   :align: center
   :alt: Pestaña Settings del complemento Pick

   Pestaña «Settings» del complemento ``Pick``.

La pestaña «Settings» controla aspectos de la búsqueda dentro del área de
selección:

* La casilla «Show Candidates» controla si se marcan o no todas las fuentes
  detectadas (como se muestra en la figura de abajo).  Además, si está marcada,
  todos los objetos encontrados se añaden a la tabla de registro de selección al
  usar los controles «Report».
* El parámetro «Draw type» se usa para elegir la forma del área de selección que
  se va a dibujar.
* El parámetro «Radius» establece el radio que se usará al encontrar y evaluar
  picos brillantes en la imagen.
* El parámetro «Threshold» se usa para establecer un umbral para la búsqueda de
  picos; si se establece en «None», se elegirá un valor predeterminado
  razonable.
* Los parámetros «Min FWHM» y «Max FWHM» se pueden usar para eliminar objetos de
  cierto tamaño de ser candidatos.
* El parámetro «Ellipticity» se usa para eliminar candidatos basándose en su
  asimetría de forma.
* El parámetro «Edge» se usa para eliminar candidatos basándose en lo cerca que
  están del borde del recorte.  *NOTA: actualmente esto funciona de forma fiable
  solo para formas rectangulares no rotadas.*
* El parámetro «Max side» se usa para limitar el tamaño del cuadro delimitador
  que se puede usar en la forma de selección.  Los tamaños más grandes tardan más
  en evaluarse.
* El parámetro «Coordinate Base» es un desplazamiento que se aplica a las fuentes
  localizadas.  Establézcalo en «1» si desea que las ubicaciones de píxel de las
  fuentes se informen de manera compatible con FITS y «0» si prefiere la
  indexación basada en 0.
* El parámetro «Calc center» se usa para determinar si el centro se calcula a
  partir del ajuste FWHM («fwhm») o del centroide («centroid»).
* El parámetro «FWHM fitting» se usa para determinar qué función se usa para el
  ajuste FWHM («gaussian» o «moffat»).  La opción de usar «lorentz» también está
  disponible si «calc_fwhm_lib» se establece en «astropy» en
  ``~/.ginga/plugin_Pick.cfg``.
* El parámetro «Contour Interpolation» se usa para establecer el método de
  interpolación usado al renderizar la imagen de fondo en el gráfico «Contour».
* El «EE total radius» define el radio (para la energía encerrada en círculo) y
  la semianchura de la caja (para la energía encerrada en cuadrado) en píxeles
  donde se espera que la fracción EE sea 1 (es decir, todo el flujo de una
  función de dispersión de punto está contenido dentro).
* El «EE sampling radius» es el radio en píxeles usado para muestrear las curvas
  EE medidas para el informe.

El botón «Redo Pick» rehará la operación de búsqueda.  Es conveniente si ha
cambiado algunos parámetros y quiere ver el efecto basándose en el área de
selección actual sin perturbarla.

.. figure:: figures/pick-candidates.png
   :width: 600px
   :align: center
   :alt: El visor de canal cuando «Show Candidates» está marcado.

   El visor de canal cuando «Show Candidates» está marcado.

**Configuración del usuario**

Es personalizable usando ``~/.ginga/plugin_Pick.cfg``, donde ``~`` es su
directorio HOME:

.. code-block:: Python

  #
  # Pick plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_Pick.cfg"

  color_pick = 'green'
  shape_pick = 'box'
  color_candidate = 'purple'

  # Offset to add to Pick results. Default is 1.0 for FITS like indexing,
  # set to 0.0 here if you prefer numpy-like 0-based indexing
  pixel_coords_offset = 0.0

  # Maximum side for a pick region
  max_side = 1024

  # For image cutout viewer ("Image" tab)
  # you can set autozoom and autocuts preferences
  cutout_autozoom = 'override'
  cutout_autocuts = 'off'

  # For contour plot ("Contour" tab)
  # widget type: let choose automatically or force 'ginga' or 'matplotlib'
  # (choice of 'ginga' requires scikit-image to be installed)
  contour_widget = 'choose'
  # if ginga widget is chosen, you can set autozoom and autocuts preferences
  contour_autozoom = 'override'
  contour_autocuts = 'override'
  num_contours = 8
  # How big of a radius are we willing to consider from the center of the
  # pick?  bigger numbers == slower
  contour_size_min = 10
  contour_size_limit = 70

  # should the pick shape recenter on the found object center, if any?
  # useful for "tracking" an object that is moving from image to image
  center_on_pick = False

  # Star candidate search parameters
  radius = 10
  # Set threshold to None to auto calculate it
  threshold = None
  # Minimum and maximum fwhm to be considered a candidate
  min_fwhm = 1.5
  max_fwhm = 50.0
  # Minimum ellipticity to be considered a candidate
  min_ellipse = 0.5
  # Percentage from edge to be considered a candidate
  edge_width = 0.01
  # Graphically indicate all possible considered candidates
  show_candidates = False

  # Center of object is based on FWHM ("fwhm") or centroid ("centroid")
  # calculation:
  calc_center_alg = 'centroid'

  # Library to use for FWHM fitting ("native" or "astropy")
  calc_fwhm_lib = 'native'

  # Fitting function to use for FWHM ("gaussian" or "moffat")
  calc_fwhm_alg = 'gaussian'

  # Defaults for delta cut levels (in Controls tab)
  delta_sky = 0.0
  delta_bright = 0.0

  # Encircled and ensquared energy (EE) calculations:
  # a. Radius (pixel) where EE fraction is expected to be 1.
  ee_total_radius = 10.0
  # b. Radius (pixel) to sample EE for reporting.
  ee_sampling_radius = 2.5

  # use a different color/intensity map than channel image?
  pick_cmap_name = None
  pick_imap_name = None

  # For Reports tab
  record_picks = True

  # Set this to a file name, if None a filename will be automatically chosen
  report_log_path = None
