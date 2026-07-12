``AutoLoad`` est un plugin simple pour surveiller un dossier à la recherche de
nouveaux fichiers et les charger automatiquement dans un canal dès qu'ils
apparaissent.

**Type de plugin : Local**

``AutoLoad`` est un plugin local, ce qui signifie qu'il est associé à un canal.
Une instance peut être ouverte pour chaque canal.

.. note:: Vous devez installer le paquet Python « watchdog » pour utiliser ce
          plugin.

**Utilisation**

* Pour configurer un dossier à surveiller, saisissez le chemin d'un dossier
  (répertoire) dans le champ « Dossier surveillé » et appuyez sur ENTRÉE ou
  cliquez sur « Définir ».
* Si vous devez distinguer les fichiers qui seront ajoutés à ce dossier, vous
  pouvez saisir une expression régulière Python dans la case « Expression
  régulière » et cliquer sur « Définir ».  Seuls les fichiers dont le nom
  correspond au motif seront pris en compte.  Notez que l'expression régulière
  ne concerne que le nom du fichier, et non une partie du chemin du dossier.
* Si vous souhaitez suspendre le chargement automatique, vous pouvez cocher la
  case « Suspendre le chargement automatique » ; cela arrêtera tout chargement
  automatique.  Notez que si vous décochez ensuite la case, les fichiers
  arrivés entre-temps ne seront pas chargés.

.. note:: La surveillance des dossiers situés sur des lecteurs réseau peut
          fonctionner ou non.

**Configuration de l'utilisateur**
