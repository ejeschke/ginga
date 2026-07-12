Un plugin pour afficher un graphique basique de deux colonnes sélectionnées
quelconques d'une table.

**Type de plugin : Local**

``PlotTable`` est un plugin local, ce qui signifie qu'il est associé à un canal.
Ce n'est pas un singleton, ce qui signifie que plusieurs instances peuvent être
ouvertes pour chaque canal.

**Utilisation**

``PlotTable`` est un plugin conçu pour tracer deux colonnes sélectionnées
quelconques d'un HDU de table FITS donné (accessible via ``MultiDim``).
Pour les colonnes masquées, les données masquées ne sont pas affichées (même si
une seule de la paire ``(X, Y)`` est masquée).
Il est destiné à examiner rapidement les données d'une table et non à une
analyse scientifique détaillée.
