Das Plugin ``Pan`` bietet ein kleines Übersichtsbild, das eine gesamte
„Vogelperspektive“ des zuletzt fokussierten Kanalbilds gibt.  Ist das Kanalbild
2-fach oder stärker vergrößert, wird der Verschiebebereich im ``Pan``-Bild
grafisch durch ein Rechteck dargestellt.

**Plugin-Typ: Lokal**

``Pan`` ist ein globales Plugin.  Es kann nur eine Instanz geöffnet werden.

**Verwendung**

Das Kanalbild kann durch Klicken und/oder Ziehen verschoben werden, um das
Rechteck zu platzieren.  Zieht man mit der rechten Maustaste ein Rechteck auf,
so versucht der Kanal-Bildbetrachter, den Bereich zu treffen (unter
Berücksichtigung der Unterschiede im Seitenverhältnis zwischen dem gezeichneten
Rechteck und den Fensterabmessungen).  Scrollen im ``Pan``-Bild zoomt das
Kanalbild.

Die Farb-/Intensitätskarte und die Schnittwerte des ``Pan``-Bilds werden
aktualisiert, wenn sie im entsprechenden Kanalbild geändert werden.
Das ``Pan``-Bild zeigt außerdem den Kompass des Weltkoordinatensystems (WCS)
an, sofern im im Kanal betrachteten FITS-HDU gültige WCS-Metadaten vorhanden
sind.

Das Plugin ``Pan`` erscheint gewöhnlich als Unterbereich unter dem Reiter
„Info“, neben dem Plugin ``Info``.

Dieses Plugin ist normalerweise nicht als schließbar konfiguriert, doch der
Benutzer kann dies ermöglichen, indem er in der Konfigurationsdatei die
Einstellung „closeable“ auf True setzt -- dann werden am unteren Rand der
Benutzeroberfläche die Schaltflächen „Schließen“ und „Hilfe“ hinzugefügt.
