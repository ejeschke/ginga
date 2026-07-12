Eseguire una rapida analisi stellare astronomica.

**Tipo di plugin: Locale**

``Pick`` è un plugin locale, il che significa che è associato a un canale.
Non è un singleton, il che significa che è possibile aprire più istanze per
ciascun canale.

**Uso**

Il plugin ``Pick`` serve a eseguire una rapida analisi della qualità dei dati
astronomici su oggetti stellari.  Localizza candidati stellari all'interno di un
riquadro disegnato e sceglie il candidato più probabile in base a un insieme di
impostazioni di ricerca.  La larghezza a metà altezza (FWHM) viene riportata per
l'oggetto candidato, così come la sua dimensione in base alla scala di lastra del
rivelatore.  Viene fatta anche una misura approssimativa di fondo, livello di
cielo e luminosità.

**Definire l'area di selezione**

L'area di selezione predefinita è definita come un riquadro di circa 30x30 pixel
che racchiude l'area di ricerca.

Il selettore sposta/disegna/modifica in fondo al plugin serve a determinare quale
operazione viene eseguita sull'area di selezione:

.. figure:: figures/pick-move-draw-edit.png
   :width: 400px
   :align: center
   :alt: Pulsanti Sposta, Disegna e Modifica

   Pulsanti « Sposta », « Disegna » e « Modifica ».

* Se è selezionato « sposta », puoi spostare l'area di selezione esistente
  trascinandola o cliccando dove vuoi collocarne il centro.  Se non c'è un'area
  esistente, ne verrà creata una predefinita.
* Se è selezionato « disegna », puoi disegnare una forma con il cursore per
  racchiudere e definire una nuova area di selezione.  La forma predefinita è un
  riquadro, ma nella scheda « Settings » si possono selezionare altre forme.
* Se è selezionato « modifica », puoi modificare l'area di selezione trascinandone
  i punti di controllo, o spostarla trascinando nel riquadro di delimitazione.

Dopo che l'area è stata spostata, disegnata o modificata, ``Pick`` cercherà
nell'area tutti i picchi e valuterà i picchi in base ai criteri nella scheda
« Settings » dell'interfaccia (vedi « La scheda Settings » sotto) e cercherà di
localizzare il miglior candidato corrispondente alle impostazioni.

.. note:: le caselle « Quick Mode » e « From Peak » sono state rimosse nella
          versione v4.0 di Ginga.

**Se viene trovato un candidato**

Il candidato verrà contrassegnato con un punto (di solito una « X ») nella tela
del visualizzatore di canale, centrato sull'oggetto come determinato dalle misure
FWHM orizzontale e verticale.

L'insieme superiore di schede dell'interfaccia verrà popolato come segue:

.. figure:: figures/pick-cutout.png
   :width: 400px
   :align: center
   :alt: Scheda Image dell'area di Pick

   Scheda « Image » dell'area di ``Pick``.

La scheda « Image » mostrerà il contenuto dell'area di ritaglio.  Il widget in
questa scheda è un widget Ginga e quindi può essere ingrandito e spostato con le
consuete associazioni di tastiera e mouse (ad es. rotellina di scorrimento).
Sarà anche contrassegnato con un punto centrato sull'oggetto e, inoltre, la
posizione di spostamento verrà impostata sul centro trovato.

.. figure:: figures/pick-contour.png
   :width: 300px
   :align: center
   :alt: Scheda Contour dell'area di Pick

   Scheda « Contour » dell'area di ``Pick``.

La scheda « Contour » mostrerà un grafico di contorno.  Questo è un grafico di
contorno dell'area immediatamente circostante il candidato, e di solito non
comprende l'intera regione dell'area di selezione.  Puoi usare la rotellina di
scorrimento per ingrandire il grafico e un clic della rotellina di scorrimento
(pulsante 2 del mouse) per impostare la posizione di spostamento nel grafico.

.. figure:: figures/pick-fwhm.png
   :width: 400px
   :align: center
   :alt: Scheda FWHM dell'area di Pick

   Scheda « FWHM » dell'area di ``Pick``.

La scheda « FWHM » mostrerà un grafico FWHM.  Le linee viola mostrano le misure
nella direzione X e le linee verdi mostrano le misure nella direzione Y.  Le
linee continue indicano i valori dei pixel reali e le linee punteggiate indicano
la funzione 1D adattata.  Le regioni ombreggiate viola e verde indicano le misure
FWHM per i rispettivi assi.

