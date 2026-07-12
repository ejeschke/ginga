
Download-GUI für den Ginga-Referenzbetrachter.

**Plugin-Typ: Global**

``Download`` ist ein globales Plugin.  Es kann nur eine Instanz geöffnet werden.

**Verwendung**

Öffnen Sie dieses Plugin, um den Fortschritt von URI-Downloads zu überwachen.
Starten Sie es über das Menü „Plugins“ oder „Operations“ und wählen Sie das
Plugin „Downloads“ unter der Kategorie „Util“ aus.

Wenn Sie einen Download starten möchten, ziehen Sie einfach eine URI in einen
Kanalbildbetrachter oder in den ``Thumbs``-Bereich.

Sie können die Informationen über einen Download jederzeit entfernen, indem Sie
für seinen Eintrag auf die Schaltfläche „Löschen“ klicken.  Sie können die
Einträge für alle Downloads löschen, indem Sie unten auf die Schaltfläche „Alle
löschen“ klicken.

Derzeit ist es nicht möglich, einen laufenden Download abzubrechen.

**Einstellungen**

Die Option ``auto_clear_download`` bewirkt, wenn auf `True` gesetzt, dass ein
Download-Eintrag automatisch aus dem Bereich gelöscht wird, wenn der Download
abgeschlossen ist.  Sie entfernt keine heruntergeladenen Dateien.

Der Download-Ordner kann benutzerdefiniert sein, indem der Einstellung
„download_folder“ in ~/.ginga/general.cfg ein Wert zugewiesen wird.  Ist er
nicht zugewiesen, wird standardmäßig ein Ordner im plattformspezifischen
Standard-Temp-Verzeichnis verwendet (wie vom Python-Modul „tempfile“ angegeben).
