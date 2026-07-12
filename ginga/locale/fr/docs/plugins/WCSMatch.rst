``WCSMatch`` est un plugin global pour le visualiseur d'images Ginga qui vous
permet d'aligner grossièrement des images d'échelles et d'orientations
différentes à des fins de visualisation, en utilisant le système de coordonnées
mondial (WCS) des images.

**Type de plugin : Global**

``WCSMatch`` est un plugin global.  Une seule instance peut être ouverte.

**Utilisation**

Pour l'utiliser, démarrez simplement le plugin et, depuis son interface,
sélectionnez un canal dans le menu déroulant « Canal de référence ».  L'image
contenue dans ce canal servira de référence pour synchroniser les images des
autres canaux.

Les canaux seront synchronisés en visualisation (panoramique, échelle (zoom),
transformations (retournements) et rotation).  Les cases « Aligner le
panoramique », « Aligner l'échelle », « Aligner les transformations » et
« Aligner la rotation » peuvent être cochées ou non pour contrôler quels
attributs sont synchronisés entre les canaux.

Pour « déverrouiller » complètement la synchronisation, sélectionnez simplement
« None » dans le menu déroulant « Canal de référence ».

Actuellement, il n'existe aucun moyen de limiter les canaux affectés par le
plugin.
