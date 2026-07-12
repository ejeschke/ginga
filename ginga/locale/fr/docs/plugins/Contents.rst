
Le plugin ``Contents`` fournit une interface de type table des matières pour
toutes les images visualisées depuis le démarrage du programme.  Contrairement à
``Thumbs``, ``Contents`` est trié par canal.  Le contenu montre aussi certaines
métadonnées configurables de l'image.

**Type de plugin : Global**

``Contents`` est un plugin global.  Une seule instance peut être ouverte.

**Utilisation**

Cliquez sur un en-tête de colonne pour trier la table selon cette colonne ;
cliquez à nouveau pour trier dans l'autre sens.

.. note:: Les colonnes et leurs valeurs sont tirées de l'en-tête FITS, le cas
          échéant.  Ceci peut être personnalisé en définissant le paramètre
          « columns » dans le fichier de paramètres « plugin_Contents.cfg ».

L'image active dans le canal actuellement focalisé est normalement mise en
surbrillance.  Un double-clic sur une image forcera l'affichage de cette image
dans le canal associé.  Un simple clic sur n'importe quelle image active les
boutons en bas de l'interface :

* « Afficher » : Fait de l'image l'image active.
* « Déplacer » : Déplace l'image vers un autre canal.
* « Copier » : Copie l'image vers un autre canal.
* « Retirer » : Retire l'image du canal.

Si « Déplacer » ou « Copier » est effectué sur une image qui a été modifiée dans
Ginga (qui aurait une entrée sous ``ChangeHistory``, si utilisé), l'historique
des modifications sera également conservé.  Retirer une image d'un canal détruit
toute modification non enregistrée.

Ce plugin n'est généralement pas configuré pour être fermable, mais
l'utilisateur peut le rendre tel en définissant le paramètre « closeable » sur
True dans le fichier de configuration -- des boutons Fermer et Aide seront alors
ajoutés en bas de l'interface.

**Exclure des images de Contents**

.. note:: Ceci contrôle aussi le comportement de ``Thumbs``.

Bien que le comportement par défaut soit que chaque image chargée dans le
visualiseur de référence apparaisse dans ``Contents``, il peut y avoir des cas
où cela n'est pas souhaitable (p. ex. lorsque de nombreuses images sont chargées
à un rythme périodique par un processus automatisé).  Dans de tels cas, il y a
deux mécanismes pour empêcher certaines images d'apparaître dans ``Contents`` :

* Attribuer le paramètre « genthumb » à False dans les paramètres d'un canal
  (par exemple depuis le plugin ``Preferences``, sous les paramètres
  « General ») exclura le canal lui-même et toutes ses images.
* Définir le mot-clé « nothumb » dans les métadonnées d'un wrapper d'image (pas
  dans l'en-tête FITS, mais p. ex. via ``image.set(nothumb=True)``) exclura
  cette image particulière de ``Contents``, même si le paramètre « genthumb »
  est True pour ce canal.

Il est personnalisable à l'aide de ``~/.ginga/plugin_Contents.cfg``, où ``~``
est votre répertoire HOME :

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