.. figure:: figures/pick-radial.png
   :width: 400px
   :align: center
   :alt: Scheda Radial dell'area di Pick

   Scheda « Radial » dell'area di ``Pick``.

La scheda « Radial » contiene un grafico di profilo radiale.  I punti tracciati in
viola sono valori di dati, e una linea viene adattata ai dati.

.. figure:: figures/pick-ee.png
   :width: 600px
   :align: center
   :alt: Scheda EE dell'area di Pick

   Scheda « EE » dell'area di ``Pick``.

La scheda « EE » contiene un grafico delle energie frazionarie racchiuse in un
cerchio e in un quadrato (EE) in viola e verde, rispettivamente, per il bersaglio
scelto.  Una semplice sottrazione del fondo viene fatta in modo coerente con i
calcoli FWHM prima che i valori EE vengano misurati.  I raggi di campionamento e
totale, mostrati come linee nere tratteggiate, possono essere impostati nella
scheda « Settings »; quando questi vengono cambiati, fai clic su « Redo Pick »
per aggiornare il grafico e le misure.  I valori EE misurati al raggio di
campionamento dato sono anche visualizzati nella scheda « Readout ».  Quando
viene richiesto il resoconto, i valori EE al raggio di campionamento dato e il
raggio stesso verranno registrati nella tabella « Report », insieme ad altre
informazioni.

Quando « Show Candidates » è attivo, i candidati vicino ai bordi del riquadro di
delimitazione non avranno valori EE (impostati a 0).

.. figure:: figures/pick-readout.png
   :width: 400px
   :align: center
   :alt: Scheda Readout dell'area di Pick

   Scheda « Readout » dell'area di ``Pick``.

La scheda « Readout » verrà popolata con un riepilogo delle misure.  Ci sono due
pulsanti e tre caselle di spunta in questa scheda:

* Il pulsante « Default Region » ripristina la regione di selezione alla forma e
  alla dimensione predefinite.
* Il pulsante « Pan to pick » sposterà il visualizzatore di canale sul centro
  localizzato.
* Se « Center on pick » è selezionato, la forma verrà ricentrata sul centro
  localizzato, se trovato (cioè la forma « segue » la selezione).

.. figure:: figures/pick-controls.png
   :width: 400px
   :align: center
   :alt: Scheda Controls dell'area di Pick

   Scheda « Controls » dell'area di ``Pick``.

La scheda « Controls » ha un paio di pulsanti che funzioneranno a partire dalle
misure.

