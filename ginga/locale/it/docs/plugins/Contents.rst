
Il plugin ``Contents`` fornisce un'interfaccia simile a un indice per tutte le
immagini visualizzate da quando è stato avviato il programma.  A differenza di
``Thumbs``, ``Contents`` è ordinato per canale.  Il contenuto mostra anche alcuni
metadati configurabili dell'immagine.

**Tipo di plugin: Globale**

``Contents`` è un plugin globale.  Può essere aperta una sola istanza.

**Uso**

Fai clic su un'intestazione di colonna per ordinare la tabella secondo quella
colonna; fai clic di nuovo per ordinare nell'altro senso.

.. note:: Le colonne e i loro valori sono tratti dall'intestazione FITS, se
          applicabile.  Questo può essere personalizzato impostando il parametro
          « columns » nel file di impostazioni « plugin_Contents.cfg ».

L'immagine attiva nel canale attualmente a fuoco è normalmente evidenziata.  Un
doppio clic su un'immagine forzerà la visualizzazione di quell'immagine nel
canale associato.  Un singolo clic su qualsiasi immagine attiva i pulsanti nella
parte inferiore dell'interfaccia:

* « Mostra »: Rende l'immagine l'immagine attiva.
* « Sposta »: Sposta l'immagine in un altro canale.
* « Copia »: Copia l'immagine in un altro canale.
* « Rimuovi »: Rimuove l'immagine dal canale.

Se « Sposta » o « Copia » viene eseguito su un'immagine che è stata modificata
in Ginga (che avrebbe una voce sotto ``ChangeHistory``, se usato), verrà
conservata anche la cronologia delle modifiche.  Rimuovere un'immagine da un
canale distrugge qualsiasi modifica non salvata.

Questo plugin di solito non è configurato per essere chiudibile, ma l'utente può
renderlo tale impostando l'impostazione « closeable » su True nel file di
configurazione -- allora i pulsanti Chiudi e Aiuto verranno aggiunti nella parte
inferiore dell'interfaccia.

**Escludere immagini da Contents**

.. note:: Questo controlla anche il comportamento di ``Thumbs``.

Sebbene il comportamento predefinito sia che ogni immagine caricata nel
visualizzatore di riferimento compaia in ``Contents``, ci possono essere casi in
cui questo è indesiderato (ad es. quando molte immagini vengono caricate a
cadenza periodica da qualche processo automatizzato).  In tali casi ci sono due
meccanismi per impedire che certe immagini compaiano in ``Contents``:

* Assegnare l'impostazione « genthumb » a False nelle impostazioni di un canale
  (ad esempio dal plugin ``Preferences``, sotto le impostazioni « General »)
  escluderà il canale stesso e tutte le sue immagini.
* Impostare la parola chiave « nothumb » nei metadati di un wrapper di immagine
  (non nell'intestazione FITS, ma ad es. tramite ``image.set(nothumb=True)``)
  escluderà quella particolare immagine da ``Contents``, anche se l'impostazione
  « genthumb » è True per quel canale.

È personalizzabile usando ``~/.ginga/plugin_Contents.cfg``, dove ``~`` è la tua
directory HOME:

.. code-block:: Python

  #
  # Contents plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_Contents.cfg"

  # columns to show from metadata -- NAME and MODIFIED recommended
  # format: [(col header, keyword1), ... ]
  columns = [ ('Name', 'NAME'), ('Object', 'OBJECT'), ('Filter', 'FILTER01'), ('Date', 'DATE-OBS'), ('Time UT', 'UT'), ('Modified', 'MODIFIED')]

  # If set to True, will always expand the tree in Contents when new entries are added
  always_expand = True

  # Option to highlight images that are displayed in channels.
  # If set to True this option will only highlight the image that is in the
  # channel with the keyboard focus
  highlight_tracks_keyboard_focus = False

  # If True, color every other row in alternating shades to improve
  # readability of long tables
  color_alternate_rows = True

  # Highlighted row colors (in addition to bold text)
  row_font_color = 'green'

  # Maximum number of rows that will turn off auto column resizing (for speed)
  max_rows_for_col_resize = 100

  # Add a close button to this plugin, so that it can be stopped
  closeable = False
