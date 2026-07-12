Le plugin ``Pan`` fournit une petite image de panoramique qui donne une vue
d'ensemble « à vol d'oiseau » de l'image de canal qui a eu le focus en dernier.
Si l'image du canal est zoomée 2X ou plus, la région de panoramique est affichée
graphiquement dans l'image ``Pan`` par un rectangle.

**Type de plugin : Local**

``Pan`` est un plugin global.  Une seule instance peut être ouverte.

**Utilisation**

L'image du canal peut être déplacée en cliquant et/ou en glissant pour placer le
rectangle.  Utiliser le bouton droit de la souris pour tracer un rectangle force
le visualiseur d'images du canal à essayer de correspondre à la région (en
tenant compte des différences de rapport d'aspect entre le rectangle tracé et
les dimensions de la fenêtre).  Faire défiler dans l'image ``Pan`` zoome l'image
du canal.

La carte de couleur/intensité et les niveaux de coupure de l'image ``Pan`` sont
mis à jour lorsqu'ils sont modifiés dans l'image de canal correspondante.
L'image ``Pan`` affiche aussi la boussole du système de coordonnées mondial
(WCS), si des métadonnées WCS valides sont présentes dans le HDU FITS visualisé
dans le canal.

Le plugin ``Pan`` apparaît généralement comme un sous-volet sous l'onglet
« Info », à côté du plugin ``Info``.

Ce plugin n'est généralement pas configuré comme fermable, mais l'utilisateur
peut le rendre tel en réglant le paramètre « closeable » sur True dans le
fichier de configuration ; les boutons Fermer et Aide sont alors ajoutés en bas
de l'interface.
