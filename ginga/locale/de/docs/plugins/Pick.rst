Schnelle astronomische Sternanalyse durchführen.

**Plugin-Typ: Lokal**

``Pick`` ist ein lokales Plugin, das heißt, es ist einem Kanal zugeordnet.
Es ist kein Singleton, das heißt, für jeden Kanal können mehrere Instanzen
geöffnet werden.

**Verwendung**

Das ``Pick``-Plugin wird verwendet, um eine schnelle Analyse der Datenqualität
astronomischer Sternobjekte durchzuführen.  Es lokalisiert Sternkandidaten
innerhalb eines gezeichneten Kastens und wählt den wahrscheinlichsten Kandidaten
auf Basis einer Reihe von Sucheinstellungen aus.  Die Halbwertsbreite (FWHM)
wird für das Kandidatenobjekt gemeldet, ebenso seine Größe auf Basis des
Plattenmaßstabs des Detektors.  Auch eine grobe Messung von Hintergrund,
Himmelspegel und Helligkeit wird vorgenommen.

**Den Pick-Bereich definieren**

Der standardmäßige Pick-Bereich ist als Kasten von etwa 30x30 Pixeln definiert,
der den Suchbereich umschließt.

Der Verschieben/Zeichnen/Bearbeiten-Selektor am unteren Rand des Plugins wird
verwendet, um zu bestimmen, welche Operation am Pick-Bereich vorgenommen wird:

.. figure:: figures/pick-move-draw-edit.png
   :width: 400px
   :align: center
   :alt: Schaltflächen „Verschieben“, „Zeichnen“ und „Bearbeiten“

   Schaltflächen „Verschieben“, „Zeichnen“ und „Bearbeiten“.

* Ist „Verschieben“ ausgewählt, können Sie den vorhandenen Pick-Bereich durch
  Ziehen verschieben oder klicken, wo Sie seine Mitte platzieren möchten.  Gibt
  es keinen vorhandenen Bereich, wird ein Standardbereich erstellt.
* Ist „Zeichnen“ ausgewählt, können Sie mit dem Cursor eine Form zeichnen, um
  einen neuen Pick-Bereich zu umschließen und zu definieren.  Die Standardform
  ist ein Kasten, doch im Reiter „Settings“ können andere Formen gewählt werden.
* Ist „Bearbeiten“ ausgewählt, können Sie den Pick-Bereich durch Ziehen seiner
  Kontrollpunkte bearbeiten oder ihn durch Ziehen im Begrenzungsrahmen
  verschieben.

Nachdem der Bereich verschoben, gezeichnet oder bearbeitet wurde, durchsucht
``Pick`` den Bereich nach allen Spitzenwerten und bewertet die Spitzenwerte
anhand der Kriterien im Reiter „Settings“ der Benutzeroberfläche (siehe „Der
Settings-Reiter“ unten) und versucht, den besten zu den Einstellungen passenden
Kandidaten zu lokalisieren.

.. note:: Die Kontrollkästchen „Quick Mode“ und „From Peak“ wurden in der
          Ginga-Version v4.0 entfernt.

**Wenn ein Kandidat gefunden wird**

Der Kandidat wird mit einem Punkt (üblicherweise einem „X“) in der
Kanalbetrachter-Leinwand markiert, zentriert auf dem Objekt, wie durch die
horizontalen und vertikalen FWHM-Messungen bestimmt.

Der obere Satz von Reitern in der Benutzeroberfläche wird wie folgt gefüllt:

.. figure:: figures/pick-cutout.png
   :width: 400px
   :align: center
   :alt: Image-Reiter des Pick-Bereichs

   „Image“-Reiter des ``Pick``-Bereichs.

Der Reiter „Image“ zeigt den Inhalt des Ausschnittsbereichs.  Das Widget in
diesem Reiter ist ein Ginga-Widget und kann daher mit den üblichen Tastatur- und
Mausbindungen (z. B. Scrollrad) gezoomt und geschwenkt werden.  Es wird ebenfalls
mit einem auf dem Objekt zentrierten Punkt markiert, und zusätzlich wird die
Schwenkposition auf das gefundene Zentrum gesetzt.

.. figure:: figures/pick-contour.png
   :width: 300px
   :align: center
   :alt: Contour-Reiter des Pick-Bereichs

   „Contour“-Reiter des ``Pick``-Bereichs.

Der Reiter „Contour“ zeigt ein Konturdiagramm.  Dies ist ein Konturdiagramm des
Bereichs unmittelbar um den Kandidaten, das üblicherweise nicht die gesamte
Region des Pick-Bereichs umfasst.  Sie können mit dem Scrollrad das Diagramm
zoomen und mit einem Klick des Scrollrads (Maustaste 2) die Schwenkposition im
Diagramm setzen.

