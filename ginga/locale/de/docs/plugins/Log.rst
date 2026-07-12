Betrachten Sie die Protokollausgabe des Referenzbetrachters.

**Plugin-Typ: Global**

``Log`` ist ein globales Plugin.  Es kann nur eine Instanz geöffnet werden.

**Verwendung**

Das Plugin ``Log`` baut eine Oberfläche mit einem großen, scrollbaren
Textwidget auf, das die laufende Ausgabe des Loggers anzeigt.  Die neueste
Ausgabe erscheint unten.  Dies kann bei der Fehlersuche nützlich sein.

Es gibt vier Steuerelemente:

* Mit dem Kombinationsfeld unten links wählen Sie die gewünschte
  Protokollierungsstufe.  Die vier Stufen sind, nach Ausführlichkeit
  geordnet: „debug“, „info“, „warn“ und „error“.
* Mit dem Feld mit der Zahl unten rechts legen Sie fest, wie viele
  Eingabezeilen im Anzeigepuffer behalten werden (z. B. nur die letzten
  1000 Zeilen behalten).
* Ist das Kontrollkästchen „Auto-Bildlauf“ aktiviert, scrollt das große
  Textwidget ans Ende, wenn neue Protokollmeldungen hinzukommen.  Deaktivieren
  Sie es, wenn Sie ältere Meldungen durchsehen und studieren möchten.
* Mit der Schaltfläche „Löschen“ wird das Textwidget geleert, sodass nur noch
  neue Protokolle erscheinen.
