Effectuer une analyse stellaire astronomique rapide.

**Type de plugin : Local**

``Pick`` est un plugin local, ce qui signifie qu'il est associé à un canal.
Ce n'est pas un singleton, ce qui signifie que plusieurs instances peuvent être
ouvertes pour chaque canal.

**Utilisation**

Le plugin ``Pick`` sert à effectuer une analyse rapide de la qualité des données
astronomiques d'objets stellaires.  Il localise des candidats stellaires dans
une boîte dessinée et choisit le candidat le plus probable en fonction d'un
ensemble de paramètres de recherche.  La largeur à mi-hauteur (FWHM) est
rapportée pour l'objet candidat, ainsi que sa taille en fonction de l'échelle de
plaque du détecteur.  Une mesure approximative du fond, du niveau de ciel et de
la luminosité est aussi effectuée.

**Définir la zone de sélection**

La zone de sélection par défaut est définie comme une boîte d'environ 30x30
pixels qui englobe la zone de recherche.

Le sélecteur déplacer/dessiner/modifier en bas du plugin sert à déterminer
quelle opération est effectuée sur la zone de sélection :

.. figure:: figures/pick-move-draw-edit.png
   :width: 400px
   :align: center
   :alt: Boutons Déplacer, Dessiner et Modifier

   Boutons « Déplacer », « Dessiner » et « Modifier ».

* Si « déplacer » est sélectionné, vous pouvez déplacer la zone de sélection
  existante en la faisant glisser ou en cliquant à l'endroit où vous voulez
  placer son centre.  S'il n'y a pas de zone existante, une zone par défaut sera
  créée.
* Si « dessiner » est sélectionné, vous pouvez dessiner une forme avec le curseur
  pour englober et définir une nouvelle zone de sélection.  La forme par défaut
  est une boîte, mais d'autres formes peuvent être sélectionnées dans l'onglet
  « Settings ».
* Si « modifier » est sélectionné, vous pouvez modifier la zone de sélection en
  faisant glisser ses points de contrôle, ou la déplacer en faisant glisser dans
  le cadre englobant.

Après que la zone a été déplacée, dessinée ou modifiée, ``Pick`` recherchera
dans la zone tous les pics et évaluera les pics selon les critères de l'onglet
« Settings » de l'interface (voir « L'onglet Settings » ci-dessous) et essaiera
de localiser le meilleur candidat correspondant aux paramètres.

.. note:: les cases « Quick Mode » et « From Peak » ont été supprimées dans la
          version v4.0 de Ginga.

**Si un candidat est trouvé**

Le candidat sera marqué d'un point (généralement un « X ») dans le canevas du
visualiseur de canal, centré sur l'objet tel que déterminé par les mesures FWHM
horizontale et verticale.

L'ensemble supérieur d'onglets de l'interface sera rempli comme suit :

.. figure:: figures/pick-cutout.png
   :width: 400px
   :align: center
   :alt: Onglet Image de la zone de Pick

   Onglet « Image » de la zone de ``Pick``.

L'onglet « Image » montrera le contenu de la zone de découpe.  Le widget de cet
onglet est un widget Ginga et peut donc être zoomé et déplacé avec les
associations habituelles de clavier et de souris (p. ex. molette de
défilement).  Il sera aussi marqué d'un point centré sur l'objet et, de plus, la
position de recentrage sera définie sur le centre trouvé.

.. figure:: figures/pick-contour.png
   :width: 300px
   :align: center
   :alt: Onglet Contour de la zone de Pick

   Onglet « Contour » de la zone de ``Pick``.

L'onglet « Contour » montrera un tracé de contour.  Il s'agit d'un tracé de
contour de la zone immédiatement autour du candidat, et n'englobant généralement
pas toute la région de la zone de sélection.  Vous pouvez utiliser la molette de
défilement pour zoomer le tracé et un clic de la molette de défilement (bouton 2
de la souris) pour définir la position de recentrage dans le tracé.

.. figure:: figures/pick-fwhm.png
   :width: 400px
   :align: center
   :alt: Onglet FWHM de la zone de Pick

   Onglet « FWHM » de la zone de ``Pick``.

