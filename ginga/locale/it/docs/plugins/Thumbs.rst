
Il plugin ``Thumbs`` fornisce un indice di miniature di tutte le immagini
visualizzate da quando è stato avviato il programma.

**Tipo di plugin: Globale**

``Thumbs`` è un plugin globale.  Può essere aperta una sola istanza.

**Uso**

Per impostazione predefinita, le ``Thumbs`` compaiono nella cronologia di
visualizzazione cronologica, con le immagini più recenti in basso e le più
vecchie in alto.  L'ordinamento può essere reso alfanumerico tramite
un'impostazione nel file di configurazione « plugin_Thumbs.cfg ».

Fare clic su una miniatura ti porta direttamente a quell'immagine nel canale
associato.  Passare il cursore su una miniatura mostrerà un suggerimento che
contiene un paio di utili informazioni di metadati dall'immagine.

La casella « Scorrimento automatico », se selezionata, farà scorrere il pannello
``Thumbs`` fino all'immagine attiva.

Questo plugin di solito non è configurato per essere chiudibile, ma l'utente può
renderlo tale impostando l'impostazione « closeable » su True nel file di
configurazione -- allora i pulsanti Chiudi e Aiuto verranno aggiunti nella parte
inferiore dell'interfaccia.

**Escludere immagini da Thumbs**

.. note:: Questo controlla anche il comportamento di ``Contents``.

Sebbene il comportamento predefinito sia che ogni immagine caricata nel
visualizzatore di riferimento compaia in ``Thumbs``, ci possono essere casi in
cui questo è indesiderato (ad es. quando molte immagini vengono caricate a
cadenza periodica da qualche processo automatizzato).  In tali casi ci sono due
meccanismi per impedire che certe immagini compaiano in ``Thumbs``:

* Assegnare l'impostazione « genthumb » a False nelle impostazioni di un canale
  (ad esempio dal plugin ``Preferences``, sotto le impostazioni « General »)
  escluderà il canale stesso e tutte le sue immagini.
* Impostare la parola chiave « nothumb » nei metadati di un wrapper di immagine
  (non nell'intestazione FITS, ma ad es. tramite ``image.set(nothumb=True)``)
  escluderà quella particolare immagine da ``Thumbs``, anche se l'impostazione
  « genthumb » è True per quel canale.

È personalizzabile usando ``~/.ginga/plugin_Thumbs.cfg``, dove ``~`` è la tua
directory HOME:

.. code-block:: Python

  #
  # Thumbs plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_Thumbs.cfg"

  # If you revisit the same directories frequently
  # caching thumbs saves a lot of time when they need to be regenerated
  cache_thumbs = False

  # cache location-- "local" puts them in a .thumbs subfolder, otherwise
  # they are cached in ~/.ginga/thumbs
  cache_location = 'local'

  # Scroll the pane automatically when new thumbnails arrive
  auto_scroll = True

  # Keywords to extract and show if we mouse over the thumbnail
  tt_keywords = ['OBJECT', 'FRAMEID', 'UT', 'DATE-OBS']

  # Mandatory unique image identifier in tooltip
  mouseover_name_key = 'NAME'

  # How many seconds to wait after an image is altered to begin trying
  # to rebuild a matching thumb.  Usually a few seconds is good in case
  # there is ongoing adjustment of the image
  rebuild_wait = 0.5

  # Max length of thumb on the long side
  thumb_length = 180

  # Separation between thumbs in pixels
  thumb_hsep = 15
  thumb_vsep = 15

  # Sort the thumbs alphabetically: 'alpha' or None
  sort_order = None

  # Thumbnail label length in num of characters (None = no limit)
  label_length = 25

  # Cut off long label ('left', 'right', or None)
  label_cutoff = 'right'

  # Option to highlight images that are displayed in channels.
  # If set to True this option will only highlight the image that is in the
  # channel with the keyboard focus
  highlight_tracks_keyboard_focus = True

  # Highlighted label colors
  label_bg_color = 'lightgreen'
  label_font_color = 'white'

  label_font_size = 10

  # Load visible thumbs in the background to replace placeholder icons
  autoload_visible_thumbs = True

  # Length of time to wait after scrolling to begin autoloading
  autoload_interval = 1.0

  # list of attributes to transfer from the channel viewer to the
  # thumbnail generator if the channel has an image in it
  transfer_attrs = ['transforms', 'cutlevels', 'rgbmap']

  # Add a close button to this plugin, so that it can be stopped
  closeable = False
