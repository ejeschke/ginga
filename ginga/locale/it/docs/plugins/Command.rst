Questo plugin fornisce un'interfaccia a riga di comando per il visualizzatore di
riferimento.

.. note:: La riga di comando è destinata all'uso *all'interno* dell'interfaccia
          del plugin.  Se cerchi un'interfaccia a riga di comando *remota*,
          vedi il plugin ``RC``.

**Tipo di plugin: Globale**

``Command`` è un plugin globale.  Può essere aperta una sola istanza.

**Uso**

Ottenere un elenco di comandi e parametri::

        g> help

Eseguire un comando della shell::

        g> !cmd arg arg ...

**Note**

Uno strumento particolarmente potente è l'uso dei comandi ``reload_local`` e
``reload_global`` per ricaricare un plugin mentre lo stai sviluppando.  Questo
evita di dover riavviare il visualizzatore di riferimento e ricaricare
faticosamente i dati, ecc.  Chiudi semplicemente il plugin, esegui il comando
« reload » appropriato (vedi l'aiuto!) e poi riavvia il plugin.

.. note:: Se hai modificato moduli *diversi* dal plugin stesso, questi non
          verranno ricaricati da questi comandi.
