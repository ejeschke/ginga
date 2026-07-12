
Masken aus einer Datei (nicht-interaktiver Modus) auf einem Bild anzeigen.

**Plugin-Typ: Lokal**

``TVMask`` ist ein lokales Plugin, das heißt, es ist einem Kanal zugeordnet.
Für jeden Kanal kann eine Instanz geöffnet werden.

**Verwendung**

Dieses Plugin ermöglicht die nicht-interaktive Anzeige einer Maske durch
Einlesen einer FITS-Datei, wobei Werte ungleich null als maskierte Daten
angenommen werden.

Um verschiedene Masken anzuzeigen (z. B. einige grün und einige rosa maskiert,
wie oben gezeigt):

1. Wählen Sie Grün aus dem Auswahlmenü.  Alternativ geben Sie den gewünschten
   Alphawert ein.
2. Laden Sie mit der Schaltfläche „Maske laden“ die entsprechende FITS-Datei.
3. Wiederholen Sie (1), wählen aber nun Rosa aus dem Auswahlmenü.
4. Wiederholen Sie (2), wählen aber eine andere FITS-Datei.
5. Um eine dritte Maske ebenfalls rosa anzuzeigen, wiederholen Sie (4), ohne das
   Auswahlmenü zu ändern.

Das Auswählen eines Eintrags (oder mehrerer Einträge) aus der Tabellenliste hebt
die Maske(n) auf dem Bild hervor.  Die Hervorhebung verwendet eine vordefinierte
Farbe und ein vordefiniertes Alpha (unten anpassbar).

Sie können auch alle Masken innerhalb eines Bereichs sowohl auf dem Bild als
auch in der Tabellenliste hervorheben, indem Sie ein Rechteck auf dem Bild
zeichnen, während dieses Plugin aktiv ist.

Das Drücken der Schaltfläche „Verbergen“ verbirgt die Masken, löscht aber nicht
den Speicher des Plugins; das heißt, wenn Sie „Anzeigen“ drücken, erscheinen
dieselben Masken wieder auf demselben Bild.  Das Drücken von „Vergessen“ löscht
die Masken jedoch sowohl aus der Anzeige als auch aus dem Speicher; das heißt,
Sie müssen Ihre Datei(en) neu laden, um die Masken wiederherzustellen.

Um dieselben Masken mit anderer Farbe oder anderem Alpha neu zu zeichnen,
drücken Sie „Vergessen“ und wiederholen die obigen Schritte nach Bedarf.

Wenn Bilder mit sehr unterschiedlichen Ausrichtungen/Abmessungen im selben Kanal
angezeigt werden, erscheinen Masken, die zu einem Bild gehören, aber außerhalb
eines anderen liegen, in Letzterem nicht.

Um eine Maske zu erstellen, die dieses Plugin lesen kann, können Sie Ergebnisse
des ``Drawing``-Plugins verwenden (drücken Sie nach dem Zeichnen „Maske
erstellen“ und speichern Sie die Maske mit ``SaveImage``), oder eine FITS-Datei
von Hand mit ``astropy.io.fits`` usw. erstellen.

Zusammen mit ``TVMark`` verwendet, können Sie in Ginga sowohl Punktquellen als
auch maskierte Bereiche überlagern.

Es ist über ``~/.ginga/plugin_TVMask.cfg`` anpassbar, wobei ``~`` Ihr
HOME-Verzeichnis ist:

.. code-block:: Python

  #
  # TVMask plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_TVMask.cfg"

  # Mask color -- Any color name accepted by Ginga
  maskcolor = 'green'

  # Mask alpha (transparency) -- 0=transparent, 1=opaque
  maskalpha = 0.5

  # Highlighted mask color and alpha
  hlcolor = 'white'
  hlalpha = 1.0
