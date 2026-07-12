Änderungen an den Kanaleinstellungen grafisch in der Benutzeroberfläche
vornehmen.

**Plugin-Typ: Lokal**

``Preferences`` ist ein lokales Plugin, das heißt, es ist einem Kanal zugeordnet.
Für jeden Kanal kann eine Instanz geöffnet werden.

**Verwendung**

Das ``Preferences``-Plugin legt die Einstellungen *auf Kanalbasis* fest.  Die
Einstellungen für einen bestimmten Kanal werden vom Kanal „Image“ geerbt, bis
sie explizit mit diesem Plugin gesetzt und gespeichert werden.

Wird „Save Settings“ gedrückt, werden die Einstellungen im Ordner
$HOME/.ginga des Benutzers gespeichert (eine Datei „channel_NAME.cfg“ für jeden
Kanal NAME), sodass ein Kanal mit demselben Namen, der in zukünftigen
Ginga-Sitzungen erstellt wird, dieselben Einstellungen erhält.

**Farbverteilungs-Einstellungen**

.. figure:: figures/cdist-prefs.png
   :width: 400px
   :align: center
   :alt: Farbverteilungs-Einstellungen

   „Color Distribution“-Einstellungen.

Die „Color Distribution“-Einstellungen steuern die Einstellungen für die
Umwandlung von Datenwert zu Farbindex, die stattfindet, nachdem die Cut-Level
angewendet wurden und kurz bevor die endgültige Farbzuordnung durchgeführt wird.
Sie betrifft, wie die Werte zwischen dem unteren und oberen Cut-Level auf die
Farb- und Intensitätszuordnungsphase verteilt werden.

Das Steuerelement „Algorithm“ wird verwendet, um den für die Zuordnung
verwendeten Algorithmus festzulegen.  Klicken Sie auf das Steuerelement, um die
Liste anzuzeigen, oder scrollen Sie einfach mit dem Mausrad, während sich der
Cursor über dem Steuerelement befindet.  Es sind acht Algorithmen verfügbar:
linear, log, power, sqrt, squared, asinh, sinh und histeq.  Der Name jedes
Algorithmus gibt an, wie die Daten den Farben in der Farbkarte zugeordnet
werden.  „linear“ ist die Standardeinstellung.

**Farbzuordnungs-Einstellungen**

.. figure:: figures/cmap-prefs.png
   :width: 400px
   :align: center
   :alt: Farbzuordnungs-Einstellungen

   „Color Mapping“-Einstellungen.

Die „Color Mapping“-Einstellungen steuern die Einstellungen für die Farbkarte
und die Intensitätskarte, die während der letzten Phase des
Farbzuordnungsprozesses verwendet werden.  Zusammen mit den „Color
Distribution“-Einstellungen steuern diese die Zuordnung von Datenwerten zu einer
visuellen 24-bpp-RGB-Darstellung.

Das Steuerelement „Colormap“ wählt aus, welche Farbkarte geladen und verwendet
werden soll.  Klicken Sie auf das Steuerelement, um die Liste anzuzeigen, oder
scrollen Sie einfach mit dem Mausrad, während sich der Cursor über dem
Steuerelement befindet.

.. note:: Ginga wird mit einer guten Auswahl an Farbkarten geliefert, doch wenn
          Sie mehr möchten, können Sie eigene hinzufügen oder, falls
          ``matplotlib`` installiert ist, alle laden, die es hat.  Siehe
          „Customizing Ginga“ für Details.

Das Steuerelement „Intensity“ wählt aus, welche Intensitätskarte mit der
Farbkarte verwendet werden soll.  Die Intensitätskarte wird kurz vor der
Farbkarte angewendet und kann verwendet werden, um die standardmäßige lineare
Werteskala in eine invertierte, logarithmische usw. Skala zu ändern.

Das Kontrollkästchen „Invert CMap“ kann verwendet werden, um die ausgewählte
Farbkarte zu invertieren (beachten Sie, dass eine Reihe von Farbkarten auch aus
dem „Colormap“-Steuerelement in invertierter Form auswählbar sind).

Das Steuerelement „Rotate“ kann verwendet werden, um die Farbkarte zu drehen,
während die Schaltfläche „Unrotate CMap“ die Drehung in ihren standardmäßigen,
ungedrehten Zustand zurückversetzt.

