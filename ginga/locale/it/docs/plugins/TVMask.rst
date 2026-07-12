
Visualizzare maschere da un file (modalità non interattiva) su un'immagine.

**Tipo di plugin: Locale**

``TVMask`` è un plugin locale, il che significa che è associato a un canale.
È possibile aprire un'istanza per ciascun canale.

**Uso**

Questo plugin consente la visualizzazione non interattiva di una maschera
leggendo un file FITS, dove si assume che i valori diversi da zero siano dati
mascherati.

Per visualizzare maschere diverse (ad es. alcune mascherate in verde e altre in
rosa, come mostrato sopra):

1. Seleziona verde dal menu a discesa.  In alternativa, inserisci il valore alfa
   desiderato.
2. Usando il pulsante « Carica maschera », carica il file FITS pertinente.
3. Ripeti (1) ma ora seleziona rosa dal menu a discesa.
4. Ripeti (2) ma scegli un altro file FITS.
5. Per visualizzare una terza maschera anch'essa in rosa, ripeti (4) senza
   cambiare il menu a discesa.

Selezionare una voce (o più voci) dall'elenco della tabella evidenzierà la/le
maschera/e sull'immagine.  L'evidenziazione usa un colore e un alfa predefiniti
(personalizzabili di seguito).

Puoi anche evidenziare tutte le maschere all'interno di una regione sia
sull'immagine sia nell'elenco della tabella, disegnando un rettangolo
sull'immagine mentre questo plugin è attivo.

Premere il pulsante « Nascondi » nasconderà le maschere ma non cancella la
memoria del plugin; ovvero, quando premi « Mostra », le stesse maschere
riappariranno sulla stessa immagine.  Premere « Dimentica », invece, cancellerà
le maschere sia dalla visualizzazione sia dalla memoria; ovvero, dovrai
ricaricare il/i file per ricreare le maschere.

Per ridisegnare le stesse maschere con colore o alfa diverso, premi
« Dimentica » e ripeti i passaggi precedenti, secondo necessità.

Se nello stesso canale vengono visualizzate immagini con puntamenti/dimensioni
molto diversi, le maschere che appartengono a un'immagine ma cadono fuori da
un'altra non appariranno in quest'ultima.

Per creare una maschera che questo plugin possa leggere, si possono usare i
risultati del plugin ``Drawing`` (premi « Crea maschera » dopo aver disegnato e
salva la maschera usando ``SaveImage``), oltre a creare un file FITS a mano
usando ``astropy.io.fits``, ecc.

Usato insieme a ``TVMark``, puoi sovrapporre in Ginga sia sorgenti puntiformi
sia regioni mascherate.

È personalizzabile usando ``~/.ginga/plugin_TVMask.cfg``, dove ``~`` è la tua
directory HOME:

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
