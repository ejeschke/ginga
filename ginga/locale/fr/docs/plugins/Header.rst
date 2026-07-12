Le plugin ``Header`` fournit une liste des métadonnées associées à l'image.

**Type de plugin : Global**

``Header`` est un plugin global.  Une seule instance peut être ouverte.

**Utilisation**

Le plugin ``Header`` affiche les métadonnées de mots-clés FITS de l'image.
Au départ, seules les métadonnées du HDU primaire sont affichées.  Toutefois,
en conjonction avec le plugin ``MultiDim``, les métadonnées des autres HDU
seront affichées.  Voir ``MultiDim`` pour plus de détails.

Si la case « Triable » en bas à gauche de l'interface est cochée, cliquer sur
un en-tête de colonne trie la table selon les valeurs de cette colonne, ce qui
peut être utile pour localiser rapidement un mot-clé particulier.

La case « Inclure l'en-tête primaire » active ou non l'inclusion des mots-clés
du HDU primaire.  Cette option peut être désactivée si l'image a été créée avec
l'option de ne pas enregistrer l'en-tête primaire.
