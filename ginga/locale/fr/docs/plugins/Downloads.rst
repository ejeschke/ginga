
Interface de téléchargements pour le visualiseur de référence Ginga.

**Type de plugin : Global**

``Download`` est un plugin global.  Une seule instance peut être ouverte.

**Utilisation**

Ouvrez ce plugin pour surveiller la progression des téléchargements d'URI.
Démarrez-le à l'aide du menu « Plugins » ou « Operations », en sélectionnant le
plugin « Downloads » sous la catégorie « Util ».

Si vous voulez lancer un téléchargement, faites simplement glisser une URI dans
un visualiseur d'image de canal ou dans le panneau ``Thumbs``.

Vous pouvez supprimer les informations sur un téléchargement à tout moment en
cliquant sur le bouton « Effacer » de son entrée.  Vous pouvez effacer les
entrées de tous les téléchargements en cliquant sur le bouton « Tout effacer »
en bas.

Actuellement, il n'est pas possible d'annuler un téléchargement en cours.

**Paramètres**

L'option ``auto_clear_download``, si elle est réglée sur `True`, fera qu'une
entrée de téléchargement est automatiquement supprimée du panneau lorsque le
téléchargement se termine.  Elle ne supprime aucun fichier téléchargé.

Le dossier de téléchargement peut être défini par l'utilisateur en attribuant
une valeur au paramètre « download_folder » dans ~/.ginga/general.cfg.  S'il
n'est pas attribué, il prend par défaut un dossier dans le répertoire temporaire
par défaut spécifique à la plateforme (tel qu'indiqué par le module « tempfile »
de Python).
