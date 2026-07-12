Apporter des modifications aux paramètres du canal de manière graphique dans
l'interface.

**Type de plugin : Local**

``Preferences`` est un plugin local, ce qui signifie qu'il est associé à un
canal.  Une instance peut être ouverte pour chaque canal.

**Utilisation**

Le plugin ``Preferences`` définit les préférences *par canal*.  Les préférences
d'un canal donné sont héritées du canal « Image » jusqu'à ce qu'elles soient
explicitement définies et enregistrées à l'aide de ce plugin.

Si « Save Settings » est pressé, il enregistrera les paramètres dans le dossier
$HOME/.ginga de l'utilisateur (un fichier « channel_NAME.cfg » pour chaque canal
NAME) de sorte que lorsqu'un canal du même nom est créé lors de futures sessions
Ginga, il obtiendra les mêmes paramètres.

**Préférences de distribution des couleurs**

.. figure:: figures/cdist-prefs.png
   :width: 400px
   :align: center
   :alt: Préférences de distribution des couleurs

   Préférences « Color Distribution ».

Les préférences « Color Distribution » contrôlent les préférences utilisées pour
la conversion de valeur de donnée en index de couleur qui se produit après
l'application des niveaux de coupe et juste avant que le mappage de couleur final
ne soit effectué.  Elles concernent la manière dont les valeurs entre les niveaux
de coupe bas et haut sont distribuées à la phase de mappage de couleur et
d'intensité.

Le contrôle « Algorithm » sert à définir l'algorithme utilisé pour le mappage.
Cliquez sur le contrôle pour afficher la liste, ou faites simplement défiler la
molette de la souris en survolant le contrôle.  Il y a huit algorithmes
disponibles : linear, log, power, sqrt, squared, asinh, sinh et histeq.  Le nom
de chaque algorithme indique comment les données sont mappées aux couleurs de la
carte de couleurs.  « linear » est la valeur par défaut.

**Préférences de mappage de couleur**

.. figure:: figures/cmap-prefs.png
   :width: 400px
   :align: center
   :alt: Préférences de mappage de couleur

   Préférences « Color Mapping ».

Les préférences « Color Mapping » contrôlent les préférences utilisées pour la
carte de couleurs et la carte d'intensité, utilisées lors de la phase finale du
processus de mappage de couleur.  Avec les préférences « Color Distribution »,
elles contrôlent le mappage des valeurs de donnée en une représentation visuelle
RGB 24 bpp.

Le contrôle « Colormap » sélectionne quelle carte de couleurs doit être chargée
et utilisée.  Cliquez sur le contrôle pour afficher la liste, ou faites
simplement défiler la molette de la souris en survolant le contrôle.

.. note:: Ginga est livré avec une bonne sélection de cartes de couleurs, mais si
          vous en voulez plus, vous pouvez en ajouter des personnalisées ou, si
          ``matplotlib`` est installé, vous pouvez charger toutes celles qu'il a.
          Voir « Customizing Ginga » pour les détails.

Le contrôle « Intensity » sélectionne quelle carte d'intensité doit être utilisée
avec la carte de couleurs.  La carte d'intensité est appliquée juste avant la
carte de couleurs, et peut servir à changer l'échelle linéaire standard des
valeurs en une échelle inversée, logarithmique, etc.

La case « Invert CMap » peut servir à inverser la carte de couleurs sélectionnée
(notez qu'un certain nombre de cartes de couleurs sont aussi sélectionnables
depuis le contrôle « Colormap » sous forme inversée).

Le contrôle « Rotate » peut servir à faire pivoter la carte de couleurs, tandis
que le bouton « Unrotate CMap » restaurera la rotation à son état par défaut, non
pivoté.

Le bouton « Color Defaults » réinitialisera tous les contrôles de mappage de
couleur aux valeurs par défaut : carte de couleurs « gray », intensité « ramp »
(linéaire), et aucune inversion ni rotation de la carte de couleurs.

**Préférences de contraste et de luminosité (bias)**

.. figure:: figures/contrast-prefs.png
   :width: 400px
   :align: center
   :alt: Préférences de contraste et de luminosité (bias)

   Préférences « Contrast and Brightness (Bias) ».

