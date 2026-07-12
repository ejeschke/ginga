``AutoLoad`` es un complemento sencillo para vigilar una carpeta en busca de
archivos nuevos y cargarlos automáticamente en un canal cuando aparecen.

**Tipo de complemento: Local**

``AutoLoad`` es un complemento local, lo que significa que está asociado a un
canal.  Se puede abrir una instancia para cada canal.

.. note:: Necesita instalar el paquete de Python «watchdog» para usar este
          complemento.

**Uso**

* Para configurar una carpeta a vigilar, escriba la ruta de una carpeta
  (directorio) en el campo «Carpeta vigilada» y pulse INTRO o haga clic en
  «Establecer».
* Si necesita distinguir entre los archivos que se añadirán a esta carpeta,
  puede escribir una expresión regular de Python en la casilla «Expresión
  regular» y hacer clic en «Establecer».  Solo se considerarán los archivos
  cuyos nombres coincidan con el patrón.  Tenga en cuenta que la expresión
  regular es solo para el nombre del archivo, no para ninguna parte de la ruta
  de la carpeta.
* Si en algún momento desea pausar la carga automática, puede marcar la casilla
  «Pausar la carga automática»; esto detendrá toda carga automática.  Tenga en
  cuenta que si posteriormente desmarca la casilla, los archivos que llegaron
  en el intervalo no se cargarán.

.. note:: La vigilancia de carpetas que residen en unidades de red puede
          funcionar o no.

**Configuración del usuario**
