Plugin zum Erstellen eines Bildmosaiks durch Konstruktion eines Kompositbildes.

**Plugin-Typ: Lokal**

``Mosaic`` ist ein lokales Plugin, das heißt, es ist einem Kanal zugeordnet.
Für jeden Kanal kann eine Instanz geöffnet werden.

**Verwendung**

.. warning:: Dies kann sehr speicherintensiv sein.

Dieses Plugin dient dazu, im Kanal automatisch ein Mosaikbild aus vom Benutzer
bereitgestellten Bildern zu erstellen (z. B. mit ``FBrowser``).
Die Position eines Bildes im Mosaik wird durch sein WCS ohne
Verzeichnungskorrektur bestimmt.  Dies ist als Schnellansicht-Werkzeug gedacht,
nicht als Ersatz für ein Image-Drizzling, das Bildverzeichnung usw.
berücksichtigt.  Das Mosaik existiert nur im Speicher, doch Sie können es mit
``SaveImage`` in eine FITS-Datei speichern.

Fällt ein Mosaik aus dem Speicher, ist es in Ginga nicht mehr zugänglich.  Um
dies zu vermeiden, müssen Sie Ihre Sitzung so konfigurieren, dass Ihr
Ginga-Datencache ausreichend groß ist (siehe „Customizing Ginga“ im Handbuch).

Um ein neues Mosaik zu erstellen, legen Sie das FOV fest und ziehen Sie Dateien
auf das Anzeigefenster.  Die Bilder müssen ein funktionierendes WCS besitzen.
Das WCS des ersten Bildes wird zur Ausrichtung der anderen Kacheln verwendet.

**Unterschied zum Plugin `Collage`**

- Reserviert ein einziges großes Array für den gesamten Mosaikinhalt
- Langsamer im Aufbau, aber die Bearbeitung großer Ergebnisbilder kann schneller
  sein
- Kann das Mosaik als neue Datendatei speichern
- Füllt Werte zwischen den Kacheln mit einem Füllwert (kann `NaN` sein)
