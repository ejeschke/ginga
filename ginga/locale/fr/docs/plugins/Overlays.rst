Un plugin pour générer des superpositions de couleur représentant la
sous-exposition et la surexposition dans l'image chargée.

**Type de plugin : Local**

``Overlays`` est un plugin local, ce qui signifie qu'il est associé à un canal.
Une instance peut être ouverte pour chaque canal.

**Utilisation**

Choisissez des couleurs dans les menus déroulants pour la limite basse et/ou
haute (« Couleur basse » et « Couleur haute », respectivement).  Indiquez les
limites pour les valeurs basses et hautes dans les cases de limite (« Limite
basse » et « Limite haute », respectivement).  Réglez l'opacité des
superpositions avec une valeur entre 0 et 1 dans la case « Opacité ».  Enfin,
appuyez sur le bouton « Refaire ».

La superposition de couleur devrait afficher les zones sous la limite basse
dans une couleur basse et les zones au-dessus de la limite haute dans la
couleur haute.  Si vous omettez une limite (case laissée vide), cette couleur
ne sera pas affichée dans la superposition.

Si une nouvelle image est sélectionnée pour le canal, l'image de superposition
sera recalculée d'après les paramètres actuels avec les nouvelles données.
