Ein Plugin zum Durchsuchen des lokalen Dateisystems und zum Laden von Dateien.

**Plugin-Typ: Global oder Lokal**

``FBrowser`` ist ein hybrides globales/lokales Plugin, das heißt, es kann auf
beide Arten aufgerufen werden.  Als lokales Plugin ist es einem Kanal
zugeordnet, und für jeden Kanal kann eine Instanz geöffnet werden.  Es kann
auch als globales Plugin geöffnet werden.

**Verwendung**

Navigieren Sie durch den Verzeichnisbaum, bis Sie zum Speicherort der zu
ladenden Dateien gelangen.  Sie können auf eine Datei doppelklicken, um sie in
den zugehörigen Kanal zu laden, oder eine Datei in ein Kanal-Betrachterfenster
ziehen, um sie in einen beliebigen Kanalbetrachter zu laden.

Mehrere Dateien lassen sich durch Gedrückthalten von ``Ctrl`` (``Command`` auf
dem Mac) auswählen oder durch ``Shift``-Klicken, um einen zusammenhängenden
Dateibereich auszuwählen.

Sie können auch den vollständigen Pfad zu den gewünschten Bildern in das
Textfeld eingeben, etwa ``/mein/pfad/zum/bild.fits``,
``/mein/pfad/zum/bild.fits[ext]`` oder
``/mein/pfad/zum/bild*.fits[extname,*]``.

Da es ein lokales Plugin ist, merkt sich ``FBrowser`` sein letztes Verzeichnis,
wenn es geschlossen und dann neu gestartet wird.
