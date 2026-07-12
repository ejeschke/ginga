Le plugin ``LoaderConfig`` vous permet de configurer les ouvreurs de fichiers
qui peuvent servir à charger divers contenus dans Ginga.

Les ouvreurs de fichiers enregistrés sont associés à des types MIME de fichier,
et il peut y avoir plusieurs ouvreurs pour un seul type MIME.  Une priorité
associée à un appariement type MIME/ouvreur détermine quel ouvreur sera utilisé
pour chaque type -- la valeur de priorité la plus basse déterminera quel ouvreur
sera utilisé.  S'il y a plusieurs ouvreurs avec la même priorité basse,
l'utilisateur sera invité à choisir quel ouvreur utiliser lors de l'ouverture
d'un fichier dans Ginga.  Ce plugin peut servir à définir les préférences
d'ouvreurs et à les enregistrer dans la zone de configuration $HOME/.ginga de
l'utilisateur.

**Type de plugin : Global**

``LoaderConfig`` est un plugin global.  Une seule instance peut être ouverte.

**Utilisation**

Après le démarrage du plugin, l'affichage montrera tous les types MIME
enregistrés et les ouvreurs enregistrés pour ces types, avec une priorité
associée à chaque appariement type MIME/ouvreur.

Sélectionnez une ou plusieurs lignes et saisissez une priorité pour elles dans
la case intitulée « Priorité : » ; appuyez sur « Définir » (ou ENTRÉE) pour
définir la priorité de ces éléments.

.. note:: Plus le nombre est bas, plus la priorité est élevée.  Les nombres
          négatifs conviennent, et la priorité par défaut d'un chargeur est
          généralement 0.  Ainsi, par exemple, s'il y a deux chargeurs
          disponibles pour un type MIME et qu'une priorité est réglée sur -1 et
          l'autre sur 0, celui à -1 sera utilisé sans demander à l'utilisateur
          de choisir.


Cliquez sur « Enregistrer » pour enregistrer les priorités dans
$HOME/.ginga/loaders.json afin qu'elles soient rechargées et utilisées lors des
redémarrages ultérieurs du programme.
