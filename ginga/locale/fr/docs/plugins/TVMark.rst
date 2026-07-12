
Marquer des points depuis un fichier (mode non interactif) sur une image.

**Type de plugin : Local**

``TVMark`` est un plugin local, ce qui signifie qu'il est associé à un canal.
Une instance peut être ouverte pour chaque canal.

**Utilisation**

Ce plugin permet le marquage non interactif de points d'intérêt en lisant un
fichier contenant une table avec les positions RA et DEC de ces points.  Tout
fichier texte ou de table FITS pouvant être lu par ``astropy.table`` est
acceptable, mais l'utilisateur *doit* définir correctement les noms des colonnes
dans le fichier de configuration du plugin (voir ci-dessous).  Une tentative
sera faite pour convertir les valeurs RA et DEC en degrés.  Si la conversion
d'unités échoue, elles seront supposées être déjà en degrés.

Alternativement, si le fichier a des colonnes contenant les positions pixel
directes, vous pouvez lire ces colonnes à la place en décochant la case
« Utiliser RADEC ».  Là encore, les noms des colonnes doivent être correctement
définis dans le fichier de configuration du plugin (voir ci-dessous).  Les
valeurs pixel peuvent être indexées à 0 ou à 1 (c.-à-d. si le premier pixel est
0 ou 1) et c'est configurable (voir ci-dessous).  Ceci est utile lorsque vous
voulez marquer les pixels physiques indépendamment du WCS (p. ex. marquer des
pixels chauds sur un détecteur).  RA et DEC seront toujours affichés si l'image
a des informations WCS, mais ils n'affecteront pas les marquages.

Pour marquer différents groupes (p. ex. afficher les galaxies en cercles verts
et l'arrière-plan en croix cyan, comme montré ci-dessus) :

1. Sélectionnez cercle vert dans les menus déroulants.  Vous pouvez aussi saisir
   la taille ou la largeur souhaitée.
2. Assurez-vous que la case « Utiliser RADEC » est cochée, le cas échéant.
3. À l'aide du bouton « Charger les coordonnées », chargez le fichier contenant
   les positions RA et DEC (ou X et Y) *uniquement* des galaxies.
4. Répétez l'étape 1 mais sélectionnez maintenant croix cyan dans les menus
   déroulants.
5. Répétez l'étape 2 mais choisissez le fichier contenant *uniquement* les
   positions de l'arrière-plan.

Sélectionner une entrée (ou plusieurs entrées) dans la liste de la table mettra
en surbrillance le(s) marquage(s) sur l'image.  La surbrillance utilise la même
forme et la même couleur, mais une ligne légèrement plus épaisse.

Vous pouvez aussi mettre en surbrillance tous les marquages d'une région, à la
fois sur l'image et dans la liste de la table, en dessinant un rectangle sur
l'image pendant que ce plugin est actif.

Appuyer sur le bouton « Masquer » masquera les marquages mais n'efface pas la
mémoire du plugin ; c'est-à-dire que lorsque vous appuyez sur « Afficher », les
mêmes marquages réapparaîtront sur la même image.  En revanche, appuyer sur
« Oublier » effacera les marquages à la fois de l'affichage et de la mémoire ;
c'est-à-dire que vous devrez recharger votre(vos) fichier(s) pour recréer les
marquages.

Pour redessiner les mêmes positions avec des paramètres de marquage différents,
appuyez sur « Oublier » et répétez les étapes ci-dessus, selon les besoins.
Cependant, si vous souhaitez simplement changer la largeur de ligne (épaisseur),
appuyer sur « Masquer » puis « Afficher » après avoir saisi la nouvelle valeur
de largeur suffira.

Si des images de pointages/dimensions très différents sont affichées dans le
même canal, les marquages qui appartiennent à une image mais tombent en dehors
d'une autre n'apparaîtront pas dans cette dernière.

Pour créer une table que ce plugin peut lire, on peut utiliser les résultats du
plugin ``Pick``, en plus de créer une table à la main, en utilisant
``astropy.table``, etc.

Utilisé avec ``TVMask``, vous pouvez superposer dans Ginga à la fois des sources
ponctuelles et des régions masquées.

Il est personnalisable à l'aide de ``~/.ginga/plugin_TVMark.cfg``, où ``~`` est
votre répertoire HOME :

.. code-block:: Python

  #
  # TVMark plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_TVMark.cfg"

  # Marking type -- 'circle' or 'cross'
  marktype = 'circle'

  # Marking color -- Any color name accepted by Ginga
  markcolor = 'green'

  # Marking size or radius
  marksize = 5

  # Marking line width (thickness)
  markwidth = 1

  # Specify whether pixel values are 0- or 1-indexed
  pixelstart = 1

  # True -- Use 'ra' and 'dec' columns to extract RA/DEC positions. This option
  #         uses image WCS to convert to pixel locations.
  # False -- Use 'x' and 'y' columns to extract pixel locations directly.
  #          This does not use WCS.
  use_radec = True

  # Columns to load into table listing (case-sensitive).
  # Whether RA/DEC or X/Y columns are used depend on associated GUI selection.
  ra_colname = 'ra'
  dec_colname = 'dec'
  x_colname = 'x'
  y_colname = 'y'
  # Extra columns to display; e.g., ['colname1', 'colname2']
  extra_columns = []
