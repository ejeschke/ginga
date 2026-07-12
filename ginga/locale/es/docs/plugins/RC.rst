
El complemento ``RC`` implementa una interfaz de control remoto para el visor
Ginga.

**Tipo de complemento: Global**

``RC`` es un complemento global.  Solo se puede abrir una instancia.

**Uso**

El complemento ``RC`` (Remote Control) proporciona una forma de controlar Ginga
de forma remota mediante el uso de una interfaz XML-RPC.  Inicie el complemento
desde el menú «Plugins» (invoque «Start RC») o lance ginga con la opción de
línea de comandos ``--modules=RC`` para iniciarlo automáticamente.

De forma predeterminada, el complemento arranca con el servidor ejecutándose en
el puerto 11771 vinculado a la interfaz localhost -- esto permite conexiones
solo desde el host local.  Si desea cambiar esto, establezca el host y el puerto
en el control «Set Addr» y pulse ``Enter`` -- debería ver cómo se actualiza la
dirección en el campo de visualización «Addr:».

Tenga en cuenta que la parte del host (antes de los dos puntos) no indica
*desde qué* host desea permitir el acceso, sino a qué interfaz vincularse.  Si
desea permitir que cualquier host se conecte, déjelo en blanco (pero incluya los
dos puntos y el número de puerto) para permitir que el servidor se vincule a
todas las interfaces.  Pulse «Restart» para reiniciar entonces el servidor en la
nueva dirección.

Una vez iniciado el complemento, puede usar el script ``ggrc`` (incluido cuando
se instala ``ginga``) para controlar Ginga.  Eche un vistazo al script si desea
ver cómo escribir su propia interfaz programática.

Mostrar ejemplo de uso::

        $ ggrc help

Mostrar ayuda para un método específico de Ginga::

        $ ggrc help ginga <method>

Mostrar ayuda para un método específico de canal::

        $ ggrc help channel <chname> <method>

Los métodos de Ginga (shell del visor) se pueden llamar así::

        $ ggrc ginga <method> <arg1> <arg2> ...

Los métodos por canal se pueden llamar así::

        $ ggrc channel <chname> <method> <arg1> <arg2> ...

Las llamadas se pueden hacer desde un host remoto añadiendo las opciones::

        --host=<hostname> --port=11771

(En la GUI del complemento, asegúrese de quitar el prefijo «localhost» de la
«addr», pero deje los dos puntos y el puerto.)

**Ejemplos**

Crear un nuevo canal::

        $ ggrc ginga add_channel FOO

Cargar un archivo::

        $ ggrc ginga load_file /home/eric/testdata/SPCAM/SUPA01118797.fits

Cargar un archivo en un canal específico::

        $ ggrc ginga load_file /home/eric/testdata/SPCAM/SUPA01118797.fits FOO

Niveles de corte::

        $ ggrc channel FOO cut_levels 163 1300

Niveles de corte automáticos::

        $ ggrc channel FOO auto_levels

Hacer zoom a un nivel específico::

        $ ggrc -- channel FOO zoom_to -7

(Note el uso de ``--`` para permitirnos pasar un parámetro que comienza con
``-``.)

Zoom para ajustar::

        $ ggrc channel FOO zoom_fit

Transformar (los argumentos son un triplete booleano: ``flipx`` ``flipy``
``swapxy``)::

        $ ggrc channel FOO transform 1 0 1

Rotar::

        $ ggrc channel FOO rotate 37.5

Cambiar el mapa de color::

        $ ggrc channel FOO set_color_map rainbow3

Cambiar el algoritmo de distribución de color::

        $ ggrc channel FOO set_color_algorithm log

Cambiar el mapa de intensidad::

        $ ggrc channel FOO set_intensity_map neg

En algunos casos, es posible que deba recurrir a escapes de shell para poder
pasar ciertos caracteres a Ginga.  Por ejemplo, un carácter de guion inicial
suele interpretarse como una opción del programa.  Para pasar un entero con
signo, es posible que deba hacer algo como::

        $ ggrc -- channel FOO zoom -7

**Interfaz desde dentro de Python**

También es posible controlar Ginga en modo RC desde dentro de Python.  A
continuación se describe parte de la funcionalidad.

*Conectar*

Primero, lance Ginga e inicie el complemento ``RC``.  Esto se puede hacer desde
la línea de comandos::

        ginga --modules=RC

Desde dentro de Python, conéctese con un objeto ``RemoteClient`` de la siguiente
manera::

        from ginga.util import grc
        host = 'localhost'
        port = grc.default_rc_port
        viewer = grc.RemoteClient(host, port)

Este objeto viewer ahora está vinculado a Ginga usando ``RC``.

*Cargar una imagen*

Puede cargar una imagen desde la memoria en un canal de su elección.  Primero,
conéctese a un canal::

        ch = viewer.channel('Image')

Luego, cargue una imagen Numpy (es decir, cualquier ``ndarray`` 2D)::

        import numpy as np
        img = np.random.rand(500, 500) * 10000.0
        ch.load_np('Image_Name', img, 'fits', {})

La imagen se mostrará en Ginga y podrá manipularse como de costumbre.

*Superponer un objeto de lienzo*

Es posible añadir objetos al lienzo en un canal dado.  Primero, conéctese::

        canvas = viewer.canvas('Image')

Esto conecta con el canal llamado «Image».  Puede borrar los objetos dibujados
en el lienzo::

        canvas.clear()

También puede añadir cualquier objeto de lienzo básico.  La cuestión clave a
tener en cuenta es que los objetos de entrada deben pasar por el protocolo
XMLRC.  Esto significa tipos de datos simples (``float``, ``int``, ``list`` o
``str``); nada de arrays.  Aquí hay un ejemplo para trazar una línea a través de
una serie de puntos definidos por dos arrays Numpy::

        x = np.arange(100)
        y = np.sqrt(x)
        points = list(zip(x.tolist(), y.tolist()))
        canvas.add('path', points, color='red')

Esto dibujará una línea roja en la imagen.
