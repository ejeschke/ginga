Das Plugin ``ColorMapPicker`` dient dazu, grafisch eine Farbkarte für einen
Kanal-Bildbetrachter zu durchsuchen und auszuwählen.

**Plugin-Typ: Global oder Lokal**

``ColorMapPicker`` ist ein hybrides globales/lokales Plugin, das heißt, es kann
auf beide Arten aufgerufen werden.  Als lokales Plugin ist es einem Kanal
zugeordnet, und für jeden Kanal kann eine Instanz geöffnet werden.  Es kann
auch als globales Plugin geöffnet werden.

**Verwendung**

Die Bedienung des Plugins ist sehr einfach: Die Farbkarten werden in Form von
Farbbalken und Beschriftungen im Hauptansichtsbereich des Plugins angezeigt.
Klicken Sie auf einen der Balken, um die Farbkarte des zugehörigen Kanals (bei
Aufruf als lokales Plugin) oder des aktuell aktiven Kanals (bei Aufruf als
globales Plugin) festzulegen.

Sie können vertikal scrollen oder die Bildlaufleisten verwenden, um durch die
Farbbalken-Muster zu blättern.

.. note:: Wenn das Plugin zum ersten Mal startet, erzeugt es ein
          RGB-Bitmap-Bild mit Farbbalken und Beschriftungen für alle
          verfügbaren Farbkarten.  Je nach Anzahl der installierten Farbkarten
          kann dies einige Sekunden dauern.

          Die Farbkarten werden mit der angewendeten Intensitätskarte „ramp“
          angezeigt.