L'onglet « FWHM » montrera un tracé FWHM.  Les lignes violettes montrent les
mesures dans la direction X et les lignes vertes montrent les mesures dans la
direction Y.  Les lignes continues indiquent les valeurs de pixel réelles et les
lignes pointillées indiquent la fonction 1D ajustée.  Les régions ombrées
violette et verte indiquent les mesures FWHM pour les axes respectifs.

.. figure:: figures/pick-radial.png
   :width: 400px
   :align: center
   :alt: Onglet Radial de la zone de Pick

   Onglet « Radial » de la zone de ``Pick``.

L'onglet « Radial » contient un tracé de profil radial.  Les points tracés en
violet sont des valeurs de données, et une ligne est ajustée aux données.

.. figure:: figures/pick-ee.png
   :width: 600px
   :align: center
   :alt: Onglet EE de la zone de Pick

   Onglet « EE » de la zone de ``Pick``.

L'onglet « EE » contient un tracé des énergies fractionnaires encerclées et
encadrées (EE) en violet et vert, respectivement, pour la cible choisie.  Une
soustraction de fond simple est effectuée d'une manière cohérente avec les
calculs FWHM avant que les valeurs EE ne soient mesurées.  Les rayons
d'échantillonnage et total, montrés en lignes noires en tirets, peuvent être
définis dans l'onglet « Settings » ; lorsqu'ils sont modifiés, cliquez sur
« Redo Pick » pour mettre à jour le tracé et les mesures.  Les valeurs EE
mesurées au rayon d'échantillonnage donné sont aussi affichées dans l'onglet
« Readout ».  Lorsqu'un rapport est demandé, les valeurs EE au rayon
d'échantillonnage donné et le rayon lui-même seront enregistrés dans la table
« Report », avec d'autres informations.

Lorsque « Show Candidates » est actif, les candidats près des bords du cadre
englobant n'auront pas de valeurs EE (fixées à 0).

.. figure:: figures/pick-readout.png
   :width: 400px
   :align: center
   :alt: Onglet Readout de la zone de Pick

   Onglet « Readout » de la zone de ``Pick``.

L'onglet « Readout » sera rempli d'un résumé des mesures.  Il y a deux boutons et
trois cases à cocher dans cet onglet :

* Le bouton « Default Region » restaure la région de sélection à la forme et à la
  taille par défaut.
* Le bouton « Pan to pick » recentrera le visualiseur de canal sur le centre
  localisé.
* Si « Center on pick » est coché, la forme sera recentrée sur le centre
  localisé, s'il est trouvé (c.-à-d. que la forme « suit » la sélection).

.. figure:: figures/pick-controls.png
   :width: 400px
   :align: center
   :alt: Onglet Controls de la zone de Pick

   Onglet « Controls » de la zone de ``Pick``.

L'onglet « Controls » a quelques boutons qui fonctionneront à partir des mesures.

* Le bouton « Bg cut » définira le niveau de coupe bas du visualiseur de canal
  sur le niveau de fond mesuré.  Un delta à cette valeur peut être appliqué en
  définissant une valeur dans la case « Delta bg » (appuyez sur « Enter » pour
  changer le paramètre).
* Le bouton « Sky cut » définira le niveau de coupe bas du visualiseur de canal
  sur le niveau de ciel mesuré.  Un delta à cette valeur peut être appliqué en
  définissant une valeur dans la case « Delta sky » (appuyez sur « Enter » pour
  changer le paramètre).
* Le bouton « Bright cut » définira le niveau de coupe haut du visualiseur de
  canal sur les niveaux mesurés de ciel+luminosité.  Un delta à cette valeur peut
  être appliqué en définissant une valeur dans la case « Delta bright » (appuyez
  sur « Enter » pour changer le paramètre).

.. figure:: figures/pick-report.png
   :width: 400px
   :align: center
   :alt: Onglet Report de la zone de Pick

   Onglet « Report » de la zone de ``Pick``.

L'onglet « Report » sert à enregistrer des informations sur les mesures sous
forme de tableau.

