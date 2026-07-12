Le plugin ``SAMP`` implémente une interface SAMP pour le visualiseur de
référence Ginga.

.. note:: Pour exécuter ce plugin, vous devez installer ``astropy`` qui
          possède le module ``samp``.

**Type de plugin : Global**

``SAMP`` est un plugin global.  Une seule instance peut être ouverte.

**Utilisation**

Ginga inclut un plugin pour activer la prise en charge de SAMP (Simple
Applications Messaging Protocol).  Avec la prise en charge de SAMP, Ginga peut
être contrôlé et interagir avec d'autres applications astronomiques de bureau.

Le module ``SAMP`` n'est pas démarré par défaut.  Pour le démarrer au lancement
de Ginga, spécifiez l'option de ligne de commande::

        --modules=SAMP

Sinon, démarrez-le en utilisant « Démarrer un hub SAMP » depuis le menu
« Plugins ».

Actuellement, la prise en charge de SAMP est limitée aux messages
``image.load.fits``, ce qui signifie que Ginga chargera un fichier FITS s'il
reçoit l'un de ces messages.

Le plugin ``SAMP`` de Ginga utilise le module ``astropy.samp``, vous devrez donc
avoir ``astropy`` installé pour utiliser le plugin.  Par défaut, le plugin
``SAMP`` de Ginga tentera de démarrer un hub SAMP s'il n'en trouve pas en cours
d'exécution.
