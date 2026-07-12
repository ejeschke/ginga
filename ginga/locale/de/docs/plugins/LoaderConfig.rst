Das Plugin ``LoaderConfig`` ermöglicht es, die Datei-Öffner zu konfigurieren,
mit denen verschiedene Inhalte in Ginga geladen werden können.

Registrierte Datei-Öffner sind mit MIME-Typen von Dateien verknüpft, und für
einen einzelnen MIME-Typ kann es mehrere Öffner geben.  Eine mit einer
MIME-Typ/Öffner-Paarung verknüpfte Priorität bestimmt, welcher Öffner für jeden
Typ verwendet wird -- der niedrigste Prioritätswert bestimmt, welcher Öffner
verwendet wird.  Gibt es mehrere Öffner mit derselben niedrigen Priorität, so
wird der Benutzer beim Öffnen einer Datei in Ginga gefragt, welcher Öffner
verwendet werden soll.  Mit diesem Plugin lassen sich die Öffner-Einstellungen
festlegen und im Konfigurationsbereich $HOME/.ginga des Benutzers speichern.

**Plugin-Typ: Global**

``LoaderConfig`` ist ein globales Plugin.  Es kann nur eine Instanz geöffnet
werden.

**Verwendung**

Nach dem Start des Plugins zeigt die Anzeige alle registrierten MIME-Typen und
die für diese Typen registrierten Öffner mit einer zugehörigen Priorität für
jede MIME-Typ/Öffner-Paarung.

Wählen Sie eine oder mehrere Zeilen aus und geben Sie im Feld „Priorität:“ eine
Priorität für sie ein; drücken Sie „Setzen“ (oder die Eingabetaste), um die
Priorität dieser Einträge festzulegen.

.. note:: Je niedriger die Zahl, desto höher die Priorität.  Negative Zahlen
          sind zulässig, und die Standardpriorität für einen Lader ist
          üblicherweise 0.  Sind beispielsweise für einen MIME-Typ zwei Lader
          verfügbar und ist die eine Priorität auf -1 und die andere auf 0
          gesetzt, wird der mit -1 verwendet, ohne den Benutzer zu fragen.


Klicken Sie auf „Speichern“, um die Prioritäten in
$HOME/.ginga/loaders.json zu speichern, sodass sie bei späteren Neustarts des
Programms neu geladen und verwendet werden.
