Le plugin ``Errors`` signale les messages d'erreur dans le visualiseur.

**Type de plugin : Global**

``Errors`` est un plugin global.  Une seule instance peut être ouverte.

**Utilisation**

Lorsqu'une erreur se produit dans Ginga, son message peut être signalé ici.

Ce plugin n'est généralement pas configuré comme fermable, mais l'utilisateur
peut le rendre tel en réglant le paramètre « closeable » sur True dans le
fichier de configuration ; les boutons Fermer et Aide sont alors ajoutés en
bas de l'interface.
