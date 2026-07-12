``Ruler`` ist ein einfaches Plugin, das zum Messen von Entfernungen auf einem
Bild dient.

**Plugin-Typ: Lokal**

``Ruler`` ist ein lokales Plugin, das heißt, es ist einem Kanal zugeordnet.
Es ist kein Singleton, das heißt, für jeden Kanal können mehrere Instanzen
geöffnet werden.

**Verwendung**

``Ruler`` misst Entfernungen, indem es über die WCS-Zuordnung dreier Punkte,
die durch eine einzige auf dem Bild gezeichnete Linie definiert werden, eine
sphärische Triangulation berechnet.  Standardmäßig wird die Entfernung in
Bogenminuten am Himmel angezeigt, doch über das Steuerelement „Einheiten“ kann
sie stattdessen in Grad oder als Pixelentfernung angezeigt werden.

Klicken und ziehen Sie, um ein Lineal zwischen zwei Punkten festzulegen.  Wenn
Sie den Zeichenvorgang beenden, ist das Lineal festgelegt, und die
Plugin-Benutzeroberfläche wird aktualisiert, um Details zur Linie anzuzeigen,
einschließlich der Endpunktpositionen und des Winkels der Linie.  Die Einheiten
des Winkels können über das benachbarte Auswahlmenü zwischen Grad und Radiant
umgeschaltet werden.

Um das alte Lineal zu löschen und ein neues zu erstellen, klicken und ziehen Sie
erneut.  Wird eine weitere Linie gezeichnet, ersetzt sie die erste.  Wird das
Plugin geschlossen, wird die grafische Überlagerung entfernt.  Möchten Sie
„haftende Lineale“, verwenden Sie das Plugin ``Drawing`` (und wählen Sie „Ruler“
als Zeichentyp).

**Bearbeiten**

Um ein vorhandenes Lineal zu bearbeiten, klicken Sie in der Plugin-Oberfläche
auf die mit „Bearbeiten“ beschriftete Optionsschaltfläche.  Wird das Lineal
nicht sofort ausgewählt, klicken Sie auf die Diagonale, die die beiden Punkte
verbindet.  Dadurch sollte ein Begrenzungsrahmen um das Lineal entstehen und
dessen Kontrollpunkte angezeigt werden.  Ziehen Sie innerhalb des
Begrenzungsrahmens, um das Lineal zu verschieben, oder klicken und ziehen Sie
die Endpunkte, um das Lineal zu bearbeiten.  Das Lineal kann mit diesen
Kontrollpunkten auch skaliert oder gedreht werden.

**UI**

Die für die Entfernung angezeigten Einheiten können im Auswahlmenü der
Benutzeroberfläche gewählt werden.  Sie haben die Wahl zwischen „arcmin“,
„degrees“ oder „pixels“.  Die ersten beiden erfordern ein gültiges und
funktionierendes WCS im Bild.

Die Endpunktwerte werden in der Benutzeroberfläche angezeigt, können aber
zusätzlich in der Lineal-Grafik angezeigt werden, wenn das Kontrollkästchen
„Enden anzeigen“ aktiviert ist.  Lotlinien werden angezeigt, wenn das Kästchen
„Lot anzeigen“ aktiviert ist.

**Schaltflächen**

Die Schaltfläche „Auf Anfang schwenken“ schwenkt das Hauptbild zum Ursprung der
gezeichneten Linie, während „Auf Ende schwenken“ zum Ende schwenkt.  „Auf Mitte
schwenken“ setzt die Schwenkposition auf den Mittelpunkt der Linie.  Diese
Schaltflächen können für Nahaufnahmen und herangezoomte Arbeit am Bild nützlich
sein.  „Löschen“ entfernt das Lineal aus dem Bild.

**Tipps**
Öffnen Sie das Plugin „Zoom“, um Details des Cursorbereichs präzise zu sehen.
Das Plugin „Pick“ kann ebenfalls zusammen mit Ruler verwendet werden, um den
Mittelpunkt eines Objekts zu bestimmen, wenn eines der Enden des Lineals
ausgerichtet wird.