En appuyant sur le bouton « Add Pick », les informations sur le candidat le plus
récent sont ajoutées à la table.  Si la case « Record Picks automatically » est
cochée, alors tous les candidats sont ajoutés à la table automatiquement.

.. note:: Si la case « Show Candidates » de l'onglet « Settings » est cochée,
          alors *tous* les objets trouvés dans la région (selon les paramètres)
          seront ajoutés à la table au lieu du seul candidat sélectionné.

Vous pouvez effacer la table à tout moment en appuyant sur le bouton « Clear
Log ».  Le journal peut être enregistré dans une table en mettant un chemin et
un nom de fichier valides dans la case « File: » et en appuyant sur « Save
table ».  Le type de fichier est déterminé automatiquement par l'extension
donnée (p. ex. « .fits » est FITS et « .txt » est du texte brut).

**Si aucun candidat n'est trouvé**

Si aucun candidat ne peut être trouvé (selon les paramètres), alors la zone de
sélection est marquée d'un point rouge centré sur la zone de sélection.

.. figure:: figures/pick-no-candidate.png
   :width: 800px
   :align: center
   :alt: Marqueur lorsqu'aucun candidat n'est trouvé

   Marqueur lorsqu'aucun candidat n'est trouvé.

La découpe d'image sera prise dans cette zone centrale et donc l'onglet « Image »
aura toujours du contenu.  Il sera aussi marqué d'un « X » rouge central.

Le tracé de contour sera toujours produit à partir de la découpe.

.. figure:: figures/pick-contour-no-candidate.png
   :width: 400px
   :align: center
   :alt: Contour lorsqu'aucun candidat n'est trouvé.

   Contour lorsqu'aucun candidat n'est trouvé.

Tous les autres tracés seront effacés.

**L'onglet Settings**

.. figure:: figures/pick-settings.png
   :width: 400px
   :align: center
   :alt: Onglet Settings du plugin Pick

   Onglet « Settings » du plugin ``Pick``.

L'onglet « Settings » contrôle les aspects de la recherche dans la zone de
sélection :

* La case « Show Candidates » contrôle si toutes les sources détectées sont
  marquées ou non (comme montré dans la figure ci-dessous).  De plus, si elle est
  cochée, tous les objets trouvés sont ajoutés à la table de journal de sélection
  lors de l'utilisation des contrôles « Report ».
* Le paramètre « Draw type » sert à choisir la forme de la zone de sélection à
  dessiner.
* Le paramètre « Radius » définit le rayon à utiliser lors de la recherche et de
  l'évaluation des pics brillants dans l'image.
* Le paramètre « Threshold » sert à définir un seuil pour la recherche de pics ;
  s'il est fixé à « None », une valeur par défaut raisonnable sera choisie.
* Les paramètres « Min FWHM » et « Max FWHM » peuvent servir à éliminer des
  objets de certaines tailles d'être candidats.
* Le paramètre « Ellipticity » sert à éliminer des candidats en fonction de leur
  asymétrie de forme.
* Le paramètre « Edge » sert à éliminer des candidats en fonction de leur
  proximité au bord de la découpe.  *NOTE : actuellement, cela fonctionne de
  manière fiable seulement pour les formes rectangulaires non pivotées.*
* Le paramètre « Max side » sert à limiter la taille du cadre englobant qui peut
  être utilisé dans la forme de sélection.  Les plus grandes tailles prennent
  plus de temps à évaluer.
* Le paramètre « Coordinate Base » est un décalage à appliquer aux sources
  localisées.  Fixez-le à « 1 » si vous voulez que les emplacements pixel des
  sources soient rapportés d'une manière conforme à FITS et « 0 » si vous
  préférez l'indexation basée sur 0.
* Le paramètre « Calc center » sert à déterminer si le centre est calculé à
  partir de l'ajustement FWHM (« fwhm ») ou du centroïde (« centroid »).
