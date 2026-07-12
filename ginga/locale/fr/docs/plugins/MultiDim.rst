
Un plugin pour naviguer parmi les HDU d'un fichier FITS ou parmi les plans d'un
cube 3D ou d'un jeu de données de dimension supérieure.

**Type de plugin : Local**

``MultiDim`` est un plugin local, ce qui signifie qu'il est associé à un canal.
Une instance peut être ouverte pour chaque canal.

**Utilisation**

``MultiDim`` est un plugin conçu pour gérer les cubes de données et les fichiers
FITS à plusieurs HDU.  Si vous avez ouvert une telle image dans Ginga, démarrer
ce plugin vous permettra de parcourir d'autres tranches du cube ou de visualiser
d'autres HDU.

Pour un cube de données, vous pouvez enregistrer une tranche en tant qu'image à
l'aide du bouton « Enregistrer la tranche » ou créer un film à l'aide du bouton
« Enregistrer le film » en saisissant les indices de tranche « Début » et
« Fin ».  Cette fonctionnalité nécessite que ``mencoder`` soit installé.

Pour une table FITS, ses données sont lues à l'aide d'une table Astropy.  Les
unités des colonnes sont affichées juste sous l'en-tête principal (« None » s'il
n'y a pas d'unité).  Pour les colonnes masquées, les valeurs masquées sont
remplacées par des valeurs de remplissage prédéfinies.

**Parcourir les HDU**

Utilisez la liste déroulante des HDU dans la partie supérieure de l'interface
pour parcourir et sélectionner une HDU à ouvrir dans le canal.

**Naviguer dans les cubes**

Utilisez les contrôles dans la partie inférieure de l'interface pour
sélectionner l'axe et parcourir les plans de cet axe.

**Configuration de l'utilisateur**

Il est personnalisable à l'aide de ``~/.ginga/plugin_MultiDim.cfg``, où ``~``
est votre répertoire HOME :

.. code-block:: Python

  #
  # MultiDim plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_MultiDim.cfg"

  # Sort option for HDU listing.
  # Available attributes:
  #   'index' -- Extension index
  #   'name' -- Extension name
  #   'extver' -- Extension version number
  #   'htype' -- HDU type (PrimaryHDU, ImageHDU, TableHDU)
  #   'dtype' -- Data type
  # Example to sort by HDU name and extver:
  #   sort_keys = ['name', 'extver']
  # Default is to sort by index only:
  sort_keys = ['index']

  # Reverse for HDU listing?
  sort_reverse = False