Les contrôles « Contrast » et « Brightness » définiront le contraste et la
luminosité (aussi appelée « bias ») du visualiseur.  Ils offrent une alternative
à 1) l'utilisation du mode contraste dans la fenêtre du visualiseur, ou 2) la
manipulation de la barre de couleurs par glissement (pour définir la
luminosité/bias) ou défilement (pour définir le contraste).

Les contrôles « Default Contrast » et « Default Brightness » ramènent leurs
paramètres respectifs à la valeur par défaut.

**Préférences de coupes automatiques**

.. figure:: figures/autocuts-prefs.png
   :width: 400px
   :align: center
   :alt: Préférences de coupes automatiques

   Préférences « Auto Cuts ».

Les préférences « Auto Cuts » contrôlent le calcul des niveaux de coupe pour la
vue lorsque le bouton ou la touche de niveaux de coupe automatiques est pressé,
ou lors du chargement d'une nouvelle image avec les coupes automatiques
activées.  Vous pouvez aussi définir les niveaux de coupe manuellement à partir
d'ici.

Les champs « Cut Low » et « Cut High » peuvent servir à spécifier manuellement
les niveaux de coupe inférieur et supérieur.  Appuyer sur « Cut Levels »
définira les niveaux à ces valeurs manuellement.  Si une valeur manque, on
suppose qu'elle prend par défaut la valeur actuelle.