Die Schaltfläche „Color Defaults“ setzt alle Farbzuordnungs-Steuerelemente auf
die Standardwerte zurück: „gray“-Farbkarte, „ramp“-Intensität (linear) und keine
Invertierung oder Drehung der Farbkarte.

**Kontrast- und Helligkeits-(Bias-)Einstellungen**

.. figure:: figures/contrast-prefs.png
   :width: 400px
   :align: center
   :alt: Kontrast- und Helligkeits-(Bias-)Einstellungen

   „Contrast and Brightness (Bias)“-Einstellungen.

Die Steuerelemente „Contrast“ und „Brightness“ setzen den Kontrast und die
Helligkeit (auch „Bias“) des Betrachters.  Sie bieten eine Alternative zu 1) der
Verwendung des Kontrastmodus im Betrachterfenster oder 2) der Manipulation der
Farbleiste durch Ziehen (zum Setzen von Helligkeit/Bias) oder Scrollen (zum
Setzen des Kontrasts).

Die Steuerelemente „Default Contrast“ und „Default Brightness“ setzen ihre
jeweiligen Einstellungen auf den Standardwert zurück.

**Auto-Cuts-Einstellungen**

.. figure:: figures/autocuts-prefs.png
   :width: 400px
   :align: center
   :alt: Auto-Cuts-Einstellungen

   „Auto Cuts“-Einstellungen.

Die „Auto Cuts“-Einstellungen steuern die Berechnung der Cut-Level für die
Ansicht, wenn die Schaltfläche oder Taste für automatische Cut-Level gedrückt
wird oder wenn ein neues Bild mit aktivierten Auto-Cuts geladen wird.  Sie
können die Cut-Level auch von hier aus manuell setzen.

Die Felder „Cut Low“ und „Cut High“ können verwendet werden, um untere und obere
Cut-Level manuell anzugeben.  Das Drücken von „Cut Levels“ setzt die Level
manuell auf diese Werte.  Fehlt ein Wert, wird angenommen, dass er standardmäßig
dem aktuellen Wert entspricht.

Das Drücken von „Auto Levels“ berechnet die Level gemäß einem Algorithmus.  Das
Steuerelement „Auto Method“ wird verwendet, um zu wählen, welcher
Auto-Cuts-Algorithmus verwendet wird: „minmax“ (Minimum-Maximum-Werte),
„median“ (basierend auf Medianfilterung), „histogram“ (basierend auf einem
Bildhistogramm), „stddev“ (basierend auf der Standardabweichung der Pixelwerte)
oder „zscale“ (basierend auf dem von IRAF populär gemachten ZSCALE-Algorithmus).
Wenn der Algorithmus geändert wird, können sich auch die Felder darunter ändern,
um Änderungen an Parametern zu ermöglichen, die für jeden Algorithmus spezifisch
sind.

**Transformations-Einstellungen**

.. figure:: figures/transform-prefs.png
   :width: 400px
   :align: center
   :alt: Transformations-Einstellungen

   „Transform“-Einstellungen.

Die „Transform“-Einstellungen ermöglichen das Transformieren der Bildansicht,
indem die Ansicht in X oder Y gespiegelt, die X- und Y-Achsen vertauscht oder
das Bild um beliebige Beträge gedreht wird.

Die Kontrollkästchen „Flip X“ und „Flip Y“ bewirken, dass die Bildansicht in der
entsprechenden Achse gespiegelt wird.

Das Kontrollkästchen „Swap XY“ bewirkt, dass die Bildansicht durch Vertauschen
der X- und Y-Achsen geändert wird.  Dies kann mit „Flip X“ und „Flip Y“
kombiniert werden, um das Bild in 90-Grad-Schritten zu drehen.  Diese Ansichten
werden schneller gerendert als beliebige Drehungen mit dem „Rotate“-
Steuerelement.

Das Steuerelement „Rotate“ dreht die Bildansicht um den angegebenen Betrag.  Der
Wert sollte in Grad angegeben werden.  „Rotate“ kann in Verbindung mit Spiegeln
und Vertauschen angegeben werden.

