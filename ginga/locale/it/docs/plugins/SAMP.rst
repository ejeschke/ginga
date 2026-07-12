Il plugin ``SAMP`` implementa un'interfaccia SAMP per il visualizzatore di
riferimento Ginga.

.. note:: Per eseguire questo plugin, è necessario installare ``astropy`` che
          abbia il modulo ``samp``.

**Tipo di plugin: Globale**

``SAMP`` è un plugin globale.  Può essere aperta una sola istanza.

**Uso**

Ginga include un plugin per abilitare il supporto a SAMP (Simple Applications
Messaging Protocol).  Con il supporto SAMP, Ginga può essere controllato e
interagire con altre applicazioni astronomiche desktop.

Il modulo ``SAMP`` non viene avviato per impostazione predefinita.  Per avviarlo
all'avvio di Ginga, specifica l'opzione della riga di comando::

        --modules=SAMP

Altrimenti, avvialo usando « Avvia un hub SAMP » dal menu « Plugin ».

Attualmente il supporto SAMP è limitato ai messaggi ``image.load.fits``, il che
significa che Ginga caricherà un file FITS se riceve uno di questi messaggi.

Il plugin ``SAMP`` di Ginga usa il modulo ``astropy.samp``, quindi dovrai avere
``astropy`` installato per usare il plugin.  Per impostazione predefinita, il
plugin ``SAMP`` di Ginga tenterà di avviare un hub SAMP se non ne trova uno in
esecuzione.
