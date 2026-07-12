
Das ``Info``-Plugin bietet einen Bereich mit häufig nützlichen Metadaten über
das fokussierte Kanalbild.  Zu den üblichen Informationen gehören einige
Metadaten-Header-Werte, Koordinaten, Abmessungen des Bildes, Minimal- und
Maximalwerte usw.  Während der Cursor über das Bild bewegt wird, werden die
X-, Y-, Wert-, RA- und DEC-Werte aktualisiert, um den Wert unter dem Cursor
widerzuspiegeln.

**Plugin-Typ: Global**

``Info`` ist ein globales Plugin.  Es kann nur eine Instanz geöffnet werden.

**Verwendung**

Am unteren Rand der ``Info``-Oberfläche befinden sich die Steuerelemente für die
Farbverteilung und die Cut-Level.  Der Selektor über den Cut-Level-Feldern lässt
Sie aus mehreren Verteilungsalgorithmen wählen, die die Werte im Bild auf die
Farbkarte abbilden.  Die Auswahl umfasst „linear“, „log“, „power“, „sqrt“,
„squared“, „asinh“, „sinh“ und „histeq“ (Histogrammausgleich).

Darunter werden die unteren und oberen Cut-Level angezeigt und können angepasst
werden.  Das Drücken der Schaltfläche „Auto Levels“ berechnet die Cut-Level
basierend auf dem aktuellen Auto-Cut-Level-Algorithmus und den in den
Kanaleinstellungen definierten Parametern neu.

Unter der Schaltfläche „Auto Levels“ wird der Status der Einstellungen für
„Cut New“, „Zoom New“ und „Center New“ für den aktuell aktiven Kanal angezeigt.
Diese geben an, wie neue Bilder, die dem Kanal hinzugefügt werden, von
automatischen Cut-Level, dem Anpassen an das Fenster und dem Schwenken zur Mitte
des Bildes beeinflusst werden.

Das Kontrollkästchen „Follow New“ steuert, ob der Betrachter automatisch neue
Bilder anzeigt, die dem Kanal hinzugefügt werden.  Das Kontrollkästchen „Raise
New“ steuert, ob ein Bildbetrachterfenster hervorgehoben wird, wenn ein neues
Bild hinzugefügt wird.  Diese beiden Steuerelemente können nützlich sein, zum
Beispiel wenn ein externes Programm Bilder zum Betrachter hinzufügt und Sie eine
Unterbrechung Ihrer Arbeit beim Untersuchen eines bestimmten Bildes verhindern
möchten.

Als globales Plugin reagiert ``Info`` auf einen Fokuswechsel zu einem neuen
Kanal, indem es die Metadaten des neuen Kanals anzeigt.  Es erscheint
üblicherweise unter dem Reiter „Synopsis“ in der Benutzeroberfläche.

Dieses Plugin ist normalerweise nicht als schließbar konfiguriert, doch der
Benutzer kann dies erreichen, indem er in der Konfigurationsdatei die
Einstellung „closeable“ auf True setzt -- dann werden am unteren Rand der
Benutzeroberfläche die Schaltflächen „Schließen“ und „Hilfe“ hinzugefügt.