Die Schaltfläche „Restore“ stellt die Ansicht in die Standardansicht zurück, die
ungespiegelt, unvertauscht und ungedreht ist.

**WCS-Einstellungen**

.. figure:: figures/wcs-prefs.png
   :width: 400px
   :align: center
   :alt: WCS-Einstellungen

   „WCS“-Einstellungen.

Die „WCS“-Einstellungen steuern die Anzeigeeinstellungen für die Berechnungen
des Weltkoordinatensystems (WCS), die verwendet werden, um die Cursorposition im
Bild zu melden.

Das Steuerelement „WCS Coords“ wird verwendet, um das Koordinatensystem
auszuwählen, in dem das Ergebnis angezeigt wird.

Das Steuerelement „WCS Display“ wird verwendet, um eine sexagesimale
(``H:M:S``)-Anzeige oder eine Dezimalgrad-Anzeige auszuwählen.

**Zoom-Einstellungen**

.. figure:: figures/zoom-prefs.png
   :width: 400px
   :align: center
   :alt: Zoom-Einstellungen

   „Zoom“-Einstellungen.

Die „Zoom“-Einstellungen steuern das Zoom-/Skalierungsverhalten von Ginga.
Ginga unterstützt zwei Zoom-Algorithmen, die über das Steuerelement „Zoom Alg“
gewählt werden:

* Der „step“-Algorithmus zoomt das Bild in diskreten Schritten von 1X, 2X, 3X
  usw. hinein oder in Schritten von 1/2X, 1/3X, 1/4X usw. hinaus.  Dieser
  Algorithmus führt visuell zu den wenigsten Artefakten, ist aber beim Zoomen
  über weite Bereiche mit einer Scrollbewegung etwas langsamer, weil mehr „Weg“
  erforderlich ist, um eine große Zoom-Änderung zu erreichen (dies ist nicht der
  Fall, wenn man die Zoom-Kurztasten wie die Zifferntasten verwendet).

* Der „rate“-Algorithmus zoomt das Bild, indem er die Skalierung mit einer Rate
  vorantreibt, die durch den Wert im Feld „Zoom Rate“ definiert ist.  Diese Rate
  ist standardmäßig die Quadratwurzel von 2.  Größere Zahlen bewirken größere
  Skalierungsänderungen zwischen Zoom-Stufen.  Wenn Sie Ihre Bilder schnell
  zoomen möchten, mit geringen Einbußen bei der Bildqualität, würden Sie
  wahrscheinlich diese Option wählen wollen.

Beachten Sie, dass unabhängig davon, welche Methode für den Zoom-Algorithmus
gewählt wird, der Zoom durch Gedrückthalten von ``Ctrl`` (grob) oder ``Shift``
(fein) beim Scrollen gesteuert werden kann, um die Zoom-Rate einzuschränken
(unter Annahme der Standard-Mausbindungen).

Das Steuerelement „Stretch XY“ kann verwendet werden, um eine der Achsen (X oder
Y) relativ zur anderen zu strecken.  Wählen Sie mit diesem Steuerelement eine
Achse und rollen Sie das Scrollrad, während Sie über dem Steuerelement „Stretch
Factor“ schweben, um die Pixel in der ausgewählten Achse zu strecken.

Die Steuerelemente „Scale X“ und „Scale Y“ bieten direkten Zugriff auf die
zugrunde liegende Skalierung und umgehen die diskreten Zoom-Schritte.  Hier
können exakte Werte eingegeben werden, um das Bild zu skalieren.  Umgekehrt sehen
Sie, wie sich diese Werte ändern, während das Bild gezoomt wird.

Die Steuerelemente „Scale Min“ und „Scale Max“ können verwendet werden, um eine
Grenze festzulegen, wie stark das Bild skaliert werden kann.

Das Steuerelement „Interpolation“ ermöglicht es Ihnen, zu wählen, wie das Bild
interpoliert wird.  Je nachdem, welche Unterstützungspakete installiert sind,
können die folgenden Optionen gewählt werden:

* „basic“ ist Nächster-Nachbar mit einem eingebauten Algorithmus, dies ist immer
  verfügbar, ist einigermaßen schnell und ist die Standardeinstellung.
