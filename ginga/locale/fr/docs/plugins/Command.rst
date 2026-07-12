Ce plugin fournit une interface en ligne de commande pour le visualiseur de
référence.

.. note:: La ligne de commande est destinée à être utilisée *au sein* de
          l'interface du plugin.  Si vous cherchez une interface en ligne de
          commande *distante*, voir le plugin ``RC``.

**Type de plugin : Global**

``Command`` est un plugin global.  Une seule instance peut être ouverte.

**Utilisation**

Obtenir une liste des commandes et des paramètres::

        g> help

Exécuter une commande shell::

        g> !cmd arg arg ...

**Remarques**

Un outil particulièrement puissant consiste à utiliser les commandes
``reload_local`` et ``reload_global`` pour recharger un plugin lorsque vous le
développez.  Cela évite de devoir redémarrer le visualiseur de référence et de
recharger laborieusement les données, etc.  Fermez simplement le plugin,
exécutez la commande « reload » appropriée (voir l'aide !) puis redémarrez le
plugin.

.. note:: Si vous avez modifié des modules *autres* que le plugin lui-même,
          ceux-ci ne seront pas rechargés par ces commandes.
