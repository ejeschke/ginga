Enregistrer des images dans des fichiers de sortie.

**Type de plugin : Global**

``SaveImage`` est un plugin global.  Une seule instance peut être ouverte.

**Utilisation**

Ce plugin global sert à enregistrer dans des images de sortie toute
modification effectuée dans Ginga.  Par exemple, une image mosaïque créée par le
plugin ``Mosaic``.  Actuellement, seules les images FITS (à une ou plusieurs
extensions) sont prises en charge.

Étant donné le répertoire de sortie (p. ex. ``/mypath/outputs/``), un suffixe
(p. ex. ``ginga``), un canal d'image (``Image``) et une image sélectionnée
(p. ex. ``image1.fits``), le fichier de sortie sera
``/mypath/outputs/image1_ginga_Image.fits``.  L'inclusion du nom du canal est
facultative et peut être omise via le fichier de configuration du plugin,
``plugin_SaveImage.cfg``.
Les extensions modifiées auront le nouvel en-tête ou les nouvelles données
extraits de Ginga, tandis que celles non modifiées resteront intactes.  Les
entrées de journal des modifications pertinentes du plugin global
``ChangeHistory`` seront insérées dans l'historique de son en-tête ``PRIMARY``.

.. note:: Ce plugin utilise le module ``astropy.io.fits`` pour écrire les images
          de sortie, quel que soit le choix de ``FITSpkg`` dans le fichier de
          configuration ``general.cfg``.
