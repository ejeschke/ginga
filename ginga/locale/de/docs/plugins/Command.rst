Dieses Plugin bietet eine Befehlszeilenschnittstelle für den Referenzbetrachter.

.. note:: Die Befehlszeile ist zur Verwendung *innerhalb* der Plugin-Oberfläche
          gedacht.  Wenn Sie eine *entfernte* Befehlszeilenschnittstelle
          suchen, siehe das Plugin ``RC``.

**Plugin-Typ: Global**

``Command`` ist ein globales Plugin.  Es kann nur eine Instanz geöffnet werden.

**Verwendung**

Eine Liste der Befehle und Parameter abrufen::

        g> help

Einen Shell-Befehl ausführen::

        g> !cmd arg arg ...

**Hinweise**

Ein besonders mächtiges Werkzeug ist die Verwendung der Befehle
``reload_local`` und ``reload_global``, um ein Plugin neu zu laden, während Sie
dieses Plugin entwickeln.  So vermeiden Sie, den Referenzbetrachter neu starten
und mühsam Daten usw. neu laden zu müssen.  Schließen Sie einfach das Plugin,
führen Sie den passenden „reload“-Befehl aus (siehe die Hilfe!) und starten Sie
das Plugin dann erneut.

.. note:: Wenn Sie *andere* Module als das Plugin selbst geändert haben, werden
          diese von diesen Befehlen nicht neu geladen.
