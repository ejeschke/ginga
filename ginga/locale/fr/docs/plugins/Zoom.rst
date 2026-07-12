Le plugin ``Zoom`` affiche une image agrandie d'une région de découpe centrée
sous la position du curseur dans l'image du canal associé.  À mesure que le
curseur se déplace sur l'image, l'image de zoom se met à jour pour permettre une
inspection minutieuse des pixels ou un contrôle précis en conjonction avec
d'autres opérations de plugins.

**Type de plugin : Global**

``Zoom`` est un plugin global.  Une seule instance peut être ouverte.

**Utilisation**

Le grossissement de la fenêtre de zoom peut être modifié en ajustant le curseur
« Niveau de zoom ».

Deux modes de fonctionnement sont possibles -- zoom absolu et relatif :

* En mode absolu, le niveau de zoom contrôle exactement le degré de zoom montré
  dans la découpe ; par exemple, l'image du canal peut être zoomée à 10X, mais
  l'image de zoom ne montrera qu'une image 3X si le niveau de zoom est réglé sur
  3X.

* En mode relatif, le réglage du niveau de zoom est interprété comme relatif au
  réglage de zoom de l'image du canal.  Si le niveau de zoom est réglé sur 3X et
  que l'image du canal est zoomée à 10X, l'image de zoom montrée sera 13X (10X +
  3X).  Notez que le réglage du niveau de zoom peut être < 1, de sorte qu'un
  réglage de 1/3X avec un zoom de 3X dans l'image du canal produira une image de
  zoom 1X.

Le réglage « Intervalle de rafraîchissement » contrôle la rapidité avec laquelle
le plugin ``Zoom`` répond au mouvement du curseur en mettant à jour l'image de
zoom.  La valeur est spécifiée en millisecondes.

.. tip:: Habituellement, régler un petit intervalle de rafraîchissement
         *améliore* la réactivité globale de l'image de zoom, et la valeur par
         défaut de 20 est raisonnable.  Vous pouvez expérimenter avec la valeur
         si l'image de zoom semble trop saccadée ou désynchronisée avec le
         mouvement de la souris dans la fenêtre de l'image du canal.

Le bouton « Par défaut » restaure les réglages par défaut des contrôles.

Il est personnalisable à l'aide de ``~/.ginga/plugin_Zoom.cfg``, où ``~`` est
votre répertoire HOME :

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