.. figure:: figures/pick-fwhm.png
   :width: 400px
   :align: center
   :alt: FWHM-Reiter des Pick-Bereichs

   „FWHM“-Reiter des ``Pick``-Bereichs.

Der Reiter „FWHM“ zeigt ein FWHM-Diagramm.  Die violetten Linien zeigen Messungen
in X-Richtung und die grünen Linien zeigen Messungen in Y-Richtung.  Die
durchgezogenen Linien geben die tatsächlichen Pixelwerte an und die gepunkteten
Linien die angepasste 1D-Funktion.  Die schattierten violetten und grünen
Bereiche geben die FWHM-Messungen für die jeweiligen Achsen an.

.. figure:: figures/pick-radial.png
   :width: 400px
   :align: center
   :alt: Radial-Reiter des Pick-Bereichs

   „Radial“-Reiter des ``Pick``-Bereichs.

Der Reiter „Radial“ enthält ein Radialprofildiagramm.  Die violett geplotteten
Punkte sind Datenwerte, und eine Linie wird an die Daten angepasst.

.. figure:: figures/pick-ee.png
   :width: 600px
   :align: center
   :alt: EE-Reiter des Pick-Bereichs

   „EE“-Reiter des ``Pick``-Bereichs.

Der Reiter „EE“ enthält ein Diagramm der fraktionalen umkreisten und
umquadrierten Energien (EE) in Violett bzw. Grün für das gewählte Ziel.  Eine
einfache Hintergrundsubtraktion wird auf eine Weise durchgeführt, die mit den
FWHM-Berechnungen konsistent ist, bevor die EE-Werte gemessen werden.  Die
Abtast- und Gesamtradien, gezeigt als schwarze gestrichelte Linien, können im
Reiter „Settings“ gesetzt werden; wenn diese geändert werden, klicken Sie auf
„Redo Pick“, um das Diagramm und die Messungen zu aktualisieren.  Die gemessenen
EE-Werte beim gegebenen Abtastradius werden auch im Reiter „Readout“ angezeigt.
Wenn ein Bericht angefordert wird, werden die EE-Werte beim gegebenen
Abtastradius und der Radius selbst zusammen mit anderen Informationen unter der
Tabelle „Report“ aufgezeichnet.

Wenn „Show Candidates“ aktiv ist, haben die Kandidaten in der Nähe der Ränder des
Begrenzungsrahmens keine EE-Werte (auf 0 gesetzt).

.. figure:: figures/pick-readout.png
   :width: 400px
   :align: center
   :alt: Readout-Reiter des Pick-Bereichs

   „Readout“-Reiter des ``Pick``-Bereichs.

Der Reiter „Readout“ wird mit einer Zusammenfassung der Messungen gefüllt.  In
diesem Reiter gibt es zwei Schaltflächen und drei Kontrollkästchen:

* Die Schaltfläche „Default Region“ stellt die Pick-Region auf die Standardform
  und -größe zurück.
* Die Schaltfläche „Pan to pick“ schwenkt den Kanalbetrachter zum lokalisierten
  Zentrum.
* Ist „Center on pick“ aktiviert, wird die Form auf dem lokalisierten Zentrum
  neu zentriert, falls gefunden (d. h. die Form „folgt“ dem Pick).

.. figure:: figures/pick-controls.png
   :width: 400px
   :align: center
   :alt: Controls-Reiter des Pick-Bereichs

   „Controls“-Reiter des ``Pick``-Bereichs.

Der Reiter „Controls“ hat ein paar Schaltflächen, die anhand der Messungen
arbeiten.

* Die Schaltfläche „Bg cut“ setzt den unteren Cut-Level des Kanalbetrachters auf
  den gemessenen Hintergrundpegel.  Ein Delta zu diesem Wert kann durch Setzen
  eines Wertes im Feld „Delta bg“ angewendet werden (drücken Sie „Enter“, um die
  Einstellung zu ändern).
* Die Schaltfläche „Sky cut“ setzt den unteren Cut-Level des Kanalbetrachters auf
  den gemessenen Himmelspegel.  Ein Delta zu diesem Wert kann durch Setzen eines
  Wertes im Feld „Delta sky“ angewendet werden (drücken Sie „Enter“, um die
  Einstellung zu ändern).
* Die Schaltfläche „Bright cut“ setzt den oberen Cut-Level des Kanalbetrachters
  auf die gemessenen Himmels- und Helligkeitspegel.  Ein Delta zu diesem Wert
  kann durch Setzen eines Wertes im Feld „Delta bright“ angewendet werden
  (drücken Sie „Enter“, um die Einstellung zu ändern).