* Il pulsante « Bg cut » imposterà il livello di taglio basso del visualizzatore
  di canale sul livello di fondo misurato.  Un delta a questo valore può essere
  applicato impostando un valore nella casella « Delta bg » (premi « Enter » per
  cambiare l'impostazione).
* Il pulsante « Sky cut » imposterà il livello di taglio basso del visualizzatore
  di canale sul livello di cielo misurato.  Un delta a questo valore può essere
  applicato impostando un valore nella casella « Delta sky » (premi « Enter » per
  cambiare l'impostazione).
* Il pulsante « Bright cut » imposterà il livello di taglio alto del
  visualizzatore di canale sui livelli misurati di cielo+luminosità.  Un delta a
  questo valore può essere applicato impostando un valore nella casella « Delta
  bright » (premi « Enter » per cambiare l'impostazione).

.. figure:: figures/pick-report.png
   :width: 400px
   :align: center
   :alt: Scheda Report dell'area di Pick

   Scheda « Report » dell'area di ``Pick``.

La scheda « Report » serve a registrare informazioni sulle misure in forma
tabellare.

Premendo il pulsante « Add Pick », le informazioni sul candidato più recente
vengono aggiunte alla tabella.  Se la casella « Record Picks automatically » è
selezionata, allora qualsiasi candidato viene aggiunto alla tabella
automaticamente.

.. note:: Se la casella « Show Candidates » nella scheda « Settings » è
          selezionata, allora *tutti* gli oggetti trovati nella regione (secondo
          le impostazioni) verranno aggiunti alla tabella invece del solo
          candidato selezionato.

Puoi cancellare la tabella in qualsiasi momento premendo il pulsante « Clear
Log ».  Il registro può essere salvato in una tabella inserendo un percorso e un
nome file validi nella casella « File: » e premendo « Save table ».  Il tipo di
file è determinato automaticamente dall'estensione data (ad es. « .fits » è FITS
e « .txt » è testo semplice).

**Se non viene trovato alcun candidato**

Se non è possibile trovare alcun candidato (in base alle impostazioni), allora
l'area di selezione viene contrassegnata con un punto rosso centrato sull'area di
selezione.

.. figure:: figures/pick-no-candidate.png
   :width: 800px
   :align: center
   :alt: Contrassegno quando non viene trovato alcun candidato

   Contrassegno quando non viene trovato alcun candidato.

Il ritaglio dell'immagine verrà preso da quest'area centrale e quindi la scheda
« Image » avrà ancora contenuto.  Sarà anche contrassegnato con una « X » rossa
centrale.

Il grafico di contorno verrà ancora prodotto dal ritaglio.

.. figure:: figures/pick-contour-no-candidate.png
   :width: 400px
   :align: center
   :alt: Contorno quando non viene trovato alcun candidato.

   Contorno quando non viene trovato alcun candidato.

Tutti gli altri grafici verranno cancellati.

**La scheda Settings**

.. figure:: figures/pick-settings.png
   :width: 400px
   :align: center
   :alt: Scheda Settings del plugin Pick

   Scheda « Settings » del plugin ``Pick``.

La scheda « Settings » controlla gli aspetti della ricerca all'interno dell'area
di selezione:

* La casella « Show Candidates » controlla se tutte le sorgenti rilevate sono
  contrassegnate o meno (come mostrato nella figura sotto).  Inoltre, se
  selezionata, tutti gli oggetti trovati vengono aggiunti alla tabella di
  registro della selezione quando si usano i controlli « Report ».
* Il parametro « Draw type » serve a scegliere la forma dell'area di selezione da
  disegnare.
* Il parametro « Radius » imposta il raggio da usare nel trovare e valutare i
  picchi luminosi nell'immagine.
* Il parametro « Threshold » serve a impostare una soglia per la ricerca dei
  picchi; se impostato a « None », verrà scelto un valore predefinito
  ragionevole.
* I parametri « Min FWHM » e « Max FWHM » possono servire a eliminare oggetti di
  certe dimensioni dall'essere candidati.
* Il parametro « Ellipticity » serve a eliminare candidati in base alla loro
  asimmetria di forma.
* Il parametro « Edge » serve a eliminare candidati in base a quanto sono vicini
  al bordo del ritaglio.  *NOTA: attualmente questo funziona in modo affidabile
  solo per forme rettangolari non ruotate.*
* Il parametro « Max side » serve a limitare la dimensione del riquadro di
  delimitazione che può essere usato nella forma di selezione.  Le dimensioni più
  grandi richiedono più tempo per essere valutate.
* Il parametro « Coordinate Base » è un offset da applicare alle sorgenti
  localizzate.  Impostalo a « 1 » se vuoi che le posizioni dei pixel delle
  sorgenti siano riportate in modo conforme a FITS e « 0 » se preferisci
  l'indicizzazione basata su 0.
* Il parametro « Calc center » serve a determinare se il centro è calcolato
  dall'adattamento FWHM (« fwhm ») o dal centroide (« centroid »).
* Il parametro « FWHM fitting » serve a determinare quale funzione è usata per
  l'adattamento FWHM (« gaussian » o « moffat »).  L'opzione di usare « lorentz »
  è anche disponibile se « calc_fwhm_lib » è impostato a « astropy » in
  ``~/.ginga/plugin_Pick.cfg``.
* Il parametro « Contour Interpolation » serve a impostare il metodo di
  interpolazione usato nel rendering dell'immagine di fondo nel grafico
  « Contour ».
* L'« EE total radius » definisce il raggio (per l'energia racchiusa in un
  cerchio) e la semilarghezza del riquadro (per l'energia racchiusa in un
  quadrato) in pixel dove ci si aspetta che la frazione EE sia 1 (cioè che tutto
  il flusso per una funzione di dispersione del punto sia contenuto all'interno).
* L'« EE sampling radius » è il raggio in pixel usato per campionare le curve EE
  misurate per il resoconto.

Il pulsante « Redo Pick » rieseguirà l'operazione di ricerca.  È comodo se hai
cambiato alcuni parametri e vuoi vedere l'effetto in base all'area di selezione
attuale senza disturbarla.

.. figure:: figures/pick-candidates.png
   :width: 600px
   :align: center
   :alt: Il visualizzatore di canale quando « Show Candidates » è selezionato.

   Il visualizzatore di canale quando « Show Candidates » è selezionato.

**Configurazione utente**

È personalizzabile usando ``~/.ginga/plugin_Pick.cfg``, dove ``~`` è la tua
directory HOME:

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
