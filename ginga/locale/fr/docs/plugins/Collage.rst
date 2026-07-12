
Plugin pour créer une mosaïque d'images via la méthode du collage.

**Type de plugin : Local**

``Collage`` est un plugin local, ce qui signifie qu'il est associé à un canal.
Une instance peut être ouverte pour chaque canal.

**Utilisation**

Ce plugin sert à créer automatiquement un collage mosaïque dans le visualiseur
de canal à partir d'images fournies par l'utilisateur.  La position d'une image
sur le collage est déterminée par son WCS sans correction de distorsion.  Ceci
est conçu comme un outil d'aperçu rapide, et non comme un remplacement du
« drizzling » d'images qui tient compte de la distorsion de l'image, etc.

Le collage n'existe que sous forme de tracé sur le canevas de Ginga.  Aucune
nouvelle image individuelle n'est réellement construite (si vous le souhaitez,
voir le plugin « Mosaic »).  Certains plugins censés opérer sur des images
individuelles peuvent ne pas fonctionner correctement avec un collage.

Pour créer un nouveau collage, cliquez sur le bouton « Nouveau collage » et
faites glisser des fichiers sur la fenêtre d'affichage (p. ex. les fichiers
peuvent être glissés depuis le plugin `FBrowser`).  Les images doivent avoir un
WCS fonctionnel.  La première image traitée sera chargée et son WCS sera utilisé
pour orienter les autres tuiles.  Vous pouvez ajouter de nouvelles images à un
collage existant simplement en faisant glisser des fichiers supplémentaires.

**Contrôles**

Le contrôle « Méthode » sert à choisir une méthode pour mosaïquer les images du
collage.  Il a deux valeurs : 'simple' et 'warp' :

- 'simple' tentera de faire pivoter et de retourner les images selon le WCS.
  C'est une méthode rapide, au détriment de la précision.  Elle ne gérera pas
  les distorsions près du bord du champ qui devraient déformer l'image.
- 'warp' utilisera le WCS pour déplacer complètement chaque pixel de l'image
  selon le WCS de l'image de référence.  Cela peut laisser des pixels vides dans
  l'image, qui sont comblés par échantillonnage des pixels environnants.  Ce
  sera plus lent que la méthode simple, et le temps augmente linéairement avec
  la taille des images.

Cochez le bouton « HDU du collage » pour que `Collage` tente de tracer toutes
les HDU d'image d'un fichier glissé au lieu de seulement la première trouvée.

Cochez « Étiqueter les images » pour que le plugin dessine le nom de chaque
image sur chaque tuile tracée.

Si « Égaliser l'arrière-plan » est coché, l'arrière-plan de chaque tuile est
ajusté par rapport à la médiane de la première tuile tracée (une sorte de
lissage grossier).

La case « Nombre de threads » attribue combien de threads du pool de threads
seront utilisés pour charger les données.  Utiliser plusieurs threads accélère
généralement le chargement de nombreux fichiers.

**Différence avec le plugin `Mosaic`**

- N'alloue pas un grand tableau pour contenir tout le contenu de la mosaïque
- Pas besoin de spécifier le FOV de sortie ni de s'en soucier
- Peut afficher le résultat plus rapidement (dépend un peu des images
  constituantes)
- Certains plugins ne fonctionneront pas correctement avec un collage, ou seront
  plus lents
- Ne peut pas enregistrer le collage comme fichier de données (mais vous pouvez
  utiliser « ScreenShot »)

Il est personnalisable à l'aide de ``~/.ginga/plugin_Collage.cfg``, où ``~`` est
votre répertoire HOME :

.. code-block:: Python

  #
  # Collage plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_Collage.cfg"

  # Set to True when you want to collage image HDUs in a file
  collage_hdus = False

  # annotate images with their names
  annotate_images = False

  # Try to match backgrounds
  match_bg = False

  # Number of threads to devote to opening images
  num_threads = 4
