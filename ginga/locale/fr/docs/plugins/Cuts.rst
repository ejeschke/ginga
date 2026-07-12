
Un plugin pour générer un tracé des valeurs le long d'une ligne ou d'un chemin.

**Type de plugin : Local**

``Cuts`` est un plugin local, ce qui signifie qu'il est associé à un canal.
Ce n'est pas un singleton, ce qui signifie que plusieurs instances peuvent être
ouvertes pour chaque canal.

**Utilisation**

``Cuts`` trace un graphique simple des valeurs de pixel en fonction de l'index
pour une ligne tracée à travers l'image.  Plusieurs coupes peuvent être tracées.

Il y a quatre sortes de coupes disponibles : line, path, freepath et
beziercurve :

* La coupe « line » est une ligne droite entre deux points.
* La coupe « path » est dessinée comme un polygone ouvert, avec des segments
  droits entre les points.
* La coupe « freepath » est comme une coupe path, mais dessinée à l'aide d'un
  tracé à main levée suivant le mouvement du curseur.
* Le chemin « beziercurve » est une courbe de Bézier cubique.

Si une nouvelle image est ajoutée au canal pendant que le plugin est actif, il
se mettra à jour avec les nouvelles coupes calculées sur la nouvelle image.

Si le paramètre « enable slit » est activé, ce plugin permettra aussi la
fonctionnalité d'image de fente (pour les images multidimensionnelles) via un
onglet « Slit ».  Dans l'interface de l'onglet, sélectionnez un axe dans la
liste « Axes » et dessinez une ligne.  Cela créera une image 2D qui suppose que
les deux premiers axes sont spatiaux et indexe les données le long de l'axe
sélectionné.  Tout comme ``Cuts``, vous pouvez visualiser les autres images de
fente à l'aide de la liste déroulante de sélection de coupe.

**Dessiner des coupes**

Le menu « New Cut Type » vous permet de choisir quel type de coupe vous allez
dessiner.

Choisissez « New Cut » dans le menu déroulant « Cut » si vous voulez dessiner une
nouvelle coupe.  Sinon, si une coupe nommée particulière est sélectionnée, elle
sera remplacée par toute coupe nouvellement dessinée.

Pendant que vous dessinez une coupe path ou beziercurve, appuyez sur « v » pour
ajouter un sommet, ou « z » pour supprimer le dernier sommet ajouté.

**Raccourcis clavier**

En survolant avec le curseur, appuyez sur « h » pour une coupe horizontale
complète et « j » pour une coupe verticale complète.

**Supprimer des coupes**

Pour supprimer une coupe, sélectionnez son nom dans le menu déroulant « Cut » et
cliquez sur le bouton « Supprimer ».  Pour supprimer toutes les coupes, appuyez
sur « Tout supprimer ».

**Modifier des coupes**

À l'aide de la fonction d'édition du canevas, il est possible d'ajouter de
nouveaux sommets à un chemin existant et de déplacer des sommets.  Cliquez sur
le bouton radio « Modifier » pour mettre le canevas en mode édition.  Si une
coupe n'est pas automatiquement sélectionnée, vous pouvez maintenant sélectionner
la ligne, le chemin ou la courbe en cliquant dessus, ce qui devrait activer les
points de contrôle aux extrémités ou aux sommets -- vous pouvez les faire
glisser.  Pour ajouter un nouveau sommet à un chemin, survolez soigneusement
avec le curseur la ligne où vous voulez le nouveau sommet et appuyez sur « v ».
Pour supprimer un sommet, survolez-le avec le curseur et appuyez sur « z ».

Vous remarquerez un point de contrôle supplémentaire pour la plupart des objets,
dont le centre est d'une couleur différente -- c'est un point de contrôle de
déplacement pour déplacer l'objet entier sur l'image en mode édition.

Vous pouvez aussi sélectionner « Déplacer » pour simplement déplacer une coupe
sans la modifier.

**Changer la largeur des coupes**

La largeur des coupes « line » peut être changée à l'aide du menu « Width Type » :

* « none » indique une coupe de rayon nul ; c.-à-d. montrant seulement les
  valeurs de pixel le long de la ligne
* « x » tracera la somme des valeurs le long de l'axe X orthogonal à la coupe.
* « y » tracera la somme des valeurs le long de l'axe Y orthogonal à la coupe.
* « perpendicular » tracera la somme des valeurs le long d'un axe perpendiculaire
  à la coupe.

Le « Width radius » contrôle la largeur de la sommation orthogonale d'une
quantité de chaque côté de la coupe -- 1 serait 3 pixels, 2 serait 5 pixels,
etc.

**Enregistrer des coupes**

Utilisez le bouton « Enregistrer » pour enregistrer le tracé de ``Cuts`` comme
image et les données comme archive Numpy compressée.

**Copier des coupes**

Pour copier une coupe, sélectionnez son nom dans le menu déroulant « Cut » et
cliquez sur le bouton « Copier la coupe ».  Une nouvelle coupe en sera créée.
Vous pouvez alors manipuler la nouvelle coupe indépendamment.

**Configuration de l'utilisateur**

Il est personnalisable à l'aide de ``~/.ginga/plugin_Cuts.cfg``, où ``~`` est
votre répertoire HOME :

.. code-block:: Python

  #
  # Cuts plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_Cuts.cfg"

  # If set to True will always select a cut after drawing it
  select_new_cut = True

  # If set to True will automatically change to "move" mode after draw
  draw_then_move = True

  # If set to True will label cuts with a text annotation
  label_cuts = True

  # If set to True will add a legend to the cuts plot
  show_cuts_legend = False

  # If set to True will add Slit tab
  enable_slit = False

  # Default cut colors
  colors = ['magenta', 'skyblue2', 'chartreuse2', 'cyan', 'pink', 'burlywood2', 'yellow3', 'turquoise', 'coral1', 'mediumpurple2']

  # If set to True, will update graph continuously as cursor is dragged
  # around image
  drag_update = False
