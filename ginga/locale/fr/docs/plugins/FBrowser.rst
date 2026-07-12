Un plugin pour parcourir le système de fichiers local et charger des fichiers.

**Type de plugin : Global ou Local**

``FBrowser`` est un plugin hybride global/local, ce qui signifie qu'il peut être
invoqué de l'une ou l'autre façon.  Invoqué comme plugin local, il est associé à
un canal, et une instance peut être ouverte pour chaque canal.  Il peut aussi
être ouvert comme plugin global.

**Utilisation**

Parcourez l'arborescence des répertoires jusqu'à l'emplacement des fichiers que
vous souhaitez charger.  Vous pouvez double-cliquer sur un fichier pour le
charger dans le canal associé, ou faire glisser un fichier vers une fenêtre de
visualiseur de canal pour le charger dans n'importe quel visualiseur de canal.

Plusieurs fichiers peuvent être sélectionnés en maintenant ``Ctrl`` (``Command``
sur Mac), ou en faisant ``Shift``-clic pour sélectionner une plage contiguë de
fichiers.

Vous pouvez aussi saisir le chemin complet des images souhaitées dans la zone de
texte, par exemple ``/mon/chemin/vers/image.fits``,
``/mon/chemin/vers/image.fits[ext]`` ou
``/mon/chemin/vers/image*.fits[extname,*]``.

Comme c'est un plugin local, ``FBrowser`` mémorise son dernier répertoire s'il
est fermé puis redémarré.
