Ein Plugin zum Zeichnen von Leinwandformen (überlagerte Grafiken).

**Plugin-Typ: Lokal**

``Drawing`` ist ein lokales Plugin, das heißt, es ist einem Kanal zugeordnet.
Es ist kein Singleton, das heißt, für jeden Kanal können mehrere Instanzen
geöffnet werden.

**Verwendung**

Mit diesem Plugin lassen sich viele verschiedene Formen auf der Bildanzeige
zeichnen.  Wählen Sie im „Zeichnen“-Modus eine Form aus dem Auswahlmenü, passen
Sie deren Parameter an (falls nötig) und zeichnen Sie mit der linken Maustaste
auf dem Bild.  Sie können im Pixel- oder im WCS-Raum zeichnen.

Um eine vorhandene Form zu verschieben oder zu bearbeiten, setzen Sie das Plugin
in den „Bearbeiten“- bzw. „Verschieben“-Modus.

Um die gezeichneten Formen als Maskenbild zu speichern, klicken Sie auf die
Schaltfläche „Maske erstellen“; dann sehen Sie ein neues Maskenbild in Ginga.
Verwenden Sie anschließend das Plugin ``SaveImage``, um es als FITS-Datei mit
einer Erweiterung zu speichern.  Beachten Sie, dass die Maske die Größe des
angezeigten Bildes übernimmt.  Um Masken für unterschiedliche Bildabmessungen zu
erstellen, müssen Sie die Schritte daher mehrmals wiederholen.

Auf der Leinwand gezeichnete Formen können im Format astropy-regions
(kompatibel mit DS9-Regionen) geladen und/oder gespeichert werden.  Dazu muss
das Paket astropy-regions installiert sein.  Zeichnen Sie einfach Objekte auf
der Leinwand mit Koordinaten als „data“ (Pixel) oder „wcs“.  Beachten Sie, dass
nicht alle Ginga-Leinwandobjekte in Regionen-Formen umgewandelt werden können
und einige Attribute möglicherweise nicht gespeichert werden, ignoriert werden
oder beim Laden der Regionen-Formen in anderer Software Fehler verursachen.
