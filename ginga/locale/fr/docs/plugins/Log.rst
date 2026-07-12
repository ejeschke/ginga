Consultez la sortie de journalisation du visualiseur de référence.

**Type de plugin : Global**

``Log`` est un plugin global.  Une seule instance peut être ouverte.

**Utilisation**

Le plugin ``Log`` construit une interface comprenant un grand widget de texte
défilant qui affiche la sortie active du journaliseur.  La sortie la plus
récente apparaît en bas.  Cela peut être utile pour résoudre les problèmes.

Il y a quatre contrôles :

* La liste déroulante en bas à gauche permet de choisir le niveau de
  journalisation souhaité.  Les quatre niveaux, par ordre de verbosité, sont :
  « debug », « info », « warn » et « error ».
* La case avec le nombre en bas à droite permet de définir combien de lignes
  d'entrée conserver dans le tampon d'affichage (p. ex. ne conserver que les
  1000 dernières lignes).
* La case « Défilement automatique », si elle est cochée, fait défiler le grand
  widget de texte jusqu'à la fin à mesure que de nouveaux messages de journal
  sont ajoutés.  Décochez-la si vous souhaitez parcourir et étudier les anciens
  messages.
* Le bouton « Effacer » sert à effacer le widget de texte, afin que seule la
  nouvelle journalisation apparaisse.
