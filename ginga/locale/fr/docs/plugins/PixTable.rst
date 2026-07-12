
``PixTable`` offre un moyen de vérifier ou de surveiller les valeurs des pixels
dans une région.

**Type de plugin : Local**

``PixTable`` est un plugin local, ce qui signifie qu'il est associé à un canal.
Une instance peut être ouverte pour chaque canal.

**Utilisation de base**

Dans l'utilisation la plus basique, déplacez simplement le curseur dans le
visualiseur de canal ; un tableau de valeurs de pixel apparaîtra dans
l'affichage « Pixel Values » de l'interface du plugin.  La valeur centrale est
mise en évidence et correspond à la valeur sous le curseur.

Vous pouvez choisir une grille 3x3, 5x5, 7x7 ou 9x9 dans le contrôle de liste
déroulante le plus à gauche.  Il peut être utile d'ajuster le contrôle « Taille
de police » pour éviter que les valeurs du tableau soient coupées sur les côtés.
Vous pouvez aussi agrandir l'espace de travail du plugin pour voir davantage de
la table.

.. note:: L'ordre de la table de valeurs affichée ne correspondra pas
          nécessairement au visualiseur de canal si l'image est retournée,
          transposée ou pivotée.

**Utiliser les marques**

Lorsque vous placez et sélectionnez une marque, les valeurs de pixel seront
affichées autour de la marque au lieu du curseur.  Il peut y avoir un nombre
quelconque de marques, et chacune est notée par un « X » numéroté.  Changez
simplement le contrôle déroulant de marque pour sélectionner une marque
différente et voir les valeurs autour d'elle.  La marque actuellement
sélectionnée est affichée avec une couleur différente des autres.

Les marques resteront en position même si une nouvelle image est chargée et
elles afficheront les valeurs de la nouvelle image.  De cette façon, vous pouvez
surveiller la zone autour d'un point si l'image se met à jour fréquemment.

Si la case « Recentrer sur la marque » est sélectionnée, alors lorsque vous
sélectionnez une marque différente dans le contrôle de marque, le visualiseur de
canal se recentrera sur cette marque.  Cela peut être utile pour inspecter les
mêmes endroits dans plusieurs images différentes, surtout lorsqu'on est zoomé au
plus près de l'image.

.. note:: Si vous remettez le contrôle de marque sur « None », la table de pixel
          se mettra à nouveau à jour à mesure que vous déplacez le curseur dans
          le visualiseur.

La case « Caption » peut servir à définir une annotation textuelle qui sera
ajoutée à l'étiquette de la marque lors de la création de la marque suivante.
Cela peut servir à étiqueter une caractéristique dans l'image, par exemple.

**Supprimer les marques**

Pour supprimer une marque, sélectionnez-la dans le contrôle de marque puis
appuyez sur le bouton intitulé « Supprimer ».  Pour supprimer toutes les
marques, appuyez sur le bouton intitulé « Tout supprimer ».

**Déplacer les marques**

Lorsque le bouton radio « Déplacer » est coché et qu'une marque est
sélectionnée, cliquer ou faire glisser n'importe où dans l'image déplacera la
marque à cet endroit et mettra à jour la table de pixel.  Si aucune marque n'est
actuellement sélectionnée, une nouvelle sera créée et déplacée.

**Dessiner les marques**

Lorsque le bouton radio « Dessiner » est coché, cliquer et faire glisser crée
une nouvelle marque.  Plus le tracé est long, plus le rayon du « X » est grand.

**Modifier les marques**

Lorsque le bouton radio « Modifier » est coché après qu'une marque a été
sélectionnée, vous pouvez faire glisser les points de contrôle de la marque pour
augmenter le rayon des bras du X, ou faire glisser le cadre englobant pour
déplacer la marque.  Si les points de contrôle d'édition ne sont pas affichés,
cliquez simplement sur le centre d'une marque pour les activer.

**Touches spéciales**

En mode « Déplacer » les touches suivantes sont actives :
- « n » placera une nouvelle marque à l'emplacement du curseur
- « m » déplacera la marque actuelle (le cas échéant) à l'emplacement du curseur
- « d » supprimera la marque actuelle (le cas échéant)
- « j » sélectionnera la marque précédente (le cas échéant)
- « k » sélectionnera la marque suivante (le cas échéant)

**Configuration de l'utilisateur**

Il est personnalisable à l'aide de ``~/.ginga/plugin_PixTable.cfg``, où ``~``
est votre répertoire HOME :

.. code-block:: Python

  #
  # PixTable plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_PixTable.cfg"

  # Default font
  font = 'fixed'

  # Default font size
  fontsize = 12

  # default size for mark point radius
  mark_radius = 10

  # style of point to draw
  mark_style = 'cross'

  # color of non-selected marks
  mark_color = 'purple'

  # color of selected mark
  select_color = 'cyan'

  # whether to update the pixel table when moving a mark around
  drag_update = True
