Un plugin pour tracer les valeurs des pixels le long d'une ligne droite qui
coupe un cube en deux.

**Type de plugin : Local**

``LineProfile`` est un plugin local, ce qui signifie qu'il est associé à un
canal.  Une instance peut être ouverte pour chaque canal.

**Utilisation**

.. warning::

   Il n'y a aucune restriction sur les axes qui peuvent être choisis.
   De ce fait, le graphique peut être dénué de sens.

Le plugin ``LineProfile`` est utilisé pour les images multidimensionnelles
(c.-à-d. 3D ou plus).  Il trace les valeurs des pixels à la position actuelle du
curseur le long de l'axe sélectionné ; ou, si une région est sélectionnée, il
trace la moyenne dans chaque image.  Cela peut servir à créer des profils de
raies spectrales normaux.  Un marqueur est placé au point de données de l'image
actuellement affichée.

L'axe X affiché est construit à l'aide des mots-clés ``CRVAL*``, ``CDELT*``,
``CRPIX*``, ``CTYPE*`` et ``CUNIT*`` de l'en-tête FITS.  Si l'un des mots-clés
n'est pas disponible, l'axe se rabat sur les valeurs ``NAXIS*``.

L'axe Y affiché est construit à l'aide de ``BTYPE`` et ``BUNIT``.  S'ils ne sont
pas disponibles, il étiquette simplement les valeurs de pixel comme « Signal ».

Pour utiliser ce plugin :

1. Sélectionnez un axe.
2. Choisissez un point ou dessinez une région à l'aide du curseur.
3. Utilisez ``MultiDim`` pour changer les valeurs de pas des axes, le cas
   échéant.
