
Un plugin pour composer des images RGB à partir d'images monochromes
constituantes.

**Type de plugin : Local**

``Compose`` est un plugin local, ce qui signifie qu'il est associé à un canal.
Une instance peut être ouverte pour chaque canal.

**Utilisation**

Démarrez le plugin ``Compose`` depuis le menu « Operation->RGB » (en bas) ou
« Plugins->RGB » (en haut).  L'onglet devrait apparaître sous l'onglet
« Dialogs » dans le visualiseur à droite en tant que « IMAGE:Compose ».

1. Sélectionnez le type de composition que vous souhaitez réaliser dans la liste
   déroulante « Compose Type » : « RGB » pour composer trois images monochromes
   en une image couleur, « Alpha » pour composer une série d'images en couches
   avec des valeurs alpha différentes pour chaque couche.
2. Appuyez sur « Nouvelle image » pour commencer à composer une nouvelle image.

***Pour la composition RGB***

1. Faites glisser vos trois images constituantes qui formeront les plans R, G et
   B dans la fenêtre « Preview » -- faites-les glisser dans l'ordre R (rouge), G
   (vert) et B (bleu).  Vous pouvez aussi charger les images dans le visualiseur
   de canal une par une et, après chacune, appuyer sur « Insérer depuis le
   canal » (de même, faites-le dans l'ordre R, G et B).

Dans l'interface du plugin, les images R, G et B devraient apparaître sous forme
de trois curseurs dans la zone « Layers » du plugin, et l'aperçu devrait montrer
une version en basse résolution de l'aspect de l'image composite avec les
curseurs réglés.

.. figure:: figures/compose-rgb.png
   :width: 800px
   :align: center
   :alt: Composition d'une image RGB

   Composition d'une image RGB.

2. Jouez avec les niveaux alpha de chaque couche à l'aide des curseurs du plugin
   ``Compose`` ; à mesure que vous ajustez un curseur, l'image d'aperçu devrait
   se mettre à jour.
3. Lorsque vous voyez quelque chose qui vous plaît, vous pouvez l'enregistrer
   dans un fichier à l'aide du bouton « Enregistrer sous » (utilisez « jpeg » ou
   « png » comme extension de fichier), ou l'insérer dans le canal à l'aide du
   bouton « Enregistrer dans le canal ».

***Pour la composition Alpha***

Pour la composition de type Alpha, les images sont simplement combinées dans
l'ordre montré dans la pile, la couche 0 étant la couche inférieure, et les
couches successives empilées par-dessus.  Le niveau alpha de chaque couche est
réglable par un curseur de la même manière que décrit ci-dessus.

.. figure:: figures/compose-alpha.png
   :width: 800px
   :align: center
   :alt: Composition Alpha d'une image

   Composition Alpha d'une image.

1. Faites glisser vos N images constituantes qui formeront les couches dans la
   fenêtre « Preview », ou chargez les images dans le visualiseur de canal une
   par une et, après chacune, appuyez sur « Insérer depuis le canal » (la
   première image sera en bas de la pile -- couche 0).
2. Jouez avec les niveaux alpha de chaque couche à l'aide des curseurs du plugin
   ``Compose`` ; à mesure que vous ajustez un curseur, l'image d'aperçu devrait
   se mettre à jour.
3. Lorsque vous voyez quelque chose qui vous plaît, vous pouvez l'enregistrer
   dans un fichier à l'aide du bouton « Enregistrer sous » (utilisez « fits »
   comme extension de fichier), ou l'insérer dans le canal à l'aide du bouton
   « Enregistrer dans le canal ».

***Remarques générales***

- La fenêtre d'aperçu est simplement un widget ginga, donc toutes les
  associations habituelles s'appliquent ; vous pouvez définir des cartes de
  couleurs, des niveaux de coupe, etc. avec les associations de souris et de
  clavier.
