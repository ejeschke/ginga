Ein Plugin zum grafischen Darstellen der Pixelwerte entlang einer geraden
Linie, die einen Datenwürfel halbiert.

**Plugin-Typ: Lokal**

``LineProfile`` ist ein lokales Plugin, das heißt, es ist einem Kanal
zugeordnet.  Für jeden Kanal kann eine Instanz geöffnet werden.

**Verwendung**

.. warning::

   Es gibt keine Einschränkungen, welche Achsen gewählt werden können.
   Daher kann das Diagramm bedeutungslos sein.

Das Plugin ``LineProfile`` wird für mehrdimensionale (d. h. 3D oder höher)
Bilder verwendet.  Es stellt die Werte der Pixel an der aktuellen
Cursorposition entlang der gewählten Achse dar; oder, wenn ein Bereich
ausgewählt ist, den Mittelwert in jedem Frame.  Damit lassen sich normale
Spektrallinienprofile erstellen.  Am Datenpunkt des aktuell angezeigten Frames
wird eine Markierung gesetzt.

Die angezeigte X-Achse wird aus den Schlüsselwörtern ``CRVAL*``, ``CDELT*``,
``CRPIX*``, ``CTYPE*`` und ``CUNIT*`` des FITS-Headers konstruiert.  Ist eines
der Schlüsselwörter nicht verfügbar, greift die Achse stattdessen auf die
``NAXIS*``-Werte zurück.

Die angezeigte Y-Achse wird aus ``BTYPE`` und ``BUNIT`` konstruiert.  Sind diese
nicht verfügbar, beschriftet sie die Pixelwerte einfach als „Signal“.

So verwenden Sie dieses Plugin:

1. Wählen Sie eine Achse.
2. Wählen Sie einen Punkt oder zeichnen Sie mit dem Cursor einen Bereich.
3. Verwenden Sie ``MultiDim``, um die Schrittwerte der Achsen zu ändern,
   falls zutreffend.
