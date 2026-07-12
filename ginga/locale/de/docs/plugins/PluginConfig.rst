
Das Plugin ``PluginConfig`` ermöglicht es, die in Ihren Menüs sichtbaren
Plugins zu konfigurieren.

**Plugin-Typ: Global**

``PluginConfig`` ist ein globales Plugin.  Es kann nur eine Instanz geöffnet
werden.

**Verwendung**

``PluginConfig`` dient dazu, die in Ginga zu verwendenden Plugins zu
konfigurieren.  Zu den für jedes Plugin konfigurierbaren Punkten gehören:

* ob es aktiviert ist (und daher, ob es in den Menüs erscheint)
* die Kategorie des Plugins (zur Konstruktion der Menühierarchie verwendet)
* der Arbeitsbereich, in dem das Plugin geöffnet wird
* bei einem globalen Plugin, ob es beim Start des Referenzbetrachters
  automatisch startet
* ob der Plugin-Name verborgen werden soll (nicht in den
  Plugin-Aktivierungsmenüs erscheint)

Beim Start von ``PluginConfig`` wird eine Tabelle der Plugins angezeigt.  Um
die obigen Attribute für Plugins zu bearbeiten, klicken Sie auf „Bearbeiten“;
dadurch öffnet sich ein Dialog zum Bearbeiten der Tabelle.

Klicken Sie für jedes zu konfigurierende Plugin auf einen Eintrag in der
Haupttabelle, passen Sie dann die Einstellungen im Dialog an und klicken Sie
im Dialog auf „Setzen“, um die Änderungen in die Tabelle zu übernehmen.  Wenn
Sie nicht auf „Setzen“ klicken, wird in der Tabelle nichts geändert.  Wenn Sie
mit dem Bearbeiten der Konfigurationen fertig sind, klicken Sie im Dialog auf
„Schließen“, um den Bearbeitungsdialog zu schließen.

.. note:: Es wird nicht empfohlen, den Arbeitsbereich eines Plugins zu ändern,
          es sei denn, Sie wählen einen zum ursprünglichen größenkompatiblen
          Arbeitsbereich, da das Plugin sonst möglicherweise nicht korrekt
          angezeigt wird.  Im Zweifel lassen Sie den Arbeitsbereich
          unverändert.  Das Deaktivieren von Plugins in der Kategorie
          „Systems“ kann außerdem dazu führen, dass einige erwartete
          Funktionen nicht mehr funktionieren.


.. important:: Damit die Änderungen über Ginga-Neustarts hinweg erhalten
               bleiben, klicken Sie auf „Speichern“, um die Einstellungen zu
               speichern (in `$HOME/.ginga/plugins.json`).  Starten Sie Ginga
               neu, um Änderungen an den Menüs (durch „category“-Änderungen)
               zu sehen.  **Entfernen Sie diese Datei manuell, wenn Sie die
               Plugin-Konfigurationen auf die Standardwerte zurücksetzen
               möchten**.
