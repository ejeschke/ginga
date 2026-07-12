``AutoLoad`` ist ein einfaches Plugin, das einen Ordner auf neue Dateien
überwacht und sie automatisch in einen Kanal lädt, sobald sie erscheinen.

**Plugin-Typ: Lokal**

``AutoLoad`` ist ein lokales Plugin, das heißt, es ist einem Kanal zugeordnet.
Für jeden Kanal kann eine Instanz geöffnet werden.

.. note:: Um dieses Plugin zu verwenden, müssen Sie das Python-Paket
          „watchdog“ installieren.

**Verwendung**

* Um einen zu überwachenden Ordner einzurichten, geben Sie im Feld
  „Überwachter Ordner“ einen Ordnerpfad (Verzeichnis) ein und drücken Sie die
  Eingabetaste oder klicken Sie auf „Setzen“.
* Wenn Sie zwischen den Dateien, die diesem Ordner hinzugefügt werden,
  unterscheiden möchten, können Sie im Feld „Regex-Muster“ einen regulären
  Python-Ausdruck eingeben und auf „Setzen“ klicken.  Nur Dateien mit
  Namen, die dem Muster entsprechen, werden berücksichtigt.  Beachten Sie, dass
  der reguläre Ausdruck nur für den Dateinamen gilt, nicht für einen Teil des
  Ordnerpfads.
* Wenn Sie das automatische Laden pausieren möchten, können Sie das
  Kontrollkästchen „Automatisches Laden pausieren“ aktivieren; dies stoppt
  jedes automatische Laden.  Beachten Sie, dass Dateien, die in der
  Zwischenzeit eingetroffen sind, nicht geladen werden, wenn Sie das Kästchen
  anschließend wieder deaktivieren.

.. note:: Das Überwachen von Ordnern auf Netzlaufwerken funktioniert
          möglicherweise nicht.

**Benutzerkonfiguration**