.. figure:: figures/pick-report.png
   :width: 400px
   :align: center
   :alt: Report-Reiter des Pick-Bereichs

   „Report“-Reiter des ``Pick``-Bereichs.

Der Reiter „Report“ wird verwendet, um Informationen über die Messungen in
tabellarischer Form aufzuzeichnen.

Durch Drücken der Schaltfläche „Add Pick“ werden die Informationen über den
neuesten Kandidaten zur Tabelle hinzugefügt.  Ist das Kontrollkästchen „Record
Picks automatically“ aktiviert, werden alle Kandidaten automatisch zur Tabelle
hinzugefügt.

.. note:: Ist das Kontrollkästchen „Show Candidates“ im Reiter „Settings“
          aktiviert, werden *alle* in der Region gefundenen Objekte (gemäß den
          Einstellungen) statt nur des ausgewählten Kandidaten zur Tabelle
          hinzugefügt.

Sie können die Tabelle jederzeit durch Drücken der Schaltfläche „Clear Log“
leeren.  Das Protokoll kann in eine Tabelle gespeichert werden, indem Sie einen
gültigen Pfad und Dateinamen in das Feld „File:“ eingeben und „Save table“
drücken.  Der Dateityp wird automatisch anhand der angegebenen Erweiterung
bestimmt (z. B. ist „.fits“ FITS und „.txt“ ist reiner Text).

**Wenn kein Kandidat gefunden wird**

Kann kein Kandidat gefunden werden (basierend auf den Einstellungen), wird der
Pick-Bereich mit einem roten Punkt markiert, der auf dem Pick-Bereich zentriert
ist.

.. figure:: figures/pick-no-candidate.png
   :width: 800px
   :align: center
   :alt: Markierung, wenn kein Kandidat gefunden wird

   Markierung, wenn kein Kandidat gefunden wird.

Der Bildausschnitt wird aus diesem zentralen Bereich genommen, sodass der Reiter
„Image“ dennoch Inhalt hat.  Er wird auch mit einem zentralen roten „X“ markiert.

Das Konturdiagramm wird weiterhin aus dem Ausschnitt erzeugt.

.. figure:: figures/pick-contour-no-candidate.png
   :width: 400px
   :align: center
   :alt: Kontur, wenn kein Kandidat gefunden wird.

   Kontur, wenn kein Kandidat gefunden wird.

Alle anderen Diagramme werden geleert.

**Der Settings-Reiter**

.. figure:: figures/pick-settings.png
   :width: 400px
   :align: center
   :alt: Settings-Reiter des Pick-Plugins

   „Settings“-Reiter des ``Pick``-Plugins.

Der Reiter „Settings“ steuert Aspekte der Suche innerhalb des Pick-Bereichs:

* Das Kontrollkästchen „Show Candidates“ steuert, ob alle erkannten Quellen
  markiert werden oder nicht (wie in der Abbildung unten gezeigt).  Zusätzlich
  werden, falls aktiviert, alle gefundenen Objekte zur Pick-Protokolltabelle
  hinzugefügt, wenn die „Report“-Steuerelemente verwendet werden.
* Der Parameter „Draw type“ wird verwendet, um die Form des zu zeichnenden
  Pick-Bereichs zu wählen.
* Der Parameter „Radius“ setzt den Radius, der beim Finden und Bewerten heller
  Spitzenwerte im Bild verwendet wird.
* Der Parameter „Threshold“ wird verwendet, um einen Schwellenwert für das Finden
  von Spitzenwerten zu setzen; ist er auf „None“ gesetzt, wird ein sinnvoller
  Standardwert gewählt.
* Die Parameter „Min FWHM“ und „Max FWHM“ können verwendet werden, um Objekte
  bestimmter Größe von den Kandidaten auszuschließen.
* Der Parameter „Ellipticity“ wird verwendet, um Kandidaten anhand ihrer
  Asymmetrie in der Form auszuschließen.
* Der Parameter „Edge“ wird verwendet, um Kandidaten anhand ihrer Nähe zum Rand
  des Ausschnitts auszuschließen.  *HINWEIS: Derzeit funktioniert dies
  zuverlässig nur für nicht gedrehte rechteckige Formen.*
* Der Parameter „Max side“ wird verwendet, um die Größe des Begrenzungsrahmens zu
  begrenzen, der in der Pick-Form verwendet werden kann.  Größere Größen dauern
  länger zum Auswerten.
* Der Parameter „Coordinate Base“ ist ein Offset, der auf lokalisierte Quellen
  angewendet wird.  Setzen Sie ihn auf „1“, wenn Sie Pixelpositionen von Quellen
  in FITS-konformer Weise gemeldet haben möchten, und auf „0“, wenn Sie
  0-basierte Indizierung bevorzugen.
