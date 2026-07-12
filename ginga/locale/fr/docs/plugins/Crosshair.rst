
``Crosshair`` est un plugin simple pour dessiner des réticules étiquetés avec la
position de la croix en coordonnées pixel, en coordonnées WCS ou la valeur de
donnée à la position de la croix.

**Type de plugin : Local**

``Crosshair`` est un plugin local, ce qui signifie qu'il est associé à un canal.
Une instance peut être ouverte pour chaque canal.

**Utilisation**

Sélectionnez le type de sortie approprié dans la liste déroulante « Format » de
l'interface : « xy » pour les coordonnées pixel, « coords » pour les coordonnées
WCS et « value » pour la valeur à la position du réticule.

Si « Glisser seulement » est coché, le réticule n'est mis à jour que lorsque le
curseur est cliqué ou glissé dans la fenêtre.  S'il est décoché, le réticule est
positionné simplement en déplaçant le curseur dans la fenêtre du visualiseur de
canal.

L'onglet « Cuts » contient un tracé de profil pour les coupes verticale et
horizontale représentées par la limite visible de la boîte présente lorsque
« Quick Cuts » est coché.  Ce tracé est mis à jour en temps réel à mesure que le
réticule est déplacé.  Lorsque « Quick Cuts » est décoché, le tracé n'est pas
mis à jour.

La taille de la boîte est déterminée par le paramètre « radius ».

Le contrôle « Niveau d'avertissement » peut servir à définir un niveau de flux
au-dessus duquel un avertissement est indiqué dans le tracé des coupes par une
ligne jaune et un fond devenant jaune.  L'avertissement est déclenché si une
valeur le long de la coupe X ou Y dépasse le seuil du niveau d'avertissement.

Le contrôle « Niveau d'alerte » est similaire, mais représenté par une ligne
rouge et un fond devenant rose.  L'avertissement est déclenché si une valeur le
long de la coupe X ou Y dépasse le seuil du niveau d'alerte.  Les alertes ont la
priorité sur les avertissements.

Les fonctions « Avertissement » et « Alerte » peuvent être désactivées en
définissant simplement une valeur vide.  Elles sont désactivées par défaut.

Le tracé des coupes est interactif, mais cela n'a vraiment de sens de l'utiliser
que si « Glisser seulement » est coché.  Vous pouvez appuyer sur « x » ou « y »
dans la fenêtre du tracé pour activer et désactiver la fonction de mise à
l'échelle automatique des axes pour l'un ou l'autre axe, et faire défiler dans
le tracé pour zoomer sur l'axe X (maintenez Ctrl enfoncé pendant le défilement
pour zoomer sur l'axe Y).

Crosshair fournit une fonction d'interaction avec le plugin Pick : lorsque le
réticule est au-dessus d'un objet, vous pouvez appuyer sur « r » dans la fenêtre
du visualiseur de canal pour que le plugin Pick soit invoqué à cet emplacement
particulier.  Si un Pick n'est pas déjà ouvert sur ce canal, il sera d'abord
ouvert.

**Configuration de l'utilisateur**

Il est personnalisable à l'aide de ``~/.ginga/plugin_Crosshair.cfg``, où ``~``
est votre répertoire HOME :

.. code-block:: Python

  #
  # Crosshair plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_Crosshair.cfg"

  # color of the crosshair
  color = 'green'

  # text color of crosshair
  text_color = 'skyblue'

  # box color indicating cut radius
  box_color = 'aquamarine'

  # cut plot line colors for X and Y
  quick_h_cross_color = '#7570b3'
  quick_v_cross_color = '#1b9e77'

  # enable quick cuts plots by default
  quick_cuts = False

  # force drag only by default
  drag_only = False

  # set a warning level for the warning feature of the cuts plot
  warn_level = None

  # set an alery level for the alert feature of the cuts plot
  alert_level = None

  # set initial radius of the cuts box
  cuts_radius = 15