* „area“
* „bicubic“
* „lanczos“
* „linear“
* „nearest“ ist Nächster-Nachbar (mit Unterstützungspaket)

Die Schaltfläche „Zoom Defaults“ setzt die Steuerelemente auf die
Ginga-Standardwerte zurück.

**Schwenk-Einstellungen**

.. figure:: figures/pan-prefs.png
   :width: 400px
   :align: center
   :alt: Schwenk-Einstellungen

   „Pan“-Einstellungen.

Die „Pan“-Einstellungen steuern das Schwenkverhalten von Ginga.

Die Steuerelemente „Pan X“ und „Pan Y“ bieten direkten Zugriff, um die
Schwenkposition im Bild zu setzen (der Teil des Bildes, der sich in der Mitte des
Fensters befindet) -- Sie sehen sie sich ändern, während Sie im Bild
umherschwenken.  Sie können diese Werte setzen und dann „Apply Pan“ drücken, um
zu dieser exakten Position zu schwenken.

Ist das Steuerelement „Pan Coord“ auf „data“ gesetzt, wird das Schwenken durch
Datenkoordinaten im Bild gesteuert; ist es auf „WCS“ gesetzt, sind die in den
Steuerelementen „Pan X“ und „Pan Y“ gezeigten Werte WCS-Koordinaten (unter
Annahme eines gültigen WCS im Bild).  Im letzteren Fall kann das Steuerelement
„WCS sexagesimal“ deaktiviert bleiben, um die Koordinaten in Grad anzuzeigen/zu
setzen, oder aktiviert werden, um die Werte in standardmäßiger sexagesimaler
Notation anzuzeigen/zu setzen.

Die Schaltfläche „Center Image“ setzt die Schwenkposition auf die Mitte des
Bildes, berechnet durch Halbieren der Abmessungen in X und Y.

Das Kontrollkästchen „Mark Center“ bewirkt, wenn aktiviert, dass Ginga ein
kleines Fadenkreuz in der Mitte des Bildes zeichnet.  Dies ist nützlich, um die
Schwenkposition zu kennen und zum Debuggen.

**Allgemeine Einstellungen**

.. figure:: figures/general-prefs.png
   :width: 400px
   :align: center
   :alt: Allgemeine Einstellungen

   „General“-Einstellungen.

Die Einstellung „Num Images“ gibt an, wie viele Bilder in diesem Kanal in Puffern
gehalten werden können, bevor sie ausgeworfen werden.  Ein Wert von null (0)
bedeutet unbegrenzt -- Bilder werden nie ausgeworfen.  Wurde ein Bild aus einem
zugänglichen Speicher geladen und wird ausgeworfen, wird es automatisch neu
geladen, wenn das Bild durch Navigieren im Kanal erneut aufgerufen wird.

Die Einstellung „Sort Order“ bestimmt, ob Bilder im Kanal alphabetisch nach Name
oder nach der Zeit, zu der sie geladen wurden, sortiert werden.  Dies betrifft
hauptsächlich die Reihenfolge, in der Bilder durchlaufen werden, wenn die
Aufwärts-/Abwärts-„Pfeil“-Tasten oder -Schaltflächen verwendet werden, und nicht
unbedingt, wie sie in Plugins wie „Contents“ oder „Thumbs“ angezeigt werden (die
im Allgemeinen ihre eigene Einstellungspräferenz für die Anordnung haben).

Das Kontrollkästchen „Use scrollbars“ steuert, ob der Kanalbetrachter
Bildlaufleisten um den Rand des Betrachterrahmens anzeigt, um das Bild zu
schwenken.

**Reset-(Betrachter-)Einstellungen**

.. figure:: figures/reset-prefs.png
   :width: 400px
   :align: center
   :alt: Reset-(Betrachter-)Einstellungen

   „Reset“-(Betrachter-)Einstellungen.

Jeder Kanalbetrachter hat ein *Betrachterprofil*, das auf den Zustand des
Betrachters unmittelbar nach der Erstellung und der Wiederherstellung der
gespeicherten Einstellungen für diesen Kanal initialisiert wird.  Beim Wechseln
zwischen Bildern können die Attribute des Betrachters gemäß den aktivierten
Kästchen in diesem Abschnitt auf dieses Profil zurückgesetzt werden.  *Ist nichts
aktiviert, wird nichts aus dem Betrachterprofil zurückgesetzt*.

