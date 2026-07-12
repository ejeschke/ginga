
Le plugin ``Info`` fournit un panneau de métadonnées couramment utiles sur
l'image du canal focalisé.  Les informations courantes comprennent certaines
valeurs d'en-tête de métadonnées, des coordonnées, les dimensions de l'image, les
valeurs minimale et maximale, etc.  À mesure que le curseur est déplacé sur
l'image, les valeurs X, Y, Value, RA et DEC sont mises à jour pour refléter la
valeur sous le curseur.

**Type de plugin : Global**

``Info`` est un plugin global.  Une seule instance peut être ouverte.

**Utilisation**

En bas de l'interface ``Info`` se trouvent les contrôles de distribution de
couleur et de niveaux de coupe.  Le sélecteur au-dessus des cases de niveaux de
coupe vous permet de choisir parmi plusieurs algorithmes de distribution qui
mappent les valeurs de l'image à la carte de couleurs.  Les choix sont
« linear », « log », « power », « sqrt », « squared », « asinh », « sinh » et
« histeq » (égalisation d'histogramme).

En dessous, les niveaux de coupe bas et haut sont affichés et peuvent être
ajustés.  Appuyer sur le bouton « Auto Levels » recalculera les niveaux de coupe
en fonction de l'algorithme actuel de niveaux de coupe automatiques et des
paramètres définis dans les préférences du canal.

Sous le bouton « Auto Levels », l'état des paramètres de « Cut New », « Zoom
New » et « Center New » est affiché pour le canal actuellement actif.  Ceux-ci
indiquent comment les nouvelles images ajoutées au canal seront affectées par les
niveaux de coupe automatiques, l'ajustement à la fenêtre et le recentrage sur le
centre de l'image.

La case « Follow New » contrôle si le visualiseur affichera automatiquement les
nouvelles images ajoutées au canal.  La case « Raise New » contrôle si une
fenêtre de visualiseur d'image est élevée lorsqu'une nouvelle image est ajoutée.
Ces deux contrôles peuvent être utiles, par exemple, si un programme externe
ajoute des images au visualiseur, et que vous souhaitez éviter l'interruption de
votre travail lors de l'examen d'une image particulière.

En tant que plugin global, ``Info`` répond à un changement de focus vers un
nouveau canal en affichant les métadonnées du nouveau canal.  Il apparaît
généralement sous l'onglet « Synopsis » dans l'interface utilisateur.

Ce plugin n'est généralement pas configuré pour être fermable, mais
l'utilisateur peut le rendre tel en définissant le paramètre « closeable » sur
True dans le fichier de configuration -- des boutons Fermer et Aide seront alors
ajoutés en bas de l'interface.
