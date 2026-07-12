Un plugin pour dessiner des formes sur le canevas (graphiques superposés).

**Type de plugin : Local**

``Drawing`` est un plugin local, ce qui signifie qu'il est associé à un canal.
Ce n'est pas un singleton, ce qui signifie que plusieurs instances peuvent être
ouvertes pour chaque canal.

**Utilisation**

Ce plugin peut servir à dessiner de nombreuses formes différentes sur
l'affichage de l'image.  En mode « dessiner », sélectionnez une forme dans le
menu déroulant, ajustez les paramètres de la forme (si nécessaire) et dessinez
sur l'image à l'aide du bouton gauche de la souris.  Vous pouvez choisir de
dessiner dans l'espace pixel ou WCS.

Pour déplacer ou modifier une forme existante, mettez le plugin en mode
« modifier » ou « déplacer », respectivement.

Pour enregistrer les formes dessinées en tant qu'image de masque, cliquez sur le
bouton « Créer un masque » et vous verrez une nouvelle image de masque créée
dans Ginga.  Utilisez ensuite le plugin ``SaveImage`` pour l'enregistrer en FITS
à extension unique.  Notez que le masque prendra la taille de l'image affichée.
Par conséquent, pour créer des masques de dimensions d'image différentes, vous
devez répéter les étapes plusieurs fois.

Les formes dessinées sur le canevas peuvent être chargées et/ou enregistrées au
format astropy-regions (compatible avec les régions DS9).  Pour l'utiliser, vous
devez avoir installé le paquet astropy-regions.  Dessinez simplement des objets
sur le canevas, avec des coordonnées « data » (pixel) ou « wcs ».  Notez que
tous les objets de canevas de Ginga ne peuvent pas être convertis en formes de
régions et que certains attributs peuvent ne pas être enregistrés, être ignorés
ou provoquer des erreurs lors du chargement des formes de régions dans d'autres
logiciels.
