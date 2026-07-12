Lire un diaporama d'images.

**Type de plugin : Local**

``SlideShow`` est un plugin local, ce qui signifie qu'il est associé à un
canal.  Ce n'est pas un singleton, ce qui signifie que plusieurs instances
peuvent être ouvertes pour chaque canal.

**Utilisation**

***Charger un diaporama***

Après le démarrage du plugin, vous pouvez utiliser le bouton « Charger » pour
charger un diaporama (voir ci-dessous le format de fichier du diaporama).  Vous
pouvez ensuite recharger ce diaporama à tout moment après avoir modifié le
fichier en externe en appuyant sur « Recharger ».

***Lire un diaporama***

Les boutons « Précédent » et « Suivant » peuvent servir à reculer et avancer
manuellement dans la liste.  Le bouton de sélection numérique entre ces deux
boutons vous amènera à une diapositive particulière dans la liste.

Les boutons « Démarrer » et « Arrêter » servent à démarrer ou arrêter
l'avancement automatique dans le diaporama.

***Contrôler la durée***

Chaque diapositive peut avoir un paramètre « duration » distinct (en secondes)
pour contrôler le temps avant de passer à la diapositive suivante, mais s'il
est absent pour une diapositive, la durée par défaut est utilisée.  La durée
par défaut peut être définie à l'aide du contrôle intitulé « Durée par
défaut ».

Sous le contrôle de durée par défaut se trouve une étiquette qui affiche la
durée de la diapositive et la durée totale du diaporama.

**Format de fichier du diaporama**

Le format de fichier du diaporama est un fichier texte brut séparé par des
virgules (CSV) avec une ligne d'en-tête.  Le fichier doit contenir au moins une
colonne, intitulée « file ».  Cette colonne contient les noms de fichiers
(relatifs ou absolus) des chemins vers les fichiers à charger pour chaque
diapositive.

***Colonnes facultatives***

* « duration » :  doit contenir la durée (en secondes) pour chaque diapositive
* « position » : indique la position de la diapositive dans le diaporama.
  Des nombres à virgule flottante peuvent être utilisés pour faciliter la
  réorganisation des diapositives lors de la modification du fichier du
  diaporama.
