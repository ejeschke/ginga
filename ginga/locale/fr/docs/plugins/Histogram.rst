
``Histogram`` trace un histogramme pour une région dessinée dans l'image, ou
pour l'image entière.

**Type de plugin : Local**

``Histogram`` est un plugin local, ce qui signifie qu'il est associé à un canal.
Ce n'est pas un singleton, ce qui signifie que plusieurs instances peuvent être
ouvertes pour chaque canal.

**Utilisation**

Cliquez et faites glisser pour définir une région dans l'image qui sera utilisée
pour calculer l'histogramme.  Pour prendre l'histogramme de l'image complète,
cliquez sur le bouton de l'interface intitulé « Image entière ».

.. note:: Selon la taille de l'image, le calcul de l'histogramme complet peut
          prendre du temps.

Si une nouvelle image est sélectionnée pour le canal, le tracé de l'histogramme
sera recalculé selon les paramètres actuels avec les nouvelles données.

Sauf s'il est désactivé dans le fichier de paramètres du plugin d'histogramme,
une ligne de statistiques simples pour la boîte est calculée et affichée sur une
ligne sous le tracé.

**Contrôles de l'interface**

Trois boutons radio en bas de l'interface servent à contrôler les effets de
l'action clic/glisser :

* sélectionnez « Déplacer » pour faire glisser la région vers un autre endroit
* sélectionnez « Dessiner » pour dessiner une nouvelle région
* sélectionnez « Modifier » pour modifier la région

Pour faire un tracé logarithmique de l'histogramme, cochez la case
« Histogramme log ».  Pour tracer selon la plage complète des valeurs de l'image
au lieu de la plage à l'intérieur des valeurs de coupe, décochez la case
« Tracer par coupes ».

Le paramètre « NumBins » détermine combien de classes sont utilisées pour
calculer l'histogramme.  Saisissez un nombre dans la case et appuyez sur
« Entrée » pour changer la valeur par défaut.

**Contrôles pratiques des niveaux de coupe**

Comme un histogramme est un retour utile pour régler les niveaux de coupe, des
contrôles sont fournis dans l'interface pour régler les niveaux de coupe bas et
haut dans l'image, ainsi que pour effectuer des niveaux de coupe automatiques,
selon les paramètres de niveaux de coupe automatiques des préférences du canal.

Vous pouvez régler les niveaux de coupe en cliquant dans le tracé de
l'histogramme :

* clic gauche : régler la coupe basse
* clic milieu : réinitialiser (niveaux de coupe automatiques)
* clic droit : régler la coupe haute

De plus, vous pouvez ajuster dynamiquement l'écart entre les coupes basse et
haute en faisant défiler la molette dans le tracé (c.-à-d. la « largeur » de la
courbe du tracé de l'histogramme).  Cela a pour effet d'augmenter ou de diminuer
le contraste dans l'image.  La quantité modifiée à chaque clic de molette est
définie par le paramètre ``scroll_pct`` du fichier de configuration du plugin.
La valeur par défaut est 10 %.

**Configuration de l'utilisateur**

Il est personnalisable à l'aide de ``~/.ginga/plugin_Histogram.cfg``, où ``~``
est votre répertoire HOME :

.. code-block:: Python

  #
  # Histogram plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_Histogram.cfg"

  # Switch to "move" mode after selection
  draw_then_move = True

  # Number of bins for histogram
  num_bins = 2048

  # Histogram color
  hist_color = 'aquamarine'

  # Calculate extra statistics on box
  show_stats = True

  # Controls formatting (width) of statistics numbers
  maxdigits = 7

  # percentage to adjust cuts gap when scrolling in histogram
  scroll_pct = 0.10
