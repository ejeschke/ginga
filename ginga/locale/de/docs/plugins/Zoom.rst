Das Plugin ``Zoom`` zeigt ein vergrößertes Bild eines Ausschnittsbereichs, der
unter der Cursorposition im zugehörigen Kanalbild zentriert ist.  Während der
Cursor über das Bild bewegt wird, aktualisiert sich das Zoombild, um eine genaue
Untersuchung der Pixel oder eine präzise Steuerung in Verbindung mit anderen
Plugin-Operationen zu ermöglichen.

**Plugin-Typ: Global**

``Zoom`` ist ein globales Plugin.  Es kann nur eine Instanz geöffnet werden.

**Verwendung**

Die Vergrößerung des Zoomfensters kann durch Anpassen des Schiebereglers
„Zoomstufe“ geändert werden.

Zwei Betriebsarten sind möglich -- absoluter und relativer Zoom:

* Im absoluten Modus steuert die Zoomstufe genau den im Ausschnitt gezeigten
  Zoomgrad; zum Beispiel kann das Kanalbild auf 10-fach vergrößert sein, doch
  das Zoombild zeigt nur ein 3-faches Bild, wenn die Zoomstufe auf 3-fach
  gesetzt ist.

* Im relativen Modus wird die Zoomstufen-Einstellung relativ zur Zoomeinstellung
  des Kanalbildes interpretiert.  Ist die Zoomstufe auf 3-fach gesetzt und das
  Kanalbild auf 10-fach gezoomt, so wird das gezeigte Zoombild 13-fach sein
  (10-fach + 3-fach).  Beachten Sie, dass die Zoomstufen-Einstellung < 1 sein
  kann, sodass eine Einstellung von 1/3-fach bei 3-fachem Zoom im Kanalbild ein
  1-fach-Zoombild erzeugt.

Die Einstellung „Aktualisierungsintervall“ steuert, wie schnell das Plugin
``Zoom`` auf die Bewegung des Cursors reagiert und das Zoombild aktualisiert.
Der Wert wird in Millisekunden angegeben.

.. tip:: Üblicherweise *verbessert* ein kleines Aktualisierungsintervall die
         allgemeine Reaktionsfähigkeit des Zoombildes, und der Standardwert von
         20 ist ein vernünftiger Wert.  Sie können mit dem Wert experimentieren,
         wenn das Zoombild zu ruckelig wirkt oder nicht mit der Mausbewegung im
         Kanalbildfenster synchron ist.

Die Schaltfläche „Standardwerte“ stellt die Standardeinstellungen der
Steuerelemente wieder her.

Es ist über ``~/.ginga/plugin_Zoom.cfg`` anpassbar, wobei ``~`` Ihr
HOME-Verzeichnis ist:

.. code-block:: Python

  #
  # Zoom plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_Zoom.cfg"

  # default zoom level
  zoom_amount = 3

  # refresh interval (sec)
  # NOTE: usually a small delay speeds things up
  refresh_interval = 0.02
