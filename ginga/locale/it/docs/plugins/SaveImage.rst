Salvare le immagini in file di output.

**Tipo di plugin: Globale**

``SaveImage`` è un plugin globale.  Può essere aperta una sola istanza.

**Uso**

Questo plugin globale serve a salvare in immagini di output qualsiasi modifica
apportata in Ginga.  Ad esempio, un'immagine mosaico creata dal plugin
``Mosaic``.  Attualmente sono supportate solo immagini FITS (con una o più
estensioni).

Dati la cartella di output (ad es. ``/mypath/outputs/``), un suffisso (ad es.
``ginga``), un canale immagine (``Image``) e un'immagine selezionata (ad es.
``image1.fits``), il file di output sarà
``/mypath/outputs/image1_ginga_Image.fits``.  L'inclusione del nome del canale è
facoltativa e può essere omessa tramite il file di configurazione del plugin,
``plugin_SaveImage.cfg``.
Le estensioni modificate avranno la nuova intestazione o i nuovi dati estratti
da Ginga, mentre quelle non modificate resteranno intatte.  Le voci di registro
delle modifiche pertinenti del plugin globale ``ChangeHistory`` verranno
inserite nella cronologia della sua intestazione ``PRIMARY``.

.. note:: Questo plugin usa il modulo ``astropy.io.fits`` per scrivere le
          immagini di output, indipendentemente da ciò che è scelto per
          ``FITSpkg`` nel file di configurazione ``general.cfg``.
