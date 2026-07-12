``Ruler`` est un plugin simple conçu pour mesurer des distances sur une image.

**Type de plugin : Local**

``Ruler`` est un plugin local, ce qui signifie qu'il est associé à un canal.
Ce n'est pas un singleton, ce qui signifie que plusieurs instances peuvent être
ouvertes pour chaque canal.

**Utilisation**

``Ruler`` mesure la distance en calculant une triangulation sphérique via le
mappage WCS de trois points définis par une seule ligne tracée sur l'image.  Par
défaut, la distance est affichée en minutes d'arc de ciel, mais à l'aide du
contrôle « Unités », elle peut être modifiée pour afficher des degrés ou une
distance en pixels à la place.

Cliquez et faites glisser pour établir une règle entre deux points.  Lorsque
vous terminez l'opération de dessin, la règle est établie et l'interface du
plugin se met à jour pour afficher des détails sur la ligne, y compris les
positions des extrémités et l'angle de la ligne.  Les unités de l'angle peuvent
être basculées entre degrés et radians à l'aide de la liste déroulante
adjacente.

Pour effacer l'ancienne règle et en créer une nouvelle, cliquez et faites
glisser à nouveau.  Lorsqu'une autre ligne est tracée, elle remplace la
première.  Lorsque le plugin est fermé, la superposition graphique est
supprimée.  Si vous voulez des « règles persistantes », utilisez le plugin
``Drawing`` (et choisissez « Ruler » comme type de dessin).

**Modification**

Pour modifier une règle existante, cliquez sur le bouton radio de l'interface du
plugin intitulé « Modifier ».  Si la règle n'est pas sélectionnée
immédiatement, cliquez sur la diagonale reliant les deux points.  Cela devrait
établir un cadre englobant autour de la règle et afficher ses points de
contrôle.  Faites glisser à l'intérieur du cadre englobant pour déplacer la
règle, ou cliquez et faites glisser les extrémités pour modifier la règle.  La
règle peut aussi être mise à l'échelle ou pivotée à l'aide de ces points de
contrôle.

**Interface**

Les unités affichées pour la distance peuvent être sélectionnées dans la liste
déroulante de l'interface.  Vous avez le choix entre « arcmin », « degrees » ou
« pixels ».  Les deux premières nécessitent un WCS valide et fonctionnel dans
l'image.

Les valeurs des extrémités sont affichées dans l'interface, mais peuvent en
outre être affichées dans le graphique de la règle si la case « Afficher les
extrémités » est cochée.  Des lignes de plomb seront affichées si la case
« Afficher le plomb » est cochée.

**Boutons**

Le bouton « Recentrer sur la source » recentrera l'image principale sur
l'origine de la ligne tracée, tandis que « Recentrer sur la destination »
recentrera sur la fin.  « Recentrer sur le centre » place la position de
recentrage au point central de la ligne.  Ces boutons peuvent être utiles pour
un travail rapproché et zoomé sur l'image.  « Effacer » efface la règle de
l'image.

**Astuces**
Ouvrez le plugin « Zoom » pour voir précisément le détail de la zone du curseur.
Le plugin « Pick » peut aussi être utilisé conjointement avec Ruler pour
identifier le point central d'un objet, lors de l'alignement de l'une ou l'autre
extrémité de la règle.
