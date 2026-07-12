Le plugin ``ColorMapPicker`` sert à parcourir et sélectionner graphiquement une
palette de couleurs pour un visualiseur d'images de canal.

**Type de plugin : Global ou Local**

``ColorMapPicker`` est un plugin hybride global/local, ce qui signifie qu'il
peut être invoqué de l'une ou l'autre façon.  Invoqué comme plugin local, il est
associé à un canal, et une instance peut être ouverte pour chaque canal.  Il
peut aussi être ouvert comme plugin global.

**Utilisation**

L'utilisation du plugin est très simple : les palettes de couleurs sont
affichées sous forme de barres de couleur et d'étiquettes dans le volet de vue
principal du plugin.  Cliquez sur l'une des barres pour définir la palette du
canal associé (si invoqué comme plugin local) ou du canal actuellement actif
(si invoqué comme plugin global).

Vous pouvez faire défiler verticalement ou utiliser les barres de défilement
pour parcourir les échantillons de barres de couleur.

.. note:: Au premier démarrage du plugin, il génère une image RGB bitmap de
          barres de couleur et d'étiquettes correspondant à toutes les palettes
          disponibles.  Cela peut prendre quelques secondes selon le nombre de
          palettes installées.

          Les palettes sont affichées avec la carte d'intensité « ramp »
          appliquée.