Um diese Funktion zu nutzen, setzen Sie Ihre Betrachtereinstellungen wie
gewünscht und klicken Sie auf die Schaltfläche „Update Viewer Profile“ am unteren
Rand des Plugins.  Aktivieren Sie nun, welche Elemente zwischen Bildern auf diese
Werte zurückgesetzt werden sollen.  Klicken Sie schließlich auf die Schaltfläche
„Save Settings“ am unteren Rand, wenn diese Einstellungen über Ginga-Neustarts
hinweg beständig sein und als Standard-Benutzerprofil für diesen Kanal gesetzt
werden sollen, wenn Sie ginga neu starten und diesen Kanal neu erstellen.

* „Reset Scale“ setzt die Zoom-(Skalierungs-)Stufe auf das Betrachterprofil
  zurück
* „Reset Pan“ setzt die Schwenkposition auf das Betrachterprofil zurück
* „Reset Transform“ setzt alle Flip-/Swap-Transformationen auf das
  Betrachterprofil zurück
* „Reset Rotation“ setzt jede Drehung auf das Betrachterprofil zurück
* „Reset Cuts“ setzt alle Cut-Level auf das Betrachterprofil zurück
* „Reset Distribution“ setzt jede Farbverteilung auf das Betrachterprofil zurück
* „Reset Contrast“ setzt jeden Kontrast/Bias auf das Betrachterprofil zurück
* „Reset Color Map“ setzt alle Farbkarten-Einstellungen auf das Betrachterprofil
  zurück

.. tip:: Wenn Sie diese Funktion verwenden, möchten Sie vielleicht auch
         „Remember (Image) Preferences“ setzen (siehe unten).

.. note:: Die vollständige Reihenfolge der Anpassungen ist:

          * alle Reset-Elemente aus dem Standard-Betrachterprofil, falls
            vorhanden
          * alle gemerkten Elemente aus dem Bildprofil werden angewendet, falls
            vorhanden
          * alle automatischen Anpassungen (cuts/zoom/center) werden angewendet,
            falls sie nicht durch eine gemerkte Einstellung überschrieben wurden

**Remember-(Bild-)Einstellungen**

.. figure:: figures/remember-prefs.png
   :width: 400px
   :align: center
   :alt: Remember-(Bild-)Einstellungen

   „Remember“-(Bild-)Einstellungen.

Wird ein Bild geladen, wird ein *Bildprofil* erstellt und an die Bildmetadaten im
Kanal angehängt.  Diese Profile werden kontinuierlich mit dem Betrachterzustand
aktualisiert, während das Bild bearbeitet wird.  Die „Remember“-Einstellungen
steuern, welche Attribute dieser Profile in den Betrachterzustand
wiederhergestellt werden, wenn das Bild im Kanal (zurück-)navigiert wird:

* „Remember Scale“ stellt die Zoom-(Skalierungs-)Stufe des Bildes wieder her
* „Remember Pan“ stellt die Schwenkposition im Bild wieder her
* „Remember Transform“ stellt alle Flip- oder Swap-Achsen-Transformationen wieder
  her
* „Remember Rotation“ stellt jede Drehung des Bildes wieder her
* „Remember Cuts“ stellt alle Cut-Level für das Bild wieder her
* „Remember Distribution“ stellt jede Farbverteilung (linear, log usw.) wieder
  her
* „Remember Contrast“ stellt jede Kontrast-/Bias-Anpassung wieder her
* „Remember Color Map“ stellt alle getroffenen Farbkarten-Auswahlen wieder her

*Ist nichts aktiviert, wird nichts aus dem Bildprofil wiederhergestellt*.

.. note:: Diese Elemente werden gesetzt, BEVOR irgendwelche automatischen
          (cut/zoom/center new) Anpassungen vorgenommen werden.  Ist ein
          gemerktes Element gesetzt, überschreibt es jede automatische
          Anpassungseinstellung für den Kanal.

.. tip:: Wenn Sie diese Funktion verwenden, möchten Sie vielleicht auch
         „Reset (Viewer) Preferences“ setzen (siehe oben).

***Ein Beispiel***