* Der Parameter „Calc center“ wird verwendet, um zu bestimmen, ob das Zentrum aus
  der FWHM-Anpassung („fwhm“) oder durch Schwerpunktbildung („centroid“)
  berechnet wird.
* Der Parameter „FWHM fitting“ wird verwendet, um zu bestimmen, welche Funktion
  für die FWHM-Anpassung verwendet wird („gaussian“ oder „moffat“).  Die Option,
  „lorentz“ zu verwenden, ist ebenfalls verfügbar, wenn „calc_fwhm_lib“ in
  ``~/.ginga/plugin_Pick.cfg`` auf „astropy“ gesetzt ist.
* Der Parameter „Contour Interpolation“ wird verwendet, um die
  Interpolationsmethode zu setzen, die beim Rendern des Hintergrundbildes im
  „Contour“-Diagramm verwendet wird.
* Der „EE total radius“ definiert den Radius (für umkreiste Energie) und die
  halbe Kastenbreite (für umquadrierte Energie) in Pixeln, wo der EE-Anteil
  voraussichtlich 1 beträgt (d. h. der gesamte Fluss für eine
  Punktspreizfunktion enthalten ist).
* Der „EE sampling radius“ ist der Radius in Pixeln, der verwendet wird, um die
  gemessenen EE-Kurven für die Berichterstattung abzutasten.

Die Schaltfläche „Redo Pick“ wiederholt die Suchoperation.  Sie ist praktisch,
wenn Sie einige Parameter geändert haben und die Wirkung basierend auf dem
aktuellen Pick-Bereich sehen möchten, ohne ihn zu stören.

.. figure:: figures/pick-candidates.png
   :width: 600px
   :align: center
   :alt: Der Kanalbetrachter, wenn „Show Candidates“ aktiviert ist.

   Der Kanalbetrachter, wenn „Show Candidates“ aktiviert ist.

**Benutzerkonfiguration**

Es ist über ``~/.ginga/plugin_Pick.cfg`` anpassbar, wobei ``~`` Ihr
HOME-Verzeichnis ist:

.. code-block:: Python

  #
  # Pick plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_Pick.cfg"

  color_pick = 'green'
  shape_pick = 'box'
  color_candidate = 'purple'

  # Offset to add to Pick results. Default is 1.0 for FITS like indexing,
  # set to 0.0 here if you prefer numpy-like 0-based indexing
  pixel_coords_offset = 0.0

  # Maximum side for a pick region
  max_side = 1024

  # For image cutout viewer ("Image" tab)
  # you can set autozoom and autocuts preferences
  cutout_autozoom = 'override'
  cutout_autocuts = 'off'

  # For contour plot ("Contour" tab)
  # widget type: let choose automatically or force 'ginga' or 'matplotlib'
  # (choice of 'ginga' requires scikit-image to be installed)
  contour_widget = 'choose'
  # if ginga widget is chosen, you can set autozoom and autocuts preferences
  contour_autozoom = 'override'
  contour_autocuts = 'override'
  num_contours = 8
  # How big of a radius are we willing to consider from the center of the
  # pick?  bigger numbers == slower
  contour_size_min = 10
  contour_size_limit = 70

  # should the pick shape recenter on the found object center, if any?
  # useful for "tracking" an object that is moving from image to image
  center_on_pick = False

  # Star candidate search parameters
  radius = 10
  # Set threshold to None to auto calculate it
  threshold = None
  # Minimum and maximum fwhm to be considered a candidate
  min_fwhm = 1.5
  max_fwhm = 50.0
  # Minimum ellipticity to be considered a candidate
  min_ellipse = 0.5
  # Percentage from edge to be considered a candidate
  edge_width = 0.01
  # Graphically indicate all possible considered candidates
  show_candidates = False

  # Center of object is based on FWHM ("fwhm") or centroid ("centroid")
  # calculation:
  calc_center_alg = 'centroid'

  # Library to use for FWHM fitting ("native" or "astropy")
  calc_fwhm_lib = 'native'

  # Fitting function to use for FWHM ("gaussian" or "moffat")
  calc_fwhm_alg = 'gaussian'

  # Defaults for delta cut levels (in Controls tab)
  delta_sky = 0.0
  delta_bright = 0.0

  # Encircled and ensquared energy (EE) calculations:
  # a. Radius (pixel) where EE fraction is expected to be 1.
  ee_total_radius = 10.0
  # b. Radius (pixel) to sample EE for reporting.
  ee_sampling_radius = 2.5

  # use a different color/intensity map than channel image?
  pick_cmap_name = None
  pick_imap_name = None

  # For Reports tab
  record_picks = True

  # Set this to a file name, if None a filename will be automatically chosen
  report_log_path = None
