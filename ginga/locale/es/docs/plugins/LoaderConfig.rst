El complemento ``LoaderConfig`` le permite configurar los abridores de archivos
que se pueden usar para cargar diversos contenidos en Ginga.

Los abridores de archivos registrados están asociados a tipos MIME de archivo, y
puede haber varios abridores para un único tipo MIME.  Una prioridad asociada a
un emparejamiento tipo MIME/abridor determina qué abridor se usará para cada
tipo: el valor de prioridad más bajo determinará qué abridor se usará.  Si hay
más de un abridor con la misma prioridad baja, se preguntará al usuario qué
abridor usar al abrir un archivo en Ginga.  Este complemento puede usarse para
establecer las preferencias de abridores y guardarlas en el área de
configuración $HOME/.ginga del usuario.

**Tipo de complemento: Global**

``LoaderConfig`` es un complemento global.  Solo se puede abrir una instancia.

**Uso**

Después de iniciar el complemento, la pantalla mostrará todos los tipos MIME
registrados y los abridores registrados para esos tipos, con una prioridad
asociada a cada emparejamiento tipo MIME/abridor.

Seleccione una o varias líneas y escriba una prioridad para ellas en la casilla
etiquetada «Prioridad:»; pulse «Establecer» (o INTRO) para establecer la
prioridad de esos elementos.

.. note:: Cuanto menor es el número, mayor es la prioridad.  Los números
          negativos son válidos y la prioridad predeterminada de un cargador
          suele ser 0.  Así, por ejemplo, si hay dos cargadores disponibles para
          un tipo MIME y una prioridad se establece en -1 y la otra en 0, se
          usará el de -1 sin pedir al usuario que elija.


Haga clic en «Guardar» para guardar las prioridades en
$HOME/.ginga/loaders.json, de modo que se vuelvan a cargar y se usen en los
posteriores reinicios del programa.
