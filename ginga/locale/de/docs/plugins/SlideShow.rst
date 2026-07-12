Eine Diashow von Bildern abspielen.

**Plugin-Typ: Lokal**

``SlideShow`` ist ein lokales Plugin, das heißt, es ist einem Kanal zugeordnet.
Es ist kein Singleton, das heißt, für jeden Kanal können mehrere Instanzen
geöffnet werden.

**Verwendung**

***Laden einer Diashow***

Nach dem Start des Plugins können Sie mit der Schaltfläche „Laden“ eine Diashow
laden (siehe unten für das Diashow-Dateiformat).  Sie können diese Diashow
jederzeit neu laden, nachdem Sie die Datei extern bearbeitet haben, indem Sie
„Neu laden“ drücken.

***Abspielen einer Diashow***

Mit den Schaltflächen „Zurück“ und „Weiter“ können Sie manuell rückwärts und
vorwärts in der Liste navigieren.  Das Drehfeld zwischen diesen beiden
Schaltflächen bringt Sie zu einer bestimmten Folie in der Liste.

Die Schaltflächen „Starten“ und „Stopp“ werden verwendet, um das automatische
Weiterschalten innerhalb der Diashow zu starten oder zu stoppen.

***Steuern der Dauer***

Jede Folie kann einen eigenen „duration“-Parameter (in Sekunden) haben, der
steuert, wie lange gewartet wird, bevor zur nächsten Folie gewechselt wird;
fehlt dieser bei einer Folie, wird die Standarddauer verwendet.  Die
Standarddauer kann über das Steuerelement „Standarddauer“ eingestellt werden.

Unter dem Steuerelement für die Standarddauer befindet sich eine Beschriftung,
die die Dauer der Folie und die Gesamtdauer der Show anzeigt.

**Diashow-Dateiformat**

Das Diashow-Dateiformat ist eine kommagetrennte (CSV) Klartextdatei mit einer
Kopfzeile.  Die Datei muss mindestens eine Spalte mit dem Titel „file“
enthalten.  Diese Spalte enthält die Dateinamen (relativ oder absolut) der
Pfade zu den für jede Folie zu ladenden Dateien.

***Optionale Spalten***

* „duration“:  sollte die Dauer (in Sekunden) für jede Folie enthalten
* „position“: gibt die Position der Folie in der Show an.
  Fließkommazahlen können verwendet werden, um das Umordnen der Folien beim
  Bearbeiten der Diashow-Datei zu erleichtern.