Appuyer sur « Auto Levels » calculera les niveaux selon un algorithme.  Le
contrôle « Auto Method » sert à choisir quel algorithme de coupes automatiques
est utilisé : « minmax » (valeurs minimum maximum), « median » (basé sur le
filtrage médian), « histogram » (basé sur un histogramme de l'image), « stddev »
(basé sur l'écart-type des valeurs de pixel) ou « zscale » (basé sur l'algorithme
ZSCALE popularisé par IRAF).  À mesure que l'algorithme change, les cases en
dessous peuvent aussi changer pour permettre des modifications de paramètres
particuliers à chaque algorithme.

**Préférences de transformation**

.. figure:: figures/transform-prefs.png
   :width: 400px
   :align: center
   :alt: Préférences de transformation

   Préférences « Transform ».

Les préférences « Transform » permettent de transformer la vue de l'image en
retournant la vue en X ou Y, en échangeant les axes X et Y, ou en faisant pivoter
l'image de quantités arbitraires.

Les cases « Flip X » et « Flip Y » font que la vue de l'image est retournée dans
l'axe correspondant.

La case « Swap XY » fait que la vue de l'image est modifiée en échangeant les axes
X et Y.  Ceci peut être combiné avec « Flip X » et « Flip Y » pour faire pivoter
l'image par incréments de 90 degrés.  Ces vues seront rendues plus rapidement que
les rotations arbitraires utilisant le contrôle « Rotate ».

Le contrôle « Rotate » fera pivoter la vue de l'image de la quantité spécifiée.
La valeur doit être spécifiée en degrés.  « Rotate » peut être spécifié
conjointement avec le retournement et l'échange.

Le bouton « Restore » restaurera la vue à la vue par défaut, qui est non
retournée, non échangée et non pivotée.

**Préférences WCS**

.. figure:: figures/wcs-prefs.png
   :width: 400px
   :align: center
   :alt: Préférences WCS

   Préférences « WCS ».

Les préférences « WCS » contrôlent les préférences d'affichage des calculs du
Système de Coordonnées Mondial (WCS) utilisés pour rapporter la position du
curseur dans l'image.

Le contrôle « WCS Coords » sert à sélectionner le système de coordonnées dans
lequel afficher le résultat.

Le contrôle « WCS Display » sert à sélectionner un affichage sexagésimal
(``H:M:S``) ou un affichage en degrés décimaux.

**Préférences de zoom**

.. figure:: figures/zoom-prefs.png
   :width: 400px
   :align: center
   :alt: Préférences de zoom

   Préférences « Zoom ».

Les préférences « Zoom » contrôlent le comportement de zoom/mise à l'échelle de
Ginga.  Ginga prend en charge deux algorithmes de zoom, choisis à l'aide du
contrôle « Zoom Alg » :

* L'algorithme « step » zoome l'image vers l'intérieur par pas discrets de 1X,
  2X, 3X, etc. ou vers l'extérieur par pas de 1/2X, 1/3X, 1/4X, etc.  Cet
  algorithme produit visuellement le moins d'artefacts, mais est un peu plus lent
  pour zoomer sur de larges plages lorsqu'on utilise un mouvement de défilement,
  car plus de « course » est nécessaire pour obtenir un grand changement de zoom
  (ce n'est pas le cas si l'on utilise les touches de raccourci de zoom, comme
  les touches de chiffres).

* L'algorithme « rate » zoome l'image en faisant progresser la mise à l'échelle à
  un taux défini par la valeur de la case « Zoom Rate ».  Ce taux vaut par défaut
  la racine carrée de 2.  Des nombres plus grands entraînent des changements plus
  grands d'échelle entre les niveaux de zoom.  Si vous aimez zoomer vos images
  rapidement, au prix d'une petite perte de qualité d'image, vous voudriez
  probablement choisir cette option.

Notez que quelle que soit la méthode choisie pour l'algorithme de zoom, le zoom
peut être contrôlé en maintenant ``Ctrl`` (grossier) ou ``Shift`` (fin) enfoncé
pendant le défilement pour contraindre le taux de zoom (en supposant les
associations de souris par défaut).

Le contrôle « Stretch XY » peut servir à étirer l'un des axes (X ou Y) par rapport
à l'autre.  Sélectionnez un axe avec ce contrôle et faites rouler la molette de
défilement en survolant le contrôle « Stretch Factor » pour étirer les pixels
dans l'axe sélectionné.

Les contrôles « Scale X » et « Scale Y » offrent un accès direct à la mise à
l'échelle sous-jacente, en contournant les pas de zoom discrets.  Ici, des
valeurs exactes peuvent être saisies pour mettre l'image à l'échelle.
Inversement, vous verrez ces valeurs changer à mesure que l'image est zoomée.

Les contrôles « Scale Min » et « Scale Max » peuvent servir à placer une limite
sur la quantité dont l'image peut être mise à l'échelle.

Le contrôle « Interpolation » vous permet de choisir comment l'image sera
interpolée.  Selon les paquets de support installés, les choix suivants peuvent
être faits :

* « basic » est le plus proche voisin utilisant un algorithme intégré, celui-ci
  est toujours disponible, est raisonnablement rapide et est la valeur par
  défaut.
* « area »
* « bicubic »
* « lanczos »
* « linear »
* « nearest » est le plus proche voisin (utilisant un paquet de support)

Le bouton « Zoom Defaults » restaurera les contrôles aux valeurs par défaut de
Ginga.

**Préférences de panoramique (pan)**

.. figure:: figures/pan-prefs.png
   :width: 400px
   :align: center
   :alt: Préférences de panoramique

   Préférences « Pan ».

Les préférences « Pan » contrôlent le comportement de panoramique de Ginga.

Les contrôles « Pan X » et « Pan Y » offrent un accès direct pour définir la
position de panoramique dans l'image (la partie de l'image située au centre de la
fenêtre) -- vous pouvez les voir changer à mesure que vous vous déplacez dans
l'image.  Vous pouvez définir ces valeurs puis appuyer sur « Apply Pan » pour
vous déplacer à cette position exacte.