Als Beispiel für die Verwendung der Reset- und Remember-Einstellungen nehmen wir
an, dass Sie häufig die Kontrastanpassung verwenden.  Sie möchten, dass der
Kontrast, den Sie mit einem bestimmten Bild setzen, wiederhergestellt wird, wenn
dieses Bild erneut betrachtet wird.  Wenn Sie jedoch ein neues Bild betrachten,
möchten Sie, dass der Kontrast bei einer normalen Einstellung beginnt.

Um dies zu erreichen, setzen Sie den Kontrast manuell auf die gewünschte
Standardeinstellung.  Aktivieren Sie „Reset Contrast“ und drücken Sie dann
„Update Viewer Profile“.  Aktivieren Sie schließlich „Remember Contrast“.
Klicken Sie auf „Save Settings“, um die Kanaleinstellungen beständig zu machen.

**Einstellungen für neue Bilder**

.. figure:: figures/newimages-prefs.png
   :width: 400px
   :align: center
   :alt: Einstellungen für neue Bilder

   „New Image“-Einstellungen.

Die „New Images“-Einstellungen bestimmen, wie Ginga reagiert, wenn ein neues Bild
in den Kanal geladen wird.  *Dies schließt ein, wenn ein älteres Bild erneut
aufgerufen wird, indem man auf sein Miniaturbild im ``Thumbs``-Plugin klickt oder
auf seinen Namen im ``Contents``-Plugin doppelklickt*.

Die Einstellung „Cut New“ steuert, ob eine automatische Cut-Level-Berechnung am
neuen Bild durchgeführt werden soll oder ob die aktuell gesetzten Cut-Level
angewendet werden sollen.  Die möglichen Einstellungen sind:

* „off“: immer die aktuell gesetzten Cut-Level verwenden;
* „once“: neue Cut-Level für das erste besuchte Bild berechnen, dann auf „off“
  schalten;
* „override“: neue Cut-Level berechnen, bis der Benutzer sie durch manuelles
  Setzen eines Cut-Levels überschreibt, dann auf „off“ schalten; oder
* „on“: immer neue Cut-Level berechnen.

.. tip:: Die Einstellung „override“ ist für den Komfort automatischer Cut-Level
         vorgesehen, während verhindert wird, dass ein manuell gesetzter Cut
         überschrieben wird, wenn ein neues Bild aufgenommen wird.  Wenn im
         Bildfenster getippt, kann die Semikolon-Taste verwendet werden, um den
         Modus zurück auf override (von „off“) zu schalten, während der
         Doppelpunkt die Einstellung auf „on“ setzt.  Das ``Info``-Plugin (Tab:
         Synopsis) zeigt den Zustand dieser Einstellung.

Die Einstellung „Zoom New“ steuert, ob das Besuchen eines Bildes die Zoom-Stufe
setzen soll, um das Bild an das Fenster anzupassen.  Die möglichen Einstellungen
sind:

* „off“: immer die aktuell gesetzten Zoom-Stufen verwenden;
* „once“: das erste Bild an das Fenster anpassen, dann auf „off“ schalten;
* „override“: Bilder werden automatisch angepasst, bis die Zoom-Stufe manuell
  geändert wird, dann wechselt der Modus automatisch auf „off“; oder
* „on“: das neue Bild wird immer zum Anpassen gezoomt.

.. tip:: Die Einstellung „override“ ist für den Komfort eines automatischen Zooms
         vorgesehen, während verhindert wird, dass eine manuell gesetzte
         Zoom-Stufe überschrieben wird, wenn ein neues Bild aufgenommen wird.
         Wenn im Bildfenster getippt, kann die Apostroph-Taste (auch
         „einfaches Anführungszeichen“) verwendet werden, um den Modus zurück auf
         „override“ (von „off“) zu schalten, während das Anführungszeichen (auch
         „doppeltes Anführungszeichen“) die Einstellung auf „on“ setzt.  Das
         ``Info``-Plugin (Tab: Synopsis) zeigt den Zustand dieser Einstellung.

Die Einstellung „Center New“ steuert, ob das Besuchen eines Bildes bewirken soll,
dass die Schwenkposition auf die Mitte des Bildes zurückgesetzt wird.  Die
möglichen Einstellungen sind:

* „off“: die aktuelle Schwenkposition unverändert lassen;
* „once“: das erste besuchte Bild zentrieren, dann auf „off“ schalten;
* „override“: Bilder werden automatisch zentriert, bis die Schwenkposition
  manuell geändert wird, dann wechselt der Modus automatisch auf „off“; oder
* „on“: das neue Bild wird immer zentriert.

Die Einstellung „Follow New“ wird verwendet, um zu steuern, ob Ginga die Anzeige
ändert, wenn ein neues Bild in den Kanal geladen wird.  Ist es deaktiviert, wird
das Bild geladen (wie z. B. an seinem Erscheinen im ``Thumbs``-Tab zu sehen),
doch die Anzeige wechselt nicht zum neuen Bild.  Diese Einstellung ist in Fällen
nützlich, in denen neue Bilder durch ein automatisiertes Mittel in einen Kanal
geladen werden und der Benutzer das aktuelle Bild studieren möchte, ohne
unterbrochen zu werden.

Die Einstellung „Raise New“ steuert, ob Ginga den Tab eines Kanals hervorhebt,
wenn ein Bild in diesen Kanal geladen wird.  Ist es deaktiviert, hebt Ginga den
Tab nicht hervor, wenn ein Bild in diesen bestimmten Kanal geladen wird.

Die Einstellung „Create Thumbnail“ steuert, ob Ginga ein Miniaturbild für in
diesen Kanal geladene Bilder erstellt.  In Fällen, in denen viele Bilder häufig
in einen Kanal geladen werden (z. B. ein niederfrequenter Videofeed), kann es
unerwünscht sein, für alle Miniaturbilder zu erstellen.

Die Einstellung „Auto Orient“ steuert, ob Ginga versuchen soll, Bilder
standardmäßig gemäß den Bildmetadaten auszurichten.  Dies ist derzeit nur für
RGB-Bilder (z. B. JPEG) nützlich, die solche Metadaten enthalten.  Es richtet
derzeit nicht nach WCS aus.

**ICC-Profile-Einstellungen**

.. figure:: figures/icc-prefs.png
   :width: 400px
   :align: center
   :alt: ICC-Profile-Einstellungen

   „ICC Profiles“-Einstellungen.

Ginga kann ICC-Profile (Farbmanagement) in der Rendering-Kette mithilfe der
LittleCMS-Bibliothek nutzen.

.. note:: Um ICC-Profile zu nutzen, erstellen Sie einen „profiles“-Ordner im
          Ginga-„Home“ (üblicherweise $HOME/.ginga) und legen Sie alle
          notwendigen Profile dort ab.  Ein Arbeitsprofil sollte gesetzt werden,
          indem ein Wert für „icc_working_profile“ in Ihrer Datei
          $HOME/.ginga/general.cfg hinzugefügt wird -- geben Sie keinen
          führenden Pfad an, nur den Dateinamen einer ICC-Datei im
          profiles-Ordner.  Dies wird verwendet, um alle RGB-Dateien, die ein
          Profil enthalten, in das Arbeitsprofil umzuwandeln.

Sie können die Ausgabeprofile für jeden Kanal in diesem Abschnitt des
Preferences-Plugins setzen.

Das Steuerelement „Output ICC profile“ wählt aus, welches Profil für das
Ausgabe-Rendering an die Anzeige verwendet werden soll.  Die Auswahl stammt aus
Ihren Profildateien in $HOME/.ginga/profiles.  Normalerweise sollte dies ein
Anzeigeprofil sein.

Das Steuerelement „Rendering intent“ wählt den Algorithmus, der zum Rendern der
Farbe im ICC-Umwandlungsprozess verwendet wird.  Die Auswahl ist:

* absolute_colorimetric
* perceptual
* relative_colorimetric
* saturation

„Proof ICC profile“ und „Proof intent“ werden ähnlich für das Proofing gewählt.

Das Kontrollkästchen „Black point compensation“ schaltet diese Funktion im
Farbumwandlungsprozess ein oder aus.  Siehe die Dokumentation zu LittleCMS oder
zum ICC-Farbmanagement im Allgemeinen für Details zu diesen Auswahlmöglichkeiten.
