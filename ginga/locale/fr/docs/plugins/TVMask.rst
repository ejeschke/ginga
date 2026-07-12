
Afficher des masques depuis un fichier (mode non interactif) sur une image.

**Type de plugin : Local**

``TVMask`` est un plugin local, ce qui signifie qu'il est associé à un canal.
Une instance peut être ouverte pour chaque canal.

**Utilisation**

Ce plugin permet l'affichage non interactif d'un masque en lisant un fichier
FITS, où les valeurs non nulles sont supposées être des données masquées.

Pour afficher différents masques (p. ex. certains masqués en vert et d'autres en
rose, comme montré ci-dessus) :

1. Sélectionnez vert dans le menu déroulant.  Vous pouvez aussi saisir la valeur
   alpha souhaitée.
2. À l'aide du bouton « Charger le masque », chargez le fichier FITS pertinent.
3. Répétez (1) mais sélectionnez maintenant rose dans le menu déroulant.
4. Répétez (2) mais choisissez un autre fichier FITS.
5. Pour afficher un troisième masque également en rose, répétez (4) sans changer
   le menu déroulant.

Sélectionner une entrée (ou plusieurs entrées) dans la liste de la table mettra
en surbrillance le(s) masque(s) sur l'image.  La surbrillance utilise une
couleur et un alpha prédéfinis (personnalisables ci-dessous).

Vous pouvez aussi mettre en surbrillance tous les masques d'une région, à la
fois sur l'image et dans la liste de la table, en dessinant un rectangle sur
l'image pendant que ce plugin est actif.

Appuyer sur le bouton « Masquer » masquera les masques mais n'efface pas la
mémoire du plugin ; c'est-à-dire que lorsque vous appuyez sur « Afficher », les
mêmes masques réapparaîtront sur la même image.  En revanche, appuyer sur
« Oublier » effacera les masques à la fois de l'affichage et de la mémoire ;
c'est-à-dire que vous devrez recharger votre(vos) fichier(s) pour recréer les
masques.

Pour redessiner les mêmes masques avec une couleur ou un alpha différent,
appuyez sur « Oublier » et répétez les étapes ci-dessus, selon les besoins.

Si des images de pointages/dimensions très différents sont affichées dans le
même canal, les masques qui appartiennent à une image mais tombent en dehors
d'une autre n'apparaîtront pas dans cette dernière.

Pour créer un masque que ce plugin peut lire, on peut utiliser les résultats du
plugin ``Drawing`` (appuyez sur « Créer un masque » après avoir dessiné et
enregistrez le masque avec ``SaveImage``), en plus de créer un fichier FITS à la
main avec ``astropy.io.fits``, etc.

Utilisé avec ``TVMark``, vous pouvez superposer dans Ginga à la fois des sources
ponctuelles et des régions masquées.

Il est personnalisable à l'aide de ``~/.ginga/plugin_TVMask.cfg``, où ``~`` est
votre répertoire HOME :

.. code-block:: Python

  #
  # TVMask plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_TVMask.cfg"

  # Mask color -- Any color name accepted by Ginga
  maskcolor = 'green'

  # Mask alpha (transparency) -- 0=transparent, 1=opaque
  maskalpha = 0.5

  # Highlighted mask color and alpha
  hlcolor = 'white'
  hlalpha = 1.0