Si le contrôle « Pan Coord » est réglé sur « data », alors le panoramique est
contrôlé par les coordonnées de donnée dans l'image ; s'il est réglé sur « WCS »,
alors les valeurs affichées dans les contrôles « Pan X » et « Pan Y » seront des
coordonnées WCS (en supposant un WCS valide dans l'image).  Dans ce dernier cas,
le contrôle « WCS sexagesimal » peut être laissé décoché pour afficher/définir
les coordonnées en degrés, ou coché pour afficher/définir les valeurs en notation
sexagésimale standard.

Le bouton « Center Image » place la position de panoramique au centre de l'image,
calculé en divisant par deux les dimensions en X et Y.

La case « Mark Center », lorsqu'elle est cochée, fera que Ginga dessine un petit
réticule au centre de l'image.  Ceci est utile pour connaître la position de
panoramique et pour le débogage.

**Préférences générales**

.. figure:: figures/general-prefs.png
   :width: 400px
   :align: center
   :alt: Préférences générales

   Préférences « General ».

Le paramètre « Num Images » spécifie combien d'images peuvent être conservées dans
les tampons de ce canal avant d'être éjectées.  Une valeur de zéro (0) signifie
illimité -- les images ne seront jamais éjectées.  Si une image a été chargée
depuis un stockage accessible et qu'elle est éjectée, elle sera automatiquement
rechargée si l'image est revisitée en naviguant dans le canal.

Le paramètre « Sort Order » détermine si les images sont triées dans le canal par
ordre alphabétique par nom ou par l'heure à laquelle elles ont été chargées.
Ceci affecte principalement l'ordre dans lequel les images sont parcourues
lorsqu'on utilise les touches ou boutons « flèche » haut/bas, et pas
nécessairement la manière dont elles sont affichées dans des plugins comme
« Contents » ou « Thumbs » (qui ont généralement leur propre préférence de
paramètre pour l'ordre).

La case « Use scrollbars » contrôle si le visualiseur de canal affichera des
barres de défilement autour du bord du cadre du visualiseur pour déplacer
l'image.

**Préférences de réinitialisation (visualiseur)**

.. figure:: figures/reset-prefs.png
   :width: 400px
   :align: center
   :alt: Préférences de réinitialisation (visualiseur)

   Préférences « Reset » (visualiseur).

Chaque visualiseur de canal a un *profil de visualiseur* qui est initialisé à
l'état du visualiseur juste après la création et la restauration des paramètres
enregistrés pour ce canal.  Lors du basculement entre les images, les attributs
du visualiseur peuvent être réinitialisés à ce profil selon les cases cochées
dans cette section.  *Si rien n'est coché, rien ne sera réinitialisé à partir du
profil de visualiseur*.

Pour utiliser cette fonctionnalité, définissez vos préférences de visualiseur
comme vous le préférez et cliquez sur le bouton « Update Viewer Profile » en bas
du plugin.  Cochez maintenant quels éléments doivent être réinitialisés à ces
valeurs entre les images.  Enfin, cliquez sur le bouton « Save Settings » en bas
si vous voulez que ces paramètres soient persistants entre les redémarrages de
Ginga et définis comme le profil utilisateur par défaut pour ce canal lorsque
vous redémarrez ginga et recréez ce canal.

* « Reset Scale » réinitialisera le niveau de zoom (échelle) au profil de
  visualiseur
* « Reset Pan » réinitialisera la position de panoramique au profil de
  visualiseur
* « Reset Transform » réinitialisera toute transformation de
  retournement/échange au profil de visualiseur
* « Reset Rotation » réinitialisera toute rotation au profil de visualiseur
* « Reset Cuts » réinitialisera tout niveau de coupe au profil de visualiseur
* « Reset Distribution » réinitialisera toute distribution de couleur au profil
  de visualiseur
* « Reset Contrast » réinitialisera tout contraste/bias au profil de visualiseur
* « Reset Color Map » réinitialisera tout paramètre de carte de couleurs au
  profil de visualiseur

.. tip:: Si vous utilisez cette fonctionnalité, vous voudrez peut-être aussi
         définir « Remember (Image) Preferences » (voir ci-dessous).

.. note:: L'ordre complet des ajustements est :

          * tout élément de réinitialisation du profil de visualiseur par défaut,
            le cas échéant
          * tout élément mémorisé du profil d'image est appliqué, le cas échéant
          * tout ajustement automatique (cuts/zoom/center) est appliqué, s'il n'a
            pas été remplacé par un paramètre mémorisé

**Préférences de mémorisation (image)**

.. figure:: figures/remember-prefs.png
   :width: 400px
   :align: center
   :alt: Préférences de mémorisation (image)

   Préférences « Remember » (image).

Lorsqu'une image est chargée, un *profil d'image* est créé et attaché aux
métadonnées de l'image dans le canal.  Ces profils sont continuellement mis à
jour avec l'état du visualiseur à mesure que l'image est manipulée.  Les
préférences « Remember » contrôlent quels attributs de ces profils sont restaurés
à l'état du visualiseur lorsque l'image est (re)naviguée dans le canal :

* « Remember Scale » restaurera le niveau de zoom (échelle) de l'image
* « Remember Pan » restaurera la position de panoramique dans l'image
* « Remember Transform » restaurera toute transformation de retournement ou
  d'échange d'axes
* « Remember Rotation » restaurera toute rotation de l'image
* « Remember Cuts » restaurera tout niveau de coupe pour l'image
* « Remember Distribution » restaurera toute distribution de couleur (linear,
  log, etc.)
* « Remember Contrast » restaurera tout ajustement de contraste/bias
* « Remember Color Map » restaurera tout choix de carte de couleurs effectué

*Si rien n'est coché, rien ne sera restauré à partir du profil d'image*.

.. note:: Ces éléments seront définis AVANT que tout ajustement automatique
          (cut/zoom/center new) ne soit effectué.  Si un élément mémorisé est
          défini, il remplacera tout paramètre d'ajustement automatique pour le
          canal.

.. tip:: Si vous utilisez cette fonctionnalité, vous voudrez peut-être aussi
         définir « Reset (Viewer) Preferences » (voir ci-dessus).

***Un exemple***

Comme exemple d'utilisation des paramètres Reset et Remember, supposons que vous
utilisez fréquemment l'ajustement de contraste.  Vous aimeriez que le contraste
que vous définissez avec une image particulière soit restauré lorsque cette image
est revue.  Cependant, lorsque vous voyez une nouvelle image, vous aimeriez que
le contraste commence à un réglage normal.

Pour accomplir cela, réinitialisez manuellement le contraste au réglage par
défaut souhaité.  Cochez « Reset Contrast » puis appuyez sur « Update Viewer
Profile ».  Enfin, cochez « Remember Contrast ».  Cliquez sur « Save Settings »
pour rendre les paramètres du canal persistants.

**Préférences de nouvelle image**

.. figure:: figures/newimages-prefs.png
   :width: 400px
   :align: center
   :alt: Préférences de nouvelle image

   Préférences « New Image ».

Les préférences « New Images » déterminent comment Ginga réagit lorsqu'une
nouvelle image est chargée dans le canal.  *Cela inclut lorsqu'une image plus
ancienne est revisitée en cliquant sur sa vignette dans le plugin ``Thumbs`` ou
en double-cliquant sur son nom dans le plugin ``Contents``*.

Le paramètre « Cut New » contrôle si un calcul automatique de niveaux de coupe
doit être effectué sur la nouvelle image, ou si les niveaux de coupe actuellement
définis doivent être appliqués.  Les paramètres possibles sont :

* « off » : toujours utiliser les niveaux de coupe actuellement définis ;
* « once » : calculer de nouveaux niveaux de coupe pour la première image
  visitée, puis passer à « off » ;
* « override » : calculer de nouveaux niveaux de coupe jusqu'à ce que
  l'utilisateur les remplace en définissant manuellement des niveaux de coupe,
  puis passer à « off » ; ou
* « on » : toujours calculer de nouveaux niveaux de coupe.

.. tip:: Le paramètre « override » est fourni pour la commodité d'avoir des
         niveaux de coupe automatiques, tout en empêchant qu'une coupe définie
         manuellement soit remplacée lorsqu'une nouvelle image est ingérée.
         Lorsqu'on tape dans la fenêtre d'image, la touche point-virgule peut
         servir à basculer le mode de nouveau sur override (depuis « off »),
         tandis que les deux-points définiront la préférence sur « on ».  Le
         plugin ``Info`` (onglet : Synopsis) montre l'état de ce paramètre.

Le paramètre « Zoom New » contrôle si le fait de visiter une image doit définir le
niveau de zoom pour ajuster l'image à la fenêtre.  Les paramètres possibles sont :

* « off » : toujours utiliser les niveaux de zoom actuellement définis ;
* « once » : ajuster la première image à la fenêtre, puis passer à « off » ;
* « override » : les images sont automatiquement ajustées jusqu'à ce que le niveau
  de zoom soit changé manuellement, puis le mode passe automatiquement à
  « off » ; ou
* « on » : la nouvelle image est toujours zoomée pour s'ajuster.

.. tip:: Le paramètre « override » est fourni pour la commodité d'avoir un zoom
         automatique, tout en empêchant qu'un niveau de zoom défini manuellement
         soit remplacé lorsqu'une nouvelle image est ingérée.  Lorsqu'on tape dans
         la fenêtre d'image, la touche apostrophe (aussi « guillemet simple »)
         peut servir à basculer le mode de nouveau sur « override » (depuis
         « off »), tandis que le guillemet (aussi « guillemet double ») définira
         la préférence sur « on ».  Le plugin ``Info`` (onglet : Synopsis) montre
         l'état de ce paramètre.

Le paramètre « Center New » contrôle si le fait de visiter une image doit faire
que la position de panoramique soit réinitialisée au centre de l'image.  Les
paramètres possibles sont :

* « off » : laisser la position de panoramique actuelle telle quelle ;
* « once » : centrer la première image visitée, puis passer à « off » ;
* « override » : les images sont automatiquement centrées jusqu'à ce que la
  position de panoramique soit changée manuellement, puis le mode passe
  automatiquement à « off » ; ou
* « on » : la nouvelle image est toujours centrée.

Le paramètre « Follow New » sert à contrôler si Ginga changera l'affichage si une
nouvelle image est chargée dans le canal.  Si décoché, l'image est chargée (comme
on le voit, par exemple, par son apparition dans l'onglet ``Thumbs``), mais
l'affichage ne changera pas pour la nouvelle image.  Ce paramètre est utile dans
les cas où de nouvelles images sont chargées par un moyen automatisé dans un
canal et que l'utilisateur souhaite étudier l'image actuelle sans être
interrompu.

Le paramètre « Raise New » contrôle si Ginga élèvera l'onglet d'un canal lorsqu'une
image est chargée dans ce canal.  Si décoché, alors Ginga n'élèvera pas l'onglet
lorsqu'une image est chargée dans ce canal particulier.

Le paramètre « Create Thumbnail » contrôle si Ginga créera une vignette pour les
images chargées dans ce canal.  Dans les cas où de nombreuses images sont
chargées fréquemment dans un canal (p. ex. un flux vidéo à basse fréquence), il
peut être indésirable de créer des vignettes pour toutes.

Le paramètre « Auto Orient » contrôle si Ginga doit tenter d'orienter les images
par défaut selon les métadonnées de l'image.  Ceci n'est actuellement utile que
pour les images RGB (p. ex. JPEG) qui contiennent de telles métadonnées.  Il
n'oriente pas automatiquement par WCS, pour le moment.

**Préférences des profils ICC**

.. figure:: figures/icc-prefs.png
   :width: 400px
   :align: center
   :alt: Préférences des profils ICC

   Préférences « ICC Profiles ».

Ginga peut utiliser des profils ICC (gestion des couleurs) dans la chaîne de
rendu à l'aide de la bibliothèque LittleCMS.

.. note:: Pour utiliser des profils ICC, créez un dossier « profiles » dans le
          « home » de Ginga (généralement $HOME/.ginga) et placez-y tous les
          profils nécessaires.  Un profil de travail doit être défini en ajoutant
          une valeur pour « icc_working_profile » dans votre fichier
          $HOME/.ginga/general.cfg -- n'incluez aucun chemin en tête, juste le
          nom de fichier d'un fichier ICC dans le dossier profiles.  Ceci sera
          utilisé pour convertir tout fichier RGB contenant un profil vers le
          profil de travail.

Vous pouvez définir les profils de sortie pour n'importe quel canal dans cette
section du plugin Preferences.

Le contrôle « Output ICC profile » sélectionne quel profil utiliser pour le rendu
de sortie vers l'affichage.  Les choix proviennent de vos fichiers de profil dans
$HOME/.ginga/profiles.  Normalement, cela devrait être un profil d'affichage.

Le contrôle « Rendering intent » choisit l'algorithme utilisé pour rendre la
couleur dans le processus de conversion ICC.  Les choix sont :

* absolute_colorimetric
* perceptual
* relative_colorimetric
* saturation

« Proof ICC profile » et « Proof intent » sont choisis de manière similaire pour
l'épreuvage.

La case « Black point compensation » active ou désactive cette fonctionnalité dans
le processus de conversion des couleurs.  Voir la documentation de LittleCMS ou
de la gestion des couleurs ICC en général pour les détails sur ces choix.
