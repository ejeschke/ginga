Das Plugin ``Header`` bietet eine Auflistung der mit dem Bild verknüpften
Metadaten.

**Plugin-Typ: Global**

``Header`` ist ein globales Plugin.  Es kann nur eine Instanz geöffnet werden.

**Verwendung**

Das Plugin ``Header`` zeigt die FITS-Schlüsselwort-Metadaten des Bildes an.
Zunächst werden nur die Metadaten des primären HDU angezeigt.  In Verbindung
mit dem Plugin ``MultiDim`` werden jedoch auch die Metadaten anderer HDUs
angezeigt.  Näheres siehe ``MultiDim``.

Ist das Kontrollkästchen „Sortierbar“ unten links in der Oberfläche
aktiviert, so wird durch Klicken auf eine Spaltenüberschrift die Tabelle nach
den Werten dieser Spalte sortiert, was das schnelle Auffinden eines bestimmten
Schlüsselworts erleichtern kann.

Das Kontrollkästchen „Primären Header einschließen“ schaltet die Einbeziehung
der Schlüsselwörter des primären HDU ein oder aus.  Diese Option kann
deaktiviert sein, wenn das Bild mit der Option erstellt wurde, den primären
Header nicht zu speichern.
