El complemento ``SAMP`` implementa una interfaz SAMP para el visor de referencia
Ginga.

.. note:: Para ejecutar este complemento, necesita instalar ``astropy`` que
          tenga el módulo ``samp``.

**Tipo de complemento: Global**

``SAMP`` es un complemento global.  Solo se puede abrir una instancia.

**Uso**

Ginga incluye un complemento para habilitar la compatibilidad con SAMP (Simple
Applications Messaging Protocol).  Con compatibilidad SAMP, Ginga puede
controlarse e interoperar con otras aplicaciones astronómicas de escritorio.

El módulo ``SAMP`` no se inicia de forma predeterminada.  Para iniciarlo cuando
Ginga arranca, especifique la opción de línea de comandos::

        --modules=SAMP

De lo contrario, iníciela usando «Iniciar un concentrador SAMP» desde el menú
«Complementos».

Actualmente, la compatibilidad con SAMP se limita a los mensajes
``image.load.fits``, lo que significa que Ginga cargará un archivo FITS si
recibe uno de estos mensajes.

El complemento ``SAMP`` de Ginga usa el módulo ``astropy.samp``, por lo que
necesitará tener ``astropy`` instalado para usar el complemento.  De forma
predeterminada, el complemento ``SAMP`` de Ginga intentará iniciar un
concentrador SAMP si no encuentra uno en ejecución.