* Le paramètre « FWHM fitting » sert à déterminer quelle fonction est utilisée
  pour l'ajustement FWHM (« gaussian » ou « moffat »).  L'option d'utiliser
  « lorentz » est aussi disponible si « calc_fwhm_lib » est fixé à « astropy »
  dans ``~/.ginga/plugin_Pick.cfg``.
* Le paramètre « Contour Interpolation » sert à définir la méthode
  d'interpolation utilisée pour le rendu de l'image de fond dans le tracé
  « Contour ».
* Le « EE total radius » définit le rayon (pour l'énergie encerclée) et la
  demi-largeur de boîte (pour l'énergie encadrée) en pixels où la fraction EE est
  censée être 1 (c.-à-d. que tout le flux d'une fonction d'étalement de point est
  contenu à l'intérieur).
* Le « EE sampling radius » est le rayon en pixels utilisé pour échantillonner
  les courbes EE mesurées pour le rapport.

Le bouton « Redo Pick » refera l'opération de recherche.  Il est pratique si vous
avez changé certains paramètres et voulez voir l'effet basé sur la zone de
sélection actuelle sans la perturber.

.. figure:: figures/pick-candidates.png
   :width: 600px
   :align: center
   :alt: Le visualiseur de canal lorsque « Show Candidates » est coché.

   Le visualiseur de canal lorsque « Show Candidates » est coché.

**Configuration de l'utilisateur**

Il est personnalisable à l'aide de ``~/.ginga/plugin_Pick.cfg``, où ``~`` est
votre répertoire HOME :

.. code-block:: Python

  #
  # Pick plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_Pick.cfg"

  color_pick = 'green'
  shape_pick = 'box'
  color_candidate = 'purple'

  # Offset to add to Pick results. Default is 1.0 for FITS like indexing,
  # set to 0.0 here if you prefer numpy-like 0-based indexing
  pixel_coords_offset = 0.0

  # Maximum side for a pick region
  max_side = 1024

  # For image cutout viewer ("Image" tab)
  # you can set autozoom and autocuts preferences
  cutout_autozoom = 'override'
  cutout_autocuts = 'off'

  # For contour plot ("Contour" tab)
  # widget type: let choose automatically or force 'ginga' or 'matplotlib'
  # (choice of 'ginga' requires scikit-image to be installed)
  contour_widget = 'choose'
  # if ginga widget is chosen, you can set autozoom and autocuts preferences
  contour_autozoom = 'override'
  contour_autocuts = 'override'
  num_contours = 8
  # How big of a radius are we willing to consider from the center of the
  # pick?  bigger numbers == slower
  contour_size_min = 10
  contour_size_limit = 70

  # should the pick shape recenter on the found object center, if any?
  # useful for "tracking" an object that is moving from image to image
  center_on_pick = False

  # Star candidate search parameters
  radius = 10
  # Set threshold to None to auto calculate it
  threshold = None
  # Minimum and maximum fwhm to be considered a candidate
  min_fwhm = 1.5
  max_fwhm = 50.0
  # Minimum ellipticity to be considered a candidate
  min_ellipse = 0.5
  # Percentage from edge to be considered a candidate
  edge_width = 0.01
  # Graphically indicate all possible considered candidates
  show_candidates = False

  # Center of object is based on FWHM ("fwhm") or centroid ("centroid")
  # calculation:
  calc_center_alg = 'centroid'

  # Library to use for FWHM fitting ("native" or "astropy")
  calc_fwhm_lib = 'native'

  # Fitting function to use for FWHM ("gaussian" or "moffat")
  calc_fwhm_alg = 'gaussian'

  # Defaults for delta cut levels (in Controls tab)
  delta_sky = 0.0
  delta_bright = 0.0

  # Encircled and ensquared energy (EE) calculations:
  # a. Radius (pixel) where EE fraction is expected to be 1.
  ee_total_radius = 10.0
  # b. Radius (pixel) to sample EE for reporting.
  ee_sampling_radius = 2.5

  # use a different color/intensity map than channel image?
  pick_cmap_name = None
  pick_imap_name = None

  # For Reports tab
  record_picks = True

  # Set this to a file name, if None a filename will be automatically chosen
  report_log_path = None
