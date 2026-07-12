
``Crosshair`` è un semplice plugin per disegnare mirini etichettati con la
posizione della croce in coordinate pixel, coordinate WCS o il valore del dato
alla posizione della croce.

**Tipo di plugin: Locale**

``Crosshair`` è un plugin locale, il che significa che è associato a un canale.
È possibile aprire un'istanza per ciascun canale.

**Uso**

Seleziona il tipo di output appropriato nella casella a discesa « Format »
nell'interfaccia: « xy » per le coordinate pixel, « coords » per le coordinate
WCS e « value » per il valore alla posizione del mirino.

Se « Solo trascina » è selezionato, il mirino viene aggiornato solo quando il
cursore viene cliccato o trascinato nella finestra.  Se non è selezionato, il
mirino viene posizionato semplicemente spostando il cursore nella finestra del
visualizzatore di canale.

La scheda « Cuts » contiene un grafico di profilo per i tagli verticale e
orizzontale rappresentati dal bordo visibile del riquadro presente quando
« Quick Cuts » è selezionato.  Questo grafico viene aggiornato in tempo reale man
mano che il mirino viene spostato.  Quando « Quick Cuts » non è selezionato, il
grafico non viene aggiornato.

La dimensione del riquadro è determinata dal parametro « radius ».

Il controllo « Livello di avviso » può essere usato per impostare un livello di
flusso oltre il quale viene indicato un avviso nel grafico dei tagli con una
linea gialla e lo sfondo che diventa giallo.  L'avviso viene attivato se un
qualsiasi valore lungo il taglio X o Y supera la soglia del livello di avviso.

Il controllo « Livello di allerta » è simile, ma rappresentato da una linea
rossa e lo sfondo che diventa rosa.  L'avviso viene attivato se un qualsiasi
valore lungo il taglio X o Y supera la soglia del livello di allerta.  Le
allerte hanno la precedenza sugli avvisi.

Sia la funzione « Avviso » sia « Allerta » possono essere disattivate
semplicemente impostando un valore vuoto.  Sono disattivate per impostazione
predefinita.

Il grafico dei tagli è interattivo, ma ha davvero senso usarlo solo se « Solo
trascina » è selezionato.  Puoi premere « x » o « y » nella finestra del grafico
per attivare e disattivare la funzione di scala automatica degli assi per l'uno
o l'altro asse, e scorrere nel grafico per ingrandire l'asse X (tieni premuto
Ctrl mentre scorri per ingrandire l'asse Y).

Crosshair fornisce una funzione di interazione con il plugin Pick: quando il
mirino è sopra un oggetto, puoi premere « r » nella finestra del visualizzatore
di canale per far invocare il plugin Pick su quella particolare posizione.  Se
un Pick non è già aperto su quel canale, verrà aperto per primo.

**Configurazione utente**

È personalizzabile usando ``~/.ginga/plugin_Crosshair.cfg``, dove ``~`` è la tua
directory HOME:

.. code-block:: Python

  #
  # Crosshair plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_Crosshair.cfg"

  # color of the crosshair
  color = 'green'

  # text color of crosshair
  text_color = 'skyblue'

  # box color indicating cut radius
  box_color = 'aquamarine'

  # cut plot line colors for X and Y
  quick_h_cross_color = '#7570b3'
  quick_v_cross_color = '#1b9e77'

  # enable quick cuts plots by default
  quick_cuts = False

  # force drag only by default
  drag_only = False

  # set a warning level for the warning feature of the cuts plot
  warn_level = None

  # set an alery level for the alert feature of the cuts plot
  alert_level = None

  # set initial radius of the cuts box
  cuts_radius = 15
