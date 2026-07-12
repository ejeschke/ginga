
Le plugin ``Thumbs`` fournit un index de vignettes de toutes les images
visualisées depuis le démarrage du programme.

**Type de plugin : Global**

``Thumbs`` est un plugin global.  Une seule instance peut être ouverte.

**Utilisation**

Par défaut, les ``Thumbs`` apparaissent dans l'historique de visualisation
chronologique, avec les images les plus récentes en bas et les plus anciennes en
haut.  Le tri peut être rendu alphanumérique par un paramètre dans le fichier de
configuration « plugin_Thumbs.cfg ».

Cliquer sur une vignette vous amène directement à cette image dans le canal
associé.  Survoler une vignette avec le curseur affichera une infobulle
contenant quelques métadonnées utiles de l'image.

La case « Défilement automatique », si elle est cochée, fera défiler le panneau
``Thumbs`` jusqu'à l'image active.

Ce plugin n'est généralement pas configuré pour être fermable, mais
l'utilisateur peut le rendre tel en définissant le paramètre « closeable » sur
True dans le fichier de configuration -- des boutons Fermer et Aide seront alors
ajoutés en bas de l'interface.

**Exclure des images de Thumbs**

.. note:: Ceci contrôle aussi le comportement de ``Contents``.

Bien que le comportement par défaut soit que chaque image chargée dans le
visualiseur de référence apparaisse dans ``Thumbs``, il peut y avoir des cas où
cela n'est pas souhaitable (p. ex. lorsque de nombreuses images sont chargées à
un rythme périodique par un processus automatisé).  Dans de tels cas, il y a
deux mécanismes pour empêcher certaines images d'apparaître dans ``Thumbs`` :

* Attribuer le paramètre « genthumb » à False dans les paramètres d'un canal
  (par exemple depuis le plugin ``Preferences``, sous les paramètres
  « General ») exclura le canal lui-même et toutes ses images.
* Définir le mot-clé « nothumb » dans les métadonnées d'un wrapper d'image (pas
  dans l'en-tête FITS, mais p. ex. via ``image.set(nothumb=True)``) exclura
  cette image particulière de ``Thumbs``, même si le paramètre « genthumb » est
  True pour ce canal.

Il est personnalisable à l'aide de ``~/.ginga/plugin_Thumbs.cfg``, où ``~`` est
votre répertoire HOME :

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
