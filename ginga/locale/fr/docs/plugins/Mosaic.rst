Plugin pour créer une mosaïque d'images en construisant une image composite.

**Type de plugin : Local**

``Mosaic`` est un plugin local, ce qui signifie qu'il est associé à un canal.
Une instance peut être ouverte pour chaque canal.

**Utilisation**

.. warning:: Cela peut consommer beaucoup de mémoire.

Ce plugin sert à construire automatiquement une image mosaïque dans le canal à
partir d'images fournies par l'utilisateur (p. ex. en utilisant ``FBrowser``).
La position d'une image dans la mosaïque est déterminée par son WCS sans
correction de distorsion.  Ceci est conçu comme un outil d'aperçu rapide, et non
comme un remplacement du « drizzling » d'images qui tient compte de la
distorsion de l'image, etc.  La mosaïque n'existe qu'en mémoire, mais vous pouvez
l'enregistrer dans un fichier FITS en utilisant ``SaveImage``.

Lorsqu'une mosaïque sort de la mémoire, elle n'est plus accessible dans Ginga.
Pour éviter cela, vous devez configurer votre session de sorte que le cache de
données de Ginga soit suffisamment grand (voir « Customizing Ginga » dans le
manuel).

Pour créer une nouvelle mosaïque, définissez le FOV et faites glisser des
fichiers sur la fenêtre d'affichage.  Les images doivent avoir un WCS
fonctionnel.  Le WCS de la première image sera utilisé pour orienter les autres
tuiles.

**Différence avec le plugin `Collage`**

- Alloue un seul grand tableau pour contenir tout le contenu de la mosaïque
- Plus lent à construire, mais peut être plus rapide à manipuler pour les
  grandes images résultantes
- Peut enregistrer la mosaïque comme un nouveau fichier de données
- Remplit les valeurs entre les tuiles avec une valeur de remplissage (peut être
  `NaN`)
