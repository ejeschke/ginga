Il plugin ``Zoom`` mostra un'immagine ingrandita di una regione ritagliata
centrata sotto la posizione del cursore nell'immagine del canale associato.  Man
mano che il cursore viene spostato sull'immagine, l'immagine di zoom si aggiorna
per consentire un'ispezione ravvicinata dei pixel o un controllo preciso in
combinazione con altre operazioni dei plugin.

**Tipo di plugin: Globale**

``Zoom`` è un plugin globale.  Può essere aperta una sola istanza.

**Uso**

L'ingrandimento della finestra di zoom può essere cambiato regolando il cursore
« Quantità di zoom ».

Sono possibili due modalità di funzionamento -- zoom assoluto e relativo:

* In modalità assoluta, la quantità di zoom controlla esattamente il livello di
  zoom mostrato nel ritaglio; ad esempio, l'immagine del canale può essere
  ingrandita a 10X, ma l'immagine di zoom mostrerà solo un'immagine 3X se la
  quantità di zoom è impostata a 3X.

* In modalità relativa, l'impostazione della quantità di zoom è interpretata
  come relativa all'impostazione di zoom dell'immagine del canale.  Se la
  quantità di zoom è impostata a 3X e l'immagine del canale è ingrandita a 10X,
  l'immagine di zoom mostrata sarà 13X (10X + 3X).  Nota che l'impostazione
  della quantità di zoom può essere < 1, quindi un'impostazione di 1/3X con uno
  zoom 3X nell'immagine del canale produrrà un'immagine di zoom 1X.

L'impostazione « Intervallo di aggiornamento » controlla la rapidità con cui il
plugin ``Zoom`` risponde al movimento del cursore aggiornando l'immagine di
zoom.  Il valore è specificato in millisecondi.

.. tip:: Di solito, impostare un piccolo intervallo di aggiornamento *migliora*
         la reattività complessiva dell'immagine di zoom, e il valore
         predefinito di 20 è ragionevole.  Puoi sperimentare con il valore se
         l'immagine di zoom sembra troppo a scatti o non sincronizzata con il
         movimento del mouse nella finestra dell'immagine del canale.

Il pulsante « Predefiniti » ripristina le impostazioni predefinite dei
controlli.

È personalizzabile usando ``~/.ginga/plugin_Zoom.cfg``, dove ``~`` è la tua
directory HOME:

.. code-block:: Python

  #
  # Zoom plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_Zoom.cfg"

  # default zoom level
  zoom_amount = 3

  # refresh interval (sec)
  # NOTE: usually a small delay speeds things up
  refresh_interval = 0.02
