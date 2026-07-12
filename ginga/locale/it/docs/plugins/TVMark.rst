
Contrassegnare punti da un file (modalità non interattiva) su un'immagine.

**Tipo di plugin: Locale**

``TVMark`` è un plugin locale, il che significa che è associato a un canale.
È possibile aprire un'istanza per ciascun canale.

**Uso**

Questo plugin consente il contrassegno non interattivo di punti di interesse
leggendo un file che contiene una tabella con posizioni RA e DEC di quei punti.
È accettabile qualsiasi file di testo o di tabella FITS leggibile da
``astropy.table``, ma l'utente *deve* definire correttamente i nomi delle
colonne nel file di configurazione del plugin (vedi sotto).  Verrà tentata la
conversione dei valori RA e DEC in gradi.  Se la conversione delle unità
fallisce, si assumerà che siano già in gradi.

In alternativa, se il file ha colonne che contengono le posizioni dirette dei
pixel, puoi leggere queste colonne deselezionando la casella « Usa RADEC ».
Anche qui i nomi delle colonne devono essere definiti correttamente nel file di
configurazione del plugin (vedi sotto).  I valori dei pixel possono essere
indicizzati a 0 o a 1 (cioè se il primo pixel è 0 o 1) ed è configurabile (vedi
sotto).  Questo è utile quando vuoi contrassegnare i pixel fisici
indipendentemente dal WCS (ad es. contrassegnare pixel caldi su un rivelatore).
RA e DEC verranno ancora visualizzati se l'immagine ha informazioni WCS, ma non
influenzeranno i contrassegni.

Per contrassegnare gruppi diversi (ad es. mostrare galassie come cerchi verdi e
lo sfondo come croci ciano, come mostrato sopra):

1. Seleziona cerchio verde dai menu a discesa.  In alternativa, inserisci la
   dimensione o la larghezza desiderata.
2. Assicurati che la casella « Usa RADEC » sia selezionata, se applicabile.
3. Usando il pulsante « Carica coordinate », carica il file che contiene le
   posizioni RA e DEC (o X e Y) *solo* delle galassie.
4. Ripeti il passo 1 ma ora seleziona croce ciano dai menu a discesa.
5. Ripeti il passo 2 ma scegli il file che contiene *solo* le posizioni dello
   sfondo.

Selezionare una voce (o più voci) dall'elenco della tabella evidenzierà il/i
contrassegno/i sull'immagine.  L'evidenziazione usa la stessa forma e lo stesso
colore, ma una linea leggermente più spessa.

Puoi anche evidenziare tutti i contrassegni all'interno di una regione sia
sull'immagine sia nell'elenco della tabella, disegnando un rettangolo
sull'immagine mentre questo plugin è attivo.

Premere il pulsante « Nascondi » nasconderà i contrassegni ma non cancella la
memoria del plugin; ovvero, quando premi « Mostra », gli stessi contrassegni
riappariranno sulla stessa immagine.  Premere « Dimentica », invece, cancellerà
i contrassegni sia dalla visualizzazione sia dalla memoria; ovvero, dovrai
ricaricare il/i file per ricreare i contrassegni.

Per ridisegnare le stesse posizioni con parametri di contrassegno diversi, premi
« Dimentica » e ripeti i passaggi precedenti, secondo necessità.  Tuttavia, se
desideri semplicemente cambiare la larghezza della linea (spessore), premere
« Nascondi » e poi « Mostra » dopo aver inserito il nuovo valore di larghezza
sarà sufficiente.

Se nello stesso canale vengono visualizzate immagini con puntamenti/dimensioni
molto diversi, i contrassegni che appartengono a un'immagine ma cadono fuori da
un'altra non appariranno in quest'ultima.

Per creare una tabella che questo plugin possa leggere, si possono usare i
risultati del plugin ``Pick``, oltre a creare una tabella a mano, usando
``astropy.table``, ecc.

Usato insieme a ``TVMask``, puoi sovrapporre in Ginga sia sorgenti puntiformi
sia regioni mascherate.

È personalizzabile usando ``~/.ginga/plugin_TVMark.cfg``, dove ``~`` è la tua
directory HOME:

.. code-block:: Python

  #
  # TVMark plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_TVMark.cfg"

  # Marking type -- 'circle' or 'cross'
  marktype = 'circle'

  # Marking color -- Any color name accepted by Ginga
  markcolor = 'green'

  # Marking size or radius
  marksize = 5

  # Marking line width (thickness)
  markwidth = 1

  # Specify whether pixel values are 0- or 1-indexed
  pixelstart = 1

  # True -- Use 'ra' and 'dec' columns to extract RA/DEC positions. This option
  #         uses image WCS to convert to pixel locations.
  # False -- Use 'x' and 'y' columns to extract pixel locations directly.
  #          This does not use WCS.
  use_radec = True

  # Columns to load into table listing (case-sensitive).
  # Whether RA/DEC or X/Y columns are used depend on associated GUI selection.
  ra_colname = 'ra'
  dec_colname = 'dec'
  x_colname = 'x'
  y_colname = 'y'
  # Extra columns to display; e.g., ['colname1', 'colname2']
  extra_columns = []
