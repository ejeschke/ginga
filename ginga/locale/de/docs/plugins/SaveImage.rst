Bilder in Ausgabedateien speichern.

**Plugin-Typ: Global**

``SaveImage`` ist ein globales Plugin.  Es kann nur eine Instanz geöffnet
werden.

**Verwendung**

Dieses globale Plugin dient dazu, in Ginga vorgenommene Änderungen zurück in
Ausgabebilder zu speichern.  Zum Beispiel ein Mosaikbild, das mit dem Plugin
``Mosaic`` erstellt wurde.  Derzeit werden nur FITS-Bilder (mit einer oder
mehreren Erweiterungen) unterstützt.

Bei gegebenem Ausgabeverzeichnis (z. B. ``/mypath/outputs/``), einem Suffix
(z. B. ``ginga``), einem Bildkanal (``Image``) und einem ausgewählten Bild
(z. B. ``image1.fits``) lautet die Ausgabedatei
``/mypath/outputs/image1_ginga_Image.fits``.  Die Einbeziehung des Kanalnamens
ist optional und kann über die Plugin-Konfigurationsdatei
``plugin_SaveImage.cfg`` weggelassen werden.
Die geänderten Erweiterungen erhalten den neuen, aus Ginga extrahierten Header
bzw. die neuen Daten, während die nicht geänderten unverändert bleiben.
Relevante Änderungsprotokolleinträge aus dem globalen Plugin ``ChangeHistory``
werden in die Historie des ``PRIMARY``-Headers eingefügt.

.. note:: Dieses Plugin verwendet zum Schreiben der Ausgabebilder das Modul
          ``astropy.io.fits``, unabhängig davon, was für ``FITSpkg`` in der
          Konfigurationsdatei ``general.cfg`` gewählt ist.
