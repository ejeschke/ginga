
Le plugin ``RC`` implémente une interface de contrôle à distance pour le
visualiseur Ginga.

**Type de plugin : Global**

``RC`` est un plugin global.  Une seule instance peut être ouverte.

**Utilisation**

Le plugin ``RC`` (Remote Control) offre un moyen de contrôler Ginga à distance
grâce à l'utilisation d'une interface XML-RPC.  Démarrez le plugin depuis le
menu « Plugins » (invoquez « Start RC ») ou lancez ginga avec l'option de ligne
de commande ``--modules=RC`` pour le démarrer automatiquement.

Par défaut, le plugin démarre avec un serveur fonctionnant sur le port 11771 lié
à l'interface localhost -- cela n'autorise les connexions que depuis l'hôte
local.  Si vous voulez changer cela, définissez l'hôte et le port dans le
contrôle « Set Addr » et appuyez sur ``Enter`` -- vous devriez voir l'adresse se
mettre à jour dans le champ d'affichage « Addr: ».

Veuillez noter que la partie hôte (avant les deux-points) n'indique pas *depuis
quel* hôte vous voulez autoriser l'accès, mais à quelle interface se lier.  Si
vous voulez autoriser n'importe quel hôte à se connecter, laissez-la vide (mais
incluez les deux-points et le numéro de port) pour permettre au serveur de se
lier à toutes les interfaces.  Appuyez ensuite sur « Restart » pour redémarrer
le serveur à la nouvelle adresse.

Une fois le plugin démarré, vous pouvez utiliser le script ``ggrc`` (inclus
lorsque ``ginga`` est installé) pour contrôler Ginga.  Jetez un œil au script si
vous voulez voir comment écrire votre propre interface programmatique.

Afficher un exemple d'utilisation::

        $ ggrc help

Afficher l'aide pour une méthode Ginga spécifique::

        $ ggrc help ginga <method>

Afficher l'aide pour une méthode de canal spécifique::

        $ ggrc help channel <chname> <method>

Les méthodes de Ginga (shell du visualiseur) peuvent être appelées ainsi::

        $ ggrc ginga <method> <arg1> <arg2> ...

Les méthodes par canal peuvent être appelées ainsi::

        $ ggrc channel <chname> <method> <arg1> <arg2> ...

Les appels peuvent être faits depuis un hôte distant en ajoutant les options::

        --host=<hostname> --port=11771

(Dans l'interface graphique du plugin, veillez à retirer le préfixe
« localhost » de l'« addr », mais laissez les deux-points et le port.)

**Exemples**

Créer un nouveau canal::

        $ ggrc ginga add_channel FOO

Charger un fichier::

        $ ggrc ginga load_file /home/eric/testdata/SPCAM/SUPA01118797.fits

Charger un fichier dans un canal spécifique::

        $ ggrc ginga load_file /home/eric/testdata/SPCAM/SUPA01118797.fits FOO

Niveaux de coupe::

        $ ggrc channel FOO cut_levels 163 1300

Niveaux de coupe automatiques::

        $ ggrc channel FOO auto_levels

Zoomer à un niveau spécifique::

        $ ggrc -- channel FOO zoom_to -7

(Notez l'utilisation de ``--`` pour nous permettre de passer un paramètre
commençant par ``-``.)

Zoomer pour ajuster::

        $ ggrc channel FOO zoom_fit

Transformer (les arguments sont un triplet booléen : ``flipx`` ``flipy``
``swapxy``)::

        $ ggrc channel FOO transform 1 0 1

Pivoter::

        $ ggrc channel FOO rotate 37.5

Changer la carte de couleurs::

        $ ggrc channel FOO set_color_map rainbow3

Changer l'algorithme de distribution des couleurs::

        $ ggrc channel FOO set_color_algorithm log

Changer la carte d'intensité::

        $ ggrc channel FOO set_intensity_map neg

Dans certains cas, vous devrez peut-être recourir à des échappements de shell
pour pouvoir passer certains caractères à Ginga.  Par exemple, un tiret initial
est généralement interprété comme une option de programme.  Afin de passer un
entier signé, vous devrez peut-être faire quelque chose comme::

        $ ggrc -- channel FOO zoom -7

**Interfaçage depuis Python**

Il est aussi possible de contrôler Ginga en mode RC depuis Python.  Ce qui suit
décrit une partie des fonctionnalités.

*Se connecter*

D'abord, lancez Ginga et démarrez le plugin ``RC``.  Cela peut être fait depuis
la ligne de commande::

        ginga --modules=RC

Depuis Python, connectez-vous avec un objet ``RemoteClient`` comme suit::

        from ginga.util import grc
        host = 'localhost'
        port = grc.default_rc_port
        viewer = grc.RemoteClient(host, port)

Cet objet viewer est maintenant lié à Ginga en utilisant ``RC``.

*Charger une image*

Vous pouvez charger une image depuis la mémoire dans un canal de votre choix.
D'abord, connectez-vous à un canal::

        ch = viewer.channel('Image')

Ensuite, chargez une image Numpy (c.-à-d. n'importe quel ``ndarray`` 2D)::

        import numpy as np
        img = np.random.rand(500, 500) * 10000.0
        ch.load_np('Image_Name', img, 'fits', {})

L'image s'affichera dans Ginga et pourra être manipulée comme d'habitude.

*Superposer un objet de canevas*

Il est possible d'ajouter des objets au canevas dans un canal donné.  D'abord,
connectez-vous::

        canvas = viewer.canvas('Image')

Ceci se connecte au canal nommé « Image ».  Vous pouvez effacer les objets
dessinés dans le canevas::

        canvas.clear()

Vous pouvez aussi ajouter n'importe quel objet de canevas basique.  Le point clé
à garder à l'esprit est que les objets fournis doivent passer par le protocole
XMLRC.  Cela signifie des types de données simples (``float``, ``int``, ``list``
ou ``str``) ; pas de tableaux.  Voici un exemple pour tracer une ligne à travers
une série de points définis par deux tableaux Numpy::

        x = np.arange(100)
        y = np.sqrt(x)
        points = list(zip(x.tolist(), y.tolist()))
        canvas.add('path', points, color='red')

Ceci dessinera une ligne rouge sur l'image.
