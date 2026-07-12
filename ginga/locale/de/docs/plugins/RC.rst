
Das ``RC``-Plugin implementiert eine Fernsteuerungsschnittstelle für den
Ginga-Betrachter.

**Plugin-Typ: Global**

``RC`` ist ein globales Plugin.  Es kann nur eine Instanz geöffnet werden.

**Verwendung**

Das ``RC``-Plugin (Remote Control) bietet eine Möglichkeit, Ginga über eine
XML-RPC-Schnittstelle fernzusteuern.  Starten Sie das Plugin über das Menü
„Plugins“ (rufen Sie „Start RC“ auf) oder starten Sie ginga mit der
Kommandozeilenoption ``--modules=RC``, um es automatisch zu starten.

Standardmäßig startet das Plugin mit einem Server, der auf Port 11771 läuft und
an die localhost-Schnittstelle gebunden ist -- dies erlaubt Verbindungen nur vom
lokalen Host.  Wenn Sie dies ändern möchten, setzen Sie Host und Port im
Steuerelement „Set Addr“ und drücken Sie ``Enter`` -- Sie sollten sehen, wie die
Adresse im Anzeigefeld „Addr:“ aktualisiert wird.

Bitte beachten Sie, dass der Host-Teil (vor dem Doppelpunkt) nicht angibt, von
*welchem* Host aus Sie den Zugriff erlauben möchten, sondern an welche
Schnittstelle gebunden werden soll.  Wenn Sie jedem Host das Verbinden erlauben
möchten, lassen Sie ihn leer (aber schließen Sie den Doppelpunkt und die
Portnummer ein), damit der Server an alle Schnittstellen bindet.  Drücken Sie
dann „Restart“, um den Server an der neuen Adresse neu zu starten.

Sobald das Plugin gestartet ist, können Sie das ``ggrc``-Skript (enthalten, wenn
``ginga`` installiert ist) verwenden, um Ginga zu steuern.  Werfen Sie einen
Blick auf das Skript, wenn Sie sehen möchten, wie Sie Ihre eigene
programmatische Schnittstelle schreiben.

Beispielverwendung anzeigen::

        $ ggrc help

Hilfe für eine bestimmte Ginga-Methode anzeigen::

        $ ggrc help ginga <method>

Hilfe für eine bestimmte Kanalmethode anzeigen::

        $ ggrc help channel <chname> <method>

Ginga-Methoden (Betrachter-Shell) können so aufgerufen werden::

        $ ggrc ginga <method> <arg1> <arg2> ...

Kanalspezifische Methoden können so aufgerufen werden::

        $ ggrc channel <chname> <method> <arg1> <arg2> ...

Aufrufe können von einem entfernten Host aus durch Hinzufügen der Optionen
gemacht werden::

        --host=<hostname> --port=11771

(Entfernen Sie in der Plugin-GUI unbedingt das Präfix „localhost“ von der
„addr“, lassen Sie aber den Doppelpunkt und den Port.)

**Beispiele**

Einen neuen Kanal erstellen::

        $ ggrc ginga add_channel FOO

Eine Datei laden::

        $ ggrc ginga load_file /home/eric/testdata/SPCAM/SUPA01118797.fits

Eine Datei in einen bestimmten Kanal laden::

        $ ggrc ginga load_file /home/eric/testdata/SPCAM/SUPA01118797.fits FOO

Cut-Level::

        $ ggrc channel FOO cut_levels 163 1300

Automatische Cut-Level::

        $ ggrc channel FOO auto_levels

Auf einen bestimmten Grad zoomen::

        $ ggrc -- channel FOO zoom_to -7

(Beachten Sie die Verwendung von ``--``, um uns das Übergeben eines mit ``-``
beginnenden Parameters zu erlauben.)

Zum Anpassen zoomen::

        $ ggrc channel FOO zoom_fit

Transformieren (Argumente sind ein boolesches Tripel: ``flipx`` ``flipy``
``swapxy``)::

        $ ggrc channel FOO transform 1 0 1

Rotieren::

        $ ggrc channel FOO rotate 37.5

Farbkarte ändern::

        $ ggrc channel FOO set_color_map rainbow3

Algorithmus zur Farbverteilung ändern::

        $ ggrc channel FOO set_color_algorithm log

Intensitätskarte ändern::

        $ ggrc channel FOO set_intensity_map neg

In manchen Fällen müssen Sie möglicherweise auf Shell-Escapes zurückgreifen, um
bestimmte Zeichen an Ginga übergeben zu können.  Zum Beispiel wird ein
führendes Minuszeichen üblicherweise als Programmoption interpretiert.  Um eine
vorzeichenbehaftete Ganzzahl zu übergeben, müssen Sie möglicherweise so etwas
tun::

        $ ggrc -- channel FOO zoom -7

**Ansteuern aus Python heraus**

Es ist auch möglich, Ginga im RC-Modus aus Python heraus zu steuern.  Das
Folgende beschreibt einen Teil der Funktionalität.

*Verbinden*

Starten Sie zuerst Ginga und starten Sie das ``RC``-Plugin.  Dies kann von der
Kommandozeile aus geschehen::

        ginga --modules=RC

Verbinden Sie sich aus Python heraus mit einem ``RemoteClient``-Objekt wie
folgt::

        from ginga.util import grc
        host = 'localhost'
        port = grc.default_rc_port
        viewer = grc.RemoteClient(host, port)

Dieses viewer-Objekt ist nun mit dem Ginga über ``RC`` verknüpft.

*Ein Bild laden*

Sie können ein Bild aus dem Speicher in einen Kanal Ihrer Wahl laden.
Verbinden Sie sich zuerst mit einem Kanal::

        ch = viewer.channel('Image')

Laden Sie dann ein Numpy-Bild (d. h. ein beliebiges 2D-``ndarray``)::

        import numpy as np
        img = np.random.rand(500, 500) * 10000.0
        ch.load_np('Image_Name', img, 'fits', {})

Das Bild wird in Ginga angezeigt und kann wie gewohnt bearbeitet werden.

*Ein Leinwandobjekt überlagern*

Es ist möglich, Objekte zur Leinwand in einem bestimmten Kanal hinzuzufügen.
Verbinden Sie sich zuerst::

        canvas = viewer.canvas('Image')

Dies verbindet mit dem Kanal namens „Image“.  Sie können die in der Leinwand
gezeichneten Objekte löschen::

        canvas.clear()

Sie können auch jedes einfache Leinwandobjekt hinzufügen.  Der entscheidende
Punkt, den Sie beachten müssen, ist, dass die eingegebenen Objekte das
XMLRC-Protokoll durchlaufen müssen.  Dies bedeutet einfache Datentypen
(``float``, ``int``, ``list`` oder ``str``); keine Arrays.  Hier ist ein
Beispiel, um eine Linie durch eine Reihe von Punkten zu zeichnen, die durch zwei
Numpy-Arrays definiert sind::

        x = np.arange(100)
        y = np.sqrt(x)
        points = list(zip(x.tolist(), y.tolist()))
        canvas.add('path', points, color='red')

Dies zeichnet eine rote Linie auf dem Bild.
