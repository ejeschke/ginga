
Le plugin ``PluginConfig`` vous permet de configurer les plugins qui sont
visibles dans vos menus.

**Type de plugin : Global**

``PluginConfig`` est un plugin global.  Une seule instance peut être ouverte.

**Utilisation**

``PluginConfig`` sert à configurer les plugins à utiliser dans Ginga.  Les
éléments configurables pour chaque plugin comprennent :

* s'il est activé (et donc s'il apparaît dans les menus)
* la catégorie du plugin (utilisée pour construire la hiérarchie des menus)
* l'espace de travail dans lequel le plugin s'ouvrira
* s'il s'agit d'un plugin global, s'il démarre automatiquement au démarrage
  du visualiseur de référence
* si le nom du plugin doit être masqué (ne pas apparaître dans les menus
  d'activation des plugins)

Au démarrage de ``PluginConfig``, une table des plugins s'affiche.  Pour
modifier les attributs ci-dessus des plugins, cliquez sur « Modifier », ce qui
ouvrira une boîte de dialogue pour modifier la table.

Pour chaque plugin que vous souhaitez configurer, cliquez sur une entrée dans
la table principale, puis ajustez les paramètres dans la boîte de dialogue,
puis cliquez sur « Définir » dans la boîte de dialogue pour répercuter les
modifications dans la table.  Si vous ne cliquez pas sur « Définir », rien
n'est modifié dans la table.  Lorsque vous avez terminé de modifier les
configurations, cliquez sur « Fermer » dans la boîte de dialogue pour fermer
la boîte de dialogue d'édition.

.. note:: Il n'est pas recommandé de changer l'espace de travail d'un plugin,
          à moins de choisir un espace de travail de taille compatible avec
          l'original, car le plugin pourrait ne pas s'afficher correctement.
          En cas de doute, laissez l'espace de travail inchangé.  De plus,
          désactiver des plugins de la catégorie « Systems » peut faire cesser
          de fonctionner certaines fonctionnalités attendues.


.. important:: Pour que les modifications persistent entre les redémarrages de
               Ginga, cliquez sur « Enregistrer » pour enregistrer les
               paramètres (dans `$HOME/.ginga/plugins.json`).  Redémarrez Ginga
               pour voir les modifications des menus (via les changements de
               « category »).  **Supprimez ce fichier manuellement si vous
               souhaitez réinitialiser les configurations des plugins aux
               valeurs par défaut**.
